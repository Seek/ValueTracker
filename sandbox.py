import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import font
import sqlite3
import hs
from collections import namedtuple
import pdb
import PIL
from PIL import ImageTk, Image
import hs
import logging
import os.path
import copy

Card = namedtuple('Card', ['id', 'name','rarity',
                             'cost', 'attack', 'health'])
                             
def card_from_row(row):
    return Card(row['id'], row['name'], row['rarity'], 
    row['cost'], row['attack'], row['health'])
  

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

def load_deck_from_sql(cursor, id):
    sql_str = sql_select_cards_from_deck.format('deck_'+str(id))
    rows = cursor.execute(sql_str).fetchall()
    deck = {}
    for row in rows:
        tmp = cursor.execute(sql_select_card_by_id, (row['card'],)).fetchone()
        card = card_from_row(tmp)
        deck[card.id] = [card, int(row['num'])]
    return deck
    
CLASS_IMAGES = [Image.open('./images/tbl_{0}.png'.format(n)) for n in range(0,10)]
CLASS_IMAGES_64 = [im.resize((64,64), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
CLASS_IMAGES_32 = [im.resize((32,32), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
CLASS_IMAGES_24 = [im.resize((24,24), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
CLASS_IMAGES_16 = [im.resize((16,16), PIL.Image.LANCZOS) for im in CLASS_IMAGES]
SEL_HILITE = Image.open('./images/sel_highlight.png')
SEL_HILITE_32 = SEL_HILITE.resize((32,32), PIL.Image.LANCZOS)
# NO_CLASS_IMAGE = Image.open('./images/0.png)
# NO_CLASS_IMAGE_64 = NO_CLASS_IMAGE.resize((64,64), PIL.Image.LANCZOS)
# NO_CLASS_IMAGE_32 = NO_CLASS_IMAGE.resize((32,32), PIL.Image.LANCZOS)
# NO_CLASS_IMAGE_24 = NO_CLASS_IMAGE.resize((24,24), PIL.Image.LANCZOS)
# NO_CLASS_IMAGE_16 = NO_CLASS_IMAGE.resize((16,16), PIL.Image.LANCZOS)

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
            
    
class Application(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        # Initialize
        ttk.Frame.__init__(self, master, **kwargs)
        self.config(pad=4)
        self.master = master
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.grid(column=0, row=0, sticky='nsew')
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        # self.deck_view = DeckCanvas(1, self, width=300, height=600)
        # self.deck_view.pack(fill=tk.BOTH, expand=tk.TRUE)
        self.db = sqlite3.connect('example_stats.db')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.pw = ttk.PanedWindow(self, width = self['width'],
        height = self['height'], orient = tk.HORIZONTAL)
        self.pw.grid(column=0, row=0, sticky='nsew')
        deck_win_frame = ttk.Frame(self.pw, width = int(self['width'] * 0.2),
                            height=self['height'])
        
        self.nb = ttk.Notebook(self.pw, width=int(self['width']*0.7), height=self['height'])
        f = ttk.Frame(self.nb,width=int(self['width']*0.7), height=self['height'])
        
        deck_filter_lblframe = ttk.LabelFrame(deck_win_frame, text='Deck Filter', width = 200, height = 74, pad=4)
        deck_select_lblframe = ttk.LabelFrame(deck_win_frame, text='Decks', width = 200, height = 390, pad=4)
        
        
        deck_select_lblframe.grid(row=5, column=0, sticky='nwse')
        deck_filter_widget = PlayerClassWidget(deck_filter_lblframe, width= 5*32, height = 64)
        deck_filter_widget.on_class_selected.append(self.on_deck_filter)
        ttk.Button(deck_win_frame, text='Import Deck').grid(column=0, row=0, sticky='ew')
        ttk.Button(deck_win_frame, text='New Deck').grid(column=0, row=1, sticky='ew')
        ttk.Button(deck_win_frame, text='Edit Deck').grid(column=0, row=2, sticky='ew')
        ttk.Button(deck_win_frame, text='Delete Deck').grid(column=0, row=3, sticky='ew')
        deck_filter_widget.grid(row=4, column=0, sticky='nwe')
        self.deck_select_widget = DeckSelectWidget(deck_select_lblframe, width = 150,
                            height=390)
        
        self.deck_select_widget.grid(row=0, column=0, sticky='nwse')
        deck_filter_lblframe.grid(row=4, column=0, sticky='nwe')
        f.grid(column=0, row=0, sticky='nsew')
        # Config notebook
        self.nb.columnconfigure(0, weight=1)
        self.nb.rowconfigure(0, weight=1)
        # Config frame
        deck_win_frame.columnconfigure(0, weight=1)
        deck_win_frame.rowconfigure(0, weight=1, minsize=20)
        deck_win_frame.rowconfigure(1, weight=1)
        deck_win_frame.rowconfigure(2, weight=1)
        deck_win_frame.rowconfigure(3, weight=1)
        deck_win_frame.rowconfigure(4, weight=1)
        deck_win_frame.rowconfigure(5, weight=1)
        deck_filter_lblframe.rowconfigure(0, weight=1)
        deck_select_lblframe.rowconfigure(0, weight=1)
        deck_filter_lblframe.columnconfigure(0, weight=1)
        deck_select_lblframe.columnconfigure(0, weight=1)
        decks = self.cursor.execute("SELECT id,name, class FROM deck").fetchall()
        self.deck_select_widget.set_deck_list(decks)
        self.nb.add(f, text='Test')
        self.pw.add(deck_win_frame)
        self.pw.add(self.nb)
    
    def on_close(self):
        self.db.close()
        self.master.destroy()
        
    def on_deck_filter(self, plr_class):
        if plr_class == 0:
            decks = self.cursor.execute("SELECT id,name, class FROM deck").fetchall()
            self.deck_select_widget.set_deck_list(decks)
        else:
            decks = self.cursor.execute("SELECT id,name, class FROM deck WHERE class = ?", (plr_class, )).fetchall()
            self.deck_select_widget.set_deck_list(decks)
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root, width=800, height=600)
app.mainloop()