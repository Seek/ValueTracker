import sqlite3
import json
import re

exp = "HERO_0(\d)"
exp = re.compile(exp)
filename = 'stats.db'
sql = "INSERT INTO 'hero'('cardid', 'name') VALUES (?,?)"
sql2 = "SELECT * FROM 'hero' WHERE cardid=?"
db = sqlite3.connect(filename)
cursor = db.cursor()
file = open('db_script.sql', 'r')
data = file.read()
file.close()
cursor.executescript(data)
db.commit()

with open('cards.json', 'r', encoding='utf-8') as f:
    cards_json = json.load(f)
    for c in cards_json:
        match = exp.match(c['id'])
        if match:
            print(c['id'])
            result = cursor.execute(sql2, (c['id'],))
            result = result.fetchone()
            if result is None:
                print(c['name'])
                cursor.execute(sql, (c['id'], c['name']))
db.commit()
db.close()