OS := $(shell uname)

dev:
	ENV=dev pipenv run start

dev-debug:
	GTK_DEBUG=interactive ENV=dev pipenv run start

format:
	pipenv run black emote

install:
	pipenv install -d

package:
	snapcraft

clean:
	snapcraft clean
