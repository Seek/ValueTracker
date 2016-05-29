from datetime import datetime
from enum import Enum
import logging
import re
import os
import time
import logging
import pdb
from collections import namedtuple

# Setup logging
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.INFO)
ch = logging.FileHandler('log.txt')
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
module_logger.addHandler(ch)


# Regular expression we rely upon
CREATE_GAME_RE = re.compile(r'PowerTaskList\.DebugPrintPower\(\) -     CREATE_GAME')
GAMEENTITY_RE = re.compile(r'PowerTaskList.DebugPrintPower\(\) -         GameEntity')
GAMEENTITY_PARAMS_RE = re.compile(r'EntityID=(\d)')
TAG_SET_RE = re.compile(r'PowerTaskList.DebugPrintPower\(\) -             tag=(.+) value=(.+)')
BLOCK_BEGIN_RE = re.compile(r'PowerTaskList\.DebugPrintPower\(\) - (ACTION|BLOCK)_START')
BLOCK_END_RE = re.compile(r'PowerTaskList\.DebugPrintPower\(\) - (ACTION|BLOCK)_END')
TAG_CHANGE_RE = re.compile(r'PowerTaskList\.DebugPrintPower\(\) -     TAG_CHANGE')
FULL_ENTITY_RE = re.compile(r'PowerTaskList\.DebugPrintPower\(\) -     FULL_ENTITY - Updating')
SHOW_ENTITY_RE = re.compile(r'PowerTaskList\.DebugPrintPower\(\) -     SHOW_ENTITY - Updating')
HIDE_ENTITY_RE = re.compile(r'PowerTaskList.DebugPrintPower() -     HIDE_ENTITY -')
PLAYER_RE = re.compile(r'PowerTaskList\.DebugPrintPower\(\) -         Player')
ENTITY1_RE = re.compile(r'\[id=(\d+?) cardId= type=(.+?) zone=(.+?) zonePos=(\d+?) player=(\d)\]')
ENTITY2_RE = re.compile(r'\[name=(.+?) id=(.+?) zone=(.+?) zonePos=(\d+) cardId=(.+?) player=(\d)\]')
BLOCK_PARAMS_RE = re.compile(r'BlockType=(.+) Entity=(.+) EffectCardId= EffectIndex=(.+) Target=(.+)')
TAG_CHANGE_PARAMS_RE = re.compile(r'Entity=(.+) tag=(.+) value=(.+)')
PLAYER_PARAMS_RE = re.compile(r'EntityID=(\d) PlayerID=(\d) GameAccountId=\[hi=(\d+?) lo=(\d+?)\]')
SHOW_ENTITY_PARAMS_RE = re.compile(r'Entity=(\[.+?\]) CardID=(.+)')
HERO_RE = re.compile(r'HERO_0(\d)')
#win_loss_pattern = r'PowerTaskList\.DebugPrintPower\(\) -     TAG_CHANGE Entity=(.+) tag=PLAYSTATE value=(WON|LOST|TIED)'

def thread_func(*args):
    path = args[0]
    exit_flag = args[1]
    state_queue = args[2]
    parser = Parser()
    egen = GameEventGenerator(parser)
    egen.add_queue(state_queue)
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


def parse_entity(subline):
    # try the two more specific regular expressions
    match = ENTITY1_RE.match(subline)
    if match:
        #entity_pattern = "\[id=(\d+?) cardId= type=(.+?) zone=(.+?) zonePos=(\d+?) player=(\d)\]"
        id = match.group(1)
        cardId = None
        t = match.group(2)
        zone = match.group(3)
        zonePos = match.group(4)
        player = match.group(5)
        return {'id': id, 'type': t, 'zone': zone, 'zonePos': zonePos, 'player': player}
    match = ENTITY2_RE.match(subline)
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

class Entity:
    def __init__(self, id):
        self.id = id
        self.tags = {}
        
    def __getitem__(self, key):
        return self.tags[key]
        
    def __setitem__(self, key, value):
        self.tags[key] = value
        
    def __repr__(self):
        return 'Entity id: {0}, {1}\n'.format(self.id, self.tags)
        
