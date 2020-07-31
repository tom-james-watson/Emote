# <span><img width="24" height="24" src="https://github.com/tom-james-watson/Emote/blob/master/static/logo.svg"></span> Emote

<a href="https://snapcraft.io/emote">
  <img alt="emote" src="https://snapcraft.io/emote/badge.svg" />
</a>
<a href="https://snapcraft.io/emote">
  <img alt="emote" src="https://snapcraft.io/emote/trending.svg?name=0" />
</a>

Emote is a modern emoji picker for Linux 🚀. Written in GTK3, Emote is lightweight and stays out of your way.

Launch the emoji picker with the configurable keyboard shortcut Ctrl+Alt+E and select one or more emojis to copy them to your clipboard.

<p align="center">
  <img width="500" src="https://raw.githubusercontent.com/tom-james-watson/Emote/master/images/screenshot.png">
</p>

## Installation

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/emote)

or

```bash
sudo snap install emote
```

## Guide

### Launching

Emote runs in the background and automatically starts when you log in.

The emoji picker can be opened with either the keyboard shortcut or by clicking the app icon again.

### Usage

Select an emoji to copy it to your clipboard. You can then paste the emoji wherever you need.

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

Install gtk development libraries:

```bash
sudo apt install libgtk-3-dev libgirepository1.0-dev
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

### Packaging

Ensure you have `snapcraft` installed:

```bash
sudo snap install --classic snapcraft
```

Create a packaged `.snap` file:

```bash
make package
```

### Publishing

Ensure you are logged in to snapcraft:

```bash
snapcraft login
```

Push the packaged snap to the `edge` channel on the snap store.

```bash
snapcraft push --release=edge <path to .snap>
```

## Attribution

### App Icon

Copyright 2020 Twitter, Inc and other contributors

Thanks for the awesome team at Twitter.

https://twemoji.twitter.com
