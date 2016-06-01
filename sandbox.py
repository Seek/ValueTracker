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

import hs
from controls import DeckSelectWidget, PlayerClassWidget

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
    
    
class CardStatsWidget(ttk.Frame):
    def __init__(self, cursor, master=None, **kwargs):
        # Initialize
        ttk.Frame.__init__(self, master, **kwargs)
        self.cursor = cursor
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=2)
        self.canvas = tk.Canvas(self, width=self['width'],
                        height = 525, bd = 0,
                        highlightthickness=0, bg='white')
        self.entry = hs.AutocompleteCardEntry(self, cursor, )
        self.entry.grid(column = 0, row=0, sticky='nw')
        self.canvas.grid(column=0, row=1, sticky='nsew')
        self.entry.cb.append(self.on_card_selected)
        self.active_deck = None
        
    def draw_results(self, card_id):
        self.canvas.delete(tk.ALL)
        cards_played = self.cursor.execute("SELECT DISTINCT matchid FROM card_played WHERE cardid LIKE ?",
                                ('%{0}%'.format(card_id),)).fetchall()
        wins = 0
        losses = 0
        turn = 0
        time = 0
        #pdb.set_trace()
        if cards_played:
            for row in cards_played:
                match = self.cursor.execute("SELECT DISTINCT * from match WHERE id = ?",
                                                (int(row['matchid']),)).fetchone()
                if match['won'] == 1:
                    wins += 1
                else:
                    losses +=1
                turn += int(match['num_turns'])
                time += int(match['duration'])
            
            name = self.cursor.execute("SELECT name FROM cards WHERE id LIKE ?",
                                    ('%{0}%'.format(card_id),)).fetchone()['name']
            total = wins+losses
            self.canvas.create_text(0,20, text= 'Card: {0}'.format(name), anchor='w')
            self.canvas.create_text(0,40, text= 'Total Games: {0}'.format(wins + losses), anchor='w')
            self.canvas.create_text(0,60, text= 'Total Wins: {0}'.format(wins), anchor='w')
            self.canvas.create_text(0,80, text= 'Mean Turns Played Per Game: {0}'.format(turn/total), anchor='w')
            self.canvas.create_text(0,100, text= 'Mean Duration: {0}'.format(time/total), anchor='w')
            self.canvas.create_text(0,120, text= 'Win Rate: {0}'.format(wins/total), anchor='w')
        
    def on_card_selected(self, name):
        results = self.cursor.execute("SELECT id, name from cards WHERE name LIKE ?", 
                                        ("%{0}%".format(name),)).fetchall()
        #pdb.set_trace()
        for row in results:
            if row['name'] == name:
                self.draw_results(row['id'])
        
        
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
        f = CardStatsWidget(self.cursor, self.nb, width=int(self['width']*0.7), height=self['height'])
        
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