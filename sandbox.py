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
from PIL import ImageTk
import hs
import logging
import os.path
import copy

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
    
class ResizeableCanvas(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        ttk.Frame.__init__(self, master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0,
                        width = self['width'],
                        height = self['height'])
        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.pack()
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
        self.win_color = '#4a9e5b'
        self.lose_color = '#7c23a6'
        self.column1_x = 0
        self.column2_x = 0.4
        self.column3_x = 0.6
        self.column4_x = 0.75
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
        
    def refresh_canvas(self):
        num_rows = 0
        width = self.canvas.winfo_reqwidth()
        height = self.canvas.winfo_reqheight()
        if self.active_deck is not None:
            results = self.cursor.execute('SELECT * from match WHERE deck = ?', (self.active_deck,))
            rows = results.fetchall()
            self.canvas.delete(tk.ALL)
            vals = list(hs.hero_dict.keys())
            for i, v in enumerate(vals):
                num_rows += 1
                ids = self.cursor.execute('SELECT id FROM hero WHERE class = ?', (v,)).fetchall()
                query = 'SELECT * FROM match WHERE deck = ? AND ('
                for id in ids:
                     query += 'opp_hero = {0} OR '.format(id['id'])
                query = query[:-4]
                query += ')'
                print(query)
                
                matches = self.cursor.execute(query, (self.active_deck,)).fetchall()
                total_num = len(matches)
                total_wins = sum(1 for i in matches if i['won'] == 1)
                # Calc
                row_top_y = i*self.row_height
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
                self.canvas.create_image(0, mean_row_y,
                        anchor=tk.W, image= self.class_images[v]
                )
                self.canvas.create_text(20, mean_row_y,
                        anchor=tk.W, text = hs.hero_dict[v], font=self.font
                )
                if total_num == 0:
                    win_rate = 'NA'
                else:
                    win_rate = total_wins/total_num
                
                self.canvas.create_text(self.column2_x * width, mean_row_y,
                        anchor=tk.W, text = 'Win Rate: {0}'.format(win_rate), font=self.font
                )
                
            # Draw the totals row
            row_top_y = num_rows*self.row_height
            row_bottom_y = (num_rows+1)*self.row_height
            mean_row_y = (row_top_y + row_bottom_y)/2
            self.canvas.create_rectangle(0,row_top_y, width, row_bottom_y, 
                            fill = color, width = 0)
            
            #Draw bottom of row
            id = self.canvas.create_line(0,row_bottom_y, width, row_bottom_y, 
                                fill = self.grid_color, tags=('grid_line_bot',)) # Top
            self.canvas.tag_raise('grid_line_bot')
            self.canvas.create_text(0, mean_row_y,
                    anchor=tk.W, text = 'Total', font=self.font
            )
            if len(rows) == 0:
                win_rate = 'NA'
            else:
                win_rate = sum(1 for i in rows if i['won'] == 1)/len(rows)
            
            self.canvas.create_text(self.column2_x * width, mean_row_y,
                    anchor=tk.W, text = 'Win Rate: {:0.3f}'.format(win_rate), font=self.font
            )
                
        else:
            return
            # results = self.cursor.execute('SELECT * from match WHERE', (self.active_deck,))
            # rows = results.fetchall()
            # self.canvas.delete(tk.ALL)
            
    
    
        

class Application(ttk.Frame):
    def __init__(self, master=None):
        # Initialize
        ttk.Frame.__init__(self, master)
        self.config(pad=0)
        self.master = master
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.pack(fill=tk.BOTH, expand=tk.TRUE)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        # self.deck_view = DeckCanvas(1, self, width=300, height=600)
        # self.deck_view.pack(fill=tk.BOTH, expand=tk.TRUE)
        self.db = sqlite3.connect('stats.db')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self.wid = DeckStatsCanvas(self.cursor, self, width=600, height=800)
        self.wid.pack(fill=tk.BOTH, expand=tk.TRUE)
        # #deck = load_deck_from_sql(self.cursor, 2)
        # #self.wid.set_deck(deck)
        self.wid.set_deck(2)
        # self.wid.refresh_canvas()
        #self.wid = HeroSelector(self)
    
    def on_close(self):
        self.db.close()
        self.master.destroy()
        
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()