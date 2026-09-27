.PHONY: dev dev-debug format install clean update-emojis flatpak flatpak-install flatpak-requirements flatpak-validate flatpak-clean flathub snap snap-clean

dev:
	ENV=dev pipenv run start

dev-debug:
	GTK_DEBUG=interactive ENV=dev pipenv run start

format:
	pipenv run black emote

install:
	pipenv install --site-packages -d

clean:
	rm -r .flatpak-builder build/

update-emojis:
	wget -O static/emojis.csv https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/data/openmoji.csv

flatpak:
	flatpak-builder --user --install --force-clean build com.tomjwatson.Emote.yml

flatpak-install:
	flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
	flatpak install flathub -y org.flatpak.Builder org.gnome.Platform//50 org.gnome.Sdk//50 org.freedesktop.appstream-glib
	wget -N https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator
	chmod +x flatpak-pip-generator

flatpak-requirements:
	pipenv lock
	pipenv requirements > requirements.txt
	pipenv run ./flatpak-pip-generator --runtime='org.gnome.Sdk//50' --output python3-requirements -r requirements.txt
	mv python3-requirements.json flatpak/python3-requirements.json

flatpak-validate:
	desktop-file-validate static/com.tomjwatson.Emote.desktop
	flatpak run org.freedesktop.appstream-glib validate flatpak/com.tomjwatson.Emote.metainfo.xml

flatpak-clean:
	rm -r .flatpak-builder build/
	flatpak remove com.tomjwatson.Emote -y --delete-data

flathub:
	flatpak-builder --repo=flathub --force-clean build flatpak/com.tomjwatson.Emote.yml

snap:
	snapcraft

snap-clean:
	snapcraft clean
