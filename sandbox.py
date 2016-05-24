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

from deckcanvas import DeckCanvas
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
        pw = ttk.PanedWindow(self, width= 1080, height = 800, orient=tk.HORIZONTAL)
        pw.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        pw.columnconfigure(0, weight=1)
        pw.rowconfigure(0, weight=1)
        f1 = ttk.Frame(pw, width = 400, height = 600, relief='sunken')
        f2 = ttk.Frame(pw, width = 400)
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
        
        ttk.Label(f2, text='Select a class:').pack(fill=tk.X, expand=0)
        self._deck_name_entry = ttk.Entry(f2)
        self._hero_class_list = HeroClassListbox(f2)
        self._hero_class_list.pack(fill=tk.X, expand=0)
        ttk.Label(f2, text='Enter Deck Name:').pack(fill=tk.X, expand=0)
        self._deck_name_entry.pack(fill=tk.X, expand=0)
        self._save_deck_btn = ttk.Button(f2, text = 'Save', command= self._btn_save)
        self._save_deck_btn.pack(fill=tk.X, expand=0)
        pw.add(f1)
        pw.add(f2)
        
    def _btn_save(self):
        if len(self._static_canvas.static_deck) > 30:
            print('Too many cards')
            return
        elif len(self._static_canvas.static_deck) < 30:
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
            save_deck_to_sql(self.cursor, self._deck_treeview.deck, table_name)
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
        self._static_canvas.add_card(card)

    def remove_card(self, card_id):
        results = self.cursor.execute(r"SELECT * FROM cards WHERE id LIKE ?", (card_id,))
        row = results.fetchone()
        card = card_from_row(row)
        self._static_canvas.remove_card(card)
        

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
        self.deck_create = DeckCreator(self.cursor, self)
        # deck = load_deck_from_sql(self.cursor, 4)
        # self.deck_view.set_deck(deck)
    
    def on_close(self):
        self.db.close()
        self.master.destroy()
        
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()