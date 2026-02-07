#!/usr/bin/bash

set -e # Fail early
sudo pacman -S python-pip git python-distutils-extra --needed

BSL_INSTALL_DIR=~/.config/bootstrap-linux

if [ -d "$BSL_INSTALL_DIR" ];
then
    cd $BSL_INSTALL_DIR && git pull
else
    git clone https://github.com/elmeriniemela/bootstrap-linux.git $BSL_INSTALL_DIR
fi

cd $BSL_INSTALL_DIR
sudo pip install --break-system-packages --editable .

bootstrap-linux distro
bootstrap-linux laptop
bootstrap-linux dotfiles
bootstrap-linux secure
# bootstrap-linux swapfile

