"""Run a command in the logged-in test user's KDE or GNOME session (inside the VM)."""

import os
from pathlib import Path
import subprocess
import sys

SESSION_VARIABLES = {
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XAUTHORITY",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "XDG_SESSION_TYPE",
    "XDG_CURRENT_DESKTOP",
    "XDG_SESSION_DESKTOP",
    "KDE_FULL_SESSION",
    "KDE_SESSION_VERSION",
}


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 desktop_run.py COMMAND [ARG ...]")
    for name in ("plasmashell", "gnome-shell"):
        result = subprocess.run(
            ["pgrep", "-u", str(os.getuid()), "-x", name],
            capture_output=True,
            text=True,
        )
        pids = result.stdout.splitlines()
        if len(pids) > 1:
            raise SystemExit(
                f"Multiple {name} processes: reboot into the intended session first"
            )
        if not pids:
            continue
        for variable in SESSION_VARIABLES:
            os.environ.pop(variable, None)
        entries = Path(f"/proc/{pids[0]}/environ").read_bytes().split(b"\0")
        for entry in entries:
            if b"=" in entry:
                key, value = os.fsdecode(entry).split("=", 1)
                if key in SESSION_VARIABLES:
                    os.environ[key] = value
        runtime = Path(f"/run/user/{os.getuid()}")
        os.environ.setdefault("XDG_RUNTIME_DIR", str(runtime))
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={runtime}/bus"
        # GNOME's process environment can omit the Wayland socket name.
        if (
            not os.environ.get("WAYLAND_DISPLAY")
            and os.environ.get("XDG_SESSION_TYPE") != "x11"
        ):
            sockets = [path for path in runtime.glob("wayland-*") if path.is_socket()]
            if len(sockets) == 1:
                os.environ["WAYLAND_DISPLAY"] = sockets[0].name
        os.environ["LC_ALL"] = "C.UTF-8"
        os.execvp(sys.argv[1], sys.argv[1:])
    raise SystemExit("No desktop session is running for this user")


if __name__ == "__main__":
    main()
