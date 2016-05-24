#GUI imports
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import scrolledtext
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
def card_from_row(row):
    return Card(row['id'], row['name'], row['rarity'], 
    row['cost'], row['attack'], row['health'])

def load_deck_from_sql(cursor, id):
    sql_str = sql_select_cards_from_deck.format('deck_'+str(id))
    rows = cursor.execute(sql_str).fetchall()
    deck = {}
    for row in rows:
        tmp = cursor.execute(sql_select_card_by_id, (row['card'],)).fetchone()
        card = card_from_row(tmp)
        deck[card.id] = (card, row['num'])
    return deck
    
    
def save_deck_to_sql(cursor, deck, table):
    insert_str = sql_insert_card_into_deck.format(table)
    select_str = sql_select_card_from_deck.format(table)
    update_str = sql_update_card_in_deck.format(table)
    for card in deck.values():
        row = cursor.execute(select_str, ('%' + card[0].id +'%',)).fetchone()
        if row is None:
            cursor.execute(insert_str, (card[0].id, card[1]))
        else:
            cursor.execute(update_str, (card[1],'%' + card[0].id +'%'))
            print('Updated ' + card[0].id + 'to ' + str(card[1]))
        
class HeroClassListbox(tk.Listbox):
        def __init__(self, master, *args, **kwargs):
            tk.Listbox.__init__(self, master,  height=9)
            vals = list(hs.hero_dict.values())
            for v in vals:
                self.insert(tk.END, v)         
# A deck will just be a dictionary with the value being 
class DeckTreeview(ttk.Treeview):
    def __init__(self, master, cursor, *args, **kwargs):
        ttk.Treeview.__init__(self, master, 
                            columns=('cost', 'name', 'num'), 
                            displaycolumns=('cost name num'),
                            show = 'headings')
        self.cursor = cursor
        self.column("name", width=150)
        self.column("num", width=15)
        self.column("cost", width=15)
        self.heading("name", text="Name")
        self.heading("num", text="#")
        self.heading("cost", text='Cost')
        self.bind("<Double-1>", self._on_double_click)
        self.tag_configure('common', background='gray')
        self.tag_configure('played', background='dim gray')
        self.tag_configure('drawn', foreground = 'OliveDrab4')
        self.tag_configure('rare', background='blue')
        self.tag_configure('epic', background='purple')
        self.tag_configure('legend', background='goldenrod')
        self.enable_building = True
        #self.reset_view()
        self.deck = {}
    
    def set_deck(self, deck):
        self.reset_view()
        
    def _on_double_click(self, event):
        if self.enable_building == True:
            sel = self.selection()
            if len(sel) > 0:
                item = self.selection()[0]
                self.remove_card(item)
        
    def add_card(self, card):
        if card not in self.deck:
            c = self.cursor.execute(sql_select_card_by_id, ('%' + card +'%',)).fetchone()
            if c is not None:
                cc = card_from_row(c)
                self.deck[card] = [cc, 1]
                #Update display
                self.insert('', 'end', cc.id, values=(str(cc.cost), cc.name, '1'))
                return
        else:
            cc = self.deck[card][0]
            n = self.deck[card][1]
            if n < 2:
                self.deck[card][1] += 1
                self.item(cc.id, values=(cc.cost, cc.name, '2'))
                return
        return
        
    def remove_card(self, card):
        if card in self.deck:
            cc = self.deck[card][0]
            n = self.deck[card][1]
            if n > 1:
                self.deck[card][1] -= 1
                self.item(cc.id, values=(cc.cost, cc.name, '1'))
            else:
                self.delete(card)
        
    def card_played(self, card):
        if card in self.deck:
            if self.tag_has('played', card) is 1:
                values = self.item(card, 'values')
                self.item(card, values=(values[0], values[1], str(int(values[2])-1)))
                return
            else:
                tags = self.item(card, 'tags')
                tags= [tags, 'played']
                self.item(card, tags=tags)
                values = self.item(card, 'values')
                self.item(card, values=(values[0], values[1], str(int(values[2])-1)))
                return
        
    def card_drawn(self, card):
        if card in self.deck:
            if self.tag_has('drawn', card) is 1:
                return
            else:
                tags = self.item(card, 'tags')
                tags= [tags, 'drawn']
                self.item(card, tags=tags)
                return
            
    def card_shuffled(self, card):
        if card in self.deck:
            print(card)
            print(self.tag_has('drawn', card))
            if self.tag_has('drawn', card) is 1:
                print(card + 'was drawn')
                tags = self.item(card, 'tags')
                print(tags)
                new_tags = []
                for tag in tags:
                    if tag == 'drawn':
                        continue
                    else:
                        new_tags.append(tag)
                print(new_tags)
                self.item(card, tags=new_tags)
                return
            else:
                return
        
    def reset_view(self):
        self.delete(*self.get_children())
        c_sorted = sorted(self.deck.values(), key = lambda x: (x[0].cost, x[0].name, x[1]))
        for val in c_sorted:
            card = val[0]
            n = val[1]
            self.insert("", 'end', card.id, values=(str(card.cost), card.name, str(n)))
            self.item(card.id, tags='')
        
    def get_num_cards(self):
        i = 0
        for v in self.deck.values():
            i += v[1]
        return i

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
        frame = ttk.Label(self, text='Select a class:')
        frame.pack(fill=tk.X, expand=0)
        self._hero_class_list = HeroClassListbox(self)
        self._hero_class_list.pack(fill=tk.X, expand=0)
        frame = ttk.Label(self, text='Enter Card Name:')
        frame.pack(fill=tk.X, expand=0)
        self._card_entry = hs.AutocompleteCardEntry(self, self.cursor)
        self._card_entry.pack(fill=tk.X, expand=0)
        self._card_entry.bind_card_cb(self._card_picked)
        self._deck_treeview = DeckTreeview(self, self.cursor)
        self._deck_treeview.pack(fill=tk.BOTH, expand=1)
        frame = ttk.Label(self, text='Enter Deck Name:')
        frame.pack(fill=tk.X, expand=0)
        self._deck_name_entry = ttk.Entry(self)
        self._deck_name_entry.pack(fill=tk.X, expand=0)
        self._save_deck_btn = ttk.Button(self, text = 'Save', command= self._btn_save)
        self._save_deck_btn.pack(fill=tk.X, expand=0)
    
    def _btn_save(self):
        if self._deck_treeview.get_num_cards() > 30:
            print('Too many cards')
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
                save_deck_to_sql(self.cursor, self._deck_treeview.deck, table_name)
                return
        
    def _card_picked(self, card):
        cards = self.cursor.execute(sql_select_card_by_name, ('%' + card +'%',)).fetchall()
        if cards is not None:
            for c in cards:
                if c['name'] == card:
                    self._deck_treeview.add_card(c['id'])

