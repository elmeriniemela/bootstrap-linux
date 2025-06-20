#!/usr/bin/bash

set -e # Fail early
sudo pacman -S python-pip git python-distutils-extra

export BOOTSTRAP_TARGET_DIR="~/.config/bootstrap-linux"
git -C "$BOOTSTRAP_TARGET_DIR" pull || git clone https://github.com/<repo>.git "$BOOTSTRAP_TARGET_DIR"
git clone https://github.com/elmeriniemela/bootstrap-linux.git
cd "$BOOTSTRAP_TARGET_DIR"
sudo pip install --break-system-packages --editable .

python bootstrap.py archinstall
python bootstrap.py dotfiles
python bootstrap.py secure

