#!/usr/bin/bash

set -e # Fail early

git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux
cd ~/.config/bootstrap-linux
sudo pacman -S python-pip
pip install -e .

bootstrap.py arcolinux
bootstrap.py dotfiles
bootstrap.py secure

