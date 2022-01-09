OS := $(shell uname)

build: emote.spec
	pipenv run pyinstaller emote.spec -y

dev:
	ENV=dev GDK_BACKEND="x11" pipenv run start

dev-debug:
	GTK_DEBUG=interactive GDK_BACKEND="x11" ENV=dev pipenv run start

format:
	pipenv run black emote

install:
	pipenv install -d

package:
	snapcraft

clean:
	pipenv --rm
	rm -rf dist build
	snapcraft clean
