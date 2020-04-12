# <span><img width="32" height="32" src="https://github.com/tom-james-watson/Emote/blob/master/static/logo.svg"></span> Emote

Emote is a simple GTK3-based Emoji Picker for linux.

Emote runs in the background and, when its keyboard shortcut (`Ctrl+Alt+E`) is presed, an emoji picker window is opened. The selected emoji is copied to the clipboard.

**NOTE - this application is under active development and is not yet ready for public use**

![Screenshot of picker](./images/screenshot.png)

## Development

### Requirements

Install pipenv:

```bash
sudo pip3 install pipenv
```

Install dependencies:

```bash
pipenv install -d
```

### Running

Run the development version:

```bash
pipenv run start
```

### Packaging

Create a packaged `.snap` file:

```bash
snapcraft
```

## Attribution

### App Icon

Copyright 2020 Twitter, Inc and other contributors

Thanks for the awesome team at Twitter.

https://twemoji.twitter.com
