#GUI imports
import tkinter as tk
from tkinter import ttk

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
        self.tag_configure('common', background='gray')
        self.tag_configure('played', background='dim gray')
        self.tag_configure('inhand', foreground = 'OliveDrab1')
        self.tag_configure('rare', background='blue')
        self.tag_configure('epic', background='purple')
        self.tag_configure('legend', background='goldenrod')
        self.reset_view()
    
    def set_deck(self, deck):
        self.reset_view()
        
    def add_card(self, card):
        if card not in self.deck:
            c = self.cursor.execute(sql_select_card_by_id, ('%' + card +'%',)).fetchone()
            cc = Card(c['id'], c['name'], c['rarity'], c['cost'], c['attack'], c['health'])
            self.deck['card'] = [cc, 1]
            #Update display
            self.insert('', 'end', cc.id, values=(str(cc.cost), cc.name, '1'))
        else:
            n = self.deck['card']
            if n < 2:
                self.deck['card'][1] += 1
                self.item(self.deck['card'][0].id, values=(cc.name, '2'))
        return
    def remove_card(self, card):
        pass
        
    def card_played(self, card):
        self.item(card, tags=('played',))
        
    def card_drawn(self, card):
        pass
        
    def reset_view(self):
        self.deck = {} 

class DeckCreator(ttk.Frame):
    def __init__(self, cursor, master=None):
        # Initialize
        ttk.Frame.__init__(self, master, width= 800, height = 600)
        self.cursor = cursor
        self.master = master
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._create_widgets(self)
        
    def on_close(self):
        self.master.destroy()

    def _create_widgets(self):
        self._card_entry = hs.AutocompleteCardEntry(self, self.cursor)
        
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
        
    def on_close(self):
        self._end_tracking_thread()
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
        f2 = ttk.LabelFrame(pw,text='Debug Output')
        self._debug_tree = ttk.Treeview(f1)
        self._debug_tree.pack(fill=tk.BOTH, expand=1)
        self._debug_text = tk.Text(f2)
        self._debug_text.pack(fill=tk.BOTH, expand=1)
        pw.add(f1)
        pw.add(f2)
        
    def _create_card_stats_frame(self):
        self._card_stats_entry = hs.AutocompleteCardEntry(self._card_stats_frame,
        self.db.cursor())
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
        self._deck_del_btn = ttk.Button(f1, text="Delete Deck", command=self._deck_del)
        self._deck_del_btn.pack(fill=tk.X)
        self._deck_tree = ttk.Treeview(f1, columns=('cls', 'name', 'tags'), displaycolumns=('cls name tags'), show='headings')
        #self._deck_tree.column("#0", width=10)
        self._deck_tree.column("cls", width=50)
        self._deck_tree.column("name", width=100)
        self._deck_tree.column("tags", width=50)
        self._deck_tree.heading("cls", text="Class")
        self._deck_tree.heading("name", text="Name")
        self._deck_tree.heading("tags", text="Tags")
        self._deck_tree.pack(fill=tk.BOTH, expand=1)
        self._deck_treeview = DeckTreeview(f2, self.db.cursor())
        self._deck_treeview.pack(fill=tk.BOTH, expand=1)
        self._deck_treeview.add_card('BRM_002')
        self._deck_treeview.card_played('BRM_002')
        pw.add(f1)
        pw.add(f2)
    
    def _init_database(self):
        self.db = sqlite3.connect('stats.db')
        self.db.row_factory = sqlite3.Row
    
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
        if etype == hs.EventType.GameStart:
            # Check if we have seen this opponnent before
            # Add them if we have not
            self._debug_text.insert(tk.END, str(event) + '\n', (None,))
            self._debug_text.see(tk.END)
            pass
        elif etype == hs.EventType.CardPlayed:
            # who played the card
            #Display
            self._debug_text.insert(tk.END, str(event) + '\n', (None,))
            self._debug_text.see(tk.END)
            pass
        elif etype == hs.EventType.GameEnd:
            # Get the opponent id
            # get the date
            self._debug_text.insert(tk.END, str(event) + '\n', (None,))
            self._debug_text.see(tk.END)
            pass
    def _deck_new(self):
        pass
        
    def _deck_del(self):
        pass
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()