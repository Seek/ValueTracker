#GUI imports
import tkinter as tk
from tkinter import ttk

import configparser

#Functional imports
import ssl
import urllib.request

# How to pull json from Hearthstone JSON
#  url = "https://api.hearthstonejson.com/v1/latest/enUS/cards.json" // TODO: Add language support
# context = ssl._create_unverified_context()
# req = urllib.request.urlopen(url, context=context)
# f = req.read() // f would contain the json data

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
        #Initialize the gui
        self._create_widgets()
        self._create_menu()
        
    def on_close(self):
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
        self._notebook.add(self._deck_frame, text = 'Tracking')
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
        #Create each interface
        self._create_debug_frame()
        
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
    
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()