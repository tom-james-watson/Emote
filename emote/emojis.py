import os
import json
from collections import defaultdict
from emote import user_data, config


MAX_VERSION = 10.0


emojis_by_category = defaultdict(list)
all_emojis = []


def init():
    global all_emojis
    global emojis_by_category

    if config.is_snap:
        filename = f"{config.snap_root}/static/emojis.json"
    else:
        filename = "static/emojis.json"

    with open(filename, "r") as f:
        emojis = json.load(f)

        for emoji_key in emojis.keys():
            emoji = emojis[emoji_key].copy()
            emoji.update({"name": emoji_key})

            emojis_by_category[emoji["category"]].append(emoji)
            all_emojis.append(emoji)

    update_recent_category()


def get_emoji_by_char(char):
    for emoji in all_emojis:
        if emoji["char"] == char:
            return emoji

    raise Exception(f"Couldn't find emoji by char {char}")


def update_recent_category():
    emojis_by_category["recent"] = []

    for char in user_data.load_recent_emojis():
        try:
            emoji = get_emoji_by_char(char)
        except:
            continue
        emojis_by_category["recent"].append(
            {"char": char, "category": "recent", "name": emoji["name"]}
        )


def get_category_order():
    """
    Return the categories in the order want to render them in

    Returned as arrays of tuples in the form
    (<category name>, <category display name>, <category_image>)
    """
    return [
        ("recent", "Recently Used", "🕙"),
        ("people", "Smileys & People", "🙂"),
        ("animals_and_nature", "Animals & Nature", "🐯"),
        ("food_and_drink", "Food & Drink", "🍔"),
        ("activity", "Activities", "⚽"),
        ("travel_and_places", "Travel & Places", "✈️"),
        ("objects", "Objects", "💡"),
        ("symbols", "Symbols", "❤️"),
        ("flags", "Flags", "🇺🇳"),
    ]


def get_emojis_by_category():
    return emojis_by_category


def search(query):
    query = query.lower()

    def search_filter(emoji):
        parts = emoji["name"].split("_")
        search_terms = parts + [" ".join(parts)] + emoji["keywords"]
        search_terms = [search_term.lower() for search_term in search_terms]
        return any(search_term.startswith(query) for search_term in search_terms)

    return list(filter(search_filter, all_emojis))
