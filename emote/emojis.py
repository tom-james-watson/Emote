import os
import json
from collections import defaultdict


MAX_VERSION = 10.0


emojis_by_category = defaultdict(list)
all_emojis = []


def init():
    global all_emojis
    global emojis_by_category

    snap = os.environ.get("SNAP")

    if snap:
        filename = f'{snap}/static/emojis.json'
    else:
        filename = 'static/emojis.json'

    with open(filename, 'r') as f:
        emojis = json.load(f)

        for emoji_key in emojis.keys():
            emoji = emojis[emoji_key].copy()
            emoji.update({'name': emoji_key})

            emojis_by_category[emoji['category']].append(emoji)
            all_emojis.append(emoji)


def get_category_order():
    '''
    Return the categories in the order want to render them in

    Returned as arrays of tuples in the form
    (<category name>, <category display name>)
    '''
    return [
        ('people', 'Smileys & People'),
        ('animals_and_nature', 'Animals & Nature'),
        ('food_and_drink', 'Food & Drink'),
        ('activity', 'Activities'),
        ('travel_and_places', 'Travel & Places'),
        ('objects', 'Objects'),
        ('symbols', 'Symbols'),
        ('flags', 'Flags')
    ]


def get_emojis_by_category():
    return emojis_by_category


def search(query):
    def search_filter(emoji):
        return (
            emoji['name'].startswith(query) or
            any(keyword.startswith(query) for keyword in emoji['keywords'])
        )

    return list(filter(search_filter, all_emojis))
