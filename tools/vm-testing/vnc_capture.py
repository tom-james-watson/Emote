"""Capture a full desktop from QEMU's localhost VNC server (requires Pillow)."""

import argparse
from pathlib import Path
import socket
import struct
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("port", type=int, help="Localhost VNC port, e.g. 5916")
parser.add_argument("output", type=Path)
options = parser.parse_args()
port, out = options.port, options.output
with socket.create_connection(("127.0.0.1", int(port)), timeout=15) as s:

    def read(n):
        b = b""
        while len(b) < n:
            r = s.recv(n - len(b))
            if not r:
                raise EOFError()
            b += r
        return b

    version = read(12)
    if version != b"RFB 003.008\n":
        raise RuntimeError(f"Expected QEMU RFB 3.8, got {version!r}")
    s.sendall(b"RFB 003.008\n")
    n = read(1)[0]
    types = read(n)
    assert 1 in types, types
    s.sendall(b"\x01")
    assert read(4) == b"\0" * 4
    s.sendall(b"\x01")
    w, h = struct.unpack(">HH", read(4))
    read(16)
    read(struct.unpack(">I", read(4))[0])
    s.sendall(
        struct.pack(">BxxxBBBBHHHBBBxxx", 0, 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
    )
    s.sendall(struct.pack(">BBHi", 2, 0, 1, 0))
    s.sendall(struct.pack(">BBHHHH", 3, 0, 0, 0, w, h))
    im = Image.new("RGB", (w, h))
    while True:
        msg = read(1)[0]
        if msg == 0:
            read(1)
            n = struct.unpack(">H", read(2))[0]
            for _ in range(n):
                x, y, rw, rh, enc = struct.unpack(">HHHHi", read(12))
                assert enc == 0, enc
                im.paste(
                    Image.frombytes("RGB", (rw, rh), read(rw * rh * 4), "raw", "BGRX"),
                    (x, y),
                )
            im.save(out)
            break
        elif msg == 2:
            pass
        elif msg == 3:
            read(3)
            read(struct.unpack(">I", read(4))[0])
        else:
            raise RuntimeError(msg)
