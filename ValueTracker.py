from AsyncTKText import AsyncTKText
from logparser import HSLogParser
import logging
from tkinter import *
from tkinter import ttk
import threading
import time
import sqlite3
import os
# Path to power.log
path_to_power_log = r"C:\Program Files (x86)\Hearthstone\Logs\Power.log"
#path_to_power_log = "../power.log"
def log(*args):
    logging.basicConfig(level=logging.INFO, format = '%(asctime)-15s %(message)s')
    logger = logging.getLogger(__name__)
    file = open(path_to_power_log, 'r')
    widget = args[0]
    exit_flag = args[1]
    parser = args[2]
    counter = 0
    db = sqlite3.connect('stats.db')
    parser.set_db(db)
    old_size = os.stat(path_to_power_log).st_size
    file.seek(0,2)
    while 1:
        if exit_flag.isSet():
            logger.info('Exiting the logging thread')
            file.close()
            return
        where = file.tell()
        line = file.readline()
        # No new line
        if not line:
            time.sleep(1)
            file.seek(where)
            counter += 1
            if counter > 5:
                file.close()
                logger.info('Reopening the power log')
                size = os.stat(path_to_power_log).st_size
                file = open(path_to_power_log, 'r')
                if size == old_size or size > old_size:
                    file.seek(where)
                old_size = size
                counter = 0
        else:
            counter -= 1
            parser.parse_line(line)

# GUI Code
root=Tk()
root.title('ValueTracker')
text=AsyncTKText(root, width=100, height=20)
text.grid(column=0, row=0, sticky=(N, S, E, W))
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

parser = HSLogParser(text)
# Use an event to sync with the log monitoring thread
exit_flag=threading.Event()
# Start watching the log
t=threading.Thread(target=log, args=(text, exit_flag, parser))
t.start()

# Enter the UI
root.mainloop()
# Exited the UI, let the thread know
exit_flag.set()
# Wait for the thread to exit
t.join()
