import queue
import time
import os
from datetime import datetime
import logregex
import re
import enum
import sqlite3
import logging

class LogEventType(enum.Enum):
    GAME_START = 0,
    ACTION_START = 1,
    ACTION_END = 2,
    TAG_CHANGE = 3,
    FULL_ENTITY = 4,
    SHOW_ENTITY = 5,
    PLAYER_ACC = 6


class LogWatcher():
    def __init__(self, observers):
        self.observers = observers

    def watch(self, filepath, exit_flag):
        file = open(filepath, 'r')
        counter = 0
        old_size = os.stat(filepath).st_size
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
                    size = os.stat(filepath).st_size
                    file = open(filepath, 'r')
                    if size == old_size or size > old_size:
                        file.seek(where)
                    old_size = size
                    counter = 0
            else:
                counter -= 1
                for obs in self.observers:
                    obs.parse_line(line)


class LogObservable():
    def __init__(self):
        self.q = queue.Queue()
        self.observers = []
        self.compile_regexs()
        pass

    def add_line(self, line):
        self.q.put(line)

    def update(self):
        try:
            while 1:
                tmp = self.q.get_nowait()
                self.parse_line(tmp)
        except queue.Empty:
            pass

    def register(self, observer):
        if not observer in self.observers:
            self.observers.append(observer)

    def unregister(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def unregister_all(self):
        if self.observers:
            del self.observers[:]

    def update_observers(self, *args, **kwargs):
        for observer in self.observers:
            observer.update(*args, **kwargs)

    def parse_line(self, line):
        magic = line[0]
        log_timestamp = line[2:17]
        try:
            log_time = datetime.strptime(log_timestamp, '%H:%M:%S.%f')
        except:
            pass
        program_time = datetime.now()
        self.timestamp = program_time.strftime('[%H:%M:%S.%f] ')
        # Take only the data we need
        data = line[19:]
        self.handle_line(data)

    def compile_regexs(self):
        self.tag_change_regex = re.compile(logregex.tag_change_pattern)
        self.action_begin_regex = re.compile(logregex.action_begin_pattern)
        self.action_end_regex = re.compile(logregex.action_end_pattern)
        self.create_game_regex = re.compile(logregex.create_game_pattern)
        self.entity_id_regex = re.compile(logregex.entity_pattern)
        self.entity_name_regex = re.compile(logregex.entity_pattern2)
        self.action_param_regex = re.compile(logregex.action_param_pattern)
        self.tag_param_regex = re.compile(logregex.tag_param_pattern)
        self.full_entity_regex = re.compile(logregex.full_entity_pattern)
        self.hero_regex = re.compile(logregex.hero_pattern)
        self.show_entity_regex = re.compile(logregex.show_entity_pattern)
        self.show_entity_sub_regex = re.compile(
            logregex.show_entity_sub_pattern)
        self.player_regex = re.compile(logregex.player_pattern)
        self.player_acc_regex = re.compile(logregex.player_acc_pattern)

    def parse_entity(self, subline):
        # try the two more specific regular expressions
        match = self.entity_id_regex.match(subline)
        if match:
            #entity_pattern = "\[id=(\d+?) cardId= type=(.+?) zone=(.+?) zonePos=(\d+?) player=(\d)\]"
            id = match.group(1)
            cardId = None
            type = match.group(2)
            zone = match.group(3)
            zonePos = match.group(4)
            player = match.group(5)
            return {'id': id, 'type': type, 'zone': zone, 'zonePos': zonePos, 'player': player}
        match = self.entity_name_regex.match(subline)
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

    def handle_line(self, line):
        # Figure out when game ends
        match = self.create_game_regex.match(line)
        if match is not None:
            self.update_observers(etype=LogEventType.GAME_START)
            return

        # Track action beginnings
        match = self.action_begin_regex.match(line)
        if match is not None:
            self.in_action = True
            subline = line[match.end(0) + 1:]
            # Fill in last_action_info
            match = self.action_param_regex.match(subline)
            if match:
                entity_str = match.group(1)
                blocktype = match.group(2)
                index = match.group(3)
                target_str = match.group(4)
                entity = self.parse_entity(entity_str)
                target = self.parse_entity(target_str)
                self.update_observers(entity, target, blocktype, index, etype=LogEventType.ACTION_START)
            return
        # Track action endings
        match = self.action_end_regex.match(line)
        if match is not None:
            self.update_observers(etype=LogEventType.ACTION_END)
            return

        # Track tag changes
        match = self.tag_change_regex.match(line)
        if match is not None:
            subline = line[match.end(0) + 1:]
            match = self.tag_param_regex.match(subline)
            if match:
                entity_str = match.group(1)
                tag = match.group(2)
                value = match.group(3)
                entity = self.parse_entity(entity_str)
                tag_change = {'entity': entity, 'tag': tag, 'value': value}
                self.update_observers(entity, tag, value, etype=LogEventType.TAG_CHANGE)
            return

        # Track FULL_ENTITY
        match = self.full_entity_regex.match(line)
        if match is not None:
            subline = line[match.end(0) + 1:]
            entity_str = subline
            entity = self.parse_entity(entity_str)
            self.update_observers(entity, etype=LogEventType.FULL_ENTITY)
            return

        # Track SHOW_ENTITY
        match = self.show_entity_regex.match(line)
        if match is not None:
            subline = line[match.end(0) + 1:]
            match = self.show_entity_sub_regex.match(subline)
            if match:
                entity_str = match.group(1)
                entity = self.parse_entity(entity_str)
                self.update_observers(entity, etype=LogEventType.SHOW_ENTITY)
            return

        # Track unique player information
        match = self.player_regex.match(line)
        if match is not None:
            subline = line[match.end(0) + 1:]
            match = self.player_acc_regex.match(subline)
            if match:
                eid = match.group(1)
                playerid = match.group(2)
                high = match.group(3)
                low = match.group(4)
                high = int(high)
                low = int(low)
                self.update_observers(eid, playerid, high, low, etype=LogEventType.PLAYER_ACC)
            return


class StatCollector():
    def __init__(self, text, plot_data):
        self.text = text
        self.plot_data = plot_data
        self.logger = logging.getLogger('valuetracker')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # add formatter to ch
        ch.setFormatter(formatter)
        self.logger.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)
        # add ch to logger
        self.logger.addHandler(ch)
        self.reset()
        self.hero_regex = re.compile(logregex.hero_pattern)
        self.update_plot_data()

    def update_plot_data(self):
        self.db = sqlite3.connect('stats.db')
        self.cursor = self.db.cursor()
        sql = "SELECT won from 'match'"
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        arr = []
        for obj in result:
            arr.append(obj[0])
        self.plot_data.put(arr)
        self.db.close()

    def update(self, *args, **kwargs):
        if kwargs['etype'] == LogEventType.GAME_START:
            self.in_game = True
            self.game_start_timestamp = datetime.now()
            self.text.write('Game created', ('g',))
            return
        elif kwargs['etype'] == LogEventType.ACTION_START:
            self.in_action = True
            entity = args[0] 
            target = args[1] 
            blocktype = args[2] 
            index = args[3]
            return
        elif kwargs['etype'] == LogEventType.TAG_CHANGE:
            entity = args[0]
            tag = args[1]
            value = args[2]
            if tag == "PLAYSTATE":
                if value in ('WON', 'LOSS', 'TIED'):
                    if self.in_game:
                        if entity == self.local_player.get('entity'):
                            if value == 'WON':
                                self.local_player['won'] = True
                                self.text.write('The local player won')
                            else:
                                self.local_player['won'] = False
                                self.text.write('The local player lost')
                        else:
                            if value == 'WON':
                                self.local_player['won'] = False
                                self.text.write('The local player lost')
                            else:
                                self.local_player['won'] = True
                                self.text.write('The local player won')
                    self.in_game = False
                    self.write_match()
                    return
            if tag == "PLAYER_ID":
                if 'entity' not in self.local_player:
                    if value == self.local_player.get('id'):
                        self.local_player['entity'] = entity
                        self.text.write(
                            'The local player is named {0}'.format(entity))
                        return
                if 'entity' not in self.foreign_player:
                    if value == self.foreign_player.get('id'):
                        self.foreign_player['entity'] = entity
                        self.text.write(
                            'The foreign player is named {0}'.format(entity))
                        return
        elif kwargs['etype'] == LogEventType.ACTION_END:
            self.in_action = False
            self.last_action_info = {}
            return
        elif kwargs['etype'] == LogEventType.SHOW_ENTITY:
            entity = args[0]
            return
        elif kwargs['etype'] == LogEventType.FULL_ENTITY:
            entity = args[0]
            name = entity.get('name')
            if name:
                if 'id' not in self.local_player:
                    if entity['player'] == '1':
                        self.local_player['id'] = '1'
                        self.text.write('Local player is id {0}'.format(entity['player']))
                        self.foreign_player['id'] = '2'
                    else:
                        self.local_player['id'] = '2'
                        self.text.write('Local player is id {0}'.format(entity['player']))
                        self.foreign_player['id'] = '1'
            
            cardId = entity.get('cardId', '')
            if cardId == 'GAME_005':
                self.local_player['first'] == True

            #Figure out who is playing what
            match = self.hero_regex.match(cardId)
            if match:
                if entity['player'] == self.local_player['id']:
                    if 'hero' not in self.local_player:
                        i = int(match.group(1))
                        self.local_player['hero'] = i
                        self.local_player['hero_str'] = entity['name']
                        self.text.write("The local player is playing {0}".format(entity['name']))
                        return
                else:
                    if 'hero' not in self.foreign_player:
                        i = int(match.group(1))
                        self.foreign_player['hero'] = i
                        self.foreign_player['hero_str'] = entity['name']
                        self.text.write("The foreign player is playing {0}".format(entity['name']))
                        return
            return
        elif kwargs['etype'] == LogEventType.PLAYER_ACC:
            eid = args[0]
            playerid = args[1]
            high = args[2]
            low = args[3]
            self.player_acc_info[playerid] = {}
            self.player_acc_info[playerid]['high'] = high
            self.player_acc_info[playerid]['low'] = low
            return
        else:
            pass

    def reset(self):
        self.logger.info('Resetting internal state')
        self.local_player = {}
        self.foreign_player = {}
        self.game_info = {}
        self.last_action_info = {}
        # Clear state
        self.in_game = False
        self.in_action = False
        self.previous_tag_changes = []
        self.entities = {}
        self.current_turn = 0
        self.num_crystals_used = None
        self.player_acc_info = {}
        self.game_start_timestamp = None
        self.local_player['first'] = 0

    def write_match(self):
        self.db = sqlite3.connect('stats.db')
        self.cursor = self.db.cursor()
        # determine if the foreign player is new
        accinfo = self.player_acc_info[self.foreign_player['id']]
        pid = self.check_player_exists_in_db(
            self.foreign_player['entity'], accinfo['high'], accinfo['low'])
        # if new add
        if pid is None:
            self.logger.info('Adding new player (name: {0}) to database'.format(
                self.foreign_player['entity']))
            pid = self.insert_player(self.foreign_player['entity'], accinfo[
                'high'], accinfo['low'])
            self.logger.info('Player id (name: {0}) is {1}'.format(
                self.foreign_player['entity'], pid))
        else:
            pid = pid[0]
        # add match
        deltaT = datetime.now() - self.game_start_timestamp
        duration = deltaT.total_seconds()
        opp_hero = self.get_hero_id(self.foreign_player['hero_str'])
        player_hero = self.get_hero_id(self.local_player['hero_str'])
        matchid = self.insert_match(pid, self.local_player['first'], self.local_player['won'],
                                    duration, self.game_start_timestamp, opp_hero, player_hero)
        # add meta info
        self.insert_match_meta_info(matchid, self.local_player[
            'id'], self.foreign_player['id'])
        # add turn info
        self.db.commit()
        self.db.close()
        self.update_plot_data()
        self.reset()

    def check_player_exists_in_db(self, name, high, low):
        sql = "SELECT playerid from 'player' WHERE high = ? AND low = ? AND name = ?"
        self.cursor.execute(sql, (high, low, name))
        result = self.cursor.fetchone()
        return result

    def insert_match(self, pid, first, won, duration, date, opp_hero, player_hero):
        sql = "INSERT INTO `match`(`opponent`,`first`,`won`,`duration`,`date`, 'opp_hero', 'player_hero') VALUES (?,?,?,?,?,?,?)"
        self.cursor.execute(
            sql, (pid, first, won, duration, date, opp_hero, player_hero))
        return self.cursor.lastrowid

    def insert_player(self, name, high, low):
        sql = "INSERT INTO `player`(`name`,`low`,`high`) VALUES (?,?,?)"
        self.cursor.execute(sql, (name, low, high))
        return self.cursor.lastrowid

    def get_hero_id(self, name):
        sql = "SELECT heroid from 'hero' where name=?"
        result = self.cursor.execute(sql, (name,))
        result = result.fetchone()
        return result[0]

    def handle_player_acc_info(self, eif, pid, high, low):
        self.player_acc_info[pid] = {'high': high, 'low': low}
        return

    def handle_game_start(self):
        self.game_start_timestamp = datetime.now()

    def insert_match_meta_info(self, matchid, localpid, forpid):
        sql = "INSERT INTO 'match_meta_info' ('matchid','local_player_id','foreign_player_id') VALUES (?,?,?)"
        self.cursor.execute(sql, (matchid, localpid, forpid))
