import os

is_debug = os.environ.get("GTK_DEBUG") == "interactive"
is_dev = os.environ.get("ENV") == "dev"
app_id = "com.tomjwatson.Emote.Devel" if is_dev else "com.tomjwatson.Emote"
is_snap = os.environ.get("SNAP") is not None
snap_root = os.environ.get("SNAP")
is_flatpak = "FLATPAK_ID" in os.environ
# The meson launcher (used by Flatpak) exports EMOTE_VERSION; snapd sets
# SNAP_VERSION for the setuptools-based Snap build.
version = (
    os.environ.get("EMOTE_VERSION") or os.environ.get("SNAP_VERSION") or "dev build"
)
if "EMOTE_PKGDATADIR" in os.environ:
    static_dir = f"{os.environ['EMOTE_PKGDATADIR']}/static"
elif is_snap:
    static_dir = f"{snap_root}/static"
else:
    static_dir = "static"
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
is_kde = "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
is_gnome = "GNOME" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
