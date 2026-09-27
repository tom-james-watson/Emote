import os
from pathlib import Path
import shelve

from emote import emojis, config

DATA_DIR = (
    os.path.join(Path.home(), ".local/share/Emote")
    if not config.is_flatpak
    else os.path.join(Path.home(), f".var/app/{config.app_id}/data")
)
SHELVE_PATH = os.path.join(DATA_DIR, "user_data")

RECENT_EMOJIS = "recent_emojis"
DEFAULT_RECENT_EMOJIS = ["🙂", "😄", "❤️", "👍", "🤞", "🔥", "🤣", "😍", "😭"]
MAX_RECENT_EMOJIS = 60

ACCELERATOR_STRING = "accelerator_string"
DEFAULT_ACCELERATOR_STRING = "<Primary><Alt>e"

ACCELERATOR_LABEL = "accelerator_label"
DEFAULT_ACCELERATOR_LABEL = "Ctrl+Alt+E"

SHOWN_WELCOME = "shown_welcome"
DEFAULT_SHOWN_WELCOME = False

SKINTONE_INDEX = "skintone_index"
DEFAULT_SKINTONE_INDEX = 0
SKINTONES = ["✋", "✋🏻", "✋🏼", "✋🏽", "✋🏾", "✋🏿"]

PICKER_SIZE = "picker_size"
DEFAULT_PICKER_SIZE = (515, 500)

EMOJI_SIZE = "emoji_size"
DEFAULT_EMOJI_SIZE = 28
EMOJI_SIZES = (20, 24, 28, 32, 36)
EMOJI_SIZE_LABELS = (
    "Small (20 px)",
    "Compact (24 px)",
    "Default (28 px)",
    "Large (32 px)",
    "Extra large (36 px)",
)


# Ensure the data dir exists
os.makedirs(DATA_DIR, exist_ok=True)


def load_recent_emojis():
    with shelve.open(SHELVE_PATH) as db:
        return db.get(RECENT_EMOJIS, DEFAULT_RECENT_EMOJIS)


def update_recent_emojis(char):
    char = emojis.strip_char_skintone(char)
    recent_emojis = load_recent_emojis()

    if char in recent_emojis:
        recent_emojis.remove(char)
        new_recent_emojis = [char] + recent_emojis[: MAX_RECENT_EMOJIS - 2]
    else:
        new_recent_emojis = [char] + recent_emojis[: MAX_RECENT_EMOJIS - 1]

    with shelve.open(SHELVE_PATH) as db:
        db[RECENT_EMOJIS] = new_recent_emojis


def load_accelerator():
    with shelve.open(SHELVE_PATH) as db:
        return (
            db.get(ACCELERATOR_STRING, DEFAULT_ACCELERATOR_STRING),
            db.get(ACCELERATOR_LABEL, DEFAULT_ACCELERATOR_LABEL),
        )


def update_accelerator(accel_string, accel_label):
    with shelve.open(SHELVE_PATH) as db:
        db[ACCELERATOR_STRING] = accel_string
        db[ACCELERATOR_LABEL] = accel_label


def load_shown_welcome():
    with shelve.open(SHELVE_PATH) as db:
        return db.get(SHOWN_WELCOME, DEFAULT_SHOWN_WELCOME)


def update_shown_welcome():
    with shelve.open(SHELVE_PATH) as db:
        db[SHOWN_WELCOME] = True


def normalize_picker_size(size):
    try:
        width, height = size
        return max(460, int(width)), max(300, int(height))
    except (TypeError, ValueError):
        return DEFAULT_PICKER_SIZE


def load_picker_size():
    with shelve.open(SHELVE_PATH) as db:
        return normalize_picker_size(db.get(PICKER_SIZE, DEFAULT_PICKER_SIZE))


def update_picker_size(width, height):
    with shelve.open(SHELVE_PATH) as db:
        db[PICKER_SIZE] = normalize_picker_size((width, height))


def normalize_emoji_size(size):
    try:
        return min(EMOJI_SIZES, key=lambda option: abs(option - float(size)))
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_EMOJI_SIZE


def load_emoji_size():
    with shelve.open(SHELVE_PATH) as db:
        return normalize_emoji_size(db.get(EMOJI_SIZE, DEFAULT_EMOJI_SIZE))


def update_emoji_size(size):
    with shelve.open(SHELVE_PATH) as db:
        db[EMOJI_SIZE] = normalize_emoji_size(size)


def load_skintone_index():
    with shelve.open(SHELVE_PATH) as db:
        return db.get(SKINTONE_INDEX, DEFAULT_SKINTONE_INDEX)


def update_skintone_index(skintone):
    with shelve.open(SHELVE_PATH) as db:
        db[SKINTONE_INDEX] = skintone
