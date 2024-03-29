#!/usr/bin/bash


new_user=elmeri

git clone https://github.com/elmeriniemela/bootstrap-linux.git /home/$new_user/.config/bootstrap-linux
cd /home/$new_user/.config/bootstrap-linux
pacman -S python-pip
pip install --break-system-packages -e .
chown $new_user:$new_user -R /home/$new_user/.config

pacman -S archlinux-keyring
pacman -Syyu

bootstrap-linux distro
bootstrap-linux secure
bootstrap-linux swapfile 8

sudo -u $new_user bootstrap-linux server
sudo -u $new_user bootstrap-linux dotfiles

