# <span><img width="24" height="24" src="https://github.com/tom-james-watson/Emote/blob/master/static/logo.svg"></span> Emote

Emote is a modern emoji picker for Linux 🚀. Written in GTK3, Emote is lightweight and stays out of your way.

Launch the emoji picker with the configurable keyboard shortcut `Ctrl+Alt+E`, and select one or more emojis to have them be automatically pasted into your currently focused app.

- 🍾 Built as a popup: quick invocation, and disappears when not needed, does not stay as a standalone window
- 🫠 Provide a large and up-to-date list of emojis retrieved from [openmoji.org](https://openmoji.org/)
- 🧠 Shows the last used emojis by default
- 🔎 Search text box automatically focused and ready to type when invoked
- ⌨️ Can use shortcuts to navigates and select emojis
- ✒️ Selected emoji automatically pasted to your currently focused app (on X11 only)

ℹ️ Note:

- ⚡️ Emote [shows up faster](https://github.com/tom-james-watson/Emote/issues/54) when invoked using the built-in keyboard shortcut (`Ctrl+Alt+E` by default), than when using a manually registered keyboard shortcut.
- 🪟 Emote under Wayland cannot automatically paste the emoji into other apps, and also requires manual registering of a global keyboard shortcut - [Hotkey In Wayland](https://github.com/tom-james-watson/Emote/wiki/Hotkey-In-Wayland). This is due to intentional restrictions in the design of Wayland itself.

<p align="center">
  <img width="500" src="https://raw.githubusercontent.com/tom-james-watson/Emote/master/images/screenshot.png">
</p>

## 📥️ Installation

Emote can be installed using various popular package managers:

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

### 🐧 Unofficial installation methods

An unofficial build of Emote is also available in the AUR : https://aur.archlinux.org/packages/emote.

## 📖 Guide

### 🚀 Launching

Emote runs in the background and automatically starts when you log in.

The emoji picker can be opened with either the keyboard shortcut, or by clicking the app icon again.

### ℹ️ Usage

Select an emoji to and have it be pasted to your currently focused app. The emoji will also be copied to your clipboard, so you can then paste the emoji wherever you need.

You can select multiple emojis by selecting them with right click.

### ⌨️ Keyboard Shortcuts

Open Emoji Picker: `Ctrl+Alt+E` (configurable)

Select Emoji: `Enter`

Add Emoji to Selection: `Shift+Enter`

Focus Search: `Ctrl+F`

Next Emoji Category: `Ctrl+Tab`

Previous Emoji Category: `Ctrl+Shift+Tab`

## 🧑‍💻 Development

[![Build package](https://github.com/tom-james-watson/Emote/actions/workflows/build.yml/badge.svg)](https://github.com/tom-james-watson/Emote/actions/workflows/build.yml)

### 📥️ Requirements

Install development libraries:

```bash
sudo apt install xdotool libgtk-3-dev libgirepository1.0-dev python3-venv gir1.2-keybinder-3.0 libkeybinder-dev desktop-file-utils
# or with dnf
sudo dnf install xdotool gtk3-devel keybinder3-devel libgirepository1.0-dev desktop-file-utils gobject-introspection-devel flatpak-builder

sudo dnf install libffi-devel
```

Install pipenv:

```bash
sudo pip3 install pipenv
```

Install dependencies:

```bash
make install
```

### 🛩️ Running

Run the development version:

```bash
make dev
```

### 🔄 Update emojis

To update the list of emojis to the latest available on [openmoji.org](https://openmoji.org), run:

```bash
make update-emojis
```

### 🐞 Debugging GTK3 with GtkInspector

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

1. Bump the version number in `snapcraft.yaml` for snap and in `meson.build` for flatpak.
2. Add a release entry to the `com.tomjwatson.Emote.metainfo.xml`.

### 📦️ Package with Flatpak

To develop locally you will need to have [`flatpak`](https://flatpak.org/setup/) installed.

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

Build the flatpak package and install it locally:

```bash
make flatpak
```

Run Emote with flatpak (can also be done from the desktop entry):

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
2. Flathub checks the GitHub repo every few minutes, and will start a build if a change as been detected, if the build succeed it is published automatically after 3 hours. You can use the [Flathub BuildBot web UI](https://buildbot.flathub.org/#/apps/com.tomjwatson.Emote) to monitor, start or publish builds manually (click the Publish button at the top of a successful build page).

More documentation for maintaining a Flathub package is available at [docs.flathub.org/docs/for-app-authors/maintanance](https://docs.flathub.org/docs/for-app-authors/maintanance#buildbot)

### 🦜 Package with Snap

Ensure you have `snapcraft` installed:

```bash
sudo snap install --classic snapcraft
```

Create a packaged `.snap` file:

```bash
make snap
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
