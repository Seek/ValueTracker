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
import PIL
from PIL import Image, ImageFont, ImageDraw, ImageColor, ImageTk
import re

CLASS_IMAGES = [Image.open('./images/tbl_{0}.png'.format(n)) for n in range(0,10)]
CLASS_IMAGES_64 = [im.resize((64,64), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
CLASS_IMAGES_32 = [im.resize((32,32), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
CLASS_IMAGES_24 = [im.resize((24,24), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
CLASS_IMAGES_16 = [im.resize((16,16), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
SEL_HILITE = Image.open('./images/sel_highlight.png')
SEL_HILITE_32 = SEL_HILITE.resize((32,32), PIL.Image.LANCZOS)

class DeckSelectWidget(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        ttk.Frame.__init__(self, master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        yscrollbar = tk.Scrollbar(self)
        yscrollbar.grid(row=0, column=1, sticky='nse')
        
        self.canvas = tk.Canvas(self, width = self['width'], height = self['height'],
                                bd = 0, highlightthickness=0,
                                yscrollcommand=yscrollbar.set,
                                scrollregion=(0, 0, self['width'], 1000))
        
        self.canvas.grid(column=0, row=0, sticky='nswe')
        yscrollbar.config(command=self.canvas.yview)
        #self.canvas['bg'] = 'black'
        # Setup 2 rows 
        self.images = [ImageTk.PhotoImage(im) for im in CLASS_IMAGES_32]
        self.canvas.bind('<Button-1>', self._canvas_clicked)
        self.active_deck = None
        self.hilite = ImageTk.PhotoImage(SEL_HILITE_32)
        self.on_deck_selected = []
        
    def set_deck_list(self, decks):
        """Decks should be a list opf dict like objects with keys name and player_class an integer"""
        self.canvas.delete(tk.ALL)
        i = 0
        for deck in decks:
            name = deck['name']
            pc = deck['class']
            id = deck['id']
            self.canvas.create_image(0, i * 32,  image=self.images[pc], tags=(id, pc, 'image_{0}'.format(id),), anchor=tk.NW)
            self.canvas.create_text(34, ((i  * 32) + (i+1)*32)/2,  text=name, tags=(id, pc,), anchor=tk.W)
            i += 1
            
    def _canvas_clicked(self, event):
        item = self.canvas.find_closest(event.x, event.y, halo=None, start=None)
        if item:
            tags =  self.canvas.gettags(item)
            if tags:
                id = tags[0]
                if id == self.active_deck:
                    self.active_deck = None
                    self.canvas.delete(self.canvas.find_withtag('hilite'))
                    for f in self.on_deck_selected:
                        f(None)
                else:
                    self.canvas.delete(self.canvas.find_withtag('hilite'))
                    im = self.canvas.find_withtag('image_{0}'.format(id))
                    x, y = self.canvas.coords(im)
                    self.canvas.create_image(x,y,  image=self.hilite, tags=(id,'hilite',), anchor=tk.NW)
                    self.active_deck = id
                    for f in self.on_deck_selected:
                        f(id)
            
class PlayerClassWidget(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        ttk.Frame.__init__(self, master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        self['width'] = 32 * 5
        self['height'] = 32 * 2
        self.canvas = tk.Canvas(self, width = self['width'], height = self['height'],
                                bd = 0, highlightthickness=0)
        self.canvas.grid(column=0, row=0, sticky='nswe')
        # Setup 2 rows 
        self.images = [ImageTk.PhotoImage(im) for im in CLASS_IMAGES_32]
        self.hilite = ImageTk.PhotoImage(SEL_HILITE_32)
        self.active_playerclass = 0
        for i in range(0,5):
            lbl_top = self.canvas.create_image(32* i, 0,  image=self.images[i], tags=(i,), anchor=tk.NW)
            lbl_top = self.canvas.create_image(32* i, 32,  image=self.images[i+5], tags=(i+5,), anchor=tk.NW)
        self.canvas.bind('<Button-1>', self._canvas_clicked)
        
        self.on_class_selected = []
        
    def _canvas_clicked(self, event):
        item = self.canvas.find_closest(event.x, event.y, halo=None, start=None)
        if item:
            tags =  self.canvas.gettags(item)
            if tags:
                i = int(tags[0])
                if self.active_playerclass == i:
                    self.canvas.delete(self.canvas.find_withtag('hilite'))
                    self.active_playerclass = 0
                    for f in self.on_class_selected:
                        f(0)
                    return
                elif i == 0:
                    self.canvas.delete(self.canvas.find_withtag('hilite'))
                    self.active_playerclass = 0
                    for f in self.on_class_selected:
                        f(0)
                else:
                    self.canvas.delete(self.canvas.find_withtag('hilite'))
                    self.active_playerclass = i
                    if i < 5:
                        self.canvas.create_image(32* i, 0,  image=self.hilite, tags=(i, 'hilite', ), anchor=tk.NW)
                    else:
                        self.canvas.create_image(32* (i-5), 32,  image=self.hilite, tags=(i, 'hilite', ), anchor=tk.NW)
                    for f in self.on_class_selected:
                        f(i)


class ResizeableCanvas(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        ttk.Frame.__init__(self, master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0,
                        width = self['width'],
                        height = self['height'])
        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.canvas['bg'] = 'white'
        self.bind("<Configure>", self.on_configure)
        
    def on_configure(self, event):
        self.canvas['width'] = event.width
        self.canvas['height'] = event.height
        self.refresh_canvas()
        
    def refresh_canvas(self):
        pass
        
class DeckStatsCanvas(ResizeableCanvas):
    def __init__(self, cursor, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.active_deck = None
        self.cursor = cursor
        self.row_height = 20
        self.font = tk.font.Font(family='Helvetica', size=10, weight = 'bold')
        self.grid_color = "#84aad9"
        self.column1_x = 0
        self.column2_x = 0.2
        self.column3_x = 0.4
        self.column4_x = 0.6
        self.column5_x = 0.8
        self.class_images = {}
        self.icon_size = 16
        self.class_images = [ImageTk.PhotoImage(im) for im in CLASS_IMAGES_16]
        
        
    def set_deck(self, deck_id):
        self.active_deck = deck_id
        self.refresh_canvas()
        
    def refresh_canvas(self):
        from math import sqrt
        num_rows = 0
        width = self.canvas.winfo_reqwidth()
        height = self.canvas.winfo_reqheight()
        data = {}
        for i in range(1,10):
            tmp = self.cursor.execute("SELECT id FROM hero WHERE class = ?", (i,)).fetchall()
            hero_ids = [x['id'] for x in tmp]
            if self.active_deck is not None:
                query = "SELECT * FROM match WHERE deck = ? AND ("
            else:
                query = "SELECT * FROM match WHERE "
            for id in hero_ids:
                query += "opp_hero = {0} OR ".format(id)
            query = query[:-4]
            if self.active_deck is not None:
                query += ")"
            logging.info("Executing query %s", query)
            if self.active_deck is not None:
                tmp = self.cursor.execute(query, (self.active_deck,)).fetchall()
            else:
                tmp = self.cursor.execute(query).fetchall()
            data[i] = tmp
        width = self.canvas.winfo_reqwidth()
        height = self.canvas.winfo_reqheight()
        # Draw the header row
        mean_row_y = self.row_height/2
            
        self.canvas.create_rectangle(0,0, width, self.row_height, 
                        fill = 'grey75', width = 0)
        #Draw bottom of row
        id = self.canvas.create_line(0,self.row_height, width, self.row_height, 
                            fill = 'grey65', tags=('grid_line_bot',)) # Top
        self.canvas.tag_raise('grid_line_bot')
        
        self.canvas.create_text(self.column1_x * width + 20, mean_row_y,
                anchor=tk.W, text = "Opponent", font=self.font
        )
        
        self.canvas.create_text(self.column2_x * width + 5, mean_row_y,
                anchor=tk.W, text = "Wins/Losses", font=self.font
        )
        
        self.canvas.create_text(self.column3_x * width - 10, mean_row_y,
                anchor=tk.W, text = "Win Rate (95% CI)", font=self.font,
        )
        self.canvas.create_text(self.column4_x * width - 10, mean_row_y,
                anchor=tk.W, text = 'Mean Duration', font=self.font,
        )
        self.canvas.create_text(self.column5_x * width, mean_row_y,
                anchor=tk.W, text = 'Mean # of Turns', font=self.font,
        )
        total_wins = 0
        total_losses = 0
        total_turns = 0
        total_duration = 0
        total_n = 0
        for i in range(1,10):
            tmp = data[i]
            wins = sum(1 for row in tmp if row['won'] == 1)
            total_wins += wins
            total = len(tmp)
            total_n += total
            losses = total - wins
            # Calc
            row_top_y = (i)*self.row_height
            row_bottom_y = (i+1)*self.row_height
            mean_row_y = (row_top_y + row_bottom_y)/2
            
            color = 'white'
            if i % 2 == 0:
                color = 'grey85'
                
            self.canvas.create_rectangle(0,row_top_y, width, row_bottom_y, 
                            fill = color, width = 0)
            
            
            #Draw bottom of row
            id = self.canvas.create_line(0,row_bottom_y, width, row_bottom_y, 
                                fill = self.grid_color, tags=('grid_line_bot',)) # Top
            self.canvas.tag_raise('grid_line_bot')
            self.canvas.create_image(self.column1_x * width, mean_row_y,
                    anchor=tk.W, image= self.class_images[i]
            )
            
            self.canvas.create_text(self.column1_x * width + 20, mean_row_y,
                    anchor=tk.W, text = hs.hero_dict[i], font=self.font
            )
            
            self.canvas.create_text(self.column2_x * width + 20, mean_row_y,
                    anchor=tk.W, text = "{0}/{1}".format(wins, losses), font=self.font
            )
            winrate = 'N/A'
            dur = "N/A"
            turns = "N/A"
            if total > 0:
                wr = wins/total
                pm = 1.96*((wr*(1-wr))/total)**(1/2)
                winrate = "[{0:.2f}, {1:.2f}]".format(wr-pm, wr+pm)
                mean_dur = sum(row['duration'] for row in tmp)
                total_duration += mean_dur
                mean_dur /= total
                dur = "{0:.2f}".format(mean_dur)
                mean_turns = sum(row['num_turns'] for row in tmp)
                total_turns += mean_turns
                mean_turns /= total
                turns = "{0}".format(int(mean_turns))
                
            
            self.canvas.create_text(self.column3_x * width, mean_row_y,
                    anchor=tk.W, text = winrate, font=self.font,
            )
            self.canvas.create_text(self.column4_x * width, mean_row_y,
                    anchor=tk.W, text = dur, font=self.font,
            )
            self.canvas.create_text(self.column5_x * width, mean_row_y,
                    anchor=tk.W, text = turns, font=self.font,
            )
        i=10
        row_top_y = (i)*self.row_height
        row_bottom_y = (i+1)*self.row_height
        mean_row_y = (row_top_y + row_bottom_y)/2
        total_losses = total_n - total_wins
        color = 'white'
        if i % 2 == 0:
            color = 'grey85'
            
        self.canvas.create_rectangle(0,row_top_y, width, row_bottom_y, 
                        fill = color, width = 0)
        
        
        #Draw bottom of row
        id = self.canvas.create_line(0,row_bottom_y, width, row_bottom_y, 
                            fill = self.grid_color, tags=('grid_line_bot',)) # Top
        self.canvas.tag_raise('grid_line_bot')
        
        self.canvas.create_text(self.column1_x * width + 20, mean_row_y,
                anchor=tk.W, text = "Total", font=self.font
        )
        
        self.canvas.create_text(self.column2_x * width + 20, mean_row_y,
                anchor=tk.W, text = "{0}/{1}".format(total_wins, total_losses), font=self.font
        )
        winrate = 'N/A'
        turns = "N/A"
        dur = "N/A"
        if total_n > 0:
            wr = total_wins/total_n
            pm = 1.96*sqrt((wr*(1-wr))/total_n)
            winrate = "[{0:.2f}, {1:.2f}]".format(wr-pm, wr+pm)
            mean_dur = total_duration/total_n
            dur = "{0:.2f}".format(mean_dur)
            mean_turns = total_turns/total_n
            turns = "{0}".format(int(mean_turns))
        
        self.canvas.create_text(self.column3_x * width, mean_row_y,
                anchor=tk.W, text = winrate, font=self.font,
        )
        self.canvas.create_text(self.column4_x * width, mean_row_y,
                anchor=tk.W, text = dur, font=self.font,
        )
        self.canvas.create_text(self.column5_x * width, mean_row_y,
                anchor=tk.W, text = turns, font=self.font,
        )
            

def render_text(text, font, text_fill=(255,255,255,255), outline_fill=(0,0,0,255)):
    w,h = font.getsize(text)
    im = Image.new('RGBA', (w+20,h+20), (0,0,0,0))
    draw = ImageDraw.Draw(im)
    x = 5
    y = 0
    # thin border
    shadowcolor = (0,0,0,255)
    draw.text((x-1, y), text, font=font, fill=outline_fill)
    draw.text((x+1, y), text, font=font, fill=outline_fill)
    draw.text((x, y-1), text, font=font, fill=outline_fill)
    draw.text((x, y+1), text, font=font, fill=outline_fill)
    # thicker border
    draw.text((x-1, y-1), text, font=font, fill=outline_fill)
    draw.text((x+1, y-1), text, font=font, fill=outline_fill)
    draw.text((x-1, y+1), text, font=font, fill=outline_fill)
    draw.text((x+1, y+1), text, font=font, fill=outline_fill)
    draw.text((x,y), text, fill=text_fill, font=font)
    
    return im.crop(im.getbbox())
# How to pull json from Hearthstone JSON
#  url = "https://api.hearthstonejson.com/v1/latest/enUS/cards.json" // TODO: Add language support
# context = ssl._create_unverified_context()
# req = urllib.request.urlopen(url, context=context)
# f = req.read() // f would contain the json data


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

def parse_geometry(geometry):
    m = re.match("(\d+)x(\d+)([-+]\d+)([-+]\d+)", geometry)
    if not m:
        raise ValueError("failed to parse geometry string")
    return [int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4))]
    
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
    all_str = "SELECT * FROM {0}".format(table)
    # We need to do two passes, one to delete cards and another to add/update
    for card in deck.values():
        row = cursor.execute(select_str, ('%' + card[0].id +'%',)).fetchone()
        if row is None:
            cursor.execute(insert_str, (card[0].id, card[1]))
        else:
            cursor.execute(update_str, (card[1],'%' + card[0].id +'%'))
    deck_cards = cursor.execute(all_str).fetchall()
    for c in deck_cards:
        if c['card'] not in deck:
            cursor.execute('DELETE FROM {0} WHERE card = ?'.format(table), (c['card'],))
    
           

class DeckCanvas(tk.Canvas):
    def __init__(self, master=None, **kwargs):
        tk.Canvas.__init__(self, master, **kwargs)
        
        # Interactivity
        self.bind("<Button-1>", self._left_click)
        self.bind("<Button-3>", self._right_click)
        #self.bind("<Configure>", self.on_resize)

        self.card_clicked = []
        self.images = {}
        self.image_store = []
        self.tmp_img = []
        # Deck options
        self.editable = False
        self.static_deck = {}
        self.active_deck = {}
        self.rarity_to_color = {
            'FREE'      : '#b7c3d2',
            'COMMON'    : '#b7c3d2',
            'RARE'      : '#1543AD',
            'EPIC'      : '#8215AD',
            'LEGENDARY' : '#EDAD18'
        }
        self.drawn_card_color = '#BBFF8B'
        # Load legendary star
        self.star_image = tk.PhotoImage(file='images/star.gif')
        
        # GUI options TODO: Move to configuration file
        self.font = tk.font.Font(family='Helvetica', size=11, weight='bold')
        self.pil_font = ImageFont.truetype('fonts/FiraSans-Regular.otf', 16)
        
        # Given in percentage of the width
        self.name_text_offset_x = 5
        self.cost_text_offset_x = 0
        self.cost_plate_size = 0.12
        self.cost_plate_top_pad = 0.5
        self.cost_plate_bot_pad = 0.5
        self.num_text_offset_x = 0
        self.num_plate_size = 0.88
        self.num_plate_top_pad = 0.5
        self.num_plate_bot_pad  = 0.5
        self.max_label_size = 35
        self.actual_height = 0
        
    def load_image(self, card_id):
        bar_file = card_id + '.png'
        path_to_file = './images/bars/'+ bar_file
        if os.path.isfile(path_to_file):
            if card_id not in self.images:
                im = PIL.Image.open(path_to_file)
                self.images[card_id] = im #PIL.ImageTk.PhotoImage(im)
        else:
            logging.warn(bar_file + 'could not be found')
    
    def get_num_cards(self):
        n = 0
        for val in self.static_deck.values():
            n += val[1]
        return n
        
    def reset_tracking(self):
        self.active_deck = copy.deepcopy(self.static_deck)
        self.tmp_img = []
        self.refresh_canvas()
    
    def set_deck(self, deck):
        self.static_deck = copy.deepcopy(deck)
        self.active_deck = copy.deepcopy(deck)
        self.images = {}
        self.image_store = []
        self.tmp_img = []
        for card in deck.values():
            self.load_image(card[0].id)
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
                self.load_image(card.id)
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
                    del self.images[card.id]
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
                    if 'name_img' in tags:
                        x, y = self.coords(item)
                        self.delete(item)
                        img = ImageTk.PhotoImage(render_text(self.active_deck[card_id][0].name,
                                self.pil_font, self.drawn_card_color))
                        self.tmp_img.append(img)
                        self.create_image(x,y,  image=img,
                                tags= (self.active_deck[card_id][0].id, 'name_img'), anchor=tk.W)
                    if 'cost_img' in tags:
                        x, y = self.coords(item)
                        self.delete(item)
                        img = ImageTk.PhotoImage(render_text(str(self.active_deck[card_id][0].cost),
                                self.pil_font, self.drawn_card_color))
                        self.tmp_img.append(img)
                        self.create_image(x,y,  image=img,
                                tags= (self.active_deck[card_id][0].cost, 'cost_img'), anchor=tk.CENTER)
                    if 'num_text' in tags:
                        self.itemconfig(item, text=str(self.active_deck[card_id][1]))
    
    def card_shuffled(self, card_id):
        if card_id in self.active_deck:
            self.active_deck[card_id][1] += 1
            items = self.find_withtag(card_id)
            if items:
                # Find the card text
                for item in items:
                    tags = self.gettags(item)
                    if 'name_img' in tags:
                        if self.active_deck[card_id][1] == self.static_deck[card_id][1]:
                            x, y = self.coords(item)
                            self.delete(item)
                            img = ImageTk.PhotoImage(render_text(self.active_deck[card_id][0].name,
                                    self.pil_font))
                            self.tmp_img.append(img)
                            self.create_image(x,y,  image=img,
                                    tags= (self.active_deck[card_id][0].id, 'name_img'), anchor=tk.W)
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
                    self.itemconfigure(item, fill='grey5')
        
    def refresh_canvas(self):
        # This is where the magic happens
        height = self.winfo_reqheight()
        width = self.winfo_reqwidth()
        num_cards = len(self.active_deck)
        if num_cards < 1:
            self.delete(tk.ALL)
            return
        frame_height = min(int(height/num_cards), self.max_label_size)
        # Get the cards in the correct order
        cards_sorted = sorted(self.active_deck.values(), 
                            key = lambda x: (x[0].cost, x[0].name, x[1]))
        # For now we will clear and completely redraw
        self.delete(tk.ALL)
        # Start redrawing
        self.actual_height = 0
        for i, card in enumerate(cards_sorted):
            # Draw the back plate
            x0 = 0
            y0 = (i)*frame_height
            x1 = width
            y1 = (i+1)*frame_height
            self.create_rectangle(x0, y0, x1, y1,
                                    fill="grey35", width=1, tags=(card[0].id, 'frame_plate'))
            
            num_plate_x1 = (width * self.num_plate_size)
            name_text_y = (y0+y1)/2
            cost_text_y = name_text_y
            
            if card[0].id in self.images:
                im = self.images[card[0].id]
                if frame_height != self.max_label_size:
                    im = im.crop((0, 0, im.width, frame_height))
                    
                pi = PIL.ImageTk.PhotoImage(im)
                self.image_store.append(pi)
                self.create_image(num_plate_x1, cost_text_y, anchor=tk.E,
                            image=pi, tags=(card[0].id, 'card_image')) 
                                    
            # Draw cost rectangle
            cost_plate_x1 = (width * self.cost_plate_size)
            self.create_rectangle(x0, y0+self.cost_plate_top_pad, 
                        cost_plate_x1,  y1-self.cost_plate_bot_pad,
                        fill=self.rarity_to_color.get(card[0].rarity,'#b7c3d2'), 
                        width=0, tags=(card[0].id))
            
            self.create_line(cost_plate_x1, y0+self.cost_plate_top_pad, 
                        cost_plate_x1,  y1-self.cost_plate_bot_pad,)
                        
            # Draw cost text
            cost_text_x = int(self.cost_plate_size/2 * width)  + self.cost_text_offset_x
            cost_text_y = (y0+y1)/2 # The center of the plate
            cost_img = ImageTk.PhotoImage(render_text(str(card[0].cost), self.pil_font))
            self.tmp_img.append(cost_img)
            self.create_image(cost_text_x, cost_text_y, 
                                image = cost_img, anchor=tk.CENTER,
                                tags=(card[0].id, 'cost_img'))
            # Draw the card name
            name_text_x = cost_plate_x1 + self.name_text_offset_x
            # The center of the plate
            name_img = ImageTk.PhotoImage(render_text(card[0].name, self.pil_font))
            self.tmp_img.append(name_img)
            # self.create_text(name_text_x, name_text_y, text=card[0].name,
            #                     fill= 'white', anchor=tk.W, font=self.font,
            #                     tags=(card[0].id, 'card_name'))
            self.create_image(name_text_x, name_text_y,
                            image=name_img,tags= (card[0].id, 'name_img'), anchor=tk.W)
            
            # Draw num  rectangle
            
            self.create_rectangle(num_plate_x1, y0+self.cost_plate_top_pad, 
                        width,  y1-self.cost_plate_bot_pad,
                        fill='grey15', 
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
                
            self.actual_height = y1
                
class FloatingDeckCanvas():
    def __init__(self):
        self.win = tk.Toplevel(background='grey', padx = 0, pady =0)
        self.win.lift()
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.90)
        self.win.attributes("-toolwindow", True)
        self.win.attributes("-transparentcolor", 'grey')
        self.deck_canvas = DeckCanvas(self.win, background='grey', bd=0,
        highlightthickness=0, width=250, height=450)
        self.deck_canvas.pack(fill=tk.BOTH, expand=tk.FALSE)
        self.win.update_idletasks()
        self.win.overrideredirect(True)
        self._offsetx = 0
        self._offsety = 0
        self.win.bind('<Button-1>',self.clickwin)
        self.win.bind('<B1-Motion>',self.dragwin)
        self.win.bind('<ButtonRelease-1>', self.release_mouse1)
        self.win.bind('<Configure>', self.on_configure)
        self.size_grip_width = 50
        
        self._in_resize = False
        
    def _in_sizegrip(self,x, y):
        width = self.deck_canvas.winfo_reqwidth()
        x0 = width - self.size_grip_width
        x1 = width
        if x > x0 and x < x1:
            return True
        else: 
            return False
    

    def on_configure(self, event):
        self.deck_canvas['width'] = event.width
        self.deck_canvas['height'] = event.height
        #self.deck_canvas.refresh_canvas()
    
    def dragwin(self,event):
        if self._in_resize:
            x_diff = self.win.winfo_pointerx() - self._screen_offsetx
            y_diff = self.win.winfo_pointery() - self._screen_offsety
            width = self._last_geom[0] + x_diff
            height = self._last_geom[1] + y_diff
            self.win.geometry('{x}x{y}'.format(x=width,y=height))

        else:
            x = self.win.winfo_pointerx() - self._offsetx
            y = self.win.winfo_pointery() - self._offsety
            self.win.geometry('+{x}+{y}'.format(x=x,y=y))
            
    def clickwin(self,event):
        self._offsetx = event.x
        self._offsety = event.y
        self._screen_offsety = self.win.winfo_pointery() 
        self._screen_offsetx = self.win.winfo_pointerx() 
        self._last_geom = parse_geometry(self.win.geometry())
        
        if self._in_sizegrip(event.x, event.y):
            self._in_resize = True
        
    def release_mouse1(self, event):
        if self._in_resize == True:
            self.deck_canvas.refresh_canvas()
            self._in_resize = False

        
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
        self.hero_class = None

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
        if self.hero_class is None:
            search = self.var.get()+'%'
            results = self.cursor.execute(r"SELECT * FROM cards WHERE name LIKE ? AND collectible = 1 ORDER BY lower(name) DESC LIMIT 10", (search,))
        else:
            search = self.var.get()+'%'
            results = self.cursor.execute(r"SELECT * FROM cards WHERE name LIKE ?  AND (player_class = ? AND collectible = 1 OR player_class = -1 AND collectible = 1)  ORDER BY lower(name) DESC LIMIT 10", (search, self.hero_class))
        rows = results.fetchall()
        return rows
        
class HeroSelector(ttk.Frame):
    def __init__(self, master=None):
        # Initialize
        self.icon_width = 32
        ttk.Frame.__init__(self, master, height = self.icon_width, width = self.icon_width* 9)
        self.config(pad=0)
        self.pack(fill=tk.X, expand=tk.TRUE)
        
        self.load_images()
        self.create_labels()
        self.active_class = None
        self.class_changed = []
        
    def set_label(self, hero_class):
        widget = self.classes[hero_class]
        for l in self.labels:
            l['background'] = self.def_color
        self.active_class = hero_class
        widget['background'] = 'blue'
        for f in self.class_changed:
            f(self.active_class)
        
    def _left_click(self, event):
        widget = event.widget
        for l in self.labels:
            l['background'] = self.def_color
        self.active_class = self.labels[event.widget]
        widget['background'] = 'blue'
        for f in self.class_changed:
            f(self.active_class)
        return
            
    def _right_click(self, event):
        pass
        
    def create_labels(self):
        self.labels = {}
        self.classes = {}
        for i in range(1,10):
             l = ttk.Label(self, image=self.class_images[i])
             l.pack(side=tk.LEFT)
             self.def_color = l['background']
             l.bind('<Button-1>', self._left_click)
             self.labels[l] = i
             self.classes[i] = l
             
    def load_images(self):
        self.class_images = {}
        self.icon_size = self.icon_width
        for i in range(1,10):
            path = './images/tbl_{0}.png'.format(i)
            im = PIL.Image.open(path)
            im = im.resize((self.icon_size,self.icon_size), PIL.Image.LANCZOS)
            im = PIL.ImageTk.PhotoImage(im)
            self.class_images[i] = im
            tk.Label(self, image=im)
                                
class DeckCreator(ttk.Frame):
    def __init__(self, cursor, master=None):
        # Initialize
        ttk.Frame.__init__(self, master, width= 800, height = 600)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.pack(fill=tk.BOTH, expand=1)
        self.cursor = cursor
        self.master = master
        self._create_widgets()
        self.update_deck = False
        self.deck_id = None
        
    def _create_widgets(self):
        f1 = ttk.Frame(self, width = 250)
        f1.pack(side = tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        f2 = ttk.Frame(self, width = 250)
        f2.pack(side = tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        #f1.rowconfigure(1, weight=1)
        self._entry_canvas = DeckCanvas(f1, width = 400, height = 600)
        self._static_canvas = DeckCanvas(f2, width = 400, height = 600)
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
        self._hero_class_list = HeroSelector(f2)
        self._hero_class_list.class_changed.append(self.on_class_changed)
        self._hero_class_list.pack(fill=tk.X, expand=0)
        ttk.Label(f2, text='Enter Deck Name:').pack(fill=tk.X, expand=0)
        self._deck_name_entry.pack(fill=tk.X, expand=0)
        self._save_deck_btn = ttk.Button(f2, text = 'Save', command= self._btn_save)
        self._save_deck_btn.pack(fill=tk.X, expand=0)
        
    def on_class_changed(self, player_class):
        if self.update_deck is not True:
            self._card_entry.hero_class = player_class
    
    def update_num_cards(self):
        self._num_cards_text.set('Number of cards: {0}'.format(self._static_canvas.get_num_cards()))
        
    def _btn_save(self):
        if len(self._static_canvas.static_deck) > 30:
            tk.messagebox.showwarning('A deck cannot contain more than 30 cards', 'Remove some cards and try again')
            return
        elif len(self._static_canvas.static_deck) < 1:
            tk.messagebox.showwarning('A deck must contain atleast one card', 'Add a card and try again')
            return
        elif self._deck_name_entry.get() == '' and self.update_deck is False:
            tk.messagebox.showwarning('Deck has no name', 'The deck does not have a name, give it one and try again')
            return
        elif self._hero_class_list.active_class is None and self.update_deck is False:
            tk.messagebox.showwarning('Deck has unassociate class', 'A deck must be associate with a hero, select a hero and try again')
            return
        elif self.update_deck is True:
            table_name = 'deck_' + str(self.deck_id)
            save_deck_to_sql(self.cursor, self._static_canvas.static_deck, table_name)
            return
        else:
            # Write to db
            heronum = self._hero_class_list.active_class
            deck = self.cursor.execute(sql_select_deck_by_name, 
                        ('%' + self._deck_name_entry.get() +'%',)).fetchone()
            if deck is not None:
                tk.messagebox.showwarning('A deck with that name exists', 'Decks must have unique names, please change the name and try again')
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

class DeckStatisticsCanvas(ttk.Frame):
    def __init__(self, cursor, master=None, **kwargs):
        ttk.Frame.__init__(self, master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        yscrollbar = tk.Scrollbar(self)
        yscrollbar.grid(row=0, column=1, sticky=(tk.N,tk.S))

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0,
                        yscrollcommand=yscrollbar.set, 
                        scrollregion=(0, 0, self['width'], 1000),
                        width = self['width'],
                        height = self['height'])

        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        yscrollbar.config(command=self.canvas.yview)

        self.row_height = 20
        
        self.pack()
        self.canvas['bg'] = 'white'
        self.cursor = cursor
        # Interactivity
        self.bind("<Button-1>", self._left_click)
        self.bind("<Button-3>", self._right_click)
        self.bind("<Configure>", self._configure)
        
        self.load_images()
        self.active_deck = None
        self.editable = False
        
        self.font = tk.font.Font(family='Helvetica', size=10, weight = 'bold')
        self.underline_font = tk.font.Font(family='Helvetica', size=10, weight = 'bold', underline=True)
        self.grid_color = "#84aad9"
        self.win_color = '#4a9e5b'
        self.lose_color = '#7c23a6'
        self.column1_x = 0
        self.column2_x = 0.2
        self.column3_x = 0.4
        self.column4_x = 0.6
        self.column5_x = 0.8
        
    def _configure(self, event):
        self.canvas['width'] = event.width
        self.canvas['height'] = event.height
        self.refresh_canvas()
        
    def load_images(self):
        self.class_images = {}
        self.icon_size = 16
        for i in range(1,10):
            path = './images/tbl_{0}.png'.format(i)
            im = PIL.Image.open(path)
            im = im.resize((self.icon_size,self.icon_size), PIL.Image.LANCZOS)
            im = PIL.ImageTk.PhotoImage(im)
            self.class_images[i] = im
            tk.Label(self, image=im)
            
    def set_deck(self, deck_id):
        self.active_deck = deck_id
        self.refresh_canvas()
        
    def _left_click(self, event):
        if self.editable is True:
            item = self.find_closest(event.x, event.y, halo=None, start=None)
            if item:
                pass
        else:
            return
            
    def _right_click(self, event):
        if self.editable is True:
            pass
        else:
            return
    
    def draw_frame(self):
        width = self.canvas.winfo_reqwidth()
        height = self.canvas.winfo_reqheight()
        self.canvas.create_line(0,0, width, 0, fill = self.grid_color) # Top
        self.canvas.create_line(0,0, 0, height, fill = self.grid_color) # Left
        self.canvas.create_line(width,0, width, height, fill = self.grid_color) # Right
        self.canvas.create_line(0,height, width, height, fill = self.grid_color) # Bottom
        
    def draw_results(self, results):
        width = self.canvas.winfo_reqwidth()
        height = self.canvas.winfo_reqheight()
        # Grab some rows
        rows = results.fetchmany(100)
        # If we have rows,draw them
        num_rows = 0 #Keep track of row
        # Draw the header row
        mean_row_y = self.row_height/2
            
        self.canvas.create_rectangle(0,0, width, self.row_height, 
                        fill = 'grey75', width = 0)
        
        
        #Draw bottom of row
        id = self.canvas.create_line(0,self.row_height, width, self.row_height, 
                            fill = 'grey65', tags=('grid_line_bot',)) # Top
        self.canvas.tag_raise('grid_line_bot')
        
        self.canvas.create_text(self.column1_x * width + 20, mean_row_y,
                anchor=tk.W, text = "Deck", font=self.font
        )
        
        self.canvas.create_text(self.column2_x * width + 5, mean_row_y,
                anchor=tk.W, text = "Opponent", font=self.font
        )
        
        self.canvas.create_text(self.column3_x * width - 10, mean_row_y,
                anchor=tk.W, text = "Outcome", font=self.font,
        )
        self.canvas.create_text(self.column4_x * width - 10, mean_row_y,
                anchor=tk.W, text = 'Duration (s)', font=self.font,
        )
        self.canvas.create_text(self.column5_x * width, mean_row_y,
                anchor=tk.W, text = 'Date', font=self.font,
        )
        # Draw the rest of the rows
        if rows:
            for i, row in enumerate(rows):
                num_rows += 1
                p_hero = self.cursor.execute(
                    "SELECT class FROM hero WHERE id = ?",
                    (row['player_hero'],)
                ).fetchone()['class']
                o_hero = self.cursor.execute(
                    "SELECT class FROM hero WHERE id = ?",
                    (row['opp_hero'],)
                ).fetchone()['class']
                deck_name = self.cursor.execute(
                    "SELECT name FROM deck WHERE id = ?",
                    (row['deck'],)
                ).fetchone()['name']
                
                date = row['date']
                won = row['won']
                duration = row['duration']
                # Calc
                row_top_y = (i+1)*self.row_height
                row_bottom_y = (i+2)*self.row_height
                mean_row_y = (row_top_y + row_bottom_y)/2
                
                color = 'white'
                if i % 2 == 0:
                    color = 'grey85'
                    
                self.canvas.create_rectangle(0,row_top_y, width, row_bottom_y, 
                                fill = color, width = 0)
                
                
                #Draw bottom of row
                id = self.canvas.create_line(0,row_bottom_y, width, row_bottom_y, 
                                 fill = self.grid_color, tags=('grid_line_bot',)) # Top
                self.canvas.tag_raise('grid_line_bot')
                self.canvas.create_image(self.column1_x * width, mean_row_y,
                        anchor=tk.W, image= self.class_images[p_hero]
                )
                
                self.canvas.create_text(self.column1_x * width + 20, mean_row_y,
                        anchor=tk.W, text = deck_name, font=self.font
                )
                
                self.canvas.create_image(self.column2_x * width, mean_row_y,
                        anchor=tk.W, image= self.class_images[o_hero]
                )
                
                self.canvas.create_text(self.column2_x * width + 20, mean_row_y,
                        anchor=tk.W, text = hs.hero_dict[o_hero], font=self.font
                )
                
                color = None
                out_text = ""
                if won == True:
                    color = self.win_color
                    out_text = 'Win'
                else:
                    color = self.lose_color
                    out_text = 'Loss'
                
                self.canvas.create_text(self.column3_x * width, mean_row_y,
                        anchor=tk.W, text = out_text, font=self.font,
                        fill = color
                )
                self.canvas.create_text(self.column4_x * width, mean_row_y,
                        anchor=tk.W, text = int(duration), font=self.font,
                )
                self.canvas.create_text(self.column5_x * width, mean_row_y,
                        anchor=tk.W, text = date[0:16], font=self.font,
                )
                
        return
        
    def refresh_canvas(self):
        # Setup the canvas
        # We need to make columns for the deck
        # the oponents deck, the outcome, and date
        # Draw the frame
        self.canvas.delete(tk.ALL)
        #self.draw_frame()
        if self.active_deck is not None:
            # Make a deck history page
            games_results = self.cursor.execute(
                "SELECT * FROM match WHERE deck = ? ORDER BY date DESC", (self.active_deck,)
            )
            
            self.draw_results(games_results)
            return
        else:
            # Make a general history page
            games_results = self.cursor.execute(
                "SELECT * FROM match ORDER BY date DESC"
            )
            self.draw_results(games_results)
            return