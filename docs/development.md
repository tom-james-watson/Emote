# Development

[Back to the README](../README.md)

## Running from source

Emote requires GTK4, libadwaita 1.5 or newer, PyGObject, and Pipenv. It uses libei for Wayland keyboard input and xdotool for X11 paste.

On Ubuntu or Debian, install the system dependencies:

```bash
sudo apt install gir1.2-adw-1 gir1.2-gtk-4.0 python3-gi python3-venv pipenv xdotool librsvg2-common libei1
```

On Fedora:

```bash
sudo dnf install libadwaita gtk4 python3-gobject pipenv xdotool rsvg-pixbuf-loader libei
```

If your distribution has an older version of libadwaita, you can build with the project's Flatpak runtime instead; see [Building a Flatpak](releasing.md#building-a-flatpak).

From the repository root:

```bash
make install
make dev
```

`make install` creates the Pipenv environment with access to system Python packages. `make dev` installs Emote's desktop metadata in your user data directory and runs the application in the foreground. The metadata lets desktop portals identify the application when it requests a global shortcut.

Leave that terminal open, then run `make dev` in a second terminal to show the picker. On X11, you can also use `Ctrl+Alt+E` after the application starts. See [Desktop integration](../README.md#desktop-integration) for shortcut and automatic-paste setup.

The source checkout stores settings and recently used emojis in `~/.local/share/Emote` by default.

## Debugging with GtkInspector

Launch Emote with the interactive inspector:

```bash
make dev-debug
```

To enable GTK's inspector keybinding:

```bash
gsettings set org.gtk.Settings.Debug enable-inspector-keybinding true
```

## Testing first-run setup and upgrades

To stop Emote and reset its local settings, automatic-paste restore token, and portal shortcut registration:

```bash
make dev-reset
make dev
```

**This also resets portal permissions for an installed Emote build**, because development and packaged builds share the same application ID. The next launch behaves like a clean install.

To clear saved data for installed Emote builds without uninstalling them, run:

```bash
make prod-reset
```

This removes settings, recent emojis, and the automatic-paste restore token for native/Snap and Flatpak installs, and resets Emote's portal shortcut permissions. The next launch runs the first-start setup again.

To simulate an upgrade from an older release instead:

```bash
make dev-reset-upgrade
make dev
```

This performs the same reset, then restores the legacy first-launch marker. It leaves manually configured desktop shortcuts in place. Check that:

- An existing manual shortcut still opens Emote after accepting or skipping native shortcut setup.
- Skipping setup does not prompt again on subsequent launches.
- Setup remains available in **Keyboard Shortcuts**.

## Testing the setup UI with Broadway

GTK's Broadway backend displays real GTK windows in a browser. Start the server:

```bash
gtk4-broadwayd --address=127.0.0.1 --port=8085 :5
```

In another terminal, run the UI harness from the repository root:

```bash
GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 pipenv run python tools/shortcut_ui.py
```

Open <http://127.0.0.1:8085>. Add `--scenario=disabled` or `--scenario=cancel` to test setup with a disabled shortcut or a cancelled request.

The controls window simulates native shortcut signals and legacy app launches. The harness uses temporary Emote data and does not change desktop shortcuts or portal permissions. It tests the GTK dialogs; GNOME's portal dialogs, key conflicts, and compositor focus behavior still need testing in a desktop session.

## Updating emoji data

To refresh the bundled emoji catalogue from [OpenMoji](https://openmoji.org/):

```bash
make update-emojis
```

The source is OpenMoji's [emoji data CSV](https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.csv). The updater currently includes emoji through Unicode 17.0 so newer characters that are not yet supported by common system emoji fonts do not appear as missing-glyph boxes.

## Formatting

```bash
make format
```

This runs Black on the `emote` package.

## Packaging

See the [release guide](releasing.md) for local Flatpak and Snap builds, package debugging, and publishing.
