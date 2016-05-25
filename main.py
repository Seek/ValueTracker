#GUI imports
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import font
#Functional imports
import ssl
import urllib.request
import sqlite3
import threading
import configparser
import os.path
import logging
import queue
from collections import namedtuple
import pdb
import datetime
#Local code
import hs
import copy
import json
# How to pull json from Hearthstone JSON
#  url = "https://api.hearthstonejson.com/v1/latest/enUS/cards.json" // TODO: Add language support
# context = ssl._create_unverified_context()
# req = urllib.request.urlopen(url, context=context)
# f = req.read() // f would contain the json data

CONFIG_FILE = 'config.json'
Card = namedtuple('Card', ['id', 'name','rarity',
                             'cost', 'attack', 'health'])
                         
#SQL statements
sql_select_card_by_id = "SELECT * FROM cards WHERE id LIKE ?"
sql_select_card_by_name = "SELECT * FROM cards WHERE name LIKE ?"
sql_select_deck_by_name = "SELECT name from deck WHERE name LIKE ?"
sql_select_deck_class_by_id = "SELECT class from deck WHERE id = ?"
sql_insert_deck = "INSERT INTO deck (name, class) VALUES(?, ?)"
sql_create_deck = """CREATE TABLE `{0}` (
	`card`	TEXT NOT NULL,
	`num`	INTEGER NOT NULL,
	PRIMARY KEY(card)
)"""
sql_insert_card_into_deck = "INSERT INTO {0} (card, num) VALUES (?,?)"
sql_select_all_decks = "SELECT id,name FROM deck"
sql_select_cards_from_deck = "SELECT * from {0}"
sql_select_card_from_deck = "SELECT * from {0} WHERE card LIKE ?"
sql_update_card_in_deck = "UPDATE {0} SET num = ? WHERE card LIKE ?"
sql_delete_deck = 'DELETE FROM deck WHERE id = ?'
sql_find_opponent = 'SELECT id from player WHERE high = ? AND low = ?'
sql_insert_opponent = 'INSERT INTO player (name, high, low) VALUES(?,?,?)'
sql_select_hero_by_name = 'SELECT id FROM hero WHERE name like ?'
sql_insert_match = """INSERT INTO match 
(opponent, first, won, duration, num_turns, date, opp_hero, player_hero, deck)
VALUES (?,?,?,?,?,?,?,?,?)"""
sql_insert_card = "INSERT INTO card_played (matchid, cardid, turn, local) VALUES(?,?,?,?)"

def card_from_row(row):
    if row is not None:
        return Card(row['id'], row['name'], row['rarity'], 
        row['cost'], row['attack'], row['health'])
    else:
        return None
   
def card_from_id(card_id, cursor):
    results = cursor.execute(r"SELECT * FROM cards WHERE id LIKE ?", (card_id,))
    row = results.fetchone()
    return card_from_row(row)

def load_deck_from_sql(cursor, id):
    sql_str = sql_select_cards_from_deck.format('deck_'+str(id))
    rows = cursor.execute(sql_str).fetchall()
    deck = {}
    for row in rows:
        tmp = cursor.execute(sql_select_card_by_id, (row['card'],)).fetchone()
        card = card_from_row(tmp)
        deck[card.id] = [card, int(row['num'])]
    return deck
    
    
def save_deck_to_sql(cursor, deck, table):
    insert_str = sql_insert_card_into_deck.format(table)
    select_str = sql_select_card_from_deck.format(table)
    update_str = sql_update_card_in_deck.format(table)
    for card in deck.values():
        row = cursor.execute(select_str, ('%' + card[0].id +'%',)).fetchone()
        if row is None:
            cursor.execute(insert_str, (card[0].id, card[1]))
        else:
            cursor.execute(update_str, (card[1],'%' + card[0].id +'%'))
            print('Updated ' + card[0].id + 'to ' + str(card[1]))
           

