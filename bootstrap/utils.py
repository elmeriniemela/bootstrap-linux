
import distutils.spawn
import subprocess
import re
from functools import partial

from .lib import (
    _Monitor,
    _path,
    _enable,
    _run,
    _packages,
    _aur,
    api,
)


@api
def monitor(reverse=0):
    '''Autoconfigure dual monitor with xrandr
    '''

    output = subprocess.check_output("xrandr -q --current", shell=True, encoding='utf-8')
    connected_monitors = []
    all_monitors = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        match = re.findall(r'^([\w-]+) connected', line)
        if match:
            name = match[0]
            # 3 tries
            for max_res_line in lines[i+1: i+4]:
                res_match = re.findall(r'[\s]*(\d+)x(\d+)', max_res_line)
                if res_match:
                    width, height = res_match[0]
                    monitor = _Monitor(name, width, height)
                    connected_monitors.append(monitor)
                    all_monitors.append(monitor)
                    break

        disconnected = re.findall(r'^([\w-]+) disconnected', line)
        for name in disconnected:
            all_monitors.append(_Monitor(name, off=True))


    if len(connected_monitors) == 2:
        # Sort with ASC
        connected_monitors.sort(reverse=bool(int(reverse)))
        below, above = connected_monitors
        below.primary = True

        _run(['xrandr ' + ' '.join(str(m) for m in connected_monitors)])

        above.x = 0
        above.y = 0


        below.x = above.width // 2 - below.width // 2
        below.y = above.height

    command = 'xrandr ' + ' '.join(str(m) for m in all_monitors)

    _run([command])

@api
def mirrors():
    '''Update mirrors
    '''
    print("Updating and ranking mirrors..")
    _run([
        'sudo reflector --country Finland --sort rate --save /etc/pacman.d/mirrorlist'
    ], dependencies=partial(_packages, ['reflector']))




@api
def fix_t14_ethernet():
    ''' The driver in question is the e1000e, and updating it with the intel one will not solve the problem. After using ethtool you need to deactivate or unplug the ethernet and re-enable it.
    '''
    # https://forums.lenovo.com/t5/Fedora/I219-V-Ethernet-on-Thinkpad-T14-Intel-Gen2-very-slow%C2%A0/m-p/5077855?page=3#5343294
    _run([
        'sudo ip link set enp0s31f6 mtu 1492',
        'sudo ethtool -s enp0s31f6 speed 1000 duplex full autoneg off',
        'sudo ethtool -C enp0s31f6 rx-usecs 768',
    ], dependencies=partial(_packages, ['ethtool']))


@api
def update():
    '''Update the system
    '''
    _packages(['archlinux-keyring'])
    _aur([], flags='-Syyu --noconfirm --overwrite "*" python-pip'.split())
    if distutils.spawn.find_executable("inxi"):
        _run([
            'inxi -Fxxxza --no-host',
            # FIX: Device-2: NVIDIA GM108M [GeForce 940MX] driver: N/A
            # 'sudo modprobe nvidia',
        ])
    input("Press enter key to quit.\n")

@api
def serial():
    '''Print machine serial number
    '''
    _run([
        'sudo dmidecode -s system-serial-number',
    ], dependencies=partial(_packages, ['dmidecode']))

@api
def keymap():
    "Finnish keyboard layout"
    _run([
        'sudo localectl --no-convert set-x11-keymap fi pc104', # finnish keyboard layout
    ])


@api
def add_ssh(filename):
    '''Creates ssh private and public key pair, adds it to ~/.ssh/config, and copies the public key to clipboard
    '''
    _run(
        [
            f'ssh-keygen -t ed25519 -f ~/.ssh/{filename} -C {filename}',
            f"cat {_path(f'~/.ssh/{filename}.pub')} | xclip -selection clipboard"
        ],
        dependencies=partial(_packages, ['xclip'])
    )

@api
def password(length=26):
    '''Generate secure password and copy to clipboard. Alphabet is a-z (26) + 0-9 (10) = 36. By default generates a PW with at least 128 bits of entropy (36**26 > 2**128).
    '''
    _run(
        [
            f'< /dev/random tr -dc a-z0-9 | head -c{length} | xclip -selection clipboard',
        ],
        dependencies=partial(_packages, ['xclip'])
    )

