import csv
import re
from collections import defaultdict
from emote import user_data, config


EMOJI_CATEGORY_BLOCKLIST = ["component", "extras-openmoji", "extras-unicode"]


emojis_by_category = defaultdict(list)
all_emojis = []


def init():
    global all_emojis
    global emojis_by_category

    filename = (
        f"{config.flatpak_root}/static/emojis.csv"
        if config.is_flatpak
        else "static/emojis.csv"
    )

    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            category = row["group"]

            # Ignore uninteresting emojis
            if category in EMOJI_CATEGORY_BLOCKLIST:
                continue

            if category in ["smileys-emotion", "people-body"]:
                category = "smileys-people"

            # Ignore emojis that are skintone combinations of other emojis. We
            # will handle this ourselves in the app.
            if row["skintone"] != "":
                continue

            shortcode = row["annotation"].lower().replace("-", " ")
            shortcode = re.sub(r"[^\w\s]", "", shortcode).replace(" ", "_")

            emoji = {
                "keywords": (row["tags"] + row["openmoji_tags"]).split(", "),
                "char": row["emoji"],
                "name": row["annotation"].capitalize(),
                "shortcode": shortcode,
                "skintone": row["skintone_combination"] == "single"
            }
            emojis_by_category[category].append(emoji)
            all_emojis.append(emoji)

    update_recent_category()


def strip_char_skintone(char):
    for skintone in user_data.SKINTONES:
        char = char.replace(skintone, "")

    return char


def get_emoji_by_char(char):
    char = strip_char_skintone(char)

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
        emojis_by_category["recent"].append(emoji)


def get_category_order():
    """
    Return the categories in the order want to render them in

    Returned as arrays of tuples in the form
    (<category name>, <category display name>, <category_image>)
    """
    return [
        ("recent", "Recently Used", "🕙"),
        ("smileys-people", "Smileys & People", "🙂"),
        ("animals-nature", "Animals & Nature", "🐯"),
        ("food-drink", "Food & Drink", "🍔"),
        ("activities", "Activities", "⚽"),
        ("travel-places", "Travel & Places", "✈️"),
        ("objects", "Objects", "💡"),
        ("symbols", "Symbols", "⁉️"),
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
        return any(query in search_term for search_term in search_terms)

    return list(filter(search_filter, all_emojis))