class Application(ttk.Frame):
    def __init__(self, master=None):
        # Initialize
        ttk.Frame.__init__(self, master)
        self.master = master
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        #Get our configuation and set up logging
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
        self.config = configparser.ConfigParser()
        if os.path.isfile('config.ini') is False:
            logging.warn('config.ini is missing, falling back on defaults')
        else:
            self.config.read('config.ini')
        
        #Initialize the gui
        self._init_database()
        self._create_widgets()
        self._create_menu()
        self._start_tracking_thread()
        self._update_gui()
        self._refresh_deck_list()
        self._reset_game_state()
        self.active_deck = None
        
    def on_close(self):
        self._end_tracking_thread()
        self.db.commit()
        self.cursor.close()
        self.db.close()
        self.master.destroy()

    def _create_widgets(self):
        self._create_notebook()

    def _create_menu(self):
        menubar = tk.Menu(self.master)
        self.master['menu'] = menubar
        menu_file = tk.Menu(menubar)
        menu_edit = tk.Menu(menubar)
        menu_file.add_separator()
        menubar.add_cascade(menu=menu_file, label='File')
        menubar.add_cascade(menu=menu_edit, label='Edit')
        menu_file.add_command(label='Exit', command=self._menu_exit)
        menu_edit.add_command(label='Preferences', command=self._menu_exit)
        
    def _menu_exit(self):
        self.master.quit()
        
    def _empty(self):
        pass
        
    def _create_notebook(self):
        self._notebook = ttk.Notebook(master=self, height=600, width=800)
        self._deck_frame = ttk.Frame(self._notebook)
        self._stats_frame = ttk.Frame(self._notebook)
        self._data_frame = ttk.Frame(self._notebook)
        self._card_stats_frame = ttk.Frame(self._notebook)
        self._debug_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._deck_frame, text = 'Decks')
        self._notebook.add(self._stats_frame, text = 'Statistics')
        self._notebook.add(self._data_frame, text = 'Data')
        self._notebook.add(self._card_stats_frame, text = 'Card Statistics')
        self._notebook.add(self._debug_frame, text = 'Debug')
        self._notebook.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        #Set up resizing
        self._notebook.columnconfigure(0, weight=1)
        self._notebook.rowconfigure(0, weight=1)
        self._debug_frame.columnconfigure(0, weight=1)
        self._debug_frame.rowconfigure(0, weight=1)
        self._deck_frame.columnconfigure(0, weight=1)
        self._deck_frame.rowconfigure(0, weight=1)
        self._card_stats_frame.columnconfigure(0, weight=1)
        self._card_stats_frame.rowconfigure(0, weight=1)
        #Create each interface
        self._create_debug_frame()
        self._create_card_stats_frame()
        self._create_deck_frame()
        
    def _create_debug_frame(self):
        pw = ttk.PanedWindow(self._debug_frame, orient=tk.HORIZONTAL)
        pw.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        pw.columnconfigure(0, weight=1)
        pw.rowconfigure(0, weight=1)
        f1 = ttk.LabelFrame(pw, text='Game State')
        #f2 = ttk.LabelFrame(pw,text='Debug Output')
        self._debug_tree = ttk.Treeview(f1)
        self._debug_tree.pack(fill=tk.BOTH, expand=1)
        self._debug_text = tk.scrolledtext.ScrolledText(pw)
        self._debug_text.pack(fill=tk.BOTH, expand=1)
        pw.add(f1)
        pw.add(self._debug_text)
        
    def _create_card_stats_frame(self):
        self._card_stats_entry = hs.AutocompleteCardEntry(self._card_stats_frame,
        self.cursor)
        self._card_stats_entry.grid(column=0, row=0, sticky=(tk.N,tk.W))
        
    def _create_deck_frame(self):
        pw = ttk.PanedWindow(self._deck_frame, orient=tk.HORIZONTAL)
        pw.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        pw.columnconfigure(0, weight=1)
        pw.rowconfigure(0, weight=1)
        f1 = ttk.LabelFrame(pw, text='Decks')
        f2 = ttk.LabelFrame(pw,text='Tracking')
        self._deck_new_btn = ttk.Button(f1, text="New Deck", command=self._deck_new)
        self._deck_new_btn.pack(fill=tk.X)
        self._deck_edit_btn = ttk.Button(f1, text="Edit Deck", command=self._deck_edit)
        self._deck_edit_btn.pack(fill=tk.X)
        self._deck_del_btn = ttk.Button(f1, text="Delete Deck", command=self._deck_del)
        self._deck_del_btn.pack(fill=tk.X)
        self._deck_tree = ttk.Treeview(f1, columns=('cls', 'name', 'tags'), displaycolumns=('cls name tags'), show='headings')
        #self._deck_tree.column("#0", width=10)
        self._deck_tree.bind("<Double-1>", self._deck_list_dbl_click)
        self._deck_tree.column("cls", width=50)
        self._deck_tree.column("name", width=100)
        self._deck_tree.column("tags", width=50)
        self._deck_tree.heading("cls", text="Class")
        self._deck_tree.heading("name", text="Name")
        self._deck_tree.heading("tags", text="Tags")
        self._deck_tree.pack(fill=tk.BOTH, expand=1)
        pw2 = ttk.PanedWindow(f2, orient=tk.HORIZONTAL)
        pw2.pack(fill=tk.BOTH, expand=1)
        self._deck_treeview = DeckTreeview(pw2, self.cursor)
        self._deck_treeview.enable_building = False
        #self._deck_treeview.pack(fill=tk.BOTH, expand=1)
        self._oppon_deck_treeview = DeckTreeview(pw2, self.cursor)
        self._oppon_deck_treeview.enable_building = False
        # self._deck_treeview.add_card('BRM_002')
        # self._deck_treeview.card_drawn('BRM_002')
        # self._deck_treeview.card_played('BRM_002')
        pw.add(f1)
        pw.add(f2)
        pw2.add(self._deck_treeview)
        pw2.add(self._oppon_deck_treeview)
    
    def _init_database(self):
        self.db = sqlite3.connect('stats.db')
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
    
    def _start_tracking_thread(self):
        self._q = queue.Queue()
        self._exit_flag = threading.Event()
        path = r'C:\Program Files (x86)\Hearthstone\Logs\Power.log'
        self._tracking_thread = threading.Thread(target=hs.thread_func, 
        args=(path, self._exit_flag, self._q))
        self._tracking_thread.start()
    
    def _end_tracking_thread(self):
        self._exit_flag.set()
        self._tracking_thread.join()
    
    def _update_gui(self):
        try:
            while 1:
                tmp = self._q.get_nowait()
                self._handle_event(tmp)
                self.update_idletasks()
        except queue.Empty:
            pass
        self.after(100, self._update_gui)
        
    def _check_db_exists(self):
        return os.path.isfile()

    def _handle_event(self, event):
        etype = event[0]
        data = event[1]
        if etype == hs.EventType.CardPlayed:
            if data.player == self.players['local'].id:
                self._debug_text.insert(tk.END, 
                'The local player just played {0} on turn {1}\n'.format(data.cardId, data.turn), 
                (None,))
                self._deck_treeview.card_played(data.cardId)
            else:
                self._debug_text.insert(tk.END, 
                'The foreign player just played {0} on turn {1}\n'.format(data.cardId, data.turn), 
                (None,))
                self._oppon_deck_treeview.add_card(data.cardId)
            self._debug_text.see(tk.END)
            self.cards_played.append(data)
            return
        elif etype == hs.EventType.CardDrawn:
            self._debug_text.insert(tk.END, 
            'The local player just drew {0} on turn {1}\n'.format(data.cardId, data.turn), 
            (None,))
            self._deck_treeview.card_drawn(data.cardId)
            return
        elif etype == hs.EventType.CardShuffled:
            self._debug_text.insert(tk.END, 
            'The local player just shuffled {0}\n'.format(data.cardId), 
            (None,))
            self._deck_treeview.card_shuffled(data.cardId)
            return
        elif etype == hs.EventType.GameEnd:
            self._debug_text.insert(tk.END, 
            'The game just ended\n', 
            (None,))
            self._write_game(data)
            self._deck_treeview.reset_view()
            return
        elif etype == hs.EventType.GameStart:
            self.players = data.players
            local = self.players['local']
            foreign = self.players['foreign']
            self._debug_text.insert(tk.END, 
            'The local player is {0} [id = {1}]\n'.format(local.name, local.id),
            (None,))
            self._debug_text.insert(tk.END, 
            'The foreign player is {0} [id = {1}]\n'.format(foreign.name, foreign.id),
            (None,))
            return
        else:
                return
    def _deck_new(self):
        win = tk.Toplevel(takefocus=True)
        dc = DeckCreator(self.cursor, master=win)
        self.wait_window(win)
        self.db.commit()
        #Refresh deck list
        self._refresh_deck_list()
        
    def _write_game(self, gameoutcome):
        # Check if we have seen the opponent before
        local = self.players['local']
        foreign = self.players['foreign']
        oppid = self.cursor.execute(sql_find_opponent, (foreign.high, foreign.low)).fetchone()
        if oppid is None:
            self.cursor.execute(sql_insert_opponent, (foreign.name,foreign.high, foreign.low))
            oppid = self.cursor.lastrowid
        else:
            oppid = oppid['id']
        if self.active_deck is not None:
            #We now have the player id, so we can write the match information
            # First we need to get the correct hero information
            local_hero = self.cursor.execute(sql_select_hero_by_name, 
                            ('%' + local.hero_name + '%',)).fetchone()
            foreign_hero = self.cursor.execute(sql_select_hero_by_name, 
                            ('%' + foreign.hero_name + '%',)).fetchone()
            # submit the data                
            date = datetime.datetime.now()
            
            sql_data = (oppid, gameoutcome.first, gameoutcome.won, 
            gameoutcome.duration, int(gameoutcome.turns),
            date, foreign_hero['id'], local_hero['id'], self.active_deck)
            self.cursor.execute(sql_insert_match, sql_data)
            matchid = self.cursor.lastrowid
            
            #submit the cards
            for card in self.cards_played:
                local_player = False
                if card.player == local.id:
                    local_player = True
                self.cursor.execute(sql_insert_card, (matchid,
                                card.cardId, card.turn, local_player))
        self.db.commit()
        self._reset_game_state()
        

    def _reset_game_state(self):
        self.cards_played = []
        self._oppon_deck_treeview.deck = {}
        self._oppon_deck_treeview.reset_view()
        self.players = None
        
    def _refresh_deck_list(self):
        rows = self.cursor.execute(sql_select_all_decks).fetchall()
        if rows is not None:
            self._deck_tree.delete(* self._deck_tree.get_children())
            for row in rows:
                self._deck_tree.insert('', 'end', row['id'], 
                values=('', row['name'], ''))
                
    def _deck_list_dbl_click(self, event):
        #Load the deck for the tracker
        sel = self._deck_tree.selection()
        if len(sel) > 0:
            item = self._deck_tree.selection()[0]
            self._deck_treeview.deck = load_deck_from_sql(self.cursor, item)
            self._deck_treeview.reset_view()
            self.active_deck = item
        return
    
    def _deck_del(self):
        sel = self._deck_tree.selection()
        if len(sel) > 0:
            item = self._deck_tree.selection()[0]
            result = tk.messagebox.askyesno("Delete Deck?","Are you sure you want to delete?")
            if result is True:
                self.cursor.execute(sql_delete_deck, (item,))
                self._refresh_deck_list()
                return
            else:
                return
    def _deck_edit(self):
        sel = self._deck_tree.selection()
        if len(sel) > 0:
            item = self._deck_tree.selection()[0]
            win = tk.Toplevel(takefocus=True)
            dc = DeckCreator(self.cursor, master=win)
            dc.update_deck = True
            dc.deck_id = item
            dc._deck_treeview.deck = load_deck_from_sql(self.cursor, item)
            dc._hero_class_list.get(0)
            dc._hero_class_list.selection_set
            dc._deck_treeview.reset_view()
            self.wait_window(win)
            dc.update_deck = False
            dc.deck_id = None
            self.db.commit()
            #Refresh deck list
            self._refresh_deck_list()
        return

root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()