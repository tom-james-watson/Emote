# <img width="24" height="24" src="static/logo.svg" alt=""> Emote

Emote is a popup emoji picker for Linux, built with GTK4 and libadwaita.

<p align="center">
  <img width="500" src="images/screenshot-dark.png" alt="Emote emoji picker in dark mode">
</p>

- Start typing to search, or scroll through the emoji categories.
- Quickly find recently used emojis.
- Navigate with your keyboard or mouse, and select one emoji or several.
- Copy emojis to the clipboard and optionally paste them into your previous app.
- Choose your preferred skin tone.
- Emote follows your desktop's theme.

## Installation

### Flatpak (recommended)

<a href="https://flathub.org/apps/com.tomjwatson.Emote"><img width="240" alt="Download on Flathub" src="https://dl.flathub.org/assets/badges/flathub-badge-en.png"></a>

```bash
flatpak install flathub com.tomjwatson.Emote
```

### Snap

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/emote)

```bash
sudo snap install emote
```

### Arch Linux

The community maintains an unofficial [AUR package](https://aur.archlinux.org/packages/emote). This is not maintained by me, so install at your own risk.

## Using Emote

Launch Emote from your app menu. The default shortcut to open the picker is `Ctrl+Alt+E`. See [Desktop integration](#desktop-integration) for shortcut setup and login startup.

Start typing to search, or browse the categories. Click an emoji or press `Enter` to copy it and close the picker. If automatic paste is enabled, Emote pastes it into the app you were using. Otherwise, paste it yourself.

To select several emojis, right-click each one or press `Shift+Enter`. Click the final emoji or press `Enter` to finish the selection and close the picker.

Open **Preferences** to change the emoji size or skin tone.

### Keyboard shortcuts

| Action | Shortcut |
| --- | --- |
| Open or close the picker | `Ctrl+Alt+E` (default global shortcut) |
| Select emoji | `Enter` |
| Add emoji to selection | `Shift+Enter` |
| Focus search | `Ctrl+F` |
| Next category | `Ctrl+Tab` |
| Previous category | `Ctrl+Shift+Tab` |

## Desktop integration

### Global shortcut

On **X11**, Emote handles the global shortcut itself. Change it from **Keyboard Shortcuts** in Emote.

On **Wayland**, your desktop manages the shortcut through its Global Shortcuts portal. Emote offers to set this up the first time you open the picker. You can skip setup and keep an existing manual shortcut, or set it up later from **Keyboard Shortcuts**. To change or enable a registered shortcut, use your desktop's shortcut settings.

If your desktop does not support the portal, configure a shortcut manually using the [Wayland shortcut guide](https://github.com/tom-james-watson/Emote/wiki/Hotkey-In-Wayland).

### Automatic paste

Automatic paste is optional on both X11 and Wayland. Turn it on or off in **Preferences**. It is on by default on X11.

On **Wayland**, it also needs your desktop's permission to control the keyboard. Emote offers to enable it during setup. On GNOME, allow “Remote Interaction” when prompted. Emote requests keyboard control, not screen access.

If automatic paste is disabled or unavailable, your selection is still copied to the clipboard.

### Login startup

Emote starts automatically when you log in. Launch it once from your app menu after installing.

## Development

[![Build package](https://github.com/tom-james-watson/Emote/actions/workflows/build.yml/badge.svg)](https://github.com/tom-james-watson/Emote/actions/workflows/build.yml)

See the [development guide](docs/development.md) for running from source, debugging, and testing desktop integration. The [release guide](docs/releasing.md) covers building and publishing Flatpak and Snap packages.

## Credits and license

Emote is licensed under the [GNU GPL v3 or later](LICENSE.md).

Emoji data comes from [OpenMoji](https://openmoji.org/). Category icons include artwork from [Lucide](https://lucide.dev/); see the [bundled icon license](static/icons/LICENSE).
