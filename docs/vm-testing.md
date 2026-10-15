# Testing in desktop VMs

[Development guide](development.md) · [Release guide](releasing.md)

Use these VMs for desktop integration that unit tests and Broadway cannot cover:
window focus and dragging, native shortcuts, clipboard, paste permissions, real
font rendering, and packaged builds. Run host commands from the repository root.
Commands labelled **guest** run inside a disposable VM, not on the host.

The tracked helpers live in [`tools/vm-testing`](../tools/vm-testing/). Images,
keys, generated launchers, packages, logs and screenshots belong under ignored
`build/platform-tests/`. No VM or private key is included in a fresh checkout.

## Environments and existing VMs

The following environments were used during Emote 5.0 beta testing. The helper
uses these names and localhost ports:

| Name | Desktop sessions | SSH | VNC | Existing user service |
| --- | --- | --- | --- | --- |
| `kubuntu-24.04` | Plasma X11 and Wayland | 2234 | 5914 | `emote-kubuntu-2404-vm` |
| `kubuntu-26.04` | Plasma X11 and Wayland | 2236 | 5916 | `emote-kubuntu-2604-vm` |
| `fedora-44` | GNOME Wayland | 2244 | 5924 | `emote-fedora-44-vm` |

Before creating anything, check for an existing
`build/platform-tests/<name>/start-vm.sh` and `guest.qcow2`. Reuse them when
appropriate. On the original test host, those VMs authorize the key at
`build/ubuntu-24.04-vm/ssh-key`; new VMs default to
`build/platform-tests/ssh-key`. The initializer refuses to overwrite an existing
VM directory. Old reports under `build/` describe their recorded runs, not the
current checkout.

The guests have a `tester` account, key-only SSH, passwordless sudo, and desktop
autologin. They are disposable test environments. SSH and VNC bind to localhost;
VNC has no password. Do not expose those ports to a network.

## Create a VM from a fresh checkout

This setup targets an x86_64 Linux host with KVM and a usable GPU render node.
On an Ubuntu/Debian host, install the tools:

```bash
sudo apt install qemu-system-x86 qemu-system-gui qemu-utils cloud-image-utils ovmf openssh-client python3-pil
```

The user running QEMU needs access to `/dev/kvm` and `/dev/dri/renderD128`.
Check those permissions before starting. `--render-node` can select another GPU.
The firmware paths also have initializer options if the host packages put OVMF
elsewhere.

Download an x86_64 qcow2 cloud image from the distribution:

