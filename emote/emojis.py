import csv
import re
from collections import defaultdict
from emote import user_data, config


SUPPORTED_SEQUENCES_UNICODE_VERSION = 11


emojis_by_category = defaultdict(list)
all_emojis = []
blocklisted_emoji_categories = ["component", "extras-openmoji", "extras-unicode"]


def init():
    global all_emojis
    global emojis_by_category

    filename = (
        f"{config.snap_root}/static/emojis.csv"
        if config.is_snap
        else "static/emojis.csv"
    )

    with open(filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            category = row["group"]

            # Ignore uninteresting emojis
            if category in blocklisted_emoji_categories:
                continue

            # Ignore emojis that are skintone combinations of other emojis. We
            # will handle this ourself in the app.
            if row["skintone"] != "":
                continue

            # Ignore emojis that are in recent unicode versions that are
            # sequences of emojis. The app itself bundles a recent version of
            # the NotoColorEmoji font and so can display recent single char
            # emojis, however any emojis that are sequences also require a
            # recent version of pango for the OS to recognise and combine the
            # sequences.
            # Upgrading to core20 should let us include more recent versions:
            # https://github.com/tom-james-watson/Emote/issues/48.
            if (
                float(row["unicode"]) > SUPPORTED_SEQUENCES_UNICODE_VERSION
                and len(row["emoji"]) > 1
            ):
                continue

            shortcode = row["annotation"].lower().replace("-", " ")
            shortcode = re.sub(r"[^\w\s]", "", shortcode).replace(" ", "_")

            emoji = {
                "keywords": row["tags"].split(", "),
                "char": row["emoji"],
                "name": row["annotation"].capitalize(),
                "shortcode": shortcode,
                "skintone": row["skintone_combination"] == "simple",
            }
            emojis_by_category[row["group"]].append(emoji)
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
        ("people-body", "Smileys & People", "🙂"),
        ("animals-nature", "Animals & Nature", "🐯"),
        ("food-drink", "Food & Drink", "🍔"),
        ("activities", "Activities", "⚽"),
        ("travel-places", "Travel & Places", "✈️"),
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
        return any(query in search_term for search_term in search_terms)

    return list(filter(search_filter, all_emojis))
