# Linux Enviroment install scripts

Archinstall
* NOTE: You might need to *temporarily* disable secure boot, otherwise EFI partition is not done correctly.
* `loadkeys fi`
* `iwctl station list`
* `iwctl --passphrase <passphrase> station <interface> connect "<SSID>"`
* `archinstall`
* Do not copy the network configuration from ISO, instead install NetworkManager. After install, setup network
* `nmcli device wifi connect "<SSID>" password "<password>"`

Install instructions:

* Laptop: `bash <(curl -sL https://eniemela.fi/api-v1/bsl)`
* Server: `bash <(curl -sL https://eniemela.fi/api-v1/bsl?server=1)`


Usage instructions:

* `bootstrap-linux` <-- this will start the CLI-interface and print available functions


```bash
$ bootstrap-linux
def odoo_venv(branch, python=False, odoo_installs_dir='~/Odoo/src'):
    Creates odoo venv

def global_odoo_deps(branch):
    Installs odoo deps

def postgresql():
    Base postgresql setup to /home/postgres

def odoo(branch, odoo_installs_dir='~/Odoo/src', enterprise=True):
    Installs odoo, enterprise and all the dependencies

def odoo_tests(db_name, modules=None):
    Run odoo tests

def monitor(reverse=0):
    Autoconfigure dual monitor with xrandr

def mirrors():
    Update mirrors

def fix_t14_ethernet():
    The driver in question is the e1000e, and updating it with the intel one will not solve the problem. After using ethtool you need to deactivate or unplug the ethernet and re-enable it.

def update():
    Update the system

def serial():
    Print machine serial number

def keymap():
    Finnish keyboard layout

def add_ssh(filename):
    Creates ssh private and public key pair, adds it to ~/.ssh/config, and copies the public key to clipboard

def password(length=26):
    Generate secure password and copy to clipboard. Alphabet is a-z (26) + 0-9 (10) = 36. By default generates a PW with at least 128 bits of entropy (36**26 > 2**128).

def pgtune():
    Alter postgres according to pgtune # DB Version: 13 # OS Type: linux # DB Type: web # Total Memory (RAM): 32 GB # CPUs num: 8 # Data Storage: ssd

def local_ufw():
    Machine with only local network connections. Use with archinstall d base installation.

def secure():
    Install and setup ufw and fail2ban.

def swapfile(gigabytes=False):
    Generate and enable a swapfile

def bashrc():
    Generate global bashrc

def dotfiles():
    This setups basic configuration: 1. Generate global bashrc 2. Clone dotfiles

def gitconfig():
    Enable ~/.gitconfig

def link_agentmd():
    Enable AGENTS.md

def distro():
    Base setup. Use laptop() or server() after this.

def laptop():
    Setup archinstall laptop

def nvidia_prime():
    Install nvidia prime

def latex():
    Install latex

def server():
    Setup server.

usage: bootstrap-linux [-h] function [arg ...]
bootstrap-linux: error: the following arguments are required: function
```


### TODO:

* Xorg disable screen off:
    * `xset -dpms` for disabling energy star features and
    * `xset s off` for disable screensaver
    * Run these in  `~/.xprofile` or `/etc/xprofile`?
* Xorg disable right mouse up click (ButtonRelease on 3).
    * Maybe this is a feature that I should learn?
    * https://www.reddit.com/r/linuxquestions/comments/dbf1ht/disable_mouse_button_release_x11/
* Awesome disable notifications:
    * Do a widget that toggles naughty
    * https://awesomewm.org/doc/api/libraries/naughty.html
* Application that better handles screen shutdown
* Firefox Google Meets share screen select sreen
* Copyq force center of screen and size
