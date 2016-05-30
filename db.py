import sqlite3
import ssl
import urllib.request
import json
import re

hero_re = re.compile(r'HERO_0(\d)')

url = "https://api.hearthstonejson.com/v1/latest/enUS/cards.json"
def download_hsjson(url):
    context = ssl._create_unverified_context()
    req = urllib.request.urlopen(url, context=context)
    f = req.read()
    with open('cards.json', 'wb') as file:
        file.write(f)
    return f

hero_dict = {9: 'priest', 3: 'rogue', 8: 'mage', 4: 'paladin', 1: 'warrior',
             7: 'warlock', 5: 'hunter', 2: 'shaman', 6: 'druid'}
hero_dict_names = {v: k for k, v in hero_dict.items()}


# In[2]:

raw_data = download_hsjson(url)


# In[3]:

with open('cards.json', 'r', encoding='utf-8') as f:
    cards_json = json.load(f)


# In[4]:

for i in range(10):
    c = cards_json[i]
    print(c['name'])


# In[4]:

path_to_db = 'stats.db'


# In[ ]:

with open('cards.json', 'w', encoding='utf-8') as f:
    json.dump(sort_keys=True, indent=4


# In[5]:

tbl_query = r"SELECT * FROM sqlite_master WHERE type='table'"

create_cards_table_sql = r"""CREATE TABLE "cards" (
	`id`	TEXT NOT NULL,
	`name`	TEXT NOT NULL,
	`rarity`	TEXT NOT NULL,
	`cost`	INTEGER NOT NULL,
	`attack`	INTEGER NOT NULL,
	`health`	INTEGER NOT NULL,
	`set`	TEXT,
	PRIMARY KEY(id)
)"""

create_hero_table_sql = r"""CREATE TABLE "hero" (
	`id`	INTEGER NOT NULL UNIQUE,
	`name`	TEXT NOT NULL,
	`cardid`	TEXT NOT NULL,
	`class`	INTEGER NOT NULL,
	PRIMARY KEY(id)
)"""

create_deck_table_sql = r"""CREATE TABLE "deck" (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	TEXT NOT NULL,
	`class`	INTEGER NOT NULL,
	`tag1`	INTEGER,
	`tag2`	INTEGER
)"""

create_match_table_sql = r"""CREATE TABLE "match" (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`opponent`	INTEGER NOT NULL,
	`first`	INTEGER NOT NULL,
	`won`	INTEGER NOT NULL,
	`duration`	INTEGER NOT NULL,
	`date`	DATETIME NOT NULL,
	`opp_hero`	INTEGER NOT NULL,
	`player_hero`	INTEGER NOT NULL,
	`deck`	INTEGER NOT NULL,
	FOREIGN KEY(`opponent`) REFERENCES `player`(`id`),
	FOREIGN KEY(`opp_hero`) REFERENCES `hero`(`id`),
	FOREIGN KEY(`player_hero`) REFERENCES `hero`(`id`),
	FOREIGN KEY(`deck`) REFERENCES deck(id)
)"""

create_player_table_sql = r"""
CREATE TABLE `player` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	TEXT NOT NULL,
	`high`	INTEGER NOT NULL,
	`low`	INTEGER NOT NULL
)"""

create_cards_played_sql = r"""CREATE TABLE "card_played" (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`cardid`	INTEGER NOT NULL,
	`turn`	INTEGER NOT NULL,
	FOREIGN KEY(`cardid`) REFERENCES `cards`(`id`)
)"""

insert_card_sql = """INSERT INTO `cards`(`id`,`name`,'rarity', 'cost',`health`,`attack`,`set`,`collectible`,`type`,`player_class`) 
VALUES (?,?,?,?,?,?,?,?,?,?);"""


# In[7]:

def update_card_table(cursor, cards):
    for card in cards:
        result = cursor.execute(r"SELECT id from cards WHERE name = ?", (card['name'],))
        row = result.fetchone()
        if row is None:
            print(card['id'])
            m = hero_re.match(card['id'])
            if m:
                sql_str = 'SELECT * from hero where cardid LIKE ?'
                row = cursor.execute(sql_str, ("%" + card['id'],)).fetchone()
                if row is None:
                    sql_str2 = 'INSERT INTO hero (name, cardid, class) VALUES (?,?,?)'
                    print('Inserting' + card['name'] )
                    cursor.execute(sql_str2, (card['name'], card['id'], m.group(1)))
            
            tmp = card.get('playerClass', None)
            player_class = -1 
            if tmp is not None:
                player_class = hero_dict_names[tmp.lower()]
            
            ins = (card['id'], card['name'], card['rarity'], card.get('cost', -1),
                  card.get('health', -1),card.get('attack', -1), card['set'], card.get('collectible', -1),
                  card['type'], player_class)
            
            cursor.execute(insert_card_sql, ins)


# In[8]:

db = sqlite3.connect(path_to_db)
db.row_factory = sqlite3.Row
cursor = db.cursor()
update_card_table(cursor, cards_json)
db.commit()
db.close()


# In[7]:

db = sqlite3.connect(path_to_db)
db.row_factory = sqlite3.Row
cursor = db.cursor()
result = cursor.execute(tbl_query)
tables = result.fetchall()
db.close()


# In[20]:

db = sqlite3.connect(path_to_db)
db.row_factory = sqlite3.Row
cursor = db.cursor()


# In[13]:

with open('db_sql.sql', 'r') as f:
    cursor.executescript(f.read())


# In[14]:

db.commit()


# In[21]:

def check_table_structure(tables, **kw):
    for table in tables:
        name = table['name']
        print(name)


# In[19]:

db.close()


# In[22]:

db.row_factory = sqlite3.Row
result = cursor.execute(tbl_query)
tables = result.fetchall()
check_table_structure(tables)


# In[ ]:

for card in cards_json:
    print(card['name'])


# In[1]:

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base()
engine = create_engine('sqlite:///alchemy.db', echo=True)

class Card(Base):
    __tablename__ = 'cards'
    id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)
    rarity = Column(String)
    playerClass = Column(String)
    cost = Column(Integer)
    health = Column(Integer)
    attack = Column(Integer)
    
    def __repr__(self):
        return "<Card(name='%s', id='%s', type='%s')>" % (
                            self.name, self.id, self.type)
    


# In[2]:

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)


# In[ ]:

for 

