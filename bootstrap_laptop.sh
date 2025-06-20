#!/usr/bin/bash

set -e # Fail early
sudo pacman -S python-pip git python-distutils-extra

git -C ~/.config/bootstrap-linux pull || git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux
cd ~/.config/bootstrap-linux
sudo pip install --break-system-packages --editable .

python bootstrap.py archinstall
python bootstrap.py dotfiles
python bootstrap.py secure

