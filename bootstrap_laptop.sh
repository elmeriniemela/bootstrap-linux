#!/usr/bin/bash

set -e # Fail early

git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux
cd ~/.config/bootstrap-linux
pip install -e .

bootstrap-linux arcolinux
bootstrap-linux dotfiles
bootstrap-linux secure

