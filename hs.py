import tkinter as tk
from tkinter import ttk
from collections import namedtuple
import sqlite3
from enum import Enum
import re
import datetime
import logging
import os
import time

# Regular expression we rely upon
win_loss_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     TAG_CHANGE Entity=(.+) tag=PLAYSTATE value=(WON|LOST|TIED)'
full_entity_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     FULL_ENTITY - Updating'
show_entity_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     SHOW_ENTITY - Updating'
show_entity_sub_pattern = "Entity=(\[.+?\]) CardID=(.+)"
hero_pattern = r'HERO_0(\d)'
create_game_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     CREATE_GAME'
tag_change_pattern = r"PowerTaskList\.DebugPrintPower\(\) -     TAG_CHANGE"
action_begin_pattern = "PowerTaskList\.DebugPrintPower\(\) - ACTION_START"
action_end_pattern = "PowerTaskList\.DebugPrintPower\(\) - ACTION_END"
action_param_pattern = "Entity=(.+) BlockType=(.+) Index=(.+) Target=(.+)"
entity_pattern = "\[id=(\d+?) cardId= type=(.+?) zone=(.+?) zonePos=(\d+?) player=(\d)\]"
entity_pattern2 = "\[name=(.+?) id=(.+?) zone=(.+?) zonePos=(\d+) cardId=(.+?) player=(\d)\]"
tag_param_pattern = "Entity=(.+) tag=(.+) value=(.+)"
player_pattern = "PowerTaskList\.DebugPrintPower\(\) -         Player"
player_acc_pattern = "EntityID=(\d) PlayerID=(\d) GameAccountId=\[hi=(\d+?) lo=(\d+?)\]"

# Hero to int mappings
hero_dict = {9: 'Priest', 3: 'Rogue', 8: 'Mage', 4: 'Paladin', 1: 'Warrior',
             7: 'Warlock', 5: 'Hunter', 2: 'Shaman', 6: 'Druid'}

hero_dict_names = {v: k for k, v in hero_dict.items()}

class AutocompleteCardEntry(ttk.Entry):
    """ Requires a working database cursor to work """
    def __init__(self, parent, cursor, **kwargs):
        ttk.Entry.__init__(self, parent, **kwargs)
        self.var = self['textvariable']
        self.parent = parent
        self.cursor = cursor
        if self.var == '':
            self.var = self['textvariable'] = tk.StringVar()

        self.var.trace('w', self.changed)
        self.bind("<Right>", self.selection)
        self.bind("<Return>", self.selection)
        self.bind("<Up>", self.up)
        self.bind("<Down>", self.down)
        self.cb = []
        
        self.lb_up = False
    def bind_card_cb(self, func):
        self.cb.append(func)

    def changed(self, name, index, mode):  
        if self.var.get() == '':
            self.lb.destroy()
            self.lb_up = False
        else:
            words = self.comparison()
            if words:            
                if not self.lb_up:
                    self.lb = tk.Listbox(self.parent)
                    self.lb.bind("<Double-Button-1>", self.selection)
                    self.lb.bind("<Right>", self.selection)
                    self.lb.place(x=self.winfo_x(), y=self.winfo_y()+self.winfo_height())
                    self.lb_up = True
                
                self.lb.delete(0, tk.END)
                for w in words:
                    self.lb.insert(tk.END,w)
            else:
                if self.lb_up:
                    self.lb.destroy()
                    self.lb_up = False
        
    def selection(self, event):
        if self.lb_up:
            self.var.set(self.lb.get(tk.ACTIVE))
            self.lb.destroy()
            self.lb_up = False
            self.icursor(tk.END)
            for f in self.cb:
                f(self.var.get())
        else:
            for f in self.cb:
                f(self.var.get())

    def up(self, event):
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
            if index != '0':                
                self.lb.selection_clear(first=index)
                index = str(int(index)-1)                
                self.lb.selection_set(first=index)
                self.lb.activate(index) 

    def down(self, event):
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
            if index != tk.END:                        
                self.lb.selection_clear(first=index)
                index = str(int(index)+1)        
                self.lb.selection_set(first=index)
                self.lb.activate(index) 

    def comparison(self):
        search = '%'+self.var.get()+'%'
        results = self.cursor.execute(r"SELECT name FROM cards WHERE name LIKE ?", (search,))
        rows = results.fetchall()
        l = []
        for row in rows:
            l.append(row[0])
        return l

#This function contains all of the logic required to parse the Hearthstone log
# and generate events from the log, there are some serious issues with reponening
# this is one of the major problems i need to research and address
def thread_func(*args):
    path = args[0]
    exit_flag = args[1]
    state_queue = args[2]
    parser = LogParser(state_queue)
    file = open(path, 'r')
    counter = 0
    old_size = os.stat(path).st_size
    file.seek(0,2)
    while 1:
        if exit_flag.is_set():
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
                size = os.stat(path).st_size
                file = open(path, 'r')
                if size == old_size or size > old_size:
                    file.seek(where)
                old_size = size
                counter = 0
        else:
            counter -= 1
            parser.parse_line(line)
        
        
