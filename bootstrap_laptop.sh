#!/usr/bin/bash

set -e # Fail early
sudo pacman -S python-pip git python-distutils-extra

git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux || :
cd ~/.config/bootstrap-linux
sudo pip install --break-system-packages --editable .

python bootstrap.py distro
python bootstrap.py laptop
python bootstrap.py dotfiles
python bootstrap.py secure

