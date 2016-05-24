import tkinter as tk
from tkinter import ttk
import queue

#This is a 'pretty' console we can use
class AsyncTKText(tk.Text):
    def __init__(self, parent, **options):
        tk.Text.__init__(self, parent, **options)
        self.scrollbar = ttk.Scrollbar(parent)
        self.scrollbar.grid(column = 1, row = 0, sticky = (tk.N,tk.S,tk.W))
        self.scrollbar.config(command=self.yview)
        self['yscrollcommand']=self.scrollbar.set
        self.tag_config('g', background='DarkOliveGreen1')
        self.tag_config('t2', background='thistle2')
        self.tag_config('b', background='LightCyan2')
        self.q = queue.Queue()
        self.update_text()
    def write(self, line, tags=(None,)):
        self.q.put((line, tags))
    def clear(self):
        self.q.put((None, None))
    def update_text(self):
        try:
            while 1:
                tmp = self.q.get_nowait()
                line = tmp[0]
                if line is None:
                    self.delete(1.0, tk.END)
                else:
                    self.insert(tk.END, str(line) + '\n', tmp[1])

                self.see(tk.END)
                self.update_idletasks()
        except queue.Empty:
            pass
        self.after(100, self.update_text)