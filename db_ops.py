import sqlite3
import ssl
import urllib.request
import json
import re
import logging
import os

database_script = """BEGIN TRANSACTION;
CREATE TABLE `player` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	TEXT NOT NULL,
	`high`	INTEGER NOT NULL,
	`low`	INTEGER NOT NULL
);
CREATE TABLE "match" (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`opponent`	INTEGER NOT NULL,
	`first`	INTEGER NOT NULL,
	`won`	INTEGER NOT NULL,
	`duration`	INTEGER NOT NULL,
	`num_turns`	INTEGER NOT NULL,
	`date`	DATETIME NOT NULL,
	`opp_hero`	INTEGER NOT NULL,
	`player_hero`	INTEGER NOT NULL,
	`deck`	INTEGER NOT NULL,
	FOREIGN KEY(`opponent`) REFERENCES `player`(`id`),
	FOREIGN KEY(`opp_hero`) REFERENCES `hero`(`id`),
	FOREIGN KEY(`player_hero`) REFERENCES `hero`(`id`),
	FOREIGN KEY(`deck`) REFERENCES `deck`(`id`)
);
CREATE TABLE "hero" (
	`id`	INTEGER NOT NULL UNIQUE,
	`name`	TEXT NOT NULL,
	`cardid`	TEXT NOT NULL,
	`class`	INTEGER NOT NULL,
	PRIMARY KEY(id)
);
CREATE TABLE "deck" (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`name`	TEXT NOT NULL,
	`class`	INTEGER NOT NULL,
	`tag1`	INTEGER,
	`tag2`	INTEGER
);
CREATE TABLE "cards" (
	`id`	TEXT NOT NULL,
	`name`	TEXT NOT NULL,
	`rarity`	TEXT NOT NULL,
	`cost`	INTEGER NOT NULL,
	`health`	INTEGER NOT NULL,
	`attack`	INTEGER NOT NULL,
	`set`	INTEGER NOT NULL,
	`collectible`	INTEGER NOT NULL,
	`type`	TEXT NOT NULL,
	`player_class`	INTEGER NOT NULL,
	PRIMARY KEY(id)
);
CREATE TABLE "card_played" (
	`rowid`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`matchid`	INTEGER NOT NULL,
	`cardid`	INTEGER NOT NULL,
	`turn`	INTEGER NOT NULL,
	`local`	INTEGER NOT NULL,
	FOREIGN KEY(`cardid`) REFERENCES `cards`(`id`)
);
COMMIT;
"""

card_table_sql = """CREATE TABLE "cards" (
	`id`	TEXT NOT NULL,
	`name`	TEXT NOT NULL,
	`rarity`	TEXT NOT NULL,
	`cost`	INTEGER NOT NULL,
	`health`	INTEGER NOT NULL,
	`attack`	INTEGER NOT NULL,
	`set`	INTEGER NOT NULL,
	`collectible`	INTEGER NOT NULL,
	`type`	TEXT NOT NULL,
	`player_class`	INTEGER NOT NULL,
	PRIMARY KEY(id)
);"""

def download_cards():
    url = "https://api.hearthstonejson.com/v1/latest/enUS/cards.json"
    def download_hsjson(url):
        context = ssl._create_unverified_context()
        req = urllib.request.urlopen(url, context=context)
        f = req.read()
        with open('cards.json', 'wb') as file:
            file.write(f)
        return f

    raw_data = download_hsjson(url)

    with open('cards.json', 'r', encoding='utf-8') as f:
        cards_json = json.load(f)

    with open('cards.json', 'w', encoding='utf-8') as f:
        json.dump(cards_json, f, sort_keys=True, indent=4)
    
    return cards_json

def check_db_integrity(cursor):
    """Does a simply check for tables in the database, returns True if they exist and false otherwise"""
    tbl_query = r"SELECT * FROM sqlite_master WHERE type='table'"
    rows = cursor.execute(tbl_query).fetchall()
    if rows:
        tables = [row['name'] for row in rows]
        if 'cards' in tables and 'match' in tables:
            return True
    else:
        return False


def update_cards(cursor, cards):
    hero_dict = {9: 'priest', 3: 'rogue', 8: 'mage', 4: 'paladin', 1: 'warrior',
                 7: 'warlock', 5: 'hunter', 2: 'shaman', 6: 'druid'}
    hero_dict_names = {v: k for k, v in hero_dict.items()}
    insert_card_sql = """INSERT INTO `cards`(`id`,`name`,'rarity', 'cost',`health`,`attack`,`set`,`collectible`,`type`,`player_class`) 
                VALUES (?,?,?,?,?,?,?,?,?,?);"""
    cursor.execute('DROP TABLE cards')
    cursor.execute(card_table_sql)
    hero_re = re.compile(r'HERO_0(\d)')
    for card in cards:
        m = hero_re.match(card['id'])
        if m:
            sql_str = 'SELECT * from hero where cardid LIKE ?'
            row = cursor.execute(sql_str, ("%" + card['id'],)).fetchone()
            if not row:
                logging.info('Could not find hero %s, inserting', card['id'])
                sql_str2 = 'INSERT INTO hero (name, cardid, class) VALUES (?,?,?)'
                cursor.execute(
                    sql_str2, (card['name'], card['id'], m.group(1)))

        tmp = card.get('playerClass', None)
        player_class = -1
        if tmp is not None:
            if player_class in hero_dict_names:
                player_class = hero_dict_names[tmp.lower()]
        
        if card['type'] in ('MINION', 'SPELL', 'WEAPON'):
            ins = (card['id'], card['name'], card.get('rarity', ""), card.get('cost', -1),
                card.get('health', -1), card.get('attack', -
                                                    1), card.get('set', ""), card.get('collectible', -1),
                card['type'], player_class)
            logging.debug('Insert card %s', card['id'])
            cursor.execute(insert_card_sql, ins)

# if __name__ == '__main__':
#     dbf = 'stats2.db'
#     db = sqlite3.connect(dbf)
#     db.row_factory = sqlite3.Row
#     cursor = db.cursor()
#     db_ok = check_db_integrity(cursor)
#     if db_ok == False:
#         import pdb
#         pdb.set_trace()
#         db.close()
#         os.remove(dbf)
#         db = sqlite3.connect(dbf)
#         db.row_factory = sqlite3.Row
#         cursor = db.cursor()
#         cursor.executescript(database_script)
#         db.commit()
#         cards = download_cards()
#         update_cards(cursor, cards)
#         db.commit()
#         db.close()
#     else:
#         cards = download_cards()
#         update_cards(cursor, cards)