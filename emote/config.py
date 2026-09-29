import os

app_id = "com.tomjwatson.Emote"
is_debug = os.environ.get("GTK_DEBUG") == "interactive"
is_dev = os.environ.get("ENV") == "dev"
is_snap = os.environ.get("SNAP") is not None
snap_root = os.environ.get("SNAP")
is_flatpak = "FLATPAK_ID" in os.environ
if "EMOTE_PKGDATADIR" in os.environ:
    static_dir = f"{os.environ['EMOTE_PKGDATADIR']}/static"
elif is_snap:
    static_dir = f"{snap_root}/static"
else:
    static_dir = "static"
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
