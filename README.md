# <span><img width="24" height="24" src="https://github.com/tom-james-watson/Emote/blob/master/static/logo.svg"></span> Emote

<a href="https://snapcraft.io/emote">
  <img alt="emote" src="https://snapcraft.io/emote/badge.svg" />
</a>
<a href="https://snapcraft.io/emote">
  <img alt="emote" src="https://snapcraft.io/emote/trending.svg?name=0" />
</a>

Emote is a modern emoji picker for Linux 🚀. Written in GTK3, Emote is lightweight and stays out of your way.

Launch the emoji picker with the configurable keyboard shortcut `Ctrl+Alt+E` and select one or more emojis to have them be automatically pasted into your currently focused app.

Note - Emote under Wayland cannot automatically paste the emoji into other apps and also requires manual registering of a global keyboard shortcut - [Hotkey In Wayland](https://github.com/tom-james-watson/Emote/wiki/Hotkey-In-Wayland). This is due to intentional restrictions in the design of Wayland itself.

<p align="center">
  <img width="500" src="https://raw.githubusercontent.com/tom-james-watson/Emote/master/images/screenshot.png">
</p>

## Installation

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/emote)

or

```bash
sudo snap install emote
```

An unofficial build of Emote is also available in the AUR : https://aur.archlinux.org/packages/emote.

## Guide

### Launching

Emote runs in the background and automatically starts when you log in.

The emoji picker can be opened with either the keyboard shortcut or by clicking the app icon again.

### Usage

Select an emoji to and have it be pasted to your currently focused app. The emoji will also be copied to your clipboard, so you can then paste the emoji wherever you need.

You can select multiple emojis by selecting them with right click.

### Keyboard Shortcuts

Open Emoji Picker: `Ctrl+Alt+E` (configurable)

Select Emoji: `Enter`

Add Emoji to Selection: `Shift+Enter`

Focus Search: `Ctrl+F`

Next Emoji Category: `Ctrl+Tab`

Previous Emoji Category: `Ctrl+Shift+Tab`

## Development

### Requirements

Install development libraries:

```bash
sudo apt install xdotool libgtk-3-dev libgirepository1.0-dev python3-venv gir1.2-keybinder-3.0 libkeybinder-dev flatpak-builder
# or with dnf
sudo dnf install xdotool gtk3-devel keybinder3-devel libgirepository1.0-dev
```

Install pipenv:

```bash
sudo pip3 install pipenv
```

Install dependencies:

```bash
make install
```

### Running

Run the development version:

```bash
make dev
```

### Debugging GTK3 with GtkInspector

Enable debug keybinding:

```bash
gsettings set org.gtk.Settings.Debug enable-inspector-keybinding true
```

Launch app in debug mode with interactive inspector:

```bash
make dev-debug
```

### Packaging for Snap

Ensure you have `snapcraft` installed:

```bash
sudo snap install --classic snapcraft
```

Create a packaged `.snap` file:

```bash
make package
```

### Publishing

First, ensure a git tag for the current version has been pushed.

Ensure you are logged in to snapcraft:

```bash
snapcraft login
```

Push the packaged snap to the `edge` channel on the snap store.

```bash
snapcraft push --release=edge <path to .snap>
```

### Packaging for Flatpak

https://docs.flatpak.org/en/latest/first-build.html

Install `flatpak-builder` and the GNOME SDK:

```bash
make flatpak-install
```

Re-generate pip requirements if they have changed:

```bash
make flatpak-requirements
```

Build the flatpak and install it locally:

```bash
make flatpak
```

Try it:

```bash
flatpak run com.tomjwatson.Emote
```

Check installed files:

```bash
pipenv run flatpak-pip-generator --runtime='org.gnome.Sdk//43' --output python3-requirements "pygobject==3.42.2" "manimpango==0.3.0" "setproctitle==1.2.2"

cat ~/.local/share/flatpak/app/com.tomjwatson.Emote/
chmod +x ~/.local/share/flatpak/app/com.tomjwatson.Emote/x86_64/master/active/files/bin/emote

cat /var/lib/flatpak/app/it.mijorus.smile/x86_64/stable/
```

Put it in a repo:

```bash
flatpak-builder --repo=repo --force-clean build com.tomjwatson.Emote.yml
```

Desktop entry: https://github.com/GNOME/balsa/blob/master/org.desktop.Balsa.desktop.meson

### Attribution

Emoji data is sourced from https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.csv which is compiled by the lovely people at https://openmoji.org.
