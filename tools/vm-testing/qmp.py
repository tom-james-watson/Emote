"""Send mouse and keyboard input through the VM's local QMP socket."""

import argparse
import json
from pathlib import Path
import socket

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("vm")
parser.add_argument("action", choices=("move", "down", "up", "keydown", "keyup", "key"))
parser.add_argument("args", nargs="*")
parser.add_argument(
    "--root",
    type=Path,
    default=Path(__file__).resolve().parents[2] / "build/platform-tests",
)
options = parser.parse_args()
vm, action, args = options.vm, options.action, options.args
counts = {
    "move": (4,),
    "down": (0, 1),
    "up": (0, 1),
    "keydown": (1,),
    "keyup": (1,),
    "key": (1,),
}
if len(args) not in counts[action]:
    parser.error(f"Wrong number of arguments for {action}; see docs/vm-testing.md")
if Path(vm).name != vm or vm in (".", ".."):
    parser.error("VM must be a directory name under --root")
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(15)
    connection.connect(str(options.root / vm / "qmp.sock"))
    stream = connection.makefile("rwb", buffering=0)

    def request(command, arguments=None):
        payload = {"execute": command}
        if arguments is not None:
            payload["arguments"] = arguments
        stream.write((json.dumps(payload) + "\n").encode())
        while True:
            line = stream.readline()
            if not line:
                raise EOFError("QMP disconnected")
            reply = json.loads(line)
            if "return" in reply or "error" in reply:
                if "error" in reply:
                    raise RuntimeError(reply)
                return reply["return"]

    stream.readline()
    request("qmp_capabilities")
    if action == "move":
        x, y, width, height = map(int, args)
        if width < 2 or height < 2 or not (0 <= x < width and 0 <= y < height):
            parser.error("Move needs in-bounds X Y WIDTH HEIGHT")
        request(
            "input-send-event",
            {
                "events": [
                    {
                        "type": "abs",
                        "data": {"axis": "x", "value": round(x * 32767 / (width - 1))},
                    },
                    {
                        "type": "abs",
                        "data": {"axis": "y", "value": round(y * 32767 / (height - 1))},
                    },
                ]
            },
        )
    elif action in ("down", "up"):
        request(
            "input-send-event",
            {
                "events": [
                    {
                        "type": "btn",
                        "data": {
                            "down": action == "down",
                            "button": args[0] if args else "left",
                        },
                    }
                ]
            },
        )
    elif action in ("keydown", "keyup"):
        request(
            "input-send-event",
            {
                "events": [
                    {
                        "type": "key",
                        "data": {
                            "down": action == "keydown",
                            "key": {"type": "qcode", "data": args[0]},
                        },
                    }
                ]
            },
        )
    elif action == "key":
        request(
            "send-key",
            {
                "keys": [{"type": "qcode", "data": key} for key in args[0].split("+")],
                "hold-time": 100,
            },
        )
    else:
        raise ValueError(action)
