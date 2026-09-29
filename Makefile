.PHONY: dev dev-debug dev-reset dev-reset-upgrade dev-portal-identity format install clean update-emojis flatpak flatpak-install flatpak-requirements flatpak-validate flatpak-clean flathub snap snap-clean

USER_DATA_HOME := $(if $(XDG_DATA_HOME),$(XDG_DATA_HOME),$(HOME)/.local/share)
DEV_DESKTOP_FILE := $(USER_DATA_HOME)/applications/com.tomjwatson.Emote.desktop
DEV_DATA_DIR := $(USER_DATA_HOME)/Emote
APP_ID := com.tomjwatson.Emote

dev: dev-portal-identity
	ENV=dev pipenv run start

dev-debug: dev-portal-identity
	GTK_DEBUG=interactive ENV=dev pipenv run start

# Restore first-run state for local testing. Portal permissions use Emote's
# production app ID, so this also resets them for an installed Emote build.
dev-reset:
	@pkill -x emote 2>/dev/null || true
	@rm -f "$(DEV_DATA_DIR)"/user_data* "$(DEV_DATA_DIR)/remote-desktop-token"
	@flatpak permission-reset "$(APP_ID)" >/dev/null 2>&1 || true
	@gsettings reset "org.gnome.settings-daemon.global-shortcuts.application:/org/gnome/settings-daemon/global-shortcuts/$(APP_ID)/" shortcuts >/dev/null 2>&1 || true
	@gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.unregister "$(APP_ID)" open-picker >/dev/null 2>&1 || true
	@gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.unregister "$(APP_ID)" open-emote >/dev/null 2>&1 || true
	@echo "Emote development state reset. Run 'make dev' to start the first-run flow."

# Simulate upgrading a released Emote installation. Unlike dev-reset, this
# retains the historical first-launch marker for migration testing. The setup
# flow is shared with clean installs, and manual desktop shortcuts remain.
dev-reset-upgrade: dev-reset
	@pipenv run python -c "import shelve; from emote import user_data; db = shelve.open(user_data.SHELVE_PATH); db[user_data.LEGACY_SHOWN_WELCOME] = True; db.close()"
	@echo "Emote upgrade state prepared. Run 'make dev' to test with an existing shortcut."

# Recent xdg-desktop-portal versions require host applications to register an
# app ID backed by an installed desktop file before using GlobalShortcuts.
dev-portal-identity:
	install -Dm644 static/com.tomjwatson.Emote.desktop "$(DEV_DESKTOP_FILE)"

format:
	pipenv run black emote

install:
	pipenv install --site-packages -d

clean:
	rm -r .flatpak-builder build/

update-emojis:
	python3 tools/update_emojis.py

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
	@if command -v appstreamcli >/dev/null; then \
		appstreamcli validate --no-net flatpak/com.tomjwatson.Emote.metainfo.xml; \
	else \
		flatpak run org.freedesktop.appstream-glib validate flatpak/com.tomjwatson.Emote.metainfo.xml; \
	fi

flatpak-clean:
	rm -r .flatpak-builder build/
	flatpak remove com.tomjwatson.Emote -y --delete-data

flathub:
	flatpak-builder --repo=flathub --force-clean build flatpak/com.tomjwatson.Emote.yml

snap:
	snapcraft

snap-clean:
	snapcraft clean
