import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import font
import sqlite3
import hs
from collections import namedtuple
import pdb
import copy

class DeckCanvas(tk.Canvas):
    def __init__(self, master=None, **kwargs):
        tk.Canvas.__init__(self, master, **kwargs)
        
        # Interactivity
        self.bind("<Button-1>", self._left_click)
        self.bind("<Button-3>", self._right_click)
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
            print(self.active_deck)
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
                    if 'card_name' in tags:
                        self.itemconfigure(item, fill='white')
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
        print(cards_sorted)
        # Start redrawing
        for i, card in enumerate(cards_sorted):
            # Debug coordinates
            print('x1 : {0}, y1 : {1}, x2 : {2}, y2 : {3}'.format(
                0, (i)*frame_height, width, (i+1)*frame_height,
            ))
            # Draw the back plate
            x0 = 0
            y0 = (i)*frame_height
            x1 = width
            y1 = (i+1)*frame_height
            self.create_rectangle(x0, y0, x1, y1,
                                    fill="grey", width=2, tags=(card[0].id, 'frame_plate'))
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