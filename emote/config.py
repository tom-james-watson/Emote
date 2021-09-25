import os


is_debug = os.environ.get("GTK_DEBUG") == "interactive"
is_dev = os.environ.get("ENV") == "dev"
is_snap = os.environ.get("SNAP") is not None
snap_root = os.environ.get("SNAP")
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"

if is_snap:
    static_root = f"{snap_root}/static"
elif is_dev:
    static_root = os.path.dirname(os.path.dirname(__file__)) + "/static"
else:
    static_root = os.path.dirname(__file__) + "/static"

if not os.path.exists(static_root):
    raise Exception(f"Directory not found: {static_root}")
