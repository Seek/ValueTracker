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
import PIL
from PIL import ImageTk
import hs
import logging

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

        yscrollbar = tk.Scrollbar(self)
        yscrollbar.grid(row=0, column=1, sticky=(tk.N,tk.S))

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0,
                        yscrollcommand=yscrollbar.set,
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
        
        self.load_images()
        self.active_deck = None
        self.editable = False
        
        self.font = tk.font.Font(family='Helvetica', size=10, weight = 'bold')
        self.grid_color = "#84aad9"
        self.win_color = '#4a9e5b'
        self.lose_color = '#7c23a6'
        self.column1_x = 0
        self.column2_x = 150
        self.column3_x = 300
        self.column4_x = 450
        
        
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
        rows = results.fetchmany(20)
        # If we have rows,draw them
        num_rows = 0 #Keep track of row
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
                
                # Calc
                row_top_y = i*self.row_height
                row_bottom_y = (i+1)*self.row_height
                mean_row_y = (row_top_y + row_bottom_y)/2
                #Draw bottom of row
                self.canvas.create_line(0,row_bottom_y, width, row_bottom_y, 
                                fill = self.grid_color) # Top
                                
                self.canvas.create_image(self.column1_x, mean_row_y,
                        anchor=tk.W, image= self.class_images[p_hero]
                )
                
                self.canvas.create_text(self.column1_x + 20, mean_row_y,
                        anchor=tk.W, text = deck_name, font=self.font
                )
                
                self.canvas.create_image(self.column2_x, mean_row_y,
                        anchor=tk.W, image= self.class_images[o_hero]
                )
                
                self.canvas.create_text(self.column2_x + 20, mean_row_y,
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
                
                self.canvas.create_text(self.column3_x, mean_row_y,
                        anchor=tk.W, text = out_text, font=self.font,
                        fill = color
                )
                
                self.canvas.create_text(self.column4_x, mean_row_y,
                        anchor=tk.W, text = date[0:19], font=self.font,
                )
                
        return
        
    def refresh_canvas(self):
        # Setup the canvas
        # We need to make columns for the deck
        # the oponents deck, the outcome, and date
        # Draw the frame
        self.draw_frame()
        if self.active_deck is not None:
            # Make a deck history page
            games_results = self.cursor.execute(
                "SELECT * FROM match WHERE deck = ?", (self.active_deck,)
            )
            
            self.draw_results(games_results)
            return
        else:
            # Make a general history page
            games_results = self.cursor.execute(
                "SELECT * FROM match", (self.active_deck,)
            )
            self.draw_results(games_results)
            return
        # if self.active_deck is not None:
        #     # This is where the magic happens
        #     height = self.winfo_reqheight()
        #     width = self.winfo_reqwidth()
        #     self.canvas.delete(tk.ALL)
        #     sql_str = 'SELECT * FROM match WHERE deck = ?'
        #     tmp = self.cursor.execute('SELECT * FROM deck WHERE id = ?', (self.active_deck,))
        #     if not tmp:
        #         logging.error('Deck id: {0} did not exist in the database'.format(self.active_deck))
        #     tmp = tmp.fetchone()
        #     deck_name = tmp['name']
        #     rows = self.cursor.execute(sql_str, (self.active_deck,)).fetchmany(20)
        #     if rows:
        #         columns = rows[0].keys()
        #         ncols = len(columns)
        #         if ncols < 1:
        #             return
        #         column_width = width/ncols
        #         x0 = 0
        #         y0 = 0
        #         x1 = width
        #         y1 = self.row_height
        #         self.canvas.create_rectangle(x0, y0, x1, y1,
        #                                 fill="grey85", width=0)
        #         self.canvas.create_line(0, self.row_height, width, self.row_height,
        #         fill='grey65')
                
                
        #         deck_name_width = self.font.measure(deck_name)
        #         x = deck_name_width + 20
        #         self.canvas.create_line(x, 0, x, height,
        #         fill='grey65')
        #         self.canvas.create_text(x/2, self.row_height/2, 
        #         anchor = tk.CENTER, text='Deck', font=self.font)
                
        #         opp_text_width = self.font.measure('Opponent')
        #         next_x = x + opp_text_width + 12
        #         self.canvas.create_line(next_x, 0, next_x, height,
        #         fill='grey65')
        #         self.canvas.create_text(((x + next_x)/2)+ 2, self.row_height/2, 
        #         anchor = tk.CENTER, text='Opponent', font=self.font)
        #         x = next_x
                
        #         sel_class = 'SELECT class FROM hero WHERE id = ?'
        #         for i, row in enumerate(rows):
        #             deck = row['deck']
        #             opp_hero = row['opp_hero']
        #             player_hero = row['player_hero']
        #             opp_class = self.cursor.execute(sel_class, (opp_hero,)).fetchone()['class']
        #             player_class = self.cursor.execute(sel_class, (player_hero,)).fetchone()['class']
        #             print(player_class)
        #             won = row['won']
                    
        #             row_top_y = (i+1)*self.row_height
        #             row_bottom_y = (i+2)*self.row_height
        #             mean_row_y = (row_top_y+row_bottom_y)/2
        #             self.canvas.create_line(0, row_bottom_y, width,row_bottom_y,
        #             fill='grey65') 
        #             self.canvas.create_image(0, mean_row_y, anchor=tk.W,
        #                             image=self.class_images[player_class])
                                    
        #             self.canvas.create_text(18, mean_row_y, 
        #             anchor = tk.W, text=deck_name, font=self.font)
                    
               
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
        self.wid.pack(fill=tk.BOTH, expand=tk.TRUE)
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