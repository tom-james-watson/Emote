.PHONY: dev dev-debug dev-reset prod-reset dev-portal-identity format install test clean update-emojis flatpak flatpak-install flatpak-requirements flatpak-validate flatpak-clean flathub snap snap-clean

USER_DATA_HOME := $(if $(XDG_DATA_HOME),$(XDG_DATA_HOME),$(HOME)/.local/share)
APP_ID := com.tomjwatson.Emote
DEV_APP_ID := com.tomjwatson.Emote.Devel
DEV_DESKTOP_FILE := $(USER_DATA_HOME)/applications/$(DEV_APP_ID).desktop
DEV_DATA_DIR := $(USER_DATA_HOME)/Emote
PROD_DATA_DIR := $(HOME)/.local/share/Emote
FLATPAK_DATA_DIR := $(HOME)/.var/app/$(APP_ID)/data
SNAP_DATA_DIR := $(HOME)/snap/emote/current/.local/share/Emote

dev: dev-portal-identity
	ENV=dev pipenv run start

dev-debug: dev-portal-identity
	GTK_DEBUG=interactive ENV=dev pipenv run start

# Restore first-run state for local testing.
dev-reset:
	@pkill -x emote 2>/dev/null || true
	@rm -f "$(DEV_DATA_DIR)"/user_data* "$(DEV_DATA_DIR)/remote-desktop-token"
	@flatpak permission-reset "$(DEV_APP_ID)" >/dev/null 2>&1 || true
	@gsettings reset "org.gnome.settings-daemon.global-shortcuts.application:/org/gnome/settings-daemon/global-shortcuts/$(DEV_APP_ID)/" shortcuts >/dev/null 2>&1 || true
	@gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.unregister "$(DEV_APP_ID)" open-picker >/dev/null 2>&1 || true
	@gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.unregister "$(DEV_APP_ID)" open-emote >/dev/null 2>&1 || true
	@echo "Emote development state reset. Run 'make dev' to start the first-run flow."

# Clear settings and portal state for installed Emote builds without uninstalling them.
prod-reset:
	@pkill -x emote 2>/dev/null || true
	@flatpak kill "$(APP_ID)" >/dev/null 2>&1 || true
	@rm -f "$(PROD_DATA_DIR)"/user_data* "$(PROD_DATA_DIR)/remote-desktop-token"
	@rm -f "$(FLATPAK_DATA_DIR)"/user_data* "$(FLATPAK_DATA_DIR)/remote-desktop-token"
	@rm -f "$(SNAP_DATA_DIR)"/user_data* "$(SNAP_DATA_DIR)/remote-desktop-token"
	@flatpak permission-reset "$(APP_ID)" >/dev/null 2>&1 || true
	@gsettings reset "org.gnome.settings-daemon.global-shortcuts.application:/org/gnome/settings-daemon/global-shortcuts/$(APP_ID)/" shortcuts >/dev/null 2>&1 || true
	@gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.unregister "$(APP_ID)" open-picker >/dev/null 2>&1 || true
	@gdbus call --session --dest org.kde.kglobalaccel --object-path /kglobalaccel --method org.kde.KGlobalAccel.unregister "$(APP_ID)" open-emote >/dev/null 2>&1 || true
	@echo "Installed Emote data reset. Launch Emote to run the first-start setup again."

# Recent xdg-desktop-portal versions require host applications to register an
# app ID backed by an installed desktop file before using GlobalShortcuts.
dev-portal-identity:
	install -Dm644 static/com.tomjwatson.Emote.desktop "$(DEV_DESKTOP_FILE)"
	desktop-file-edit \
		--set-key=Exec --set-value="$(shell command -v pipenv) run start" \
		--set-key=Path --set-value="$(CURDIR)" \
		--set-key=NoDisplay --set-value=true \
		--remove-key=X-Flatpak \
		"$(DEV_DESKTOP_FILE)"

format:
	pipenv run black emote

install:
	pipenv install --site-packages -d

test:
	pipenv run python -m unittest discover -v

clean:
	rm -r .flatpak-builder build/

update-emojis:
	python3 tools/update_emojis.py

flatpak:
	flatpak-builder --user --install --force-clean build com.tomjwatson.Emote.yml

flatpak-pip-generator:
	wget -O $@.tmp https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator.py
	chmod +x $@.tmp
	mv $@.tmp $@

flatpak-install: flatpak-pip-generator
	flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
	flatpak install flathub -y org.flatpak.Builder org.gnome.Platform//51 org.gnome.Sdk//51 org.freedesktop.appstream-glib

flatpak-requirements: flatpak-pip-generator
	pipenv lock
	pipenv requirements > requirements.txt
	pipenv run ./flatpak-pip-generator --runtime='org.gnome.Sdk//51' --output flatpak/python3-requirements -r requirements.txt

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
	snapcraft pack

snap-clean:
	snapcraft clean
