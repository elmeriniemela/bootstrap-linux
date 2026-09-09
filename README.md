# Linux Enviroment install scripts

Archinstall
* NOTE: You might need to *temporarily* disable secure boot, otherwise EFI partition is not done correctly.
* `loadkeys fi`
* `iwctl station list`
* `iwctl --passphrase <passphrase> station <interface> connect "<SSID>"`
* `archinstall`
* `cp .zsh_history /mnt/home/elmeri`
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


### Fingerprint reader

`laptop()` installs `fprintd` and deploys PAM configs that enable the reader for
`sudo`, polkit prompts (`pkexec`) and the `i3lock` lock screen. Enrollment is
*not* part of this repo (it lives in `/var/lib/fprint`), so it has to be redone
by hand after every reinstall.

Check the reader is supported *before* expecting any of it to work:

* `lsusb | grep -iE 'finger|goodix|synaptics|validity|elan'` <-- find the reader and note its `vendor:product` id
    * T14 Gen 5 reports `27c6:6594 Shenzhen Goodix Technology Co.,Ltd.`
* Look that id up in https://fprint.freedesktop.org/supported-devices.html
    * Listed --> plain `fprintd` + `libfprint` from `extra` is enough, which is what `laptop()` installs.
    * Not listed --> upstream `libfprint` has no driver. Some Goodix/Synaptics readers
      need a proprietary TOD driver from the AUR (`libfprint-2-tod1-*`) instead. Do not
      bother enrolling until this is sorted.
* `pacman -Q libfprint` <-- some devices need a minimum version (the `27c6:6594` needs >= 1.94.9)

Enroll (as your own user, **not** with `sudo` -- enrollment is per-user):

* `fprintd-enroll` <-- touch the reader ~5 times when prompted
* `fprintd-enroll -f left-index-finger` <-- repeat for any extra fingers
* `fprintd-verify` <-- confirm a scan matches before relying on it
* `fprintd-list $USER` <-- show which fingers are enrolled
* `fprintd-delete $USER` <-- wipe enrollment and start over

Notes:

* Every PAM entry is `auth sufficient`, so a failed scan, a missing reader or an
  unenrolled finger falls through to the normal password prompt. It cannot lock you out.
* `sudo` over SSH has no reader attached and just asks for the password, as expected.
* The `i3lock` lock screen has an upstream limitation (https://github.com/i3/i3lock/issues/217):
  i3lock only starts PAM once you press Enter and never renders PAM's prompts. So the flow is
  **press Enter on an empty field, then touch the reader while it shows "verifying"**.
  It cannot scan while sitting idle.
* After editing any PAM file, keep a spare root shell (`sudo -i`) open in another
  terminal until you have verified `sudo` still works. Before testing the lock screen,
  switch to a TTY (`Ctrl+Alt+F2`) first so you can `pkill i3lock` if it misbehaves.

#### Fingerprint gate on SSH keys

`ssh-agent` normally caches a decrypted key for its whole lifetime, so after the
one passphrase prompt *any* process running as your user can sign with it
silently -- AI agents, a VS Code extension, an npm `postinstall`. The blanked
`SSH_AUTH_SOCK` wrappers in `global.bashrc` only cover tools listed there by
name, so they are a denylist.

`laptop()` deploys the pieces for a per-use gate instead:

* `/usr/local/bin/ssh-askpass-fprint` <-- root-owned `SSH_ASKPASS` helper; runs `fprintd-verify` and exits 0/1
* `/etc/systemd/user/ssh-agent.service.d/fprint-askpass.conf` <-- points the agent at it with `SSH_ASKPASS_REQUIRE=force`

The remaining half is **not** in this repo, because `~/.ssh/config` is not
managed here. Set it once by hand -- per host rather than under `Host *`, since
an Ansible run or an `rsync` loop over the ~50 server entries would otherwise
demand a touch per connection:

```
Host github.com gitlab.com bitbucket.org
    AddKeysToAgent confirm
    ControlMaster auto
    ControlPath ~/.ssh/control/%C
    ControlPersist 5m
```

The control socket directory has to exist first:

* `mkdir -p ~/.ssh/control && chmod 700 ~/.ssh/control`
* Use `%C` (a hash of the connection parameters), not `%r@%h:%p` -- unix socket
  paths cap out near 104 characters and the longer hostnames blow past that.

Per `ssh_config(5)`, `confirm` means "each use of the key must be confirmed, as
if the `-c` option was specified to `ssh-add(1)`", and `ssh-add(1)` confirms via
the *exit status* of `SSH_ASKPASS` rather than any text it returns -- which is
what lets a fingerprint check stand in for a passphrase prompt. Net effect: one
passphrase per key per boot, then a fingerprint touch for every single use.

What it does and does not protect against:

* Stops silent background use of a loaded key. Every signature needs a live touch.
* Does **not** identify the requester. The prompt says which key, not who asked,
  so malware can time a request to land while you are authorising your own and
  get yours signed. Inherent to ssh-agent's confirm design.
* The helper must stay root-owned. Writable by `elmeri` means it can be replaced
  with `exit 0`.
* `~/.config/systemd/user` outranks `/etc/systemd/user`, so the drop-in can be
  shadowed -- but only by restarting the agent, which drops every key and forces
  a visible re-add.
* Reading the key out of agent memory needs ptrace. Keep
  `/proc/sys/kernel/yama/ptrace_scope` at `1` or higher.

##### Making one touch last 5 minutes

`AddKeysToAgent confirm 5m` does **not** do this. The trailing interval is the
key's *lifetime in the agent*, so it means "confirm every use, and additionally
drop the key after 5 minutes" -- strictly more friction, not less. ssh-agent has
no confirmation cache at all: `sudo` can only cache because it is setuid root
and keeps timestamps in root-owned `/run/sudo/ts`, whereas the askpass helper
runs as `elmeri` and has nowhere unforgeable to keep one.

The `ControlMaster` block above is what buys the ergonomics instead. The agent
signature -- and therefore the touch -- happens once per SSH *connection*, not
per command, so later commands to the same host reuse the master connection and
do not authenticate at all. `ControlPersist 5m` keeps that master alive through
5 minutes of *idle* time, so an active burst of work extends the window rather
than being cut off mid-stream.

Tradeoff: while the master is up, the socket under `~/.ssh/control` is usable by
anything running as `elmeri`, so the touch can be ridden. That exposure is
scoped to hosts already connected, for 5 idle minutes, and cannot authenticate
to a new host -- unlike a blanket grace period on the key itself, which would
apply to every host in the config. A genuine global grace period would need a
root-owned service holding the timestamp and doing the fprintd verification
itself, so grants cannot be forged.

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
