import tkinter as tk
from tkinter import ttk
import configparser
import matplotlib
from numpy import arange, sin, pi, cumsum
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import pdb
import AsyncTKText
import threading
import hslog
import time
import queue
matplotlib.use('TkAgg')

#Create threading functions for log parsing
def log_watching(*args):
    # Grab the important params
    text = args[0]
    exit_flag = args[1]
    parsers = args[2]
    fp = args[3]

    # Create the watcher and begin watching
    watcher = hslog.LogWatcher(parsers)
    watcher.watch(fp, exit_flag)

def log_parsing(*args):
    # Grab important params
    text = args[0]
    exit_flag = args[1]
    parser_created = args[2]
    parser = args[3]
    plot_data = args[4]

    observer = hslog.LogObservable()
    sc = hslog.StatCollector(text, plot_data)
    observer.register(sc)
    parser.append(observer)

    parser_created.set()

    while 1:
        if exit_flag.is_set():
            #clean up
            return
        for p in parser:
            p.update()
        time.sleep(0.1)

class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.master = master
        self.matches = queue.Queue()
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()
        self.configure()
        self.create_threads()
        self.update_plots()
        

    def on_close(self):
        self.config['window']['last_geom'] = self.last_geom
        with open('config.ini', 'w') as file:
            self.config.write(file)
        self.destroy_threads()
        self.master.destroy()

    def create_widgets(self):
        # Create the host paned window
        pw1 = ttk.PanedWindow(self.master, orient=tk.VERTICAL)
        pw1.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.W, tk.E))

        # Create the bottom and top paned widgets
        top_pane = ttk.PanedWindow(pw1, orient=tk.HORIZONTAL)
        bottom_pane = AsyncTKText.AsyncTKText(pw1, width=100, height=20)
        self.text = bottom_pane
        # Add the panes to the master panedwindow
        pw1.add(top_pane)
        pw1.add(bottom_pane)

        # Create the widgets in the top paned window
        tl_tag_label_frame = ttk.LabelFrame(top_pane, text='Tags')
        tl_tag1_combobox = ttk.Combobox(tl_tag_label_frame, values=['Zoolock'])
        tl_tag_label_frame2 = ttk.LabelFrame(top_pane, text='Tags')
        tl_tag1_combobox2 = ttk.Combobox(
            tl_tag_label_frame, values=['Zoolock'])
        tr_notebook = ttk.Notebook(top_pane, height=400, width=600)
        tr_tab1 = ttk.Frame(tr_notebook)
        tl_tag_label_frame.grid(column=0, row=0, sticky=(tk.N, tk.W))
        tl_tag1_combobox.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E))
        tr_notebook.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E))

        # Add to the top paned window
        top_pane.add(tl_tag_label_frame)
        top_pane.add(tr_notebook)

        # Fix resizing
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        pw1.rowconfigure(0, weight=1)
        pw1.columnconfigure(0, weight=1)
        tl_tag_label_frame.rowconfigure(0, weight=1)
        tl_tag_label_frame.columnconfigure(0, weight=1)

        # Setup a canvas for plotting
        f = Figure(figsize=(5, 4), dpi=100)
        a = f.add_subplot(111)
        t = range(10)
        self.axis = a

        a.plot(t)
        canvas = FigureCanvasTkAgg(f, master=tr_tab1)
        self.canvas = canvas
        canvas.show()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        toolbar = NavigationToolbar2TkAgg(canvas, tr_tab1)
        toolbar.update()
        canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        tabid = tr_notebook.add(tr_tab1)
        tr_notebook.tab(0, text='Win-Loss Info')

    def configure(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.last_geom = self.config['window']['last_geom']
        self.master.geometry(self.last_geom)
        self.master.bind('<Configure>', self.on_configure)

    def on_configure(self, event):
        if type(event.widget) == tk.Tk:
            xstr = '+' if event.x > 0 else '-'
            xstr += str(event.x)
            ystr = '+' if event.y > 0 else '-'
            ystr += str(event.y)
            self.last_geom = '{0}x{1}{2}{3}'.format(
                event.width, event.height, xstr, ystr)
            print(self.last_geom)

    def create_threads(self):
        self.par_exit_flag = threading.Event()
        self.wat_exit_flag = threading.Event()
        parser_created = threading.Event()
        parser = []
        self.par_thread = threading.Thread(target=log_parsing, args=(self.text, self.par_exit_flag, parser_created, parser, self.matches))
        self.par_thread.start()
        parser_created.wait()
        filepath = r"C:\Program Files (x86)\Hearthstone\Logs\Power.log"
        self.wat_thread = threading.Thread(target=log_watching, args=(self.text,  self.wat_exit_flag, parser, filepath))
        self.wat_thread.start()
    
    def destroy_threads(self):
        self.par_exit_flag.set()
        self.wat_exit_flag.set()
        self.wat_thread.join()
        self.par_thread.join()

    def update_plots(self):
        try:
            tmp = self.matches.get_nowait()
            tmp = cumsum(tmp)
            self.axis.clear()
            self.axis.plot(tmp, 'ko-')
            self.canvas.show()
            self.after(2000, self.update_plots)
        except queue.Empty:
            pass

root = tk.Tk()
root.title('ValueTracker')
app = Application(master=root)
app.mainloop()