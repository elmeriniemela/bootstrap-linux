#!/usr/bin/bash

git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux
cd ~/.config/bootstrap-linux
sudo pacman -S python-pip
sudo pip install --break-system-packages -e .

python bootstrap.py arcolinux
python bootstrap.py dotfiles
python bootstrap.py secure

