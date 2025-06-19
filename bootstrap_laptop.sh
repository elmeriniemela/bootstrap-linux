#!/usr/bin/bash

sudo pacman -S python-pip git
git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux
cd ~/.config/bootstrap-linux
sudo pip install --break-system-packages -e .

python bootstrap.py archinstall
python bootstrap.py dotfiles
python bootstrap.py secure

