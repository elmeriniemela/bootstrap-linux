#!/usr/bin/bash

set -e # Fail early

sudo pacman -S python-pip git python-distutils-extra --needed

git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux || cd ~/.config/bootstrap-linux && git pull
cd ~/.config/bootstrap-linux
sudo pip install --break-system-packages --editable .

bootstrap-linux distro
bootstrap-linux server
bootstrap-linux dotfiles
bootstrap-linux secure
bootstrap-linux swapfile 16

