#!/bin/bash
set -euxo pipefail
dnf -y upgrade
dnf -y group install workstation-product-environment
dnf -y install flatpak python3-gobject python3-pillow wl-clipboard gnome-text-editor
mkdir -p /etc/gdm
cat > /etc/gdm/custom.conf <<EOF
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=tester
EOF
systemctl set-default graphical.target
systemctl enable gdm
touch /var/tmp/emote-provisioned
echo "Desktop installed. Reboot the guest to start the test session."
