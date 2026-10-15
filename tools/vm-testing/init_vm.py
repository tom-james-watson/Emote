"""Create a disposable desktop-test VM from a verified qcow2 cloud image."""

import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2] / "build/platform-tests"
PORTS = {
    "kubuntu-24.04": (2234, 14),
    "kubuntu-26.04": (2236, 16),
    "fedora-44": (2244, 24),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=PORTS)
    parser.add_argument("image", type=Path, help="Verified x86_64 qcow2 cloud image")
    parser.add_argument("--ssh-key", type=Path, default=ROOT / "ssh-key.pub")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--render-node", default="/dev/dri/renderD128")
    parser.add_argument(
        "--firmware-code", type=Path, default=Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
    )
    parser.add_argument(
        "--firmware-vars", type=Path, default=Path("/usr/share/OVMF/OVMF_VARS_4M.fd")
    )
    args = parser.parse_args()
    directory = args.root.resolve() / args.name
    if directory.exists():
        parser.error(f"Refusing to overwrite existing VM: {directory}")
    for path in (args.image, args.ssh_key, args.firmware_code, args.firmware_vars):
        if not path.is_file():
            parser.error(f"Missing file: {path}")
    key = args.ssh_key.read_text().strip()
    if not key.startswith("ssh-") or "\n" in key:
        parser.error("--ssh-key must contain one OpenSSH public key")
    info = json.loads(
        subprocess.check_output(
            ["qemu-img", "info", "--output=json", str(args.image.resolve())]
        )
    )
    if info["format"] != "qcow2":
        parser.error("Expected a qcow2 cloud image")
    if "backing-filename" in info:
        parser.error("Expected a standalone cloud image without a backing file")

    port, vnc = PORTS[args.name]
    group = "wheel" if args.name.startswith("fedora") else "sudo"
    directory.mkdir(parents=True)
    (directory / "user-data").write_text(f"""#cloud-config
hostname: emote-{args.name.replace('.', '-')}
users:
  - name: tester
    groups: [{group}]
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
    ssh_authorized_keys:
      - {json.dumps(key)}
ssh_pwauth: false
""")
    (directory / "meta-data").write_text(f"instance-id: emote-{args.name}\n")
    subprocess.run(
        [
            "cloud-localds",
            str(directory / "seed.iso"),
            str(directory / "user-data"),
            str(directory / "meta-data"),
        ],
        check=True,
    )
    shutil.copyfile(args.firmware_vars, directory / "OVMF_VARS.fd")
    subprocess.run(
        [
            "cp",
            "--reflink=auto",
            "--sparse=always",
            str(args.image.resolve()),
            str(directory / "guest.qcow2"),
        ],
        check=True,
    )
    subprocess.run(
        ["qemu-img", "resize", str(directory / "guest.qcow2"), "60G"], check=True
    )
    script = f"""#!/usr/bin/env bash
set -euo pipefail
vm_dir="$(cd "$(dirname "$0")" && pwd)"
exec qemu-system-x86_64 -name emote-{args.name} \\
  -machine q35,accel=kvm -cpu host -smp 3 -m 4096 \\
  -drive if=pflash,format=raw,readonly=on,file={shlex.quote(str(args.firmware_code.resolve()))} \\
  -drive if=pflash,format=raw,file="$vm_dir/OVMF_VARS.fd" \\
  -drive if=virtio,format=qcow2,file="$vm_dir/guest.qcow2" \\
  -drive if=ide,media=cdrom,readonly=on,file="$vm_dir/seed.iso" \\
  -nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:{port}-:22 \\
  -device qemu-xhci,id=emote-usb -device usb-tablet,bus=emote-usb.0 \\
  -device virtio-vga-gl -display egl-headless,rendernode={shlex.quote(args.render_node)} \\
  -vnc 127.0.0.1:{vnc} -serial file:"$vm_dir/serial.log" \\
  -qmp unix:"$vm_dir/qmp.sock",server=on,wait=off -monitor none
"""
    (directory / "start-vm.sh").write_text(script)
    (directory / "start-vm.sh").chmod(0o755)
    print(f"Created {directory}; SSH localhost:{port}, VNC localhost:{5900 + vnc}")


if __name__ == "__main__":
    main()
