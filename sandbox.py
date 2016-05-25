#GUI imports
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import font
import sqlite3
import hs
from collections import namedtuple
import pdb

import hs

Card = namedtuple('Card', ['id', 'name','rarity',
                             'cost', 'attack', 'health'])
                             
def card_from_row(row):
    return Card(row['id'], row['name'], row['rarity'], 
    row['cost'], row['attack'], row['health'])


class HeroClassListbox(tk.Listbox):
        def __init__(self, master, *args, **kwargs):
            tk.Listbox.__init__(self, master,  height=9)
            vals = list(hs.hero_dict.values())
            for v in vals:
                self.insert(tk.END, v)   

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
    
        
class DeckStatisticsCanvas(ttk.Frame):
    def __init__(self, cursor, master=None, **kwargs):
        ttk.Frame.__init__(self, master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        xscrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        xscrollbar.grid(row=1, column=0, sticky=(tk.E, tk.W))

        yscrollbar = tk.Scrollbar(self)
        yscrollbar.grid(row=0, column=1, sticky=(tk.N,tk.S))

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0,
                        xscrollcommand=xscrollbar.set,
                        yscrollcommand=yscrollbar.set,
                        width = self['width'],
                        height = self['height'])

        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        xscrollbar.config(command=self.canvas.xview)
        yscrollbar.config(command=self.canvas.yview)

        self.row_height = 20
        
        self.pack()
        self.canvas['bg'] = 'white'
        self.cursor = cursor
        # Interactivity
        self.bind("<Button-1>", self._left_click)
        self.bind("<Button-3>", self._right_click)
        
        self.editable = False
        
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
    
    def refresh_canvas(self):
        # This is where the magic happens
        height = self.winfo_reqheight()
        width = self.winfo_reqwidth()
        self.canvas.delete(tk.ALL)
        sql_str = 'SELECT * FROM match WHERE deck = ?'
        rows = self.cursor.execute(sql_str, (self.active_deck,)).fetchmany(20)
        print(rows)
        if rows:
            columns = rows[0].keys()
            ncols = len(columns)
            if ncols < 1:
                return
            column_width = width/ncols
            x0 = 0
            y0 = 0
            x1 = width
            y1 = self.row_height
            self.canvas.create_rectangle(x0, y0, x1, y1,
                                    fill="grey85", width=0)
            self.canvas.create_line(0, self.row_height, width, self.row_height,
            fill='grey50')
            
            for i, column in enumerate(columns):
                self.canvas.create_line((i+1)*column_width, 0,
                                       (i+1)*column_width, height, fill='grey50')
        return
        

class Application(ttk.Frame):
    def __init__(self, master=None):
        # Initialize
        ttk.Frame.__init__(self, master)
        self.config(pad=0)
        self.master = master
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        # self.deck_view = DeckCanvas(1, self, width=300, height=600)
        # self.deck_view.pack(fill=tk.BOTH, expand=tk.TRUE)
        self.db = sqlite3.connect('stats.db')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.wid = DeckStatisticsCanvas(self.cursor, self, width=600, height=600)
        self.wid.canvas.configure(scrollregion=(0, 0, 600, 600))
        # deck = load_deck_from_sql(self.cursor, 4)
        self.wid.set_deck(2)
    
    def on_close(self):
        self.db.close()
        self.master.destroy()
        
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()