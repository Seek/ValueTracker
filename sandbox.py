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
        self.star_image = tk.PhotoImage(file='./star.gif')
        self.tmp = ttk.Label(self, image=self.star_image)
        
        # GUI options TODO: Move to configuration file
        self.outline_font = tk.font.Font(family='Helvetica', size=12, weight='bold')
        self.font = tk.font.Font(family='Helvetica', size=11, weight='bold')
        
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
        self.refresh_canvas()
    
    def set_deck(self, deck):
        self.static_deck = copy.deepcopy(deck)
        self.active_deck = copy.deepcopy(deck)
        self.images = {}
        self.image_store = []
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
             # The center of the plate
            self.create_text(name_text_x, name_text_y, text=card[0].name,
                                fill= 'white', anchor=tk.W, font=self.font,
                                tags=(card[0].id, 'card_name'))

            
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
        self.wid = DeckCanvas(self, width=350, height=800)
        self.wid.pack(fill=tk.BOTH, expand=tk.TRUE)
        deck = load_deck_from_sql(self.cursor, 2)
        self.wid.set_deck(deck)
        #self.wid.set_deck(2)
    
    def on_close(self):
        self.db.close()
        self.master.destroy()
        
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()