- [Ubuntu released cloud images](https://cloud-images.ubuntu.com/releases/): use
  Ubuntu Server 24.04 or 26.04, then install Kubuntu's desktop in the guest.
  The `.img` extension is normal for Ubuntu's qcow2 cloud images.
- [Fedora Cloud downloads](https://fedoraproject.org/cloud/download/): choose
  Fedora 44 QEMU qcow2 and follow its verification instructions.

Keep the image and the distribution's checksum files under
`build/platform-tests/images/`. Verify the download against its published
checksum before passing it to the initializer; the helper checks the image
format, not its provenance. Record the exact image URL and checksum in the test
report. Cloud images with a desktop installed exercise the desktop packages,
not the distribution's ISO installer.

For example, after saving a verified Ubuntu 24.04 image at the path below:

```bash
mkdir -p build/platform-tests/images
ssh-keygen -t ed25519 -N '' -f build/platform-tests/ssh-key
python3 tools/vm-testing/init_vm.py kubuntu-24.04 \
  build/platform-tests/images/ubuntu-24.04.img
```

Generate the key only if it does not already exist. The initializer creates a
standalone copy of the image, grows its virtual disk to 60 GiB, creates a
cloud-init seed, copies the UEFI variable store, and writes `start-vm.sh`. It uses
3 CPUs, 4 GiB RAM, accelerated virtio graphics and a USB tablet. Changing the
name selects the corresponding ports from the table above. Supply the matching
OS image; naming a VM `kubuntu-26.04` does not install that OS for you.

If initialization fails, inspect the partial directory before removing it and
retrying. Never rerun initialization over a VM you want to retain.

## Start, connect and stop

Choose the VM and its matching ports/service from the table. For a newly created
Kubuntu 24.04 VM:

```bash
VM_NAME=kubuntu-24.04
VM_PORT=2234
VM_UNIT=emote-kubuntu-2404-vm
VM_KEY="$PWD/build/platform-tests/ssh-key"

systemd-run --user --unit="$VM_UNIT" --property="WorkingDirectory=$PWD" \
  "$PWD/build/platform-tests/$VM_NAME/start-vm.sh"
ssh -i "$VM_KEY" -p "$VM_PORT" tester@127.0.0.1
```

Use the legacy key path noted above when reusing the original VMs. SSH may need
another attempt while the guest boots. On a first boot, wait inside the guest:

```bash
sudo cloud-init status --wait
```

Inspect failures with `journalctl --user -u "$VM_UNIT" -n 50 --no-pager` on the
host, and `build/platform-tests/$VM_NAME/serial.log`. If SSH reports a changed
host key after deliberately replacing a VM, verify that replacement before
removing its old known-host entry. Do not disable SSH host-key checks globally.

Stop the VM when finished:

```bash
systemctl --user stop "$VM_UNIT"
```

The service runs QEMU in the foreground and stopping it ends the VM process.
For a clean guest shutdown, run `sudo poweroff` inside the VM first. Do not run
two copies of a VM against the same disk, firmware store or forwarded ports.

## Install the desktop (new VMs only)

Copy the matching provisioning script, then run it **inside the guest**:

```bash
scp -i "$VM_KEY" -P "$VM_PORT" tools/vm-testing/provision-kubuntu.sh \
  tester@127.0.0.1:/home/tester/provision.sh
ssh -i "$VM_KEY" -p "$VM_PORT" tester@127.0.0.1 \
  'sudo bash /home/tester/provision.sh'
```

For Fedora, copy `provision-fedora.sh` instead. These scripts install the desktop
and test tools, configure autologin, and select the graphical boot target. Reboot
the guest after the script finishes. They do not install Emote. Kubuntu 24.04
initially uses X11; Kubuntu 26.04 and Fedora use Wayland.

For Flatpak testing, add the runtime remote **in the guest**:

```bash
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

## Run commands in the desktop session

An SSH shell does not necessarily have the desktop's display, authorization or
session-bus variables. Copy the guest-side helper:

```bash
scp -i "$VM_KEY" -P "$VM_PORT" tools/vm-testing/desktop_run.py \
  tester@127.0.0.1:/home/tester/desktop_run.py
```

Inside the guest, use `python3 ~/desktop_run.py COMMAND ...`. It takes the session
variables from the logged-in user's `plasmashell` or `gnome-shell` process. On
GNOME it also finds an unambiguous Wayland socket when the process environment
omits its name. It refuses to pick between multiple copies of the same shell;
reboot into a clean session instead.

For example, inside the guest:

```bash
python3 ~/desktop_run.py flatpak run --env=GDK_BACKEND=wayland \
  --branch=test com.tomjwatson.Emote
```

Explicitly choose `GDK_BACKEND=wayland` or `x11` when testing that GTK backend.
For Snap, use `python3 ~/desktop_run.py env GDK_BACKEND=wayland snap run emote`.
The first invocation may start a hidden background application; invoke it again
or use its configured shortcut to open the picker. Complete first-run setup in
the guest desktop.

### Native X11 versus Xwayland

For native X11 testing, log into an X11 desktop session. Forcing GTK's X11 backend
inside a Wayland desktop tests **Xwayland**, not a native X11 desktop.

On Kubuntu, list the installed session files in `/usr/share/xsessions/` and
`/usr/share/wayland-sessions/`. Set `Session=` in
`/etc/sddm.conf.d/99-emote-test.conf` to the chosen filename, then **fully reboot**.
The previously tested files were:

| Guest | X11 | Wayland |
| --- | --- | --- |
| Kubuntu 24.04 | `plasma.desktop` | `plasmawayland.desktop` |
| Kubuntu 26.04 | `plasmax11.desktop` | `plasma.desktop` |

Confirm the current files rather than assuming they remain the same. Use
`loginctl list-sessions`, then `loginctl show-session SESSION_ID -p Type -p Desktop`
to verify the desktop session. A GTK test harness can additionally record
`picker.get_surface().__gtype__.name`: expect `GdkWaylandToplevel` or
`GdkX11Toplevel`. An X11 surface alone does not distinguish X11 from Xwayland.

Restarting SDDM alone previously left old shells and portals attached to the
wrong session. Those failures are invalid test evidence; reboot and repeat.

## Install and check the actual package

Copy the final CI artifact to the guest. For a Snap, run in the guest:

```bash
sudo snap install --dangerous /home/tester/emote-beta.snap
python3 ~/desktop_run.py env GDK_BACKEND=wayland snap run emote
```

For a local Flatpak bundle, use `flatpak install --user -y /home/tester/emote.flatpak`.
For Flathub releases, also install the exact test-build `.flatpakref` posted by
the bot in the publishing PR, as required by the [release guide](releasing.md).
Use the installed branch (`test`, `master` or `beta`) explicitly when launching.
If replacing a previous Flathub test origin, uninstall the old `//test` branch
without `--delete-data`, then install the new `.flatpakref`.

Wait for installation and runtime updates to finish before testing. Confirm
`snap list emote` or `flatpak info --user com.tomjwatson.Emote//test`. The Flatpak
launcher `/app/bin/emote` records its application version; `flatpak info
--show-commit` records the package commit. Do not rely only on cached AppStream
version text in `flatpak remote-info`.

Stop another Emote instance before switching package formats: Snap and Flatpak
share the application D-Bus name, and a running instance can prevent the other
from registering. Do this only in the test guest, not on the user's host.

Tests of an installed package must import its installed modules. Flatpak installs
Emote under `/app/share/emote`; a custom Python harness must add that to
`sys.path` and set `EMOTE_PKGDATADIR=/app/share/emote` before importing Emote.
Snap's launch environment supplies `SNAP` and its packaged Python paths. A source
overlay can help diagnose a fix, but must be labelled as such and followed by a
check of the final package. Record the imported module path when using a harness.
Use temporary preferences in harnesses to keep runs independent.

## Desktop screenshots and input

A full-desktop screenshot is enough for test evidence. Wake the display first
if it has gone into standby. For example, on the host:

```bash
python3 tools/vm-testing/qmp.py "$VM_NAME" move 600 300 1280 800
python3 tools/vm-testing/qmp.py "$VM_NAME" key shift
python3 tools/vm-testing/vnc_capture.py 5914 \
  "$PWD/build/platform-tests/$VM_NAME/desktop.png"
```

`move` takes `X Y WIDTH HEIGHT`; use the actual guest resolution, not always
1280×800. `key` accepts QEMU key chords such as `ctrl+alt+e`.
For a pointer drag, send `move`, `down left`, another `move`, then `up left` as
separate calls with short pauses. The helper also has `keydown` and `keyup` for
holding a modifier during a drag. Always release held buttons and keys.

Use the matching VNC port from the table when taking a screenshot. The capture
helper requires Pillow and talks directly to QEMU's localhost VNC server. QMP's
`screendump` returned `no surface` with the accelerated virtual GPU during the
helper checks, so use the VNC helper for desktop captures.

For interactive inspection, connect a VNC viewer to the localhost port in the
table. QMP and VNC operate the VM's real desktop, including compositor and portal
dialogs. If a product screenshot is needed, KDE Spectacle's active-window capture
or GNOME's Window screenshot mode preserves native decoration and corner alpha;
a desktop crop does not provide the same result.

## What to check and record

Scale the checks to the change. For a release or a layout/input change, cover:

- First-run setup, a second launch, restart and reboot. Startup after setup should
  leave the picker hidden until invoked.
- Search, clearing search, category jumps, and keyboard selection during search.
- Resize at the minimum width and larger sizes; emoji sizes, both font options,
  old-system-font split/missing glyphs, and absence of horizontal overflow.
- Multiple selections, opaque footer emojis, the `+X` count and its alignment.
- Header dragging, compositor-assisted dragging, Escape, and clicking outside.
- Clipboard bytes and automatic paste into an independent text editor. Check
  shortcut focus, permission acceptance/rejection, Stop, and permission reuse.
- Light and dark themes. Save a desktop screenshot when diagnosing visual issues.

For broad compatibility checks use both native desktop sessions on each Kubuntu
release, plus Fedora Wayland. Not every small data fix needs that full matrix.

Write a report under `build/platform-tests/` with the source commit/tag, package
checksum or Flatpak commit, guest OS/desktop version, native session/backend,
exact checks and results, screenshots, and any limitations. Distinguish automated
assertions, visual inspection, and checks not repeated. A hidden/unmapped window
is not a valid layout or screenshot check. Shut down the VMs when done.

## Known test-environment limitations

- Stock Plasma 5.27 on Kubuntu 24.04 lacked the required `ConnectToEIS` portal
  backend and working shortcut setup in the earlier tests. Copy-only operation
  worked. Record installed versions and retest before treating that as permanent.
- Software-only virtual graphics previously crashed KWin before Emote started.
  The launchers use virgl/EGL acceleration through the host render node. A Cairo
  renderer can help diagnose a failure, but report that override and repeat with
  the default renderer before drawing rendering-performance conclusions.
- Display standby can unmap GTK surfaces. Wake the VM, confirm the picker is
  mapped, and repeat rather than counting that as an application failure.
- These VMs do not cover physical GPU drivers, the ISO installer, fractional
  scaling, multiple monitors, or every destination application for paste.