class Parser:
    def __init__(self):
        self.entities = {}
        self.name_to_entity_id = {}
        self.last_entity = None
        self.on_tag_changed = []
        self.on_block_begin = []
        self.on_block_end = []
        self.on_full_entity = []
        self.on_show_entity = []
        self.on_hide_entity = []
        self.on_player = []
        self.on_create_game = []
        
    def get_entity(self, string):
        ent = parse_entity(string)
        if isinstance(ent, dict):
            if ent['id'] in self.entities:
                return self.entities[ent['id']]
            else:
                return None
        elif isinstance(ent, str):
            if ent in self.name_to_entity_id:
                return self.entities[self.name_to_entity_id[ent]]
            else:
                return None
        else:
            return None
        
    def parse_line(self, line):
        # First line is D
        magic = line[0]
        # Next is the log timestamp
        log_timestamp = line[2:17]
        # Try to parse, but its not that important
        try:
            log_time = datetime.strptime(log_timestamp, '%H:%M:%S.%f')
        except:
            pass
        # Take only the data we need
        data = line[19:]
        #module_logger.debug(data) # Line is stripped of timestamp
        # Narrow down the options
        #pdb.set_trace()
        m = TAG_CHANGE_RE.match(data)
        if m:
            params = data[m.end(0) + 1 : ]
            mp = TAG_CHANGE_PARAMS_RE.match(params)
            if mp:
                entity_str = mp.group(1)
                tag = mp.group(2)
                value = mp.group(3)
                if tag == 'PLAYER_ID':
                    #pdb.set_trace()
                    for e in self.entities.values():
                        if 'PLAYER_ID' in e.tags:
                            if e['PLAYER_ID'] == value:
                                self.name_to_entity_id[entity_str] = e.id
                                e['name'] = entity_str
                
                ent = self.get_entity(entity_str)
                if not ent:
                    module_logger.debug('Failed to handle tag change for (%s)',
                                            mp.group(1))
                    return
                module_logger.debug('Tag (%s) changed to %s for entity (%s)',
                            tag, value, ent)
                for f in self.on_tag_changed:
                    f(ent, tag, value)
                ent[tag] = value
                return
            else:
                module_logger.info('Failed to parse tag (%s) change parameters!', 
                                    params)
                return
        m = BLOCK_BEGIN_RE.match(data)
        if m:
            params = data[m.end(0) + 1 : ]
            mp = BLOCK_PARAMS_RE.match(params)
            if mp:
                #pdb.set_trace()
                entity = self.get_entity(mp.group(2))
                block_type = mp.group(1)
                effect_index = mp.group(3)
                target = mp.group(4)
                #pdb.set_trace()
                module_logger.debug('ACTION BEGIN\t Entity id: %s, Block Type: %s, Index: %s, Target:%s',
                entity.id, block_type, effect_index, target)
                for f in self.on_block_begin:
                    f(entity, block_type, effect_index, target)
                return
            else:
                module_logger.info('Failed to parse parameters for action %s', params)
        m = BLOCK_END_RE.match(data)
        if m:
            module_logger.debug('Action has ended')
            for f in self.on_block_end:
                    f(entity, block_type, effect_index, target)
            return
        m = TAG_SET_RE.match(data)
        if m:
            tag = m.group(1)
            value = m.group(2)
            self.last_entity[tag] = value
            module_logger.debug('Tag (%s) set to (%s) on entity id (%s)',
                                    tag, value, self.last_entity.id)
            return
        m = FULL_ENTITY_RE.match(data)
        if m:
            params = data[m.end(0) + 1 : ]
            entity = parse_entity(params)
            module_logger.debug('Adding entity (%s)', entity)
            if entity['id'] not in self.entities:
                ent = Entity(entity['id'])
                del entity['id']
                for key in entity.keys():
                    ent[key] = entity[key]
                self.entities[ent.id] = ent
                self.last_entity = ent
                for f in self.on_full_entity:
                    f(ent)
            return
        m = SHOW_ENTITY_RE.match(data)
        if m:
            params = data[m.end(0) + 1 : ]
            mp = SHOW_ENTITY_PARAMS_RE.match(params)
            if mp:
                entity_str = mp.group(1)
                cardId = mp.group(2)
                ent = self.get_entity(entity_str)
                if ent:
                    module_logger.debug('Entity id: %s was shown [cardId = %s]',
                                    ent.id, cardId)
                    self.last_entity = ent
                    for f in self.on_show_entity:
                        f(ent, cardId)
                    return
                else:
                    module_logger.debug('Failed to parse entity for SHOW_ENTITY (%s)',
                        params)
                    return
            else:
                module_logger.info('Failed to parse paramters for SHOW_ENTITY (%s)',
                                    params)
            return
        m =  HIDE_ENTITY_RE.match(data)
        if m:
            params = data[m.end(0) + 1 : ]
            mp = TAG_CHANGE_PARAMS_RE.match(params)
            if mp:
                ent_str = match.group(1)
                tag = match.group(2)
                value = match.group(3)
                ent = self.get_entity(ent_str)
                if ent:
                    module_logger.debug('Entity id: %s was hidden [tag = %s, value=%s]',
                                    ent.id, tag, value)
                    for f in self.on_hide_entity:
                            f(ent, tag, value)
                else:
                    module_logger.info('Failed to parse entity for HIDE_ENTITY (%s)',
                                    ent_str)
                return
            else:
                module_logger.info('Failed to parse parameters for HIDE_ENTITY (%s)',
                                    params)
                return
        m = PLAYER_RE.match(data)
        if m:
            params = data[m.end(0) + 1 : ]
            mp = PLAYER_PARAMS_RE.match(params)
            entityid = mp.group(1)
            playerid = mp.group(2)
            high = mp.group(3)
            low = mp.group(4)
            module_logger.debug('Player id (%s) mapped to entity id (%s), [high=%s;low=%s]',
                                playerid, entityid, high, low)
            ent = Entity(entityid)
            ent['PLAYER_ID'] = playerid
            ent['HIGH'] = high
            ent['LOW'] = low
            self.entities[ent.id] = ent
            self.last_entity = ent
            for f in self.on_player:
                f(ent)
            return
        m = CREATE_GAME_RE.match(data)
        if m:
            module_logger.debug('GAME STARTED')
            for f in self.on_create_game:
                f()
            return
        m = GAMEENTITY_RE.match(data)
        if m:
            params = data[m.end(0) + 1 : ]
            mp = GAMEENTITY_PARAMS_RE.match(params)
            id = mp.group(1)
            self.name_to_entity_id['GameEntity'] = id
            ent = Entity(id)
            ent['name'] = 'GameEntity'
            self.entities[id] = ent
            self.last_entity = ent
            module_logger.debug('Mapped entity id (%s) to name (%s)', id, 'GameEntity')
            return

