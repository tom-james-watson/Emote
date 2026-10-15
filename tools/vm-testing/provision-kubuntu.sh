#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
printf 'sddm shared/default-x-display-manager select sddm\n' | debconf-set-selections
. /etc/os-release
if [[ "$VERSION_ID" == 24.04 ]]; then
    session_package=plasma-workspace-wayland
else
    session_package=plasma-session-x11
fi
apt-get install -y kubuntu-desktop "$session_package" openssh-server xdotool xclip wl-clipboard flatpak python3-gi python3-pil snapd spectacle
mkdir -p /etc/sddm.conf.d
if [[ "$VERSION_ID" == 24.04 ]]; then
    initial_session=$(basename "$(find /usr/share/xsessions -name '*plasma*.desktop' | head -1)")
else
    initial_session=$(basename "$(find /usr/share/wayland-sessions -name '*plasma*.desktop' | head -1)")
fi
cat > /etc/sddm.conf.d/99-emote-test.conf <<EOF
[Autologin]
User=tester
Session=$initial_session
Relogin=true
EOF
systemctl set-default graphical.target
systemctl enable sddm
# Reboot after provisioning so the display manager and portals start together.
touch /var/tmp/emote-provisioned
echo "Desktop installed. Reboot the guest to start the test session."