class DeckCanvas(tk.Canvas):
    def __init__(self, master=None, **kwargs):
        tk.Canvas.__init__(self, master, **kwargs)
        
        # Interactivity
        self.bind("<Button-1>", self._left_click)
        self.bind("<Button-3>", self._right_click)
        #self.bind("<Configure>", self.on_resize)

        self.card_clicked = []
        # Deck options
        self.editable = False
        self.static_deck = {}
        self.active_deck = {}
        self.rarity_to_color = {
            'FREE'      : '#b7c3d2',
            'COMMON'    : '#b7c3d2',
            'RARE'      : '#608bbf',
            'EPIC'      : '#ab60bf',
            'LEGENDARY' : '#bf9b60'
        }
        self.drawn_card_color = '#BBFF8B'
        # Load legendary star
        self.star_image = tk.PhotoImage(file='./star.gif')
        self.tmp = ttk.Label(self, image=self.star_image)
        
        # GUI options TODO: Move to configuration file
        self.outline_font = tk.font.Font(family='Helvetica', size=12, weight='bold')
        self.font = tk.font.Font(family='Helvetica', size=12, weight='bold')
        
        # Given in percentage of the width
        self.name_text_offset_x = 5
        self.cost_text_offset_x = 0
        self.cost_plate_size = 0.12
        self.cost_plate_top_pad = 1
        self.cost_plate_bot_pad = 1
        self.num_text_offset_x = 0
        self.num_plate_size = 0.88
        self.num_plate_top_pad = 1
        self.num_plate_bot_pad  = 1
        self.max_label_size = 30
    
    def get_num_cards(self):
        n = 0
        for val in self.static_deck.values():
            n += val[1]
        return n
        
    def reset_tracking(self):
        self.active_deck = copy.deepcopy(self.static_deck)
        self.refresh_canvas()
    
    def set_deck(self, deck):
        self.static_deck = copy.deepcopy(deck)
        self.active_deck = copy.deepcopy(deck)
        self.refresh_canvas()
        
    def bind_card_clicked(self, func):
        self.card_clicked.append(func)
        
    def unbind_card_clicked(self, func):
        self.card_clicked.remove(func)
        
    def on_resize(self,event):
        self.width = event.width   #>>>854
        self.height = event.height #>>>404
        self['width'] = self.width
        self['height'] = self.height
        #self.refresh_canvas()
        
    def _left_click(self, event):
        if self.editable is True:
            item = self.find_closest(event.x, event.y, halo=None, start=None)
            if item:
                tags = self.gettags(item)
                if tags:
                    for func in self.card_clicked:
                        func(tags[0])
        else:
            return
            
    def _right_click(self, event):
        if self.editable is True:
            pass
        else:
            return

    # These functions are meant to support deck building
    def add_card(self, card):
        # This function expects a Card namedtuple
        if self.editable is True:
            #pdb.set_trace()
            if card.id in self.static_deck:
                # Check if legendary
                if card.rarity == 'LEGENDARY':
                    return
                else:
                    # Check to see if we have  two copies already
                    deck_card = self.static_deck[card.id]
                    if int(deck_card[1]) > 1:
                        return
                    else:
                        # If not add one
                        deck_card[1] =  int(deck_card[1]) + 1
            else:
                # Add the card to the deck
                self.static_deck[card.id] = [copy.deepcopy(card), 1]
            # Copy the deck over
            self.active_deck = copy.deepcopy(self.static_deck)
            # Redraw
            self.refresh_canvas()
        else:
            return
        
    def remove_card(self, card):
        if self.editable is True:
            if card.id in self.static_deck:
                # Check to see if we have  two copies already
                deck_card = self.static_deck[card.id]
                if int(deck_card[1]) > 1:
                    deck_card[1] =  int(deck_card[1]) - 1
                else:
                    # Delete the last one
                    del self.static_deck[card.id]
            else:
                return
            # Copy the deck over
            self.active_deck = copy.deepcopy(self.static_deck)
            # Redraw
            self.refresh_canvas()
        else:
            return
    
    # These functions are an interface for tracking
    def card_drawn(self, card_id):
        if card_id in self.active_deck:
            self.active_deck[card_id][1] -= 1
            items = self.find_withtag(card_id)
            if items:
                # Find the card text
                for item in items:
                    tags = self.gettags(item)
                    print(tags)
                    if 'card_name' in tags:
                        self.itemconfigure(item, fill=self.drawn_card_color)
                    if 'num_text' in tags:
                        self.itemconfigure(item, 
                        text=str(self.active_deck[card_id][1]))
    def card_shuffled(self, card_id):
        if card_id in self.active_deck:
            self.active_deck[card_id][1] += 1
            items = self.find_withtag(card_id)
            if items:
                # Find the card text
                for item in items:
                    tags = self.gettags(item)
                    if 'card_name' in tags and 'drawn2' not in tags:
                        self.itemconfigure(item, fill='white')
                        self.dtag(item, 'drawn1')
                    if 'num_text' in tags:
                        self.itemconfigure(item, 
                        text=str(self.active_deck[card_id][1]))
                    
        
    def card_played(self, card_id):
        items = self.find_withtag(card_id)
        if items:
            # Find the card text
            for item in items:
                tags = self.gettags(item)
                if 'frame_plate' in tags:
                    self.itemconfigure(item, fill='grey25')
        
    def refresh_canvas(self):
        # This is where the magic happens
        height = self.winfo_reqheight()
        width = self.winfo_reqwidth()
        num_cards = len(self.active_deck)
        if num_cards < 1:
            self.delete(tk.ALL)
            return
        frame_height = min(int(height/num_cards), 30)
        # Get the cards in the correct order
        cards_sorted = sorted(self.active_deck.values(), 
                            key = lambda x: (x[0].cost, x[0].name, x[1]))
        # For now we will clear and completely redraw
        self.delete(tk.ALL)
        # Start redrawing
        for i, card in enumerate(cards_sorted):
            # Draw the back plate
            x0 = 0
            y0 = (i)*frame_height
            x1 = width
            y1 = (i+1)*frame_height
            self.create_rectangle(x0, y0, x1, y1,
                                    fill="grey60", width=2, tags=(card[0].id, 'frame_plate'))
            # Draw cost rectangle
            cost_plate_x1 = (width * self.cost_plate_size)
            self.create_rectangle(x0, y0+self.cost_plate_top_pad, 
                        cost_plate_x1,  y1-self.cost_plate_bot_pad,
                        fill=self.rarity_to_color[card[0].rarity], 
                        width=0, tags=(card[0].id))
            
            self.create_line(cost_plate_x1, y0+self.cost_plate_top_pad, 
                        cost_plate_x1,  y1-self.cost_plate_bot_pad,)
                        
            # Draw cost text
            cost_text_x = int(self.cost_plate_size/2 * width)  + self.cost_text_offset_x
            cost_text_y = (y0+y1)/2 # The center of the plate
            self.create_text(cost_text_x, cost_text_y, 
                                text=str(card[0].cost),
                                fill= 'white', anchor=tk.CENTER, font=self.font,
                                tags=(card[0].id, 'cost_text'))
            # Draw the card name
            name_text_x = cost_plate_x1 + self.name_text_offset_x
            name_text_y = (y0+y1)/2 # The center of the plate
            self.create_text(name_text_x, name_text_y, text=card[0].name,
                                fill= 'white', anchor=tk.W, font=self.font,
                                tags=(card[0].id, 'card_name'))
            
            # Draw num  rectangle
            num_plate_x1 = (width * self.num_plate_size)
            self.create_rectangle(num_plate_x1, y0+self.cost_plate_top_pad, 
                        width,  y1-self.cost_plate_bot_pad,
                        fill='grey25', 
                        width=0, tags=(card[0].id))
            
            self.create_line(num_plate_x1, y0+self.cost_plate_top_pad, 
                        num_plate_x1,  y1-self.cost_plate_bot_pad,)
                        
            # Draw num text
            if card[0].rarity != 'LEGENDARY':
                num_text_x = int((self.num_plate_size * width + width)/2)  + self.num_text_offset_x
                num_text_y = (y0+y1)/2 # The center of the plate
                self.create_text(num_text_x, num_text_y, 
                                    text=str(card[1]),
                                    fill= 'gold', anchor=tk.CENTER, font=self.font,
                                    tags=(card[0].id, 'num_text'))
            else:
                num_text_x = int((self.num_plate_size * width + width)/2)  + self.num_text_offset_x
                num_text_y = (y0+y1)/2 # The center of the plate
                self.create_image(num_text_x, num_text_y,
                image=self.star_image,
                tags= (card[0].id,))
                
