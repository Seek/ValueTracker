import json
import requests
from controls import Card, card_from_row


def deck_from_tempostorm(url, cursor):
    deck_str = url[url.rfind('/') + 1:]
    tempo_storm_url = 'https://tempostorm.com/api/decks/findOne?filter='
    tempo_storm_req = {'fields': {},
                       'include': [{'relation': 'cards', 'scope': {'include': 'card'}}],
                       'where': {'slug': 'midrange-shaman-standard-meta-snapshot-may-29-2016'}}
    tempo_storm_req['where']['slug'] = deck_str
    resp = requests.get(url=tempo_storm_url + json.dumps(tempo_storm_req))
    data = json.loads(resp.text, encoding = 'utf-8')
    if 'heroName' not in data:
        return
    
    hero = data['heroName']
    deck_name = data['name']
    cards = [(card['card']['name'], card['cardQuantity'])
             for card in data['cards']]
    deck = {}
    for i, card in enumerate(cards):
        row = cursor.execute('SELECT * FROM cards WHERE name LIKE ?',
                             ('%{0}%'.format(card[0]),)).fetchone()
        deck[row['id']] = [card_from_row(row), card[1]]
    if hero == 'Guldan':
        hero = "Gul'dan"
    hero_id = cursor.execute('SELECT class FROM hero WHERE name LIKE ?',
                             ('%{0}%'.format(hero),)).fetchone()['class']
    return (hero_id, deck_name, deck)


if __name__ == '__main__':
    import pdb
    import sqlite3
    db = sqlite3.connect('example_stats.db')
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    hero, deck_name, deck = deck_from_tempostorm(
        "https://tempostorm.com/hearthstone/decks/zoolock-standard-meta-snapshot-may-29-2016", cursor)