class GameEvent(Enum):
    GameStart = 1
    PlayerWon = 2
    PlayerLoss = 3
    PlayerTi3 = 4
    
    
class Player:
    def __init__(self, entity_id, player_id, high, low, name=None,
                    player_class = None, player_hero = None):
        self.entity_id = entity_id
        self.player_id = player_id
        self.high = high
        self.low = low
        self.name = name
    def __repr__(self):
        return 'Player name: {0}'.format(self.name)
    
class GameEventGenerator:
    def __init__(self, parser):
        self.queues = []
        self.parser = parser
        self.reset_state()
        self.parser.on_block_begin.append(self.on_block_begin)
        self.parser.on_create_game.append(self.on_game_created)
        self.parser.on_full_entity.append(self.on_full_entity)
        self.parser.on_show_entity.append(self.on_show_entity)
        self.parser.on_player.append(self.on_player)
        self.parser.on_tag_changed.append(self.on_tag_changed)
        
    def reset_state(self):
        self.players = {}
        self.in_game = False
        self.turn_num = 1
        self.game_start_time = None
        self.entities = {}
        self.local_player_found = False
        self.foreign_player_found = False
        self.first = True
        
    def add_queue(self, queue):
        self.queues.append(queue)

    def remove_queue(self, queue):
        self.queues.append(queue)
            
    def on_tag_changed(self, entity, tag, value):
        if tag == 'PLAYER_ID':
            if value == self.players['local'].player_id:
                pdb.set_trace()
                self.players['local'].name = entity['name']
            else:
                self.players['foreign'].name = entity['name']
            if self.players['local'].name:
                if self.players['foreign'].name:
                    pdb.set_trace()
                    for q in self.queues:
                        q.put((GameEvent.GameStart, self.players['local'],
                        self.players['foreign']))
        if tag == 'PLAYSTATE':
            if value in ('WON', 'LOST', 'TIED'):
                if self.in_game:
                    if entity['name'] != self.players['local'].name:
                        return
                    else:
                        deltaT = datetime.datetime.now() - self.game_start_time
                        duration = deltaT.total_seconds()
                        outcome = None
                        if value == 'WON':
                            outcome = GameOutcome(True, self.first, duration, self.turn_num)
                        else:
                            outcome = GameOutcome(False, self.first, duration, self.turn_num)
                        for q in self.queues:
                            q.put(GameEvent(EventType.GameEnd, outcome))
                        self._reset()
                        return
    def on_block_begin(self, entity, block_type, effect_index, target):
        return
    
    def on_full_entity(self, entity):
        # Full entity
        print(entity)
        if 'name' in entity.tags and self.local_player_found == False:
            playerid = entity['player']
            self.players['local'] = self.players[playerid]
            module_logger.info('The local player is id %s', playerid)
            self.local_player_found = True
        if self.foreign_player_found == False:
            if self.local_player_found == True:
                if entity['player'] != self.players['local'].player_id:
                    playerid = entity['player']
                    self.players['foreign'] = self.players[playerid]
                    module_logger.info('The foreign player is id %s', playerid)
                    self.foreign_player_found = True
            
        if 'cardId' in entity.tags:
            cardId = entity['cardId']
            if cardId == 'GAME_005':
                self.first = False
            m = HERO_RE.match(cardId)
            if m:
                if entity['player'] == self.players['local'].player_id:
                    self.players['local'].player_class = int(m.group(1))
                    self.players['local'].player_hero = entity['name']
                    logging.info('The local player is playing %s', self.players['local'].player_hero)
                    return
                else:
                    self.players['foreign'].player_class = int(m.group(1))
                    self.players['foreign'].player_hero = entity['name']
                    logging.info('The foreign player is playing %s', self.players['local'].player_hero)
                    return

    def on_show_entity(self, entity, cardId):
        return
    
    def on_hide_entity(self, entity, tag, value):
        return
    
    def on_player(self, ent):
        self.players[ent['PLAYER_ID']] = Player(ent.id, ent['PLAYER_ID'],
        ent['HIGH'], ent['LOW'])
    
    def on_game_created(self):
        self.in_game = True
        self.game_start_time = datetime.now()
                
        

if __name__ == '__main__':
    path = r'C:\Program Files (x86)\Hearthstone\Logs\Power.log'
    parser = Parser()
    gen = GameEventGenerator(parser)
    file = open(path, 'r')
    counter = 0
    old_size = os.stat(path).st_size
    #file.seek(0,2)
    while 1:
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
    
    
