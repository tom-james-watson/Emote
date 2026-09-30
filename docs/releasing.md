# Packaging and releases

[Back to the README](../README.md) · [Development guide](development.md)

Run the commands below from the repository root.

## Preparing a release

1. Bump the version in [`snap/snapcraft.yaml`](../snap/snapcraft.yaml) for Snap and [`meson.build`](../meson.build) for Flatpak.
2. Add a release entry to [`flatpak/com.tomjwatson.Emote.metainfo.xml`](../flatpak/com.tomjwatson.Emote.metainfo.xml).
3. Build and test the packages using the instructions below.

For a beta, use a version such as `5.0.0-beta.1`. Use the AppStream form
`5.0.0~beta1` with `type="development"` so it sorts before the final release.
Publishing remains a manual step for both stores.

## Building a Flatpak

Install Flatpak and flatpak-builder using your distribution's package manager. The [manifest](../com.tomjwatson.Emote.yml) targets the GNOME 51 runtime.

This command installs the Flatpak builder app, runtime, SDK, and validation tool. It also downloads `flatpak-pip-generator`:

```bash
make flatpak-install
```

If Python dependencies have changed, regenerate [`flatpak/python3-requirements.json`](../flatpak/python3-requirements.json) from the Pipenv environment. This target downloads `flatpak-pip-generator` automatically if it is missing:

```bash
make flatpak-requirements
```

The Python-Xlib module is installed from its pure-Python wheel because its source archive expects `pkg_resources`, which is no longer included in the GNOME 51 SDK's setuptools.

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

Update that repository's [`com.tomjwatson.Emote.yml`](https://github.com/flathub/com.tomjwatson.Emote/blob/master/com.tomjwatson.Emote.yml) to match the locally tested manifest, replacing the local `dir` source with the release tag archive and its SHA-256 checksum. Open a pull request and install the temporary test build posted by the Flathub bot before publishing it.

The Flathub repository's `master` branch publishes to the stable repository. Its
`beta` branch publishes to the separate Flathub Beta repository. Prepare beta
changes on a branch based on `master`; after its pull-request test build passes,
create or update the `beta` branch with those changes. Do not merge beta-only
changes into `master`.

Pushing or merging the publishing branch triggers the official build. Monitor it
in [Flathub Buildbot](https://buildbot.flathub.org/#/apps/com.tomjwatson.Emote).

Testers can install and run the beta with:

```bash
flatpak remote-add --if-not-exists --user flathub-beta https://flathub.org/beta-repo/flathub-beta.flatpakrepo
flatpak install --user flathub-beta com.tomjwatson.Emote//beta
flatpak run --branch=beta com.tomjwatson.Emote
```

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

Upload a beta package to the `beta` channel, replacing the placeholder with the built `.snap` file:

```bash
snapcraft upload <path-to-snap> --release=beta
```

Testers can install it with `sudo snap install emote --beta`, or switch an
existing installation with `sudo snap refresh emote --beta`.
