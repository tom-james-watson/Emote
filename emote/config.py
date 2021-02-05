import os


is_snap = os.environ.get("SNAP") is not None
snap_root = os.environ.get("SNAP")
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
