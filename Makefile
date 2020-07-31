OS := $(shell uname)

dev:
	pipenv run start

dev-debug:
	GTK_DEBUG=interactive pipenv run start

install:
	pipenv install -d

package:
	snapcraft