class FloatingDeckCanvas():
    def __init__(self):
        self.win = tk.Toplevel(background='grey', padx = 4, pady =4)
        self.win.lift()
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.90)
        self.win.attributes("-toolwindow", True)
        self.win.attributes("-transparentcolor", 'grey')
        self.deck_canvas = DeckCanvas(self.win, background='grey',
        highlightthickness=0, width=250, height=450)
        self.deck_canvas.pack(fill=tk.BOTH, expand=tk.TRUE)
        self.win.update_idletasks()
        self.win.overrideredirect(True)
        self._offsetx = 0
        self._offsety = 0
        self.win.bind('<Button-1>',self.clickwin)
        self.win.bind('<B1-Motion>',self.dragwin)
    def dragwin(self,event):
        x = self.win.winfo_pointerx() - self._offsetx
        y = self.win.winfo_pointery() - self._offsety
        self.win.geometry('+{x}+{y}'.format(x=x,y=y))

    def clickwin(self,event):
        self._offsetx = event.x
        self._offsety = event.y


        
class HeroClassListbox(tk.Listbox):
        def __init__(self, master, *args, **kwargs):
            tk.Listbox.__init__(self, master,  height=9)
            vals = list(hs.hero_dict.values())
            for v in vals:
                self.insert(tk.END, v)
                
                
class DeckBuilderCardEntry(ttk.Entry):
    """ Requires a working database cursor to work """
    def __init__(self, parent, cursor, deckcanvas, **kwargs):
        ttk.Entry.__init__(self, parent, **kwargs)
        self.var = self['textvariable']
        self.parent = parent
        self.cursor = cursor
        self.deckcanvas = deckcanvas
        if self.var == '':
            self.var = self['textvariable'] = tk.StringVar()

        self.var.trace('w', self.changed)

    def changed(self, name, index, mode):  
        words = self.comparison()
        deck = {}
        if words:
            for word in words:
                deck[word['id']] = [card_from_row(word), 1]
            self.deckcanvas.set_deck(deck)
        else:
            self.deckcanvas.set_deck({})
                

    def comparison(self):
        search = '%'+self.var.get()+'%'
        results = self.cursor.execute(r"SELECT * FROM cards WHERE name LIKE ?", (search,))
        rows = results.fetchmany(20)
        return rows
                                
