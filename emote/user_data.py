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

THEME = "theme"
DEFAULT_THEME = "System Default"
THEMES = [
    DEFAULT_THEME,
    "Adwaita",
    "Adwaita-dark",
    "Ambiance",
    "Ambiant-MATE",
    "Ambiant-MATE-Dark",
    "Arc",
    "Arc-Dark",
    "Arc-Darker",
    "Breeze",
    "Breeze-Dark",
    "Communitheme",
    "Communitheme-dark",
    "Communitheme-light",
    "Greybird",
    "Greybird-dark",
    "HighContrast",
    "Matcha-aliz",
    "Matcha-azul",
    "Matcha-dark-aliz",
    "Matcha-dark-azul",
    "Matcha-dark-sea",
    "Matcha-sea",
    "Materia",
    "Materia-compact",
    "Materia-dark",
    "Materia-dark-compact",
    "Materia-light",
    "Materia-light-compact",
    "Radiance",
    "Radiant-MATE",
    "Yaru",
    "Yaru-dark",
    "Yaru-light",
    "elementary",
]

SKINTONE = "skintone"
DEFAULT_SKINTONE_INDEX = 0
SKINTONES = ["✋", "✋🏻", "✋🏼", "✋🏽", "✋🏾", "✋🏿"]


# Ensure the data dir exists
os.makedirs(DATA_DIR, exist_ok=True)
# Initialize shelve file if does not exist
if not os.path.exists(SHELVE_PATH):
    with shelve.open(SHELVE_PATH) as db:
        db[RECENT_EMOJIS] = DEFAULT_RECENT_EMOJIS

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


def load_theme():
    with shelve.open(SHELVE_PATH) as db:
        return db.get(THEME, DEFAULT_THEME)


def update_theme(theme):
    with shelve.open(SHELVE_PATH) as db:
        db[THEME] = theme


def load_skintone_index():
    with shelve.open(SHELVE_PATH) as db:
        return db.get(SKINTONE, DEFAULT_SKINTONE_INDEX)


def update_skintone_index(skintone):
    with shelve.open(SHELVE_PATH) as db:
        db[SKINTONE] = skintone
