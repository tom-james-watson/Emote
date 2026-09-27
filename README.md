# <span><img width="24" height="24" src="https://github.com/tom-james-watson/Emote/blob/master/static/logo.svg"></span> Emote

Emote is a popup emoji picker for Linux. It uses GTK4 and keeps the full emoji catalogue in one continuous, scrollable view.

On X11, launch the picker with the configurable keyboard shortcut `Ctrl+Alt+E`. Selected emojis are copied to the clipboard and pasted into the previously focused app. On Wayland, create a desktop shortcut to launch Emote and paste from the clipboard yourself.

- 🍾 Built as a popup: quick invocation, and disappears when not needed, does not stay as a standalone window
- 🫠 Includes a large list of emojis retrieved from [openmoji.org](https://openmoji.org/)
- 📜 Scroll continuously between categories, or select a category to jump to it
- 🧠 Shows up to two rows of recently used emojis
- 🔧 Adjust emoji size in Preferences; the grid reflows to fit
- 🔎 Search text box automatically focused and ready to type when invoked
- ⌨️ Use keyboard shortcuts to navigate and select emojis
- ✒️ Selected emoji automatically pasted to your currently focused app (on X11 only)

ℹ️ On Wayland, Emote copies the selected emoji to the clipboard. Automatic pasting and an app-owned global shortcut are not available yet. Set a desktop shortcut to launch Emote; see [Hotkey In Wayland](https://github.com/tom-james-watson/Emote/wiki/Hotkey-In-Wayland).

<p align="center">
  <img width="500" src="images/gtk4-preview.png" alt="GTK4 Emote picker with continuous emoji categories">
</p>

## 📥️ Installation

The Flatpak and Snap store releases may not include the changes shown on this branch yet. To test this checkout, follow [Development](#-development). Released versions are available through these package managers:

### 📦️ Install with Flatpak (preferred)

<a href='https://flathub.org/apps/com.tomjwatson.Emote'><img width='240' alt='Download on Flathub' src='https://dl.flathub.org/assets/badges/flathub-badge-en.png'/></a>

or

```bash
flatpak install com.tomjwatson.Emote
```

### 🦜 Install with Snap

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/emote)

or

```bash
sudo snap install emote
```

### 🐧 Unofficial 3rd party installation methods

An unofficial build of Emote is also available in the AUR : https://aur.archlinux.org/packages/emote. This is not maintained by me, so install at your own risk.

## 📖 Guide

### 🚀 Launching

The Flatpak requests background permission for login startup, and the Snap has an autostart entry. You can also launch Emote from the app menu. On X11, use the configurable `Ctrl+Alt+E` shortcut to open the picker. On Wayland, assign a desktop keyboard shortcut to launch Emote.

### ℹ️ Usage

Select an emoji to copy it to the clipboard. On X11, Emote also pastes it into the previously focused app. On Wayland, paste it yourself with your desktop’s usual shortcut.

Right-click an emoji to add it to a selection of multiple emojis.

### ⌨️ Keyboard Shortcuts

Open Emoji Picker: `Ctrl+Alt+E` (configurable on X11; use a desktop shortcut on Wayland)

Select Emoji: `Enter`

Add Emoji to Selection: `Shift+Enter`

Focus Search: `Ctrl+F`

Next Emoji Category: `Ctrl+Tab`

Previous Emoji Category: `Ctrl+Shift+Tab`

## 🧑‍💻 Development

[![Build package](https://github.com/tom-james-watson/Emote/actions/workflows/build.yml/badge.svg)](https://github.com/tom-james-watson/Emote/actions/workflows/build.yml)

### Test this checkout on Linux

Install GTK 4, PyGObject, Pipenv, and the X11 paste helper. On Ubuntu or Debian:

```bash
sudo apt install gir1.2-gtk-4.0 python3-gi python3-venv pipenv xdotool
```

On Fedora:

```bash
sudo dnf install gtk4 python3-gobject pipenv xdotool
```

From a checkout of the branch you want to test:

```bash
make install
make dev
```

`make dev` runs the application in the foreground. Leave that terminal open, then launch Emote again from a second terminal with `make dev` to show the picker. On X11, you can also use `Ctrl+Alt+E` after the application starts. On Wayland, use a desktop shortcut to launch it and paste selected emojis from the clipboard.

`make dev-debug` launches with GtkInspector. The source checkout uses `~/.local/share/Emote` for settings and recently used emojis.

### 🔄 Update emojis

To update the list of emojis to the latest available on [openmoji.org](https://openmoji.org), run:

```bash
make update-emojis
```

### 🐞 Debugging GTK4 with GtkInspector

Enable debug keybinding:

```bash
gsettings set org.gtk.Settings.Debug enable-inspector-keybinding true
```

Launch app in debug mode with interactive inspector:

```bash
make dev-debug
```

## 🚢 Publishing

### Releasing a new version

1. Bump the version in `snap/snapcraft.yaml` for Snap and `meson.build` for Flatpak.
2. Add a release entry to `flatpak/com.tomjwatson.Emote.metainfo.xml`.

### 📦️ Package with Flatpak

To build the Flatpak locally, install [`flatpak`](https://flatpak.org/setup/). The manifest currently targets the GNOME 50 runtime.

#### Install

Install `flatpak-builder`, the GNOME SDK, and `flatpak-pip-generator`:

```bash
make flatpak-install
```

Optionally re-generate the `flatpak/python3-requirements.json` if the dependencies in the `Pipfile` have been changed:

```bash
make flatpak-requirements
```

#### Build

Build the Flatpak and install it locally:

```bash
make flatpak
```

Launch the installed Flatpak (or use its desktop entry):

```bash
flatpak run com.tomjwatson.Emote
```

#### Debug

In case you are facing issues with the cache not properly updating, or need to reset user data, you can clean the cache with:

```bash
make flatpak-clean
```

To see potential error messages of the flatpak app you can use `journalctl`: 

```bash
journalctl -f -n 50
```

Run the command below if you want to access inside the containerized flatpak app to debug.

```bash
flatpak run --command=sh --devel com.tomjwatson.Emote
```

#### Publish to Flathub

Emote is published to Flathub using the repository [github.com/flathub/com.tomjwatson.Emote](https://github.com/flathub/com.tomjwatson.Emote).

Flathub builds can be monitored at [buildbot.flathub.org/#/apps/com.tomjwatson.Emote](https://buildbot.flathub.org/#/apps/com.tomjwatson.Emote)

To update the version published to Flathub:

1. In the [`com.tomjwatson.Emote.yml` manifest](https://github.com/flathub/com.tomjwatson.Emote/blob/master/com.tomjwatson.Emote.yml#L66) of the flathub/com.tomjwatson.Emote repo: change the commit hash to the commit of the Emote repository you want to publish
2. Flathub checks the GitHub repo every few minutes, and will start a build if a change has been detected. If the build succeeds, it is published automatically after 3 hours. You can use the [Flathub BuildBot web UI](https://buildbot.flathub.org/#/apps/com.tomjwatson.Emote) to monitor, start or publish builds manually (click the Publish button at the top of a successful build page).

More documentation for maintaining a Flathub package is available at [docs.flathub.org/docs/for-app-authors/maintanance](https://docs.flathub.org/docs/for-app-authors/maintanance#buildbot).

### 🦜 Package with Snap

Ensure you have `snapcraft` installed:

```bash
sudo snap install --classic snapcraft
```

Create a packaged `.snap` file (Snapcraft can build in an LXD or Multipass environment):

```bash
make snap
```

Install the resulting package locally to test it:

```bash
sudo snap install --dangerous ./emote_*.snap
```

Clean the cache:

```bash
make snap-clean
```

#### Publishing

First, ensure a git tag for the current version has been pushed.

Ensure you are logged in to snapcraft:

```bash
snapcraft login
```

Push the packaged snap to the `edge` channel on the snap store.

```bash
snapcraft push --release=edge <path to .snap>
```

## 🤝 Attribution

Emoji data is sourced from https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.csv which is compiled by the lovely people at https://openmoji.org 🫠.
