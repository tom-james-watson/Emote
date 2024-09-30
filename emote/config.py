import os

app_id = "com.tomjwatson.Emote"
is_debug = os.environ.get("GTK_DEBUG") == "interactive"
is_dev = os.environ.get("ENV") == "dev"
is_snap = os.environ.get("SNAP") is not None
snap_root = os.environ.get("SNAP")
is_flatpak = os.environ.get("FLATPAK") is not None
flatpak_root = os.environ.get("FLATPAK")
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"

version = os.environ.get("FLATPAK_APP_VERSION", os.environ.get("SNAP_VERSION", "dev build"))

css_path = (
    f"{snap_root}/static/style.css"
    if is_snap
    else f"{flatpak_root}/static/style.css"
    if is_flatpak
    else "static/style.css"
)

emoji_path = (
    f"{snap_root}/static/emojis.csv"
    if is_snap
    else f"{flatpak_root}/static/emojis.csv"
    if is_flatpak
    else "static/emojis.csv"
)

logo_path = (
    f"{snap_root}/static/logo.svg"
    if is_snap
    else f"{flatpak_root}/static/logo.svg"
    if is_flatpak
    else "static/logo.svg"
)

version = os.environ.get("FLATPAK_APP_VERSION", os.environ.get("SNAP_VERSION", "dev build"))

css_path = (
    f"{snap_root}/static/style.css"
    if is_snap
    else f"{flatpak_root}/static/style.css"
    if is_flatpak
    else "static/style.css"
)

emoji_path = (
    f"{snap_root}/static/emojis.csv"
    if is_snap
    else f"{flatpak_root}/static/emojis.csv"
    if is_flatpak
    else "static/emojis.csv"
)

logo_path = (
    f"{snap_root}/static/logo.svg"
    if is_snap
    else f"{flatpak_root}/static/logo.svg"
    if is_flatpak
    else "static/logo.svg"
)