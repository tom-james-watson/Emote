import dbm
import json
import os
from pathlib import Path
import shelve
import tempfile

from emote import emojis, config

DATA_DIR = (
    os.path.join(Path.home(), ".local/share/Emote")
    if not config.is_flatpak
    else os.path.join(Path.home(), f".var/app/{config.app_id}/data")
)
SHELVE_PATH = os.path.join(DATA_DIR, "user_data")

SETTINGS_PATH = os.path.join(
    os.environ.get("XDG_CONFIG_HOME") or os.path.join(Path.home(), ".config"),
    "Emote",
    "settings.json",
)

RECENT_EMOJIS = "recent_emojis"
DEFAULT_RECENT_EMOJIS = ["🙂", "😄", "❤️", "👍", "🤞", "🔥", "🤣", "😍", "😭"]
MAX_RECENT_EMOJIS = 60

ACCELERATOR = "accelerator"
DEFAULT_ACCELERATOR = "<Primary><Alt>e"

WAYLAND_AUTO_PASTE = "wayland_auto_paste"
X11_AUTO_PASTE = "x11_auto_paste"
WAYLAND_GLOBAL_SHORTCUT = "wayland_global_shortcut"
WAYLAND_GLOBAL_SHORTCUT_LABEL = "wayland_global_shortcut_label"
SHOWN_WELCOME = "shown_welcome"

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

DEFAULT_SETTINGS = {
    ACCELERATOR: DEFAULT_ACCELERATOR,
    SKINTONE_INDEX: DEFAULT_SKINTONE_INDEX,
    EMOJI_SIZE: DEFAULT_EMOJI_SIZE,
    PICKER_SIZE: list(DEFAULT_PICKER_SIZE),
    X11_AUTO_PASTE: True,
    WAYLAND_AUTO_PASTE: None,
    SHOWN_WELCOME: False,
}

SHELVE_KEY_TO_SETTING = {
    "accelerator_string": ACCELERATOR,
    SKINTONE_INDEX: SKINTONE_INDEX,
    EMOJI_SIZE: EMOJI_SIZE,
    PICKER_SIZE: PICKER_SIZE,
    X11_AUTO_PASTE: X11_AUTO_PASTE,
    WAYLAND_AUTO_PASTE: WAYLAND_AUTO_PASTE,
    SHOWN_WELCOME: SHOWN_WELCOME,
}


# Ensure the data dir exists
os.makedirs(DATA_DIR, exist_ok=True)


def _legacy_settings():
    try:
        with shelve.open(SHELVE_PATH, flag="r") as db:
            return {
                key: db[legacy_key]
                for legacy_key, key in SHELVE_KEY_TO_SETTING.items()
                if legacy_key in db
            }
    except dbm.error:
        return {}


def _write_settings(settings):
    config_dir = os.path.dirname(SETTINGS_PATH)
    os.makedirs(config_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=config_dir, suffix=".tmp", delete=False
    ) as settings_file:
        json.dump(settings, settings_file, indent=2)
        settings_file.write("\n")
    os.replace(settings_file.name, SETTINGS_PATH)


def _load_or_create_settings():
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
    except FileNotFoundError:
        settings = {**DEFAULT_SETTINGS, **_legacy_settings()}
        _write_settings(settings)
        return settings
    except ValueError as error:
        print(f"Ignoring unreadable {SETTINGS_PATH}: {error}")
        return None
    if not isinstance(settings, dict):
        print(f"Ignoring {SETTINGS_PATH}: expected a JSON object")
        return None
    return settings


def _read_setting(key, kind):
    value = (_load_or_create_settings() or {}).get(key)
    # Exact type check: bool is a subclass of int, and JSON numbers may be floats
    return value if type(value) is kind else DEFAULT_SETTINGS[key]


def _update_setting(key, value):
    settings = _load_or_create_settings()
    if settings is None:
        os.replace(SETTINGS_PATH, SETTINGS_PATH + ".bak")
        print(f"Moved unreadable settings to {SETTINGS_PATH}.bak")
        settings = dict(DEFAULT_SETTINGS)
    settings[key] = value
    _write_settings(settings)


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
    return _read_setting(ACCELERATOR, str)


def update_accelerator(accel):
    _update_setting(ACCELERATOR, accel)


def load_wayland_auto_paste_choice():
    """Return None until the user has chosen a Wayland paste mode."""
    return _read_setting(WAYLAND_AUTO_PASTE, bool)


def update_wayland_auto_paste_choice(enabled):
    _update_setting(WAYLAND_AUTO_PASTE, bool(enabled))


def load_x11_auto_paste_enabled():
    return _read_setting(X11_AUTO_PASTE, bool)


def update_x11_auto_paste_enabled(enabled):
    _update_setting(X11_AUTO_PASTE, bool(enabled))


def load_wayland_global_shortcut_choice():
    """Return whether the portal most recently reported Emote's shortcut."""
    with shelve.open(SHELVE_PATH) as db:
        return db.get(WAYLAND_GLOBAL_SHORTCUT)


def update_wayland_global_shortcut_choice(enabled):
    with shelve.open(SHELVE_PATH) as db:
        db[WAYLAND_GLOBAL_SHORTCUT] = bool(enabled)


def load_wayland_global_shortcut_label():
    with shelve.open(SHELVE_PATH) as db:
        return db.get(WAYLAND_GLOBAL_SHORTCUT_LABEL, "Ctrl+Alt+E")


def update_wayland_global_shortcut_label(label):
    with shelve.open(SHELVE_PATH) as db:
        db[WAYLAND_GLOBAL_SHORTCUT_LABEL] = str(label)


def load_shown_welcome():
    return _read_setting(SHOWN_WELCOME, bool)


def update_shown_welcome():
    _update_setting(SHOWN_WELCOME, True)


def normalize_picker_size(size):
    try:
        width, height = size
        return max(460, int(width)), max(300, int(height))
    except (TypeError, ValueError):
        return DEFAULT_PICKER_SIZE


def load_picker_size():
    return normalize_picker_size(_read_setting(PICKER_SIZE, list))


def update_picker_size(width, height):
    _update_setting(PICKER_SIZE, list(normalize_picker_size((width, height))))


def normalize_emoji_size(size):
    try:
        return min(EMOJI_SIZES, key=lambda option: abs(option - float(size)))
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_EMOJI_SIZE


def load_emoji_size():
    return normalize_emoji_size(_read_setting(EMOJI_SIZE, int))


def update_emoji_size(size):
    _update_setting(EMOJI_SIZE, normalize_emoji_size(size))


def load_skintone_index():
    index = _read_setting(SKINTONE_INDEX, int)
    return index if 0 <= index < len(SKINTONES) else DEFAULT_SKINTONE_INDEX


def update_skintone_index(skintone):
    _update_setting(SKINTONE_INDEX, skintone)