# We need a well defined interface to pass events to the GUI
# Events we need:
# Game started and playerid's'
# Who the foreign player is
# when a card is played, what turn it was played, and who played it
# when the game ends and the outcome (including relevant statistics)
Player = namedtuple('Player', ['name', 'id', 'high', 'low', 'hero', 'hero_name'])
GameStart = namedtuple('GameStart', ['players',])
GameOutcome = namedtuple('GameOutcome', ['won', 'first', 'duration', 'turns'])
CardPlayed = namedtuple('CardPlayed', ['cardId', 'turn', 'player'])
CardDrawn = namedtuple('CardDrawn', ['cardId', 'turn'])
CardShuffled = namedtuple('CardDrawn', ['cardId', 'player'])
GameEvent = namedtuple('GameEvent', ['type', 'data']) # This will get passed back to the GUI

# Enum for GameEvent types
class EventType(Enum):
    #Contains a dictionary with information about the local and foreign player data['foreign'] = Player(...)
    GameStart = 1 
    #Contains a dictionary with information about the outcome of the game
    GameEnd = 2
    #Contains a dictionary with the information about who, when, and what
    CardPlayed = 3
    CardDrawn = 4
    CardShuffled = 5
class LogParser():
    def __init__(self, state_queue):
        self.q = state_queue
        self._compile_regex()
        self._reset()
    
    def _reset(self):
        self.players = {}
        self.in_game = False
        self.turn_num = 1
        self.game_start_time = None
        self.entities = {}
        self.local_player_found = False
        self.foreign_player_found = False
        self.first = True
    def _game_start(self):
        self.in_game = True
        self.game_start_time = datetime.datetime.now()
        return
   
    def _player_acc(self, entityid, playerid, high, low):
        self.players[playerid] = Player(None, playerid, high, low, None, None)
        return
    
    def _full_entity(self, entity):
        name = entity.get('name', None)
        if self.local_player_found is False:
            if name is not None:
                pinfo = self.players[entity['player']]
                self.players['local'] = Player(None, pinfo.id, pinfo.high, pinfo.low,
                None, None)
                print('The local player is ID: {0}'.format(pinfo.id))
                self.local_player_found = True
        if self.foreign_player_found is False:
            if self.local_player_found is True:
                if entity['player'] is not self.players['local'].id:
                    pinfo = self.players[entity['player']]
                    self.players['foreign'] = Player(None, pinfo.id, pinfo.high, pinfo.low,
                    None, None)
                    print('The foreign player is ID: {0}'.format(pinfo.id))
                    self.foreign_player_found = True
        cardId = entity.get('cardId', None)
        if cardId is not None:
            e = CardDrawn(cardId,  self.turn_num)
            self.q.put(GameEvent(EventType.CardDrawn, e))
            if cardId == 'GAME_005':
                self.first = False
            m = self.re_hero.match(cardId)
            if m is not None:
                if entity['player'] == self.players['local'].id:
                    tmp_p = self.players['local']
                    p = Player(tmp_p.name, tmp_p.id, tmp_p.high,
                            tmp_p.low, int(m.group(1)), entity.get('name', None))
                    self.players['local'] = p
                    print("The local player is playing {0}".format(entity['name']))
                    return
                else:
                    tmp_p = self.players['foreign']
                    p = Player(tmp_p.name, tmp_p.id, tmp_p.high,
                            tmp_p.low, int(m.group(1)), entity.get('name', None))
                    self.players['foreign'] = p
                    print("The foreign player is playing {0}".format(entity['name']))
                    return
    
    def _show_entity(self, entity, cardId):
        if entity['player'] is self.players['foreign'].id:
            if entity['zone'] in ('DECK', 'HAND'):
                e = CardPlayed(cardId,  self.turn_num, entity['player'])
                self.q.put(GameEvent(EventType.CardPlayed, e))
        if entity['player'] is self.players['local'].id:
            if entity['zone'] == 'DECK':
                e = CardDrawn(cardId,  self.turn_num)
                self.q.put(GameEvent(EventType.CardDrawn, e))
    
    def _tag_change(self, tag, value, entity):
        if tag == 'PLAYSTATE':
            if value in ('WON', 'LOST', 'TIED'):
                if self.in_game:
                    if entity != self.players['local'].name:
                        return
                    else:
                        deltaT = datetime.datetime.now() - self.game_start_time
                        duration = deltaT.total_seconds()
                        outcome = None
                        if value == 'WON':
                            outcome = GameOutcome(True, self.first, duration, self.turn_num)
                        else:
                            outcome = GameOutcome(False, self.first, duration, self.turn_num)
                        self.q.put(GameEvent(EventType.GameEnd, outcome))
                        self._reset()
                        return
        elif tag == 'PLAYER_ID':
            if value == self.players['local'].id:
                tmp_p = self.players['local']
                p = Player(entity, tmp_p.id, tmp_p.high,
                        tmp_p.low, tmp_p.hero, tmp_p.hero_name)
                self.players['local'] = p
            else:
                tmp_p = self.players['foreign']
                p = Player(entity, tmp_p.id, tmp_p.high,
                        tmp_p.low, tmp_p.hero, tmp_p.hero_name)
                self.players['foreign'] = p
            if self.players['foreign'].name is not None:
                if self.players['local'].name is not None:
                    #Submit the event to the GUI
                    self.q.put(GameEvent(EventType.GameStart, GameStart(self.players)))
                    return
            return
        elif tag == 'ZONE':
            if value == 'PLAY':
                if isinstance(entity, dict):
                    #Local player played a card
                    cardid = entity.get('cardId', None)
                    if cardid is not None:
                        e = CardPlayed(entity['cardId'],  self.turn_num, entity['player'])
                        self.q.put(GameEvent(EventType.CardPlayed, e))
            if value == 'DECK':
                if isinstance(entity, dict):
                    #Local player played a card
                    cardid = entity.get('cardId', None)
                    if cardid is not None:
                        e = CardShuffled(entity['cardId'], entity['player'])
                        self.q.put(GameEvent(EventType.CardShuffled, e))
        elif tag == 'TURN':
            if entity == 'GameEntity':
                self.turn_num = int(value)
    def parse_entity(self, subline):
        # try the two more specific regular expressions
        match = self.re_ent_id.match(subline)
        if match:
            #entity_pattern = "\[id=(\d+?) cardId= type=(.+?) zone=(.+?) zonePos=(\d+?) player=(\d)\]"
            id = match.group(1)
            cardId = None
            t = match.group(2)
            zone = match.group(3)
            zonePos = match.group(4)
            player = match.group(5)
            return {'id': id, 'type': t, 'zone': zone, 'zonePos': zonePos, 'player': player}
        match = self.re_ent_name.match(subline)
        if match:
            #entity_pattern2 = "\[name=(.+?) id=(.+?) zone=(.+?) zonePos=(\d+) cardId=(.+?) player=(\d)\]"
            name = match.group(1)
            id = match.group(2)
            zone = match.group(3)
            zonePos = match.group(4)
            cardId = match.group(5)
            player = match.group(6)
            return {'name': name, 'id': id, 'zone': zone, 'zonePos': zonePos, 'cardId': cardId, 'player': player}
        return subline
    
    def parse_line(self, line):
        magic = line[0]
        log_timestamp = line[2:17]
        try:
            log_time = datetime.strptime(log_timestamp, '%H:%M:%S.%f')
        except:
            pass
        # program_time = datetime.now()
        # self.timestamp = program_time.strftime('[%H:%M:%S.%f] ')
        # Take only the data we need
        data = line[19:]
        self.handle_line(data)
    
    def handle_line(self, line):
        # TAG CHANGE
        m = self.re_tag_change.match(line)
        if m is not None:
            subline = line[m.end(0) + 1:]
            mm = self.re_tag_param.match(subline)
            if mm is not None:
                ent_str = mm.group(1)
                tag = mm.group(2)
                value = mm.group(3)
                entity = self.parse_entity(ent_str)
                self._tag_change(tag, value, entity)
            return
        # SHOW ENTITY
        m = self.re_show_ent.match(line)
        if m is not None:
            subline = line[m.end(0) + 1:]
            mm = self.re_sub_ent.match(subline)
            if mm is not None:
                ent_str = mm.group(1)
                entity = self.parse_entity(ent_str)
                self._show_entity(entity, mm.group(2))
            return
        # FULL ENTITY
        m = self.re_full_ent.match(line)
        if m is not None:
            subline = line[m.end(0) + 1:]
            entity = self.parse_entity(subline)
            self._full_entity(entity)
            return
        # PLAYER
        m = self.re_player.match(line)
        if m is not None:
            subline = line[m.end(0) + 1:]
            mm = self.re_player_acc.match(subline)
            if mm is not None:
                entityid = mm.group(1)
                pid = mm.group(2)
                high = int(mm.group(3))
                low = int(mm.group(4))
                self._player_acc(entityid, pid, high, low)
            return
        # CREATE GAME
        m = self.re_game_start.match(line)
        if m is not None:
            self._game_start()
    def _compile_regex(self):
        self.re_game_start  = re.compile(create_game_pattern)
        self.re_player      = re.compile(player_pattern)
        self.re_player_acc  = re.compile(player_acc_pattern)
        self.re_game_end    = re.compile(win_loss_pattern)
        self.re_hero        = re.compile(hero_pattern)
        self.re_tag_change  = re.compile(tag_change_pattern)
        self.re_tag_param   = re.compile(tag_param_pattern)
        self.re_ent_id      = re.compile(entity_pattern)
        self.re_ent_name    = re.compile(entity_pattern2)
        self.re_full_ent    = re.compile(full_entity_pattern)
        self.re_show_ent    = re.compile(show_entity_pattern)
        self.re_sub_ent     = re.compile(show_entity_sub_pattern)