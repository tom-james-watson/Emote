import os
from pathlib import Path
import shelve


DATA_DIR = os.path.join(Path.home(), '.local/share/Emote')
SHELVE_PATH = os.path.join(DATA_DIR, 'user_data')
DEFAULT_RECENT_EMOJIS = ['🙂', '😄', '❤️', '👍', '😡', '🔥', '🤣', '😍', '😭']
RECENT_EMOJIS = 'recent_emojis'


# Ensure the data dir exists
os.makedirs(DATA_DIR, exist_ok=True)


def load_recent_emojis():
    with shelve.open(SHELVE_PATH) as db:
        return db.get(RECENT_EMOJIS, DEFAULT_RECENT_EMOJIS)


def update_recent_emojis(emoji):
    new_recent_emojis = [emoji] + load_recent_emojis()[:53]

    with shelve.open(SHELVE_PATH) as db:
        db[RECENT_EMOJIS] = new_recent_emojis
