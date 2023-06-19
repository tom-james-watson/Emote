import csv
import re
from collections import defaultdict
from emote import user_data, config

EMOJI_CATEGORY_BLOCKLIST = ["component", "extras-openmoji", "extras-unicode"]


emojis_by_category = defaultdict(list)
all_emojis = []


def make_emoji_data(row):
    shortcode = row["annotation"].lower().replace("-", " ")
    shortcode = re.sub(r"[^\w\s]", "", shortcode).replace(" ", "_")

    return {
        "keywords": (row["tags"] + row["openmoji_tags"]).split(", "),
        "char": row["emoji"],
        "name": row["annotation"].capitalize(),
        "shortcode": shortcode,
        "skintone": {} if row["skintone_combination"] == "single" else None,
    }


def process_emoji_row(row):
    global all_emojis
    global emojis_by_category
    category = row["group"]

    # Ignore uninteresting emojis
    if category in EMOJI_CATEGORY_BLOCKLIST:
        return

    if category in ["smileys-emotion", "people-body"]:
        category = "smileys-people"

    if row["skintone"] != "":
        for emoji in all_emojis:
            if (
                row["skintone_base_emoji"] == emoji["char"]
                and emoji["skintone"] is not None
            ):
                emoji["skintone"][row["skintone"]] = make_emoji_data(row)
                return

    emoji = make_emoji_data(row)
    emojis_by_category[category].append(emoji)
    all_emojis.append(emoji)


def init():
    filename = (
        f"{config.snap_root}/static/emojis.csv"
        if config.is_snap
        else f"{config.flatpak_root}/static/emojis.csv"
        if config.is_flatpak
        else "static/emojis.csv"
    )

    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            process_emoji_row(row)

    update_recent_category()


def strip_char_skintone(char):
    # Define a regex pattern for skin tone modifiers
    skintone_pattern = re.compile("[\U0001F3FB-\U0001F3FF]")

    return skintone_pattern.sub("", char)


def strip_qualified_variant(char):
    return char.replace("\uFE0F", "")


def get_emoji_by_char(char):
    char = strip_qualified_variant(strip_char_skintone(char))

    for emoji in all_emojis:
        if strip_qualified_variant(emoji["char"]) == char:
            return emoji

    raise Exception(f"Couldn't find emoji by char {char}")


def update_recent_category():
    global emojis_by_category
    emojis_by_category["recent"] = []

    for char in user_data.load_recent_emojis():
        try:
            emoji = get_emoji_by_char(char)
        except Exception:
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
