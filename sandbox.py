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
    
CLASS_IMAGES = {}
class PlayerClassWidget(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        ttk.Frame.__init__(self, master, **kwargs)
        # Setup 2 rows 
        self.labels = []
        self.active_playerclass = 0
        for i in range(5):
            lbl_top = ttk.Label(self, width=16, text=str(i))
            lbl_bot = ttk.Label(self, width=16, text=str(i+4))
            lbl_top.grid(column=i, row=0, sticky='w')
            lbl_bot.grid(column=i, row=1, sticky='w')
            
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
        f1 = ttk.LabelFrame(self.pw, text='Deck Interface', width = int(self['width'] * 0.4),
                            height=self['height'])
        self.nb = ttk.Notebook(self.pw, width=int(self['width']*0.6), height=self['height'])
        f = ttk.Frame(self.nb,width=int(self['width']*0.6), height=self['height'])
        m = PlayerClassWidget(f1)
        m.grid(row=0, column=0, sticky='nw')
        f.grid(column=0, row=0, sticky='nsew')
        self.nb.columnconfigure(0, weight=1)
        self.nb.rowconfigure(0, weight=1)
        self.nb.add(f, text='Test')
        self.pw.add(f1)
        self.pw.add(self.nb)
    
    def on_close(self):
        self.db.close()
        self.master.destroy()
        
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root, width=800, height=600)
app.mainloop()