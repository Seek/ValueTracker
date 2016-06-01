# GUI imports
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import font
from tkinter import simpledialog
# Functional imports
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
# Local code
import hs
import copy
import json
import PIL
from PIL import Image, ImageFont, ImageDraw, ImageColor, ImageTk
import re
from controls import *
import db_ops
import os
import importing

CONFIG_FILE = 'config.json'

class Application(ttk.Frame):
    def __init__(self, master=None, **kwargs):
        # Initialize
        ttk.Frame.__init__(self, master, **kwargs)
        self.master = master
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.pack(fill=tk.BOTH, expand=tk.TRUE)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

        # Get our configuation and set up logging
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s')
        self.app_config = {}
        if os.path.isfile(CONFIG_FILE) is False:
            logging.warning(
                '{0} is missing, falling back on defaults'.format(CONFIG_FILE))
        else:
            with open(CONFIG_FILE, 'r') as file:
                self.app_config = json.load(file)
        
        self._tracking_thread = None
        
        # Initialize the gui
        self._init_database()
        self._create_widgets()
        self._create_menu()
        self._start_tracking_thread()
        self._update_gui()
        self.load_settings()
        self.master.deiconify()
        self._refresh_deck_list()
        self._reset_game_state()
        self.active_deck = None

    def load_settings(self):
        # Restore the old window
        # if 'main_window_geom' in self.app_config:
        #     last_geom = self.app_config["main_window_geom"]
        #     self.master.geometry(last_geom)
        if 'local_deck_geom' in self.app_config:
            last_geom = self.app_config["local_deck_geom"]
            self._deck_tracker.win.geometry(last_geom)
            self._deck_tracker.deck_canvas.refresh_canvas()
        if 'foreign_deck_geom' in self.app_config:
            last_geom = self.app_config["foreign_deck_geom"]
            self._foreign_deck_tracker.win.geometry(last_geom)
            self._foreign_deck_tracker.deck_canvas.refresh_canvas()
        if 'deck_bar_font' in self.app_config:
            font_size = 16
            if "deck_bar_font_size" in self.app_config:
                font_size = self.app_config['deck_bar_font_size']
            self._deck_tracker.deck_canvas.pil_font = ImageFont.truetype(
                                    self.app_config['deck_bar_font'], font_size)
            self._deck_tracker.deck_canvas.refresh_canvas()
            self._foreign_deck_tracker.deck_canvas.refresh_canvas()
    def save_settings(self):
        try:
            self.app_config['main_window_geom'] = self.master.geometry()
            self.app_config['local_deck_geom'] = self._deck_tracker.win.geometry()
            self.app_config[
                'foreign_deck_geom'] = self._foreign_deck_tracker.win.geometry()
        except:
            pass
        with open(CONFIG_FILE, 'w') as file:
            json.dump(self.app_config, file, indent=4, sort_keys=True)

    def on_close(self):
        self.save_settings()
        self._end_tracking_thread()
        self.db.commit()
        self.cursor.close()
        self.db.close()
        self.master.destroy()

    def _create_widgets(self):
        self.pw = ttk.PanedWindow(self, width = self['width'],
        height = self['height'], orient = tk.HORIZONTAL)
        self.pw.grid(column=0, row=0, sticky='nsew')
        deck_win_frame = ttk.Frame(self.pw, width = int(self['width'] * 0.2),
                            height=self['height'])
        
        self._notebook = ttk.Notebook(self.pw, width=int(self['width']*0.7), height=self['height'])
        deck_filter_lblframe = ttk.LabelFrame(deck_win_frame, text='Deck Filter', width = 200, height = 74, pad=4)
        deck_select_lblframe = ttk.LabelFrame(deck_win_frame, text='Decks', width = 200, height = 390, pad=4)
        
        
        deck_select_lblframe.grid(row=5, column=0, sticky='nwse')
        self.deck_filter_widget = PlayerClassWidget(deck_filter_lblframe, width= 5*32, height = 64)
        self.deck_filter_widget.on_class_selected.append(self.on_deck_filter)
        ttk.Button(deck_win_frame, text='Import Deck', command=self.on_import_deck).grid(column=0, row=0, sticky='ew')
        ttk.Button(deck_win_frame, text='New Deck', command=self._deck_new).grid(column=0, row=1, sticky='ew')
        ttk.Button(deck_win_frame, text='Edit Deck', command=self._deck_edit).grid(column=0, row=2, sticky='ew')
        ttk.Button(deck_win_frame, text='Delete Deck', command=self._deck_del).grid(column=0, row=3, sticky='ew')
        self.deck_filter_widget.grid(row=4, column=0, sticky='nwe')
        self.deck_select_widget = DeckSelectWidget(deck_select_lblframe, width = 150,
                            height=390)
        self.deck_select_widget.on_deck_selected.append(self.on_deck_select)
        
        self.deck_select_widget.grid(row=0, column=0, sticky='nwse')
        deck_filter_lblframe.grid(row=4, column=0, sticky='nwe')
        # Config notebook
        self._notebook .columnconfigure(0, weight=1)
        self._notebook .rowconfigure(0, weight=1)
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
        
        self._deck_frame = ttk.Frame(self._notebook)
        self._stats_frame = ttk.Frame(self._notebook)
        self._data_frame = ttk.Frame(self._notebook)
        self._card_stats_frame = ttk.Frame(self._notebook)
        self._debug_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._deck_frame, text='Decks')
        self._notebook.add(self._stats_frame, text='Statistics')
        self._notebook.add(self._data_frame, text='Data')
        self._notebook.add(self._card_stats_frame, text='Card Statistics')
        self._notebook.add(self._debug_frame, text='Debug')
        self._notebook.columnconfigure(0, weight=1)
        self._notebook.rowconfigure(0, weight=1)
        self._debug_frame.columnconfigure(0, weight=1)
        self._debug_frame.rowconfigure(0, weight=1)
        self._deck_frame.columnconfigure(0, weight=1)
        self._deck_frame.rowconfigure(0, weight=1)
        self._card_stats_frame.columnconfigure(0, weight=1)
        self._card_stats_frame.rowconfigure(0, weight=1)
        self._stats_frame.columnconfigure(0, weight=1)
        self._stats_frame.rowconfigure(0, weight=1)
        # Create each interface
        self._create_debug_frame()
        self._create_card_stats_frame()
        self._create_deck_frame()
        self._create_stats_frame()
        self.pw.add(deck_win_frame)
        self.pw.add(self._notebook )
        
    # def _create_widgets(self):
    #     self._create_notebook()

    def _create_menu(self):
        menubar = tk.Menu(self.master)
        self.master['menu'] = menubar
        menu_file = tk.Menu(menubar)
        menu_edit = tk.Menu(menubar)
        #menu_file.add_separator()
        menubar.add_cascade(menu=menu_file, label='File')
        menubar.add_cascade(menu=menu_edit, label='Edit')
        menu_file.add_command(label='Reset Tracking Thread', command=self._menu_rest_tracking)
        menu_file.add_command(label='Exit', command=self._menu_exit)
        menu_edit.add_command(label='Reload Configuration', command=self._reload_config)
        menu_edit.add_command(label='Preferences', command=self._menu_preferences)
        menu_edit.add_command(label='Set path to Hearthstone logs', command=self._set_hs_log_path)
        menu_edit.add_command(label='Set path to database', command=self._set_database_path)
        menu_edit.add_command(label='Update card database', command=self._update_card_table)
    def _menu_exit(self):
        self.on_close()
        
    def _reload_config(self):
        if os.path.isfile(CONFIG_FILE) is False:
            logging.warning(
                '{0} is missing, falling back on defaults'.format(CONFIG_FILE))
        else:
            with open(CONFIG_FILE, 'r') as file:
                self.app_config = json.load(file)
        self.load_settings()
        
    def _menu_preferences(self):
        return
        
    def _menu_rest_tracking(self):
        self._end_tracking_thread()
        self._start_tracking_thread()

    def _set_hs_log_path(self):
        path = tk.filedialog.askdirectory(title="Set path to Hearthstone's log files")
        if path != '':
            self.app_config['path_to_hs_logs'] = path
            self._end_tracking_thread()
            self._start_tracking_thread()
            
    def _set_database_path(self):
        path = tk.filedialog.askopenfilename(title="Set path to Hearthstone's log files")
        if path != '':
            self.app_config['path_to_db'] = path
            
    def _update_card_table(self):
        result = tk.messagebox.askyesno('Connect to internet?',
                        """May I connect to the hearthstonejson website to download new card definitions?If not, you will be prompted to provide a proper .json file to update""")
        if result == True:
            cards = db_ops.download_cards()
            db_ops.update_cards(self.cursor, cards)
            tk.messagebox.showinfo('Update complete', 'The update was completed')
            self.db.commit()
        else:
            path = tk.filedialog.askopenfilename(title='Path to cards.json')
            if path != '':
                with open(path, 'r', encoding='utf-8') as f:
                    cards = json.load(f)
                    db_ops.update_cards(self.cursor, cards)
                    tk.messagebox.showinfo('Update complete', 'The update was completed')
                    self.db.commit()
                    self.db.commit()
                        
        
    def _create_notebook(self):
        self._notebook = ttk.Notebook(master=self, height=800, width=1200)
        self._deck_frame = ttk.Frame(self._notebook)
        self._stats_frame = ttk.Frame(self._notebook)
        self._data_frame = ttk.Frame(self._notebook)
        self._card_stats_frame = ttk.Frame(self._notebook)
        self._debug_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._deck_frame, text='Decks')
        self._notebook.add(self._stats_frame, text='Statistics')
        self._notebook.add(self._data_frame, text='Data')
        self._notebook.add(self._card_stats_frame, text='Card Statistics')
        self._notebook.add(self._debug_frame, text='Debug')
        self._notebook.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        # Set up resizing
        self._notebook.columnconfigure(0, weight=1)
        self._notebook.rowconfigure(0, weight=1)
        self._debug_frame.columnconfigure(0, weight=1)
        self._debug_frame.rowconfigure(0, weight=1)
        self._deck_frame.columnconfigure(0, weight=1)
        self._deck_frame.rowconfigure(0, weight=1)
        self._card_stats_frame.columnconfigure(0, weight=1)
        self._card_stats_frame.rowconfigure(0, weight=1)
        self._stats_frame.columnconfigure(0, weight=1)
        self._stats_frame.rowconfigure(0, weight=1)
        # Create each interface
        self._create_debug_frame()
        self._create_card_stats_frame()
        self._create_deck_frame()
        self._create_stats_frame()

    def _create_stats_frame(self):
        self._deck_stats = DeckStatsCanvas(self.cursor, self._stats_frame)
        self._deck_stats.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))

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
        self._card_stats_entry.grid(column=0, row=0, sticky=(tk.N, tk.W))

    def _create_deck_frame(self):
        f2 = ttk.LabelFrame(self._deck_frame, text='History', pad=6)
        f2.grid(column=0, row=0, sticky='nsew')
        self._deck_history = DeckStatisticsCanvas(self.cursor, f2, width=600)
        self._deck_history.pack(fill=tk.BOTH, expand=tk.TRUE)
        self._deck_history.set_deck(None)
        self._deck_tracker = FloatingDeckCanvas()
        self._foreign_deck_tracker = FloatingDeckCanvas()
        self._deck_treeview = self._deck_tracker.deck_canvas
        self._deck_treeview.pack(fill=tk.BOTH, expand=tk.TRUE)
        self._deck_treeview.editable = False
        self._oppon_deck_treeview = self._foreign_deck_tracker.deck_canvas
        self._oppon_deck_treeview.editable = True

    def _init_database(self):
        self.path_to_db = 'stats.db'
        if 'path_to_db' not in self.app_config:
                logging.info('No path to database set, assuming the default')
        else:
            self.path_to_db = self.app_config['path_to_db']
        self.db = sqlite3.connect(self.path_to_db)
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        if db_ops.check_db_integrity(self.cursor) == False:
            result = tk.messagebox.askyesno('The database is malformed.','Should I make a new one?')
            if result:
                self.db.close()
                os.remove(self.path_to_db)
                db = sqlite3.connect(self.path_to_db)
                db.row_factory = sqlite3.Row
                cursor = db.cursor()
                cursor.executescript(db_ops.database_script)
                db.commit()
                cards = db_ops.download_cards()
                db_ops.update_cards(cursor, cards)
                db.commit()
                self.db = db
                self.cursor = cursor
            else:
                tk.messagebox.showwarning('Important Warning!',
                                    'Using a malformed database will result in undefined behavior\n')
                
            

    def _start_tracking_thread(self):
        self._q = queue.Queue()
        self._exit_flag = threading.Event()
        if 'path_to_hs_logs' not in self.app_config:
            tk.messagebox.showerror(
                'Path to Hearthstone log directory not configured!',
                "Please set the path to your Hearthstone log files. (Under Edit > Set HS log path)"
            )
            return
        else:
            path = self.app_config['path_to_hs_logs']
            path += '/Power.log'
            logging.info('Opening {0}'.format(path))
            self._tracking_thread = threading.Thread(target=hs.thread_func,
                                                    args=(path, self._exit_flag, self._q))
            logging.info('Starting tracking thread')
            self._tracking_thread.start()

    def _end_tracking_thread(self):
        self._exit_flag.set()
        if self._tracking_thread:
            logging.info('Killing tracking thread')
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

    def _handle_event(self, event):
        etype = event[0]
        data = event[1]
        if etype == hs.EventType.CardPlayed:
            if data.player == self.players['local'].id:
                self._debug_text.insert(tk.END,
                                        'The local player just played {0} on turn {1}\n'.format(
                                            data.cardId, data.turn),
                                        (None,))
                self._deck_treeview.card_played(data.cardId)
            else:
                self._debug_text.insert(tk.END,
                                        'The foreign player just played {0} on turn {1}\n'.format(
                                            data.cardId, data.turn),
                                        (None,))
                tmp_card = card_from_id(data.cardId, self.cursor)
                if tmp_card is not None or tmp_card != '':
                    self._oppon_deck_treeview.add_card(tmp_card)
            self._debug_text.see(tk.END)
            self.cards_played.append(data)
            return
        elif etype == hs.EventType.CardDrawn:
            self._debug_text.insert(tk.END,
                                    'The local player just drew {0} on turn {1}\n'.format(
                                        data.cardId, data.turn),
                                    (None,))
            self._deck_treeview.card_drawn(data.cardId)
            return
        elif etype == hs.EventType.CardShuffled:
            self._debug_text.insert(tk.END,
                                    'The local player just shuffled {0}\n'.format(
                                        data.cardId),
                                    (None,))
            self._deck_treeview.card_shuffled(data.cardId)
            return
        elif etype == hs.EventType.GameEnd:
            self._debug_text.insert(tk.END,
                                    'The game just ended\n',
                                    (None,))
            self._write_game(data)
            return
        elif etype == hs.EventType.GameStart:
            self.players = data.players
            local = self.players['local']
            foreign = self.players['foreign']
            self._debug_text.insert(tk.END,
                                    'The local player is {0} [id = {1}]\n'.format(
                                        local.name, local.id),
                                    (None,))
            self._debug_text.insert(tk.END,
                                    'The foreign player is {0} [id = {1}]\n'.format(
                                        foreign.name, foreign.id),
                                    (None,))
            return
        else:
            return

    def _deck_new(self):
        win = tk.Toplevel(takefocus=True)
        win.grid_rowconfigure(0, weight=1)
        win.grid_columnconfigure(0, weight=1)
        dc = DeckCreator(self.cursor, master=win)
        self.wait_window(win)
        self.db.commit()
        # Refresh deck list
        self._refresh_deck_list()

    def _write_game(self, gameoutcome):
        # Check if we have seen the opponent before
        if self.active_deck is not None:
            local = self.players['local']
            foreign = self.players['foreign']
            oppid = self.cursor.execute(
                sql_find_opponent, (foreign.high, foreign.low)).fetchone()
            if oppid is None:
                self.cursor.execute(sql_insert_opponent,
                                    (foreign.name, foreign.high, foreign.low))
                oppid = self.cursor.lastrowid
            else:
                oppid = oppid['id']
            if self.active_deck is not None:
                # We now have the player id, so we can write the match information
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

                # submit the cards
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
        self._deck_treeview.reset_tracking()
        self._oppon_deck_treeview.set_deck({})
        self._deck_history.refresh_canvas()
        self._deck_stats.refresh_canvas()
        self.players = None

    def _refresh_deck_list(self):
        plr_class = self.deck_filter_widget.active_playerclass
        if plr_class == 0:
            decks = self.cursor.execute("SELECT id,name, class FROM deck ORDER BY name ASC").fetchall()
            self.deck_select_widget.set_deck_list(decks)
        else:
            decks = self.cursor.execute("SELECT id,name, class FROM deck WHERE class = ? ORDER BY name ASC", (plr_class, )).fetchall()
            self.deck_select_widget.set_deck_list(decks)

    def _deck_del(self):
        deck = self.deck_select_widget.active_deck
        if deck is not None:
            result = tk.messagebox.askyesno(
                "Delete Deck?", "Are you sure you want to delete?")
            if result is True:
                self.cursor.execute(sql_delete_deck, (deck,))
                self._refresh_deck_list()
                return
            else:
                return

    def _deck_edit(self):
        deck = self.deck_select_widget.active_deck
        if deck is not None:
            win = tk.Toplevel(takefocus=True)
            win.grid_rowconfigure(0, weight=1)
            win.grid_columnconfigure(0, weight=1)
            dc = DeckCreator(self.cursor, master=win)
            dc.update_deck = True
            dc.deck_id = deck
            dc._static_canvas.set_deck(load_deck_from_sql(self.cursor, deck))
            dc.update_num_cards()
            data = self.cursor.execute(
                "SELECT name, class FROM deck WHERE id = ?", (deck,)).fetchone()

            dc._hero_class_list.set_label(int(data['class']))
            dc._deck_name_entry.insert(tk.END, data['name'])
            self.wait_window(win)
            dc.update_deck = False
            dc.deck_id = None
            self.db.commit()
            # Refresh deck list
            self._refresh_deck_list()
            
    def on_deck_filter(self, plr_class):
        if plr_class == 0:
            decks = self.cursor.execute("SELECT id,name, class FROM deck ORDER BY name ASC").fetchall()
            self.deck_select_widget.set_deck_list(decks)
        else:
            decks = self.cursor.execute("SELECT id,name, class FROM deck WHERE class = ? ORDER BY name ASC", (plr_class, )).fetchall()
            self.deck_select_widget.set_deck_list(decks)
            
    def on_deck_select(self, deck):
        # Load the deck for the tracker
        if deck is not None:
            self._deck_treeview.set_deck(
                load_deck_from_sql(self.cursor, str(deck)))
            self.active_deck = deck
            self._deck_history.set_deck(int(deck))
            self._deck_stats.set_deck(int(deck))
        else:
            self.active_deck = None
            self._deck_history.set_deck(None)
            self._deck_stats.set_deck(None)
            self._deck_treeview.set_deck({})
            
    def on_import_deck(self):
        url = tk.simpledialog.askstring('Import a deck', 'Insert a URL from tempostorm.com to import a deck')
        if url != "":
            hero, deck_name, deck = importing.deck_from_tempostorm(url, self.cursor)
            win = tk.Toplevel(takefocus=True)
            win.grid_rowconfigure(0, weight=1)
            win.grid_columnconfigure(0, weight=1)
            dc = DeckCreator(self.cursor, master=win)
            dc._static_canvas.set_deck(deck)
            dc._hero_class_list.set_label(hero)
            dc._deck_name_entry.insert(tk.END, deck_name)
            dc.update_num_cards()
            self.wait_window(win)
            self.db.commit()
            # Refresh deck list
            self._refresh_deck_list()
            
            
root = tk.Tk()
root.withdraw()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()
