import csv
import re
from collections import defaultdict
from emote import user_data, config


# These are emojis that support skintone sequences but that are not yet
# supported on the core18 snap base and as such would render as two separate
# emojis.
SKINTONE_SEQUENCE_BLOCKLIST = [
    "hand_with_fingers_splayed",
    "victory_hand",
    "backhand_index_pointing_left",
    "backhand_index_pointing_right",
    "backhand_index_pointing_up",
    "backhand_index_pointing_down",
    "index_pointing_up",
    "thumbs_up",
    "thumbs_down",
    "writing_hand",
    "ear",
    "man_beard",
    "woman_beard",
    "woman_blond_hair",
    "man_blond_hair",
    "man_frowning",
    "woman_frowning",
    "man_pouting",
    "woman_pouting",
    "man_gesturing_no",
    "woman_gesturing_no",
    "man_gesturing_ok",
    "woman_gesturing_ok",
    "man_tipping_hand",
    "woman_tipping_hand",
    "man_raising_hand",
    "woman_raising_hand",
    "man_bowing",
    "woman_bowing",
    "man_facepalming",
    "woman_facepalming",
    "man_shrugging",
    "woman_shrugging",
    "health_worker",
    "man_health_worker",
    "woman_health_worker",
    "student",
    "man_student",
    "woman_student",
    "teacher",
    "man_teacher",
    "woman_teacher",
    "judge",
    "man_judge",
    "woman_judge",
    "farmer",
    "man_farmer",
    "woman_farmer",
    "cook",
    "man_cook",
    "woman_cook",
    "mechanic",
    "man_mechanic",
    "woman_mechanic",
    "factory_worker",
    "man_factory_worker",
    "woman_factory_worker",
    "office_worker",
    "man_office_worker",
    "woman_office_worker",
    "scientist",
    "man_scientist",
    "woman_scientist",
    "technologist",
    "man_technologist",
    "woman_technologist",
    "singer",
    "man_singer",
    "woman_singer",
    "artist",
    "man_artist",
    "woman_artist",
    "pilot",
    "man_pilot",
    "woman_pilot",
    "astronaut",
    "man_astronaut",
    "woman_astronaut",
    "firefighter",
    "man_firefighter",
    "woman_firefighter",
    "man_police_officer",
    "woman_police_officer",
    "detective",
    "man_detective",
    "woman_detective",
    "man_guard",
    "woman_guard",
    "man_construction_worker",
    "woman_construction_worker",
    "man_wearing_turban",
    "woman_wearing_turban",
    "man_in_tuxedo",
    "woman_in_tuxedo",
    "man_with_veil",
    "woman_with_veil",
    "woman_feeding_baby",
    "man_feeding_baby",
    "person_feeding_baby",
    "mx_claus",
    "man_mage",
    "woman_mage",
    "man_fairy",
    "woman_fairy",
    "man_vampire",
    "woman_vampire",
    "merman",
    "mermaid",
    "man_elf",
    "woman_elf",
    "man_getting_massage",
    "woman_getting_massage",
    "man_getting_haircut",
    "woman_getting_haircut",
    "man_walking",
    "woman_walking",
    "man_running",
    "woman_running",
    "person_in_suit_levitating",
    "man_in_steamy_room",
    "woman_in_steamy_room",
    "man_climbing",
    "woman_climbing",
    "snowboarder",
    "person_golfing",
    "man_golfing",
    "woman_golfing",
    "person_surfing",
    "man_surfing",
    "woman_surfing",
    "man_rowing_boat",
    "woman_rowing_boat",
    "person_swimming",
    "man_swimming",
    "woman_swimming",
    "person_bouncing_ball",
    "man_bouncing_ball",
    "woman_bouncing_ball",
    "person_lifting_weights",
    "man_lifting_weights",
    "woman_lifting_weights",
    "man_biking",
    "woman_biking",
    "man_mountain_biking",
    "woman_mountain_biking",
    "man_cartwheeling",
    "woman_cartwheeling",
    "man_playing_water_polo",
    "woman_playing_water_polo",
    "man_playing_handball",
    "woman_playing_handball",
    "man_juggling",
    "woman_juggling",
    "man_in_lotus_position",
    "woman_in_lotus_position",
    "people_holding_hands",
    "kiss_woman_man",
    "kiss_man_man",
    "kiss_woman_woman",
    "couple_with_heart_woman_man",
    "couple_with_heart_man_man",
    "couple_with_heart_woman_woman",
    "pinched_fingers",
    "pinching_hand",
    "leg",
    "foot",
    "ear_with_hearing_aid",
    "deaf_person",
    "ninja",
    "superhero",
    "supervillain",
    "person_standing",
    "person_kneeling",
]
# These are emojis that are not supported on core18 snap base and as such
# render as two separate emojis. The app itself bundles a recent version of the
# NotoColorEmoji font and so can display recent single char emojis, however any
# emojis that are sequences also require a recent version of pango for the OS
# to recognise and combine the sequences. Upgrading to core20 should let us
# include more recent unicode sequences:
# https://github.com/tom-james-watson/Emote/issues/48.
SEQUENCE_BLOCKLIST = [
    "man_red_hair",
    "man_curly_hair",
    "man_white_hair",
    "man_bald",
    "woman_red_hair",
    "person_red_hair",
    "woman_curly_hair",
    "person_curly_hair",
    "woman_white_hair",
    "person_white_hair",
    "woman_bald",
    "person_bald",
    "deaf_man",
    "deaf_woman",
    "man_superhero",
    "woman_superhero",
    "man_supervillain",
    "woman_supervillain",
    "man_standing",
    "woman_standing",
    "man_kneeling",
    "woman_kneeling",
    "person_with_white_cane",
    "man_with_white_cane",
    "woman_with_white_cane",
    "person_in_motorized_wheelchair",
    "man_in_motorized_wheelchair",
    "woman_in_motorized_wheelchair",
    "person_in_manual_wheelchair",
    "man_in_manual_wheelchair",
    "woman_in_manual_wheelchair",
    "service_dog",
    "transgender_flag",
    "mending_heart",
]
EMOJI_CATEGORY_BLOCKLIST = ["component", "extras-openmoji", "extras-unicode"]


emojis_by_category = defaultdict(list)
all_emojis = []


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

            if shortcode in SEQUENCE_BLOCKLIST:
                continue

            emoji = {
                "keywords": (row["tags"] + row["openmoji_tags"]).split(", "),
                "char": row["emoji"],
                "name": row["annotation"].capitalize(),
                "shortcode": shortcode,
                "skintone": row["skintone_combination"] == "single"
                and shortcode not in SKINTONE_SEQUENCE_BLOCKLIST,
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