class DeckCreator(ttk.Frame):
    def __init__(self, cursor, master=None):
        # Initialize
        ttk.Frame.__init__(self, master, width= 800, height = 600)
        self.pack(fill=tk.BOTH, expand=1)
        self.cursor = cursor
        self.master = master
        self._create_widgets()
        self.update_deck = False
        self.deck_id = None
        
    def _create_widgets(self):
        f1 = ttk.Frame(self, width = 400, height = 600)
        f1.pack(side = tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        f2 = ttk.Frame(self, width = 400)
        f2.pack(side = tk.RIGHT, fill=tk.BOTH, expand=tk.TRUE)
        #f1.rowconfigure(1, weight=1)
        self._entry_canvas = DeckCanvas(f1, width = 500, height = 500)
        self._static_canvas = DeckCanvas(f2, width = 500, height = 500)
        self._entry_canvas.editable = True
        self._static_canvas.editable = True
        self._entry_canvas.bind_card_clicked(self.add_card)
        self._static_canvas.bind_card_clicked(self.remove_card)
        self._card_entry = DeckBuilderCardEntry(f1, self.cursor, self._entry_canvas)
        ttk.Label(f1, text='Enter Card Name:').pack(fill=tk.X, expand=0)
        self._card_entry.pack(fill=tk.X, expand = tk.FALSE)
        self._entry_canvas.pack(fill=tk.BOTH, expand=tk.TRUE)
        self._static_canvas.pack(fill=tk.BOTH, expand=tk.TRUE)
        self._num_cards_text = tk.StringVar()
        
        self._num_cards_text.set('Number of cards: {0}'.format(len(self._static_canvas.static_deck)))
        self._num_cards_label = ttk.Label(f2, textvariable=self._num_cards_text).pack(fill=tk.X, expand=0)
        
        ttk.Label(f2, text='Select a class:').pack(fill=tk.X, expand=0)
        self._deck_name_entry = ttk.Entry(f2)
        self._hero_class_list = HeroClassListbox(f2)
        self._hero_class_list.pack(fill=tk.X, expand=0)
        ttk.Label(f2, text='Enter Deck Name:').pack(fill=tk.X, expand=0)
        self._deck_name_entry.pack(fill=tk.X, expand=0)
        self._save_deck_btn = ttk.Button(f2, text = 'Save', command= self._btn_save)
        self._save_deck_btn.pack(fill=tk.X, expand=0)
        
    def update_num_cards(self):
        self._num_cards_text.set('Number of cards: {0}'.format(self._static_canvas.get_num_cards()))
        
    def _btn_save(self):
        if len(self._static_canvas.static_deck) > 30:
            print('Too many cards')
            return
        elif len(self._static_canvas.static_deck) < 1:
            print('Too few cards')
            return
        elif self._deck_name_entry.get() == '' and self.update_deck is False:
            print('No name given')
            return
        elif len(self._hero_class_list.curselection()) < 1 and self.update_deck is False:
            print('No class selected')
            return
        elif self.update_deck is True:
            table_name = 'deck_' + str(self.deck_id)
            save_deck_to_sql(self.cursor, self._static_canvas.static_deck, table_name)
            return
        else:
            # Write to db
            item = self._hero_class_list.curselection()[0]
            herostr = self._hero_class_list.get(item)
            heronum = hs.hero_dict_names[herostr]
            deck = self.cursor.execute(sql_select_deck_by_name, 
                        ('%' + self._deck_name_entry.get() +'%',)).fetchone()
            if deck is not None:
                print('Deck with that name already exists')
                return
            else:
                self.cursor.execute(sql_insert_deck, (self._deck_name_entry.get(),heronum))
                deckid = self.cursor.lastrowid
                table_name = 'deck_' + str(deckid)
                self.cursor.execute(sql_create_deck.format(table_name))
                save_deck_to_sql(self.cursor, self._static_canvas.static_deck, table_name)
                return
    
    def add_card(self, card_id):
        results = self.cursor.execute(r"SELECT * FROM cards WHERE id LIKE ?", (card_id,))
        row = results.fetchone()
        card = card_from_row(row)
        if card is not None:
            self._static_canvas.add_card(card)
            self._num_cards_text.set('Number of cards: {0}'.format(self._static_canvas.get_num_cards()))

    def remove_card(self, card_id):
        results = self.cursor.execute(r"SELECT * FROM cards WHERE id LIKE ?", (card_id,))
        row = results.fetchone()
        card = card_from_row(row)
        if card is not None:
            self._static_canvas.remove_card(card)
            self._num_cards_text.set('Number of cards: {0}'.format(self._static_canvas.get_num_cards()))

# # A deck will just be a dictionary with the value being 
# class DeckTreeview(ttk.Treeview):
#     def __init__(self, master, cursor, *args, **kwargs):
#         ttk.Treeview.__init__(self, master, 
#                             columns=('cost', 'name', 'num'), 
#                             displaycolumns=('cost name num'),
#                             show = 'headings')
#         self.cursor = cursor
#         self.column("name", width=150)
#         self.column("num", width=15)
#         self.column("cost", width=15)
#         self.heading("name", text="Name")
#         self.heading("num", text="#")
#         self.heading("cost", text='Cost')
#         self.bind("<Double-1>", self._on_double_click)
#         self.tag_configure('common', background='gray')
#         self.tag_configure('played', background='dim gray')
#         self.tag_configure('drawn', foreground = 'OliveDrab4')
#         self.tag_configure('rare', background='blue')
#         self.tag_configure('epic', background='purple')
#         self.tag_configure('legend', background='goldenrod')
#         self.enable_building = True
#         #self.reset_view()
#         self.deck = {}
    
#     def set_deck(self, deck):
#         self.reset_view()
        
#     def _on_double_click(self, event):
#         if self.enable_building == True:
#             sel = self.selection()
#             if len(sel) > 0:
#                 item = self.selection()[0]
#                 self.remove_card(item)
        
#     def add_card(self, card):
#         if card not in self.deck:
#             c = self.cursor.execute(sql_select_card_by_id, ('%' + card +'%',)).fetchone()
#             if c is not None:
#                 cc = card_from_row(c)
#                 self.deck[card] = [cc, 1]
#                 #Update display
#                 self.insert('', 'end', cc.id, values=(str(cc.cost), cc.name, '1'))
#                 return
#         else:
#             cc = self.deck[card][0]
#             n = self.deck[card][1]
#             if n < 2:
#                 self.deck[card][1] += 1
#                 self.item(cc.id, values=(cc.cost, cc.name, '2'))
#                 return
#         return
        
#     def remove_card(self, card):
#         if card in self.deck:
#             cc = self.deck[card][0]
#             n = self.deck[card][1]
#             if n > 1:
#                 self.deck[card][1] -= 1
#                 self.item(cc.id, values=(cc.cost, cc.name, '1'))
#             else:
#                 self.delete(card)
        
#     def card_played(self, card):
#         if card in self.deck:
#             if self.tag_has('played', card) is 1:
#                 values = self.item(card, 'values')
#                 self.item(card, values=(values[0], values[1], str(int(values[2])-1)))
#                 return
#             else:
#                 tags = self.item(card, 'tags')
#                 tags= [tags, 'played']
#                 self.item(card, tags=tags)
#                 values = self.item(card, 'values')
#                 self.item(card, values=(values[0], values[1], str(int(values[2])-1)))
#                 return
        
#     def card_drawn(self, card):
#         if card in self.deck:
#             if self.tag_has('drawn', card) is 1:
#                 return
#             else:
#                 tags = self.item(card, 'tags')
#                 tags= [tags, 'drawn']
#                 self.item(card, tags=tags)
#                 return
            
#     def card_shuffled(self, card):
#         if card in self.deck:
#             print(card)
#             print(self.tag_has('drawn', card))
#             if self.tag_has('drawn', card) is 1:
#                 print(card + 'was drawn')
#                 tags = self.item(card, 'tags')
#                 print(tags)
#                 new_tags = []
#                 for tag in tags:
#                     if tag == 'drawn':
#                         continue
#                     else:
#                         new_tags.append(tag)
#                 print(new_tags)
#                 self.item(card, tags=new_tags)
#                 return
#             else:
#                 return
        
#     def reset_view(self):
#         self.delete(*self.get_children())
#         c_sorted = sorted(self.deck.values(), key = lambda x: (x[0].cost, x[0].name, x[1]))
#         for val in c_sorted:
#             card = val[0]
#             n = val[1]
#             self.insert("", 'end', card.id, values=(str(card.cost), card.name, str(n)))
#             self.item(card.id, tags='')
        
#     def get_num_cards(self):
#         i = 0
#         for v in self.deck.values():
#             i += v[1]
#         return i

# class DeckCreator(ttk.Frame):
#     def __init__(self, cursor, master=None):
#         # Initialize
#         ttk.Frame.__init__(self, master, width= 800, height = 600)
#         self.pack(fill=tk.BOTH, expand=1)
#         self.cursor = cursor
#         self.master = master
#         self._create_widgets()
#         self.update_deck = False
#         self.deck_id = None

#     def _create_widgets(self):
#         frame = ttk.Label(self, text='Select a class:')
#         frame.pack(fill=tk.X, expand=0)
#         self._hero_class_list = HeroClassListbox(self)
#         self._hero_class_list.pack(fill=tk.X, expand=0)
#         frame = ttk.Label(self, text='Enter Card Name:')
#         frame.pack(fill=tk.X, expand=0)
#         self._card_entry = hs.AutocompleteCardEntry(self, self.cursor)
#         self._card_entry.pack(fill=tk.X, expand=0)
#         self._card_entry.bind_card_cb(self._card_picked)
#         self._deck_treeview = DeckTreeview(self, self.cursor)
#         self._deck_treeview.pack(fill=tk.BOTH, expand=1)
#         frame = ttk.Label(self, text='Enter Deck Name:')
#         frame.pack(fill=tk.X, expand=0)
#         self._deck_name_entry = ttk.Entry(self)
#         self._deck_name_entry.pack(fill=tk.X, expand=0)
#         self._save_deck_btn = ttk.Button(self, text = 'Save', command= self._btn_save)
#         self._save_deck_btn.pack(fill=tk.X, expand=0)
    
#     def _btn_save(self):
#         if self._deck_treeview.get_num_cards() > 30:
#             print('Too many cards')
#             return
#         elif self._deck_name_entry.get() == '' and self.update_deck is False:
#             print('No name given')
#             return
#         elif len(self._hero_class_list.curselection()) < 1 and self.update_deck is False:
#             print('No class selected')
#             return
#         elif self.update_deck is True:
#             table_name = 'deck_' + str(self.deck_id)
#             save_deck_to_sql(self.cursor, self._deck_treeview.deck, table_name)
#             return
#         else:
#             # Write to db
#             item = self._hero_class_list.curselection()[0]
#             herostr = self._hero_class_list.get(item)
#             heronum = hs.hero_dict_names[herostr]
#             deck = self.cursor.execute(sql_select_deck_by_name, 
#                         ('%' + self._deck_name_entry.get() +'%',)).fetchone()
#             if deck is not None:
#                 print('Deck with that name already exists')
#                 return
#             else:
#                 self.cursor.execute(sql_insert_deck, (self._deck_name_entry.get(),heronum))
#                 deckid = self.cursor.lastrowid
#                 table_name = 'deck_' + str(deckid)
#                 self.cursor.execute(sql_create_deck.format(table_name))
#                 save_deck_to_sql(self.cursor, self._deck_treeview.deck, table_name)
#                 return
        
#     def _card_picked(self, card):
#         cards = self.cursor.execute(sql_select_card_by_name, ('%' + card +'%',)).fetchall()
#         if cards is not None:
#             for c in cards:
#                 if c['name'] == card:
#                     self._deck_treeview.add_card(c['id'])

class Application(ttk.Frame):
    def __init__(self, master=None):
        # Initialize
        ttk.Frame.__init__(self, master)
        self.master = master
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        #Get our configuation and set up logging
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')

        #Initialize the gui
        self._init_database()
        self._create_widgets()
        self._create_menu()
        self.load_settings()
        self._start_tracking_thread()
        self._update_gui()
        self._refresh_deck_list()
        self._reset_game_state()
        self.active_deck = None
        
    def load_settings(self):
        self.config = {}
        if os.path.isfile(CONFIG_FILE) is False:
            logging.warn('{0} is missing, falling back on defaults'.format(CONFIG_FILE))
        else:
            with open(CONFIG_FILE, 'r') as file:
                self.config = json.load(file)
        # Restore the old window 
        if 'main_window_geom' in self.config:
            last_geom = self.config["main_window_geom"]
            self.master.geometry(last_geom)
        if 'local_deck_geom' in self.config:
            last_geom = self.config["local_deck_geom"]
            self._deck_tracker.win.geometry(last_geom)
        if 'foreign_deck_geom' in self.config:
            last_geom = self.config["foreign_deck_geom"]
            self._foreign_deck_tracker.win.geometry(last_geom)
        
        
    def save_settings(self):
        self.config['main_window_geom'] = self.master.geometry()
        self.config['local_deck_geom'] = self._deck_tracker.win.geometry()
        self.config['foreign_deck_geom'] = self._foreign_deck_tracker.win.geometry()
        with open(CONFIG_FILE, 'w') as file:
            json.dump(self.config, file)
        
    def on_close(self):
        self.save_settings()
        self._end_tracking_thread()
        self.db.commit()
        self.cursor.close()
        self.db.close()
        self.master.destroy()
        
        
    def _create_widgets(self):
        self._create_notebook()

    def _create_menu(self):
        menubar = tk.Menu(self.master)
        self.master['menu'] = menubar
        menu_file = tk.Menu(menubar)
        menu_edit = tk.Menu(menubar)
        menu_file.add_separator()
        menubar.add_cascade(menu=menu_file, label='File')
        menubar.add_cascade(menu=menu_edit, label='Edit')
        menu_file.add_command(label='Exit', command=self._menu_exit)
        menu_edit.add_command(label='Preferences', command=self._menu_exit)
        
    def _menu_exit(self):
        self.master.quit()
        
    def _empty(self):
        pass
        
    def _create_notebook(self):
        self._notebook = ttk.Notebook(master=self, height=800, width=1200)
        self._deck_frame = ttk.Frame(self._notebook)
        self._stats_frame = ttk.Frame(self._notebook)
        self._data_frame = ttk.Frame(self._notebook)
        self._card_stats_frame = ttk.Frame(self._notebook)
        self._debug_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._deck_frame, text = 'Decks')
        self._notebook.add(self._stats_frame, text = 'Statistics')
        self._notebook.add(self._data_frame, text = 'Data')
        self._notebook.add(self._card_stats_frame, text = 'Card Statistics')
        self._notebook.add(self._debug_frame, text = 'Debug')
        self._notebook.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        #Set up resizing
        self._notebook.columnconfigure(0, weight=1)
        self._notebook.rowconfigure(0, weight=1)
        self._debug_frame.columnconfigure(0, weight=1)
        self._debug_frame.rowconfigure(0, weight=1)
        self._deck_frame.columnconfigure(0, weight=1)
        self._deck_frame.rowconfigure(0, weight=1)
        self._card_stats_frame.columnconfigure(0, weight=1)
        self._card_stats_frame.rowconfigure(0, weight=1)
        #Create each interface
        self._create_debug_frame()
        self._create_card_stats_frame()
        self._create_deck_frame()
        
    def _create_debug_frame(self):
        pw = ttk.PanedWindow(self._debug_frame, orient=tk.HORIZONTAL)
        pw.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        pw.columnconfigure(0, weight=1)
        pw.rowconfigure(0, weight=1)
        f1 = ttk.LabelFrame(pw, text='Game State')
        #f2 = ttk.LabelFrame(pw,text='Debug Output')
        self._debug_tree = ttk.Treeview(f1)
        self._debug_tree.pack(fill=tk.BOTH, expand=1)
        self._debug_text = tk.scrolledtext.ScrolledText(pw)
        self._debug_text.pack(fill=tk.BOTH, expand=1)
        pw.add(f1)
        pw.add(self._debug_text)
        
    def _create_card_stats_frame(self):
        self._card_stats_entry = hs.AutocompleteCardEntry(self._card_stats_frame,
        self.cursor)
        self._card_stats_entry.grid(column=0, row=0, sticky=(tk.N,tk.W))
        
    def _create_deck_frame(self):
        pw = ttk.PanedWindow(self._deck_frame, orient=tk.HORIZONTAL)
        pw.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        pw.columnconfigure(0, weight=1)
        pw.rowconfigure(0, weight=1)
        f1 = ttk.LabelFrame(pw, text='Decks')
        f2 = ttk.LabelFrame(pw,text='Tracking')
        self._deck_new_btn = ttk.Button(f1, text="New Deck", command=self._deck_new)
        self._deck_new_btn.pack(fill=tk.X)
        self._deck_edit_btn = ttk.Button(f1, text="Edit Deck", command=self._deck_edit)
        self._deck_edit_btn.pack(fill=tk.X)
        self._deck_del_btn = ttk.Button(f1, text="Delete Deck", command=self._deck_del)
        self._deck_del_btn.pack(fill=tk.X)
        self._deck_tree = ttk.Treeview(f1, columns=('cls', 'name', 'tags'), displaycolumns=('cls name tags'), show='headings')
        #self._deck_tree.column("#0", width=10)
        self._deck_tree.bind("<Double-1>", self._deck_list_dbl_click)
        self._deck_tree.column("cls", width=50)
        self._deck_tree.column("name", width=100)
        self._deck_tree.column("tags", width=50)
        self._deck_tree.heading("cls", text="Class")
        self._deck_tree.heading("name", text="Name")
        self._deck_tree.heading("tags", text="Tags")
        self._deck_tree.pack(fill=tk.BOTH, expand=1)
        pw2 = ttk.PanedWindow(f2, orient=tk.HORIZONTAL)
        pw2.pack(fill=tk.BOTH, expand=1)
        # window = tk.Toplevel()
        # window.lift()
        # window.attributes("-topmost", True)
        # window.attributes("-alpha", 0.90)
        
        #window.overrideredirect(1) #Remove border
        #window.call('wm', 'attributes', '.', '-topmost', '1')
        self._deck_tracker = FloatingDeckCanvas()
        self._foreign_deck_tracker = FloatingDeckCanvas()
        self._deck_treeview = self._deck_tracker.deck_canvas
        #self._deck_treeview = DeckCanvas(window, width=400, height= 800)
        self._deck_treeview.pack(fill=tk.BOTH, expand=tk.TRUE)
        self._deck_treeview.editable = False
        #self._deck_treeview.pack(fill=tk.BOTH, expand=1)
        self._oppon_deck_treeview = self._foreign_deck_tracker.deck_canvas
        self._oppon_deck_treeview.editable = True
        # self._deck_treeview.add_card('BRM_002')
        # self._deck_treeview.card_drawn('BRM_002')
        # self._deck_treeview.card_played('BRM_002')
        pw.add(f1)
        pw.add(f2)
    
    def _init_database(self):
        self.db = sqlite3.connect('stats.db')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
    
    def _start_tracking_thread(self):
        self._q = queue.Queue()
        self._exit_flag = threading.Event()
        path = r'C:\Program Files (x86)\Hearthstone\Logs\Power.log'
        self._tracking_thread = threading.Thread(target=hs.thread_func, 
        args=(path, self._exit_flag, self._q))
        self._tracking_thread.start()
    
    def _end_tracking_thread(self):
        self._exit_flag.set()
        self._tracking_thread.join()
    
    def _update_gui(self):
        try:
            while 1:
                tmp = self._q.get_nowait()
                self._handle_event(tmp)
                self.update_idletasks()
        except queue.Empty:
            pass
        self.after(100, self._update_gui)
        
    def _check_db_exists(self):
        return os.path.isfile()

    def _handle_event(self, event):
        etype = event[0]
        data = event[1]
        if etype == hs.EventType.CardPlayed:
            if data.player == self.players['local'].id:
                self._debug_text.insert(tk.END, 
                'The local player just played {0} on turn {1}\n'.format(data.cardId, data.turn), 
                (None,))
                self._deck_treeview.card_played(data.cardId)
            else:
                self._debug_text.insert(tk.END, 
                'The foreign player just played {0} on turn {1}\n'.format(data.cardId, data.turn), 
                (None,))
                tmp_card = card_from_id(data.cardId, self.cursor)
                if tmp_card is not None:
                    self._oppon_deck_treeview.add_card(tmp_card)
            self._debug_text.see(tk.END)
            self.cards_played.append(data)
            return
        elif etype == hs.EventType.CardDrawn:
            self._debug_text.insert(tk.END, 
            'The local player just drew {0} on turn {1}\n'.format(data.cardId, data.turn), 
            (None,))
            self._deck_treeview.card_drawn(data.cardId)
            return
        elif etype == hs.EventType.CardShuffled:
            self._debug_text.insert(tk.END, 
            'The local player just shuffled {0}\n'.format(data.cardId), 
            (None,))
            self._deck_treeview.card_shuffled(data.cardId)
            return
        elif etype == hs.EventType.GameEnd:
            self._debug_text.insert(tk.END, 
            'The game just ended\n', 
            (None,))
            self._write_game(data)
            return
        elif etype == hs.EventType.GameStart:
            self.players = data.players
            local = self.players['local']
            foreign = self.players['foreign']
            self._debug_text.insert(tk.END, 
            'The local player is {0} [id = {1}]\n'.format(local.name, local.id),
            (None,))
            self._debug_text.insert(tk.END, 
            'The foreign player is {0} [id = {1}]\n'.format(foreign.name, foreign.id),
            (None,))
            return
        else:
                return
    def _deck_new(self):
        win = tk.Toplevel(takefocus=True)
        dc = DeckCreator(self.cursor, master=win)
        self.wait_window(win)
        self.db.commit()
        #Refresh deck list
        self._refresh_deck_list()
        
    def _write_game(self, gameoutcome):
        # Check if we have seen the opponent before
        local = self.players['local']
        foreign = self.players['foreign']
        oppid = self.cursor.execute(sql_find_opponent, (foreign.high, foreign.low)).fetchone()
        if oppid is None:
            self.cursor.execute(sql_insert_opponent, (foreign.name,foreign.high, foreign.low))
            oppid = self.cursor.lastrowid
        else:
            oppid = oppid['id']
        if self.active_deck is not None:
            #We now have the player id, so we can write the match information
            # First we need to get the correct hero information
            local_hero = self.cursor.execute(sql_select_hero_by_name, 
                            ('%' + local.hero_name + '%',)).fetchone()
            foreign_hero = self.cursor.execute(sql_select_hero_by_name, 
                            ('%' + foreign.hero_name + '%',)).fetchone()
            # submit the data                
            date = datetime.datetime.now()
            
            sql_data = (oppid, gameoutcome.first, gameoutcome.won, 
            gameoutcome.duration, int(gameoutcome.turns),
            date, foreign_hero['id'], local_hero['id'], self.active_deck)
            self.cursor.execute(sql_insert_match, sql_data)
            matchid = self.cursor.lastrowid
            
            #submit the cards
            for card in self.cards_played:
                local_player = False
                if card.player == local.id:
                    local_player = True
                self.cursor.execute(sql_insert_card, (matchid,
                                card.cardId, card.turn, local_player))
        self.db.commit()
        self._reset_game_state()
        

    def _reset_game_state(self):
        self.cards_played = []
        self._deck_treeview.reset_tracking()
        self._oppon_deck_treeview.set_deck({})
        self.players = None
        
    def _refresh_deck_list(self):
        rows = self.cursor.execute(sql_select_all_decks).fetchall()
        if rows is not None:
            self._deck_tree.delete(* self._deck_tree.get_children())
            for row in rows:
                self._deck_tree.insert('', 'end', row['id'], 
                values=('', row['name'], ''))
                
    def _deck_list_dbl_click(self, event):
        #Load the deck for the tracker
        sel = self._deck_tree.selection()
        if len(sel) > 0:
            item = self._deck_tree.selection()[0]
            self._deck_treeview.set_deck(load_deck_from_sql(self.cursor, item))
            self.active_deck = item
        return
    
    def _deck_del(self):
        sel = self._deck_tree.selection()
        if len(sel) > 0:
            item = self._deck_tree.selection()[0]
            result = tk.messagebox.askyesno("Delete Deck?","Are you sure you want to delete?")
            if result is True:
                self.cursor.execute(sql_delete_deck, (item,))
                self._refresh_deck_list()
                return
            else:
                return
    def _deck_edit(self):
        sel = self._deck_tree.selection()
        if len(sel) > 0:
            item = self._deck_tree.selection()[0]
            win = tk.Toplevel(takefocus=True)
            dc = DeckCreator(self.cursor, master=win)
            dc.update_deck = True
            dc.deck_id = item
            dc._static_canvas.set_deck(load_deck_from_sql(self.cursor, item))
            dc.update_num_cards()
            dc._hero_class_list.get(0)
            dc._hero_class_list.selection_set
            self.wait_window(win)
            dc.update_deck = False
            dc.deck_id = None
            self.db.commit()
            #Refresh deck list
            self._refresh_deck_list()
        return

root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()