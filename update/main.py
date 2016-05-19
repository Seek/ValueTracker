import tkinter as tk
from tkinter import ttk
import configparser

class Application(ttk.Frame):
    def __init__(self, master=None):
        # Initialize
        ttk.Frame.__init__(self, master)
        self.master = master
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
        self._notebook = ttk.Notebook(master=self.master, height=600, width=800)
        self._deck_frame = ttk.Frame(self._notebook)
        self._stats_frame = ttk.Frame(self._notebook)
        self._data_frame = ttk.Frame(self._notebook)
        self._card_stats_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._deck_frame, text = 'Tracking')
        self._notebook.add(self._stats_frame, text = 'Statistics')
        self._notebook.add(self._data_frame, text = 'Data')
        self._notebook.add(self._card_stats_frame, text = 'Card Statistics')
        self._notebook.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))
    
root = tk.Tk()
root.title('ValueTracker')
root.option_add('*tearOff', False)
app = Application(master=root)
app.mainloop()