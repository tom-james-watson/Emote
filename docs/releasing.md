# Packaging and releases

[Back to the README](../README.md) · [Development guide](development.md)

Run the commands below from the repository root.

## Preparing a release

1. Bump the version in [`snap/snapcraft.yaml`](../snap/snapcraft.yaml) for Snap and [`meson.build`](../meson.build) for Flatpak.
2. Add a release entry to [`flatpak/com.tomjwatson.Emote.metainfo.xml`](../flatpak/com.tomjwatson.Emote.metainfo.xml).
3. Build and test the packages using the instructions below.

## Building a Flatpak

Install Flatpak and flatpak-builder using your distribution's package manager. The [manifest](../com.tomjwatson.Emote.yml) targets the GNOME 50 runtime.

This command installs the Flatpak builder app, runtime, SDK, and validation tool. It also downloads `flatpak-pip-generator`:

```bash
make flatpak-install
```

If Python dependencies have changed, regenerate [`flatpak/python3-requirements.json`](../flatpak/python3-requirements.json) from the Pipenv environment:

```bash
make flatpak-requirements
```

Build and install the package locally:

```bash
make flatpak
```

Launch it from the app menu or run:

```bash
flatpak run com.tomjwatson.Emote
```

Validate the desktop and AppStream metadata:

```bash
make flatpak-validate
```

### Debugging

Follow the journal for errors:

```bash
journalctl -f -n 50
```

Open a shell inside the Flatpak development environment:

```bash
flatpak run --command=sh --devel com.tomjwatson.Emote
```

To remove the build cache and uninstall the local package, including its user data:

```bash
make flatpak-clean
```

### Publishing to Flathub

Emote's Flathub package is maintained in [flathub/com.tomjwatson.Emote](https://github.com/flathub/com.tomjwatson.Emote).

Update the Emote source commit in that repository's [`com.tomjwatson.Emote.yml`](https://github.com/flathub/com.tomjwatson.Emote/blob/master/com.tomjwatson.Emote.yml) to the commit you want to release. Monitor the resulting build and publication in [Flathub Buildbot](https://buildbot.flathub.org/#/apps/com.tomjwatson.Emote).

## Building a Snap

Install Snapcraft:

```bash
sudo snap install --classic snapcraft
```

Build the package:

```bash
make snap
```

Install the resulting `.snap` file locally to test it:

```bash
sudo snap install --dangerous ./emote_*.snap
```

Clean the build cache:

```bash
make snap-clean
```

### Publishing to the Snap Store

Ensure the Git tag for the release has been pushed, then log in:

```bash
snapcraft login
```

Upload the package to the `edge` channel, replacing the placeholder with the built `.snap` file:

```bash
snapcraft push --release=edge <path-to-snap>
```
