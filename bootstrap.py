#!/usr/bin/python3

import subprocess
import os
import sys
from contextlib import contextmanager
import distutils.spawn
import re
import random
from functools import partial

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FILES_DIR = os.path.join(CURRENT_DIR, 'files')
HOME_DIR = os.path.expanduser('~')
ODOO_INSTALLS_DEFAULT_DIR = '~/Work'

@contextmanager
def _quittable():
    try:
        yield
    except (EOFError, KeyboardInterrupt):
        print("Bye")

def _path(path):
    if path.startswith('~/'):
        formatted = os.path.join(os.path.expanduser('~'), path[2:])
    else:
        formatted = path
    return formatted

def _pipe(data, command):
    default_kwargs = {
        'shell': True,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'stdin': subprocess.PIPE,
        'encoding': 'utf-8'
    }
    p = subprocess.Popen(
        command,
        **default_kwargs,
    )
    stdout_data, stderr_data = p.communicate(input=data)
    if stderr_data:
        print(stderr_data)
    assert p.returncode == 0
    return stdout_data

def _enable(services, try_now=True):
    _run([f'sudo systemctl enable {service}' for service in services])
    if try_now:
        try:
            _run([f'sudo systemctl start {service}' for service in services])
        except:
            pass



def _run(commands, dependencies=None, ignore_errors=False, **kwargs):
    for command in commands:
        print("Running command: ", command)
        if command.startswith('cd'):
            folder = command[3:]
            os.chdir(_path(folder))
        else:
            default_kwargs = {
                'shell': True,
                'stdout': sys.stdout,
                'stderr': sys.stderr,
                'check': True,
                'encoding': 'utf-8'
            }
            default_kwargs.update(kwargs)
            try:
                subprocess.run(command, **default_kwargs)
            except subprocess.CalledProcessError as error:
                if dependencies:
                    dependencies()
                    # Retry after running dependencies.
                    _run([command], **kwargs)
                elif ignore_errors:
                    pass
                else:
                    raise

def _installed_packages():
    return set(subprocess.check_output(
            "pacman -Qqe --groups | awk '{print $1}' && pacman -Qqe",
            shell=True,
            encoding='utf-8',
        ).splitlines())

def _packages(list_of_packages, flags=('-S', '--noconfirm', '--needed')):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '

    existing = _installed_packages()
    list_of_packages = [p for p in list_of_packages if p not in existing]

    if '-S' in flags and not list_of_packages:
        return

    flag_str = ' '.join(flags)
    _run([
        f'{prepend}pacman {flag_str} ' + ' '.join(list_of_packages)
    ])

def _yay():
    if not os.path.exists('/usr/bin/yay'):
        dst = '/tmp/yay'
        _run([
            f'git clone https://aur.archlinux.org/yay.git {dst}',
            f'cd {dst}',
            'makepkg -si',
            f'rm -rf {dst}'
        ])

def _aur(list_of_packages, flags=('-S', '--noconfirm', '--needed'), deps=False):
    if os.geteuid() == 0:
        print("Do not run this as root")
        return
    flag_str = ' '.join(flags)

    existing = _installed_packages()
    list_of_packages = [p for p in list_of_packages if p not in existing]

    _run([
        f'yay {flag_str} ' + ' '.join(list_of_packages)
    ], dependencies=_yay if deps else False)

def _lineinfile(files_dict):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '

    for filename, line in files_dict.items():
        line = line.replace(r"'", r"\'")
        _run([
            f"{prepend}touch {filename}",
            f"grep -qxF '{line}' {filename} || echo '{line}' | {prepend}tee -a {filename}",
        ])

def _link(files_dict):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '
    for fname, dest_path in files_dict.items():
        if os.path.isfile(dest_path):
            _run([f'{prepend}rm {dest_path}'])
        _run([f'{prepend}ln {os.path.join(FILES_DIR, fname)} {dest_path}'], ignore_errors=True)

def _copy(files_dict):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '
    for dest_path, fname in files_dict.items():
        if os.path.isfile(dest_path):
            _run([f'{prepend}rm {dest_path}'])
        _run([f'{prepend}cp {os.path.join(FILES_DIR, fname)} {dest_path}'])

class _Monitor():
    def __init__(self, name, width=0, height=0, x=0, y=0, off=False):
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.x = int(x)
        self.y = int(y)
        self.off = off
        self.primary = False

    def __eq__(self, other):
        return self.width == other.width

    def __ne__(self, other):
        return self.width != other.width

    def __gt__(self, other):
        return self.width > other.width

    def __ge__(self, other):
        return self.width >= other.width

    def __lt__(self, other):
        return self.width < other.width

    def __le__(self, other):
        return self.width <= other.width


    def __str__(self):
        if self.off:
            return f'--output {self.name} --off'
        prim_flag = ' --primary' if self.primary else ''
        return f'--output {self.name}{prim_flag} --mode {self.width}x{self.height} --pos {self.x}x{self.y}'

    def __repr__(self):
        return f'_Monitor(name={self.name!r}, width={self.width!r}, height={self.height!r}, x={self.x!r}, y={self.y!r}, off={self.off!r})'

def monitor():
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
        connected_monitors.sort()
        below, above = connected_monitors
        below.primary = True

        _run(['xrandr ' + ' '.join(str(m) for m in connected_monitors)])

        above.x = 0
        above.y = 0


        below.x = above.width // 2 - below.width // 2
        below.y = above.height

    command = 'xrandr ' + ' '.join(str(m) for m in all_monitors)

    _run([command])

def battery():
    '''Linux tlp install
    '''
    _packages(['tlp'])
    _enable(['tlp'])

def mirrors():
    '''Update mirrors
    '''
    print("Updating and ranking mirrors..")
    _run([
        'sudo reflector --country Finland --sort rate --save /etc/pacman.d/mirrorlist'
    ], dependencies=partial(_packages, ['reflector']))


def fix_t14_ethernet():
    '''
    https://forums.lenovo.com/t5/Fedora/I219-V-Ethernet-on-Thinkpad-T14-Intel-Gen2-very-slow%C2%A0/m-p/5077855?page=3#5343294

    The driver in question is the e1000e, and updating it with the intel one will not solve the problem.

    After using ethtool you need to deactivate or unplug the ethernet and re-enable it.
    '''
    _run([
        'sudo ip link set enp0s31f6 mtu 1492',
        'sudo ethtool -s enp0s31f6 speed 1000 duplex full autoneg off',
        'sudo ethtool -C enp0s31f6 rx-usecs 768',
    ], dependencies=partial(_packages, ['ethtool']))


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

def serial():
    '''Print machine serial number
    '''
    _run([
        'sudo dmidecode -s system-serial-number',
    ], dependencies=partial(_packages, ['dmidecode']))


def odoo_tests(db_name, modules=None):
    """Run odoo tests
    """
    ODOO_VERSION_DIR = os.environ['ODOO_VERSION_DIR']
    modules = modules or ','.join(os.listdir())
    _run([f'python {ODOO_VERSION_DIR}/odoo/odoo-bin --conf {ODOO_VERSION_DIR}/odoorc.conf -d {db_name} -i {modules} --test-tags={modules} --stop-after-init'])

def distro():
    '''
    Base setup. Use archlaptop() or server() after this.
    '''
    _packages([
        'base-devel',
        'openssh', # SSH client
        'sudo',
        'cronie',
        'rsync',
        'ncdu', # diskspace
        'htop',
        'bash-completion',
        'tmux',
        'unzip',
        'zip',
        'wget',
        'syncthing',
        'reflector',
    ])
    _enable([
        'cronie',
        'systemd-timesyncd',
    ])
    _run([
        '( crontab -l | grep -v -F "@hourly pacman -Sy" ; echo "@hourly pacman -Sy" ) | crontab -',
        "sed -i '/^#en_US.UTF-8/s/^#//g' /etc/locale.gen",
        "sed -i '/^#fi_FI.UTF-8/s/^#//g' /etc/locale.gen",
        'locale-gen',
    ])

    _lineinfile({
        '/etc/sysctl.d/99-sysctl.conf': 'kernel.sysrq=1',
        '/etc/sysctl.d/99-swappiness.conf': 'vm.swappiness=10',
        '/etc/sudoers.d/wheel_group': '%wheel ALL=(ALL) ALL',
    })

    # https://archived.forum.manjaro.org/t/entire-system-hangs-when-writing-to-ssd/100585/21
    # This is a simple tweak to force the Linux kernel using block multi-queue mode, allowing a better usage of the NVME drive
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'scsi_mod.use_blk_mq=1'})

    # https://lonesysadmin.net/2013/12/22/better-linux-disk-caching-performance-vm-dirty_ratio/
    # Contains the amount of dirty memory at which a process generating disk writes will itself start writeback.
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'vm.dirty_background_ratio=5'})
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'vm.dirty_ratio=10'})


    _copy({
        '/etc/vconsole.conf': 'vconsole.conf',
    })
    secure()


def archlaptop():
    '''User space apps, cannot be run as root. Run after distro.
    '''
    _packages([
        'xorg',
        'lightdm',
        'lightdm-gtk-greeter',
        'lightdm-gtk-greeter-settings',
        'ffmpeg', # screenrecorder, for preview generation
        'networkmanager',
        'veracrypt',
        'sshpass',
        'thunderbird',
        'bind',  # bind-tools
        'terminator',  # Terminal configured to awesome
        'ttf-bitstream-vera',  # Fix vscode fonts
        'ttf-droid',
        'ttf-roboto',
        'noto-fonts-emoji',  # emoji support for chromium based browsers, discord, etc
        'alsa-utils',
        'pulseaudio',
        'pulseaudio-alsa',
        'pulseaudio-bluetooth',  # bluetoothctl
        'bluez-utils',  # bluetoothctl
        'blueman',
        'pavucontrol',
        'arandr',
        'thunar',  # Light filemanager
        'tumbler', # for thumbnails in thunar
        # For easy mount 'udisksctl mount -b /dev/sdb1'. GVFS uses udisks2 for mounting functionality and is the recommended solution for most file managers.
        'udisks2',
        'gvfs',  # For automount
        'gvfs-mtp',  # Media Transfer Protocol for filemanager to automount android devices and browse files
        'udiskie',  # For automount
        'polkit',  # privilege escalation
        'polkit-gnome',  # privilege escalation gui 'auth agent'
        'lxqt-policykit',
        'network-manager-applet',
        'nm-connection-editor',  # Wifi selections
        'xorg-xev',
        'xarchiver',  # browse zip files
        'xclip',  # To copy to clipboard from terminal
        'nomacs',  # to view images
        'libreoffice-fresh',  # to view docs
        'rofi',  # application launcher
        'rofi-calc',
        'ntfs-3g',  # Read/write implementation of windows filesystem
        # It is recommended to install the hicolor-icon-theme package as many programs will deposit their icons in /usr/share/icons/hicolor and most other icon themes will inherit icons from the Hicolor icon theme.
        'hicolor-icon-theme',
        'papirus-icon-theme',  # Icon theme
        'arc-gtk-theme',  # Gtk theme
        'lxappearance',  # theme picker
        'deluge',  # torrent
        'deluge-gtk',
        'gocryptfs',
        'syncthing',
        'telegram-desktop',
        'signal-desktop',
        'networkmanager-openvpn',
        'openvpn',  # personal
        'openconnect',  # work
        'simplescreenrecorder',
        'vlc',
        'texlive-most',  # Latex
        'galculator',  # calculator
        'xdg-user-dirs',
        'xfce4-power-manager',  # default launch application for battery widget
        'upower',  # upower - UPower command line tool, Battery widget
        'redshift',  # Sets color temperature of display according to time of day, Blue light widget
        # Gtk-WARNING **: Unable to locate theme engine in module_path: "murrine",
        'gtk-engine-murrine',
        # Gtk-WARNING **: Unable to locate theme engine in module_path: "adwaita",
        'gnome-themes-extra',
        'gtk-engines',  # HighContrast GTK2 theme
        'sof-firmware',
    ],  flags=('-S', '--needed'))
    _aur([
        'python38',
        'lightdm-webkit-theme-aether-git',
        'awesome-git',
        'picom-git',
        'copyq-git',
        'whatsapp-for-linux',
        'slack-desktop',
        'teams',
        'inxi',  # Command line system information script for console
        # 'timeshift',  # Backups
        'brave-bin',
        'flameshot',  # Screenshots
        'zoom',
        'visual-studio-code-bin',
        'light-git',  # RandR-based backlight control application
        'qt5-styleplugins',  # Same theme for Qt/KDE applications and GTK applications
        'lua-pam-git',  # pam authentication for awesome wm lockscreen
        'zulip-desktop',
        'xidlehook-git',
    ], deps=True)

    awesome_path = _path('~/.config/awesome')
    if not os.path.exists(awesome_path):
        os.makedirs(awesome_path)
        os.chdir(awesome_path)
        _run([
            f'git clone --recursive https://github.com/elmeriniemela/awesome-floppy.git {awesome_path}',
        ])

    link_files()
    _run([
        'echo "arch" | sudo tee /etc/hostname',
        # Set default lightdm-webkit2-greeter theme to Aether
        "sudo sed -E -i 's/^webkit_theme.*/webkit_theme = lightdm-webkit-theme-aether/' /etc/lightdm/lightdm-webkit2-greeter.conf",

        # Set default lightdm greeter to lightdm-webkit2-greeter.
        "sudo sed -E -i 's/^[#]?greeter-session=.*/greeter-session=lightdm-webkit2-greeter/' /etc/lightdm/lightdm.conf",

        # Unstable if python major version changes.
        # "sudo sed -E -i 's/^[#]?display-setup-script=.*/display-setup-script=bootstrap-linux monitor/' /etc/lightdm/lightdm.conf",
        # "sudo sed -E -i '/HandlePowerKey/s/.*/HandlePowerKey=ignore/g' /etc/systemd/logind.conf",
        "sudo systemctl restart systemd-logind",
        "xdg-user-dirs-update", # Creating a full suite of localized default user directories within the $HOME directory can be done automatically by running
        "sudo Xorg :2 -configure",
        "sudo mv /root/xorg.conf.new /etc/X11/xorg.conf",
        "sudo nvidia-xconfig",
    ], ignore_errors=True)
    _enable([
        'NetworkManager',
        'avahi-daemon',
        'lightdm',
        'bluetooth',
    ], try_now=False)



def fix_slow_ssd(dev):
    """https://wiki.debian.org/SSDOptimization#Low-Latency_IO-Scheduler
    """
    if os.geteuid() != 0:
        print("Run as root")
        return
    if not dev:
        raise RuntimeError("Give devince name (for example 'sda' or 'nvme0n1')")
    _packages(['sysfsutils'])
    _lineinfile({'/etc/sysfs.conf': f'block/{dev}/queue/scheduler = deadline'})
    _run([f'echo deadline > /sys/block/{dev}/queue/scheduler'])


def awesome_arcolinux():
    """ Configure awesome for arcolinux
    """
    if not os.path.exists(_path('~/.config/awesome/.git')):
        import shutil
        awesome_path = _path('~/.config/awesome')
        shutil.rmtree(awesome_path, ignore_errors=True)
        os.makedirs(awesome_path)
        os.chdir(awesome_path)
        _run([
            f'git clone --recursive https://github.com/elmeriniemela/awesome-arcolinux.git {awesome_path}',
        ])

def arcolinux():
    "Setup arcolinux laptop"
    awesome_arcolinux()
    link_files()
    _aur([
        'python38',
        'zulip-desktop',
        'flameshot',  # Screenshots
        'brave-bin',
        'slack-desktop',
        'mkinitcpio-openswap', # Hibernate on SWAP for encrypted setup.
    ])

    _packages([
        'xfce4-clipman-plugin',
        'sddm',
        'awesome',
        'alacritty',
        'rofi',
        'rofi-calc',
        'brave',
        'picom',
        'signal-desktop',
        'udisks2',
        'gvfs',  # For automount
        'udiskie',  # For automount
        'alsa-utils',
        'pulseaudio',
        'python-qdarkstyle', # Electrum dark style
        'pulseaudio-alsa',
        'pulseaudio-bluetooth',
        'bluez-utils',
        'pavucontrol', # Volume/audio control
        'archlinux-logout-git', # logout widget
        'openconnect',  # work
        'openvpn',  # personal
        'networkmanager-openvpn',
        'syncthing',
        'thunderbird',
        'veracrypt',
        'gocryptfs',
        'nomacs',
    ])
    _enable([
        'sddm',
        'syncthing@elmeri',
    ], try_now=True)




def keymap():
    "Finnish keyboard layout"
    _run([
        'sudo localectl --no-convert set-x11-keymap fi pc104', # finnish keyboard layout
    ])


def link_files():
    "Link laptop configuration files"
    _link({
        'elmeri': '/var/lib/AccountsService/users/elmeri',
        'elmeri.png': '/var/lib/AccountsService/icons/elmeri',
        'backlight.rules': '/etc/udev/rules.d/backlight.rules',
        'hosts': '/etc/hosts',
        'locale.conf': '/etc/locale.conf',
        '30-touchpad.conf': '/etc/X11/xorg.conf.d/30-touchpad.conf',
        'environment': '/etc/environment',
        '99-disable-sleep.sh': '/etc/X11/xinit/xinitrc.d/99-disable-sleep.sh',
    })


def server():
    '''Setup server.
    '''
    _packages([
        'php',
        'php-pgsql',
        'nginx',
        'php-apcu',
        'php-gd',
        'php-intl',
        'php-cgi',
        'php-fpm',
        'php-imagick',
        'php-apcu',
        'ffmpeg',

        'base-devel',
        'openssh', # SSH client
        'sudo',
        'cronie',
        'rsync',
        'ncdu', # diskspace
        'htop',
        'bash-completion',
        'tmux',
        'unzip',
        'zip',
        'wget',
        'syncthing',
        'reflector',
    ])
    _enable([
        'cronie',
        'systemd-timesyncd',
    ])

    _aur([
        'python38',
        'ums',
    ], deps=True)

    php_extensions = [
        'bcmath',
        'curl',
        'gd',
        'gmp',
        'intl',
        'opcache',
        'sysvsem',
        'pdo_pgsql',
        'pgsql',
        'zip',
        'fileinfo', # (highly recommended, enhances file analysis performance; required to set custom theming images or if PHP module imagick with SVG support is installed)
        # 'imagick', # this should be enabled in /etc/php/conf.d/imagick.ini
        # 'apcu', # this should be enabled in /etc/php/conf.d/apcu.ini
    ]
    _lineinfile({'/etc/php/conf.d/apcu.ini': 'extension=apcu.so'})
    _lineinfile({'/etc/php/conf.d/apcu.ini': 'apc.enable_cli=1'})

    _lineinfile({'/etc/php/conf.d/imagick.ini': 'extension=imagick'})


    _run([f"sudo sed -i 's/;extension={ext}/extension={ext}/g' /etc/php/php.ini" for ext in php_extensions])


    _enable(['nginx', 'php-fpm'])

    _link({
        'locale.conf': '/etc/locale.conf',
    })

    odoo_venv(branch='15.0', odoo_installs_dir='/home/elmeri/Odoo')



def local_machine():
    ''' Machine with only local network connections. Use with arcolinux d base installation.
    '''
    _packages(['archlinux-keyring'])
    _packages([], flags='-Syyu --noconfirm'.split())
    _packages([
        'sddm',
        'awesome',
        'alacritty',
        'git',
        'python-pip',
        'ufw',
        'rofi',
        'rofi-calc',
        'thunar',
        'tumbler', # for thumbnails in thunar
        'udisks2',
        'gvfs',
        'udiskie',
        'zbar',
    ])

    dotfiles()
    awesome_arcolinux()

    _enable(['ufw'], try_now=True)
    _run([
        'sudo ufw default deny incoming',
        'sudo ufw default deny outgoing',
        'sudo ufw allow out to 192.168.1.250',
        'sudo ufw enable',
    ])
    _enable(['sddm'], try_now=True)


def secure():
    ''' Install and setup ufw and fail2ban.
    '''
    _packages(['ufw', 'fail2ban'], flags=('-S', '--needed'))
    _enable(['fail2ban', 'ufw'])
    _run([
        # 'sudo ufw allow 22/tcp',
        # 'sudo ufw allow 80/tcp',
        # 'sudo ufw allow 443/tcp',
        # 'sudo ufw allow syncthing',
        # 'sudo ufw allow from 192.168.1.0/16',
        'sudo ufw default deny incoming',
        'sudo ufw default allow outgoing',
        'sudo ufw enable',
    ])

def backlight_fix():
    ''' Fix the backlight control on a laptop.
    '''
    _packages([
        'acpilight', # https://unix.stackexchange.com/a/507333   (xbacklight is still the correct command)
    ], flags=('-S', '--needed'))

def swapfile(gigabytes):
    ''' Generate and enable a swapfile
    '''
    _run([
        f'sudo dd if=/dev/zero of=/swapfile bs=1M count={int(gigabytes) * 1024} status=progress',
        'sudo chmod 600 /swapfile',
        'sudo mkswap /swapfile',
        'sudo swapon /swapfile',
    ])
    _lineinfile({
        '/etc/fstab': '/swapfile none swap defaults 0 0',
    })
    _run(['sudo findmnt --verify --verbose'])

def bashrc():
    ''' Generate global bashrc
    '''
    if os.geteuid() == 0:
        print("Do not run this as root")
        return

    _lineinfile({
        '/etc/bash.bashrc': f'[ -r {FILES_DIR}/global.bashrc   ] && . {FILES_DIR}/global.bashrc',
    })

    _run([
        'rm -f ~/.bashrc',
        'rm -f ~/.bash_profile',
        'sudo rm -f /root/.bash_profile',
        'sudo rm -f /root/.bashrc',
    ])

def dotfiles():
    ''' This setups basic configuration.
        * Generate global bashrc
        * Clone dotfiles
    '''
    bashrc()
    if not os.path.exists(_path('~/.dotfiles')):
        _run([
            'git clone --bare https://github.com/elmeriniemela/dotfiles.git $HOME/.dotfiles',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME reset --hard',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME submodule update --init',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME config --local status.showUntrackedFiles no',
        ])

def gitconfig():
    "Enable ~/.gitconfig"
    _link({
        '.gitconfig': '~/.gitconfig',
    })



def add_ssh(filename):
    '''Creates ssh private and public key pair,
    adds it to ~/.ssh/config,
    and copies the public key to clipboard
    '''
    _run(
        [
            f'ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/{filename}',
            f"cat {_path(f'~/.ssh/{filename}.pub')} | xclip -selection clipboard"
        ],
        dependencies=partial(_packages, ['xclip'])
    )

def password(length=32):
    '''Generate secure password and copy to clipboard
    '''
    _run(
        [
            f'< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c{length} | xclip -selection clipboard',
        ],
        dependencies=partial(_packages, ['xclip'])
    )

def _odoo_version(branch):
    if branch == 'master':
        return float('inf')
    return float(branch)

def _branch_name(branch):
    try:
        return str(int(float(branch)))
    except:
        return branch

def _get_odoo_path(branch, odoo_installs_dir, repo):
    return _path(f'{odoo_installs_dir}/{_branch_name(branch)}/{repo}')


def odoo_venv(branch, odoo_installs_dir=ODOO_INSTALLS_DEFAULT_DIR, python=False):
    '''Creates odoo venv
    '''
    os.makedirs(_path('~/.venv'), exist_ok=True)
    venv_name = 'odoo{}'.format(_branch_name(branch))
    odoo_path = _get_odoo_path(branch, odoo_installs_dir, repo='odoo')

    if not os.path.isdir(_path('~/.venv/' + venv_name)):
        if _odoo_version(branch) <= 10.0:
            _run(
                [
                    f'python2 -m virtualenv -p python2 ~/.venv/{venv_name}'
                ],
                dependencies=partial(_packages, ['python2', 'python2-virtualenv'])
            )

        else:
            python = python or 'python3.8'
            _run([
                f'{python} -m venv ~/.venv/{venv_name}'
            ])


    assert os.path.exists(f'{odoo_path}/requirements.txt'), f'{odoo_path}/requirements.txt'
    _run([
        f'sed "/psycopg2/d;/lxml/d;/greenlet/d;/ldap/d" {odoo_path}/requirements.txt | /home/elmeri/.venv/{venv_name}/bin/pip install -r /dev/stdin psycopg2 lxml greenlet',
        f'/home/elmeri/.venv/{venv_name}/bin/pip install --upgrade pip',
    ], dependencies=partial(global_odoo_deps, branch=branch))

    if _odoo_version(branch) >= 11.0:
        _run([
            f'/home/elmeri/.venv/{venv_name}/bin/pip install zeep cryptography xmlsec signxml py3o.template py3o.formats'
        ], dependencies=partial(global_odoo_deps, branch=branch))

def global_odoo_deps(branch):
    '''Installs odoo deps
    '''
    if _odoo_version(branch) >= 11.0:
        _packages([
            'xmlsec',
            'pwgen',
            'libxml2',
            'pkg-config',
        ])
    if _odoo_version(branch) < 12.0:
        _packages([
            'npm',
        ])
        _run([
            'sudo npm install --global less@3.0.1 less-plugin-clean-css',
        ])


    _packages(['postgresql'])
    _aur(['wkhtmltopdf-static'])

    try:
        _run([
            "sudo -u postgres initdb --locale $LANG -E UTF8 -D '/var/lib/postgres/data/'",
        ])
        _enable(['postgresql'])
    except:
        pass


    try:
        _run([
            'sudo su - postgres -c "createuser -s $USER"',
            'sudo su - postgres -c "createuser -s root"',
        ])
    except:
        pass


def pgtune():
    '''pg tune

    # DB Version: 13
    # OS Type: linux
    # DB Type: web
    # Total Memory (RAM): 32 GB
    # CPUs num: 8
    # Data Storage: ssd
    '''
    postgres_config = {
        'shared_buffers': '8GB',
        'effective_cache_size': '24GB',
        'maintenance_work_mem': '2GB',
        'checkpoint_completion_target': '0.9',
        'wal_buffers': '16MB',
        'default_statistics_target': '100',
        'random_page_cost': '1.1',
        'effective_io_concurrency': '200',
        'work_mem': '10MB',
        'min_wal_size': '1GB',
        'max_wal_size': '4GB',
        'max_worker_processes': '8',
        'max_parallel_workers_per_gather': '4',
        'max_parallel_workers': '8',
        'max_parallel_maintenance_workers': '4',
    }

    for key, value in postgres_config.items():
        try:
            _run([
                f"""psql postgres -c "ALTER SYSTEM SET {key} = '{value}'" """,
            ])
        except:
            pass




def odoo(branch, odoo_installs_dir=ODOO_INSTALLS_DEFAULT_DIR, enterprise=True):
    '''Installs odoo, enterprise and all the dependencies
    '''

    odoo_path = _get_odoo_path(branch, odoo_installs_dir, repo='odoo')
    odoo_version_path = os.path.dirname(odoo_path)

    _get_odoo_source(branch, odoo_installs_dir, repo='odoo')
    if _odoo_version(branch) >= 9.0 and enterprise:
        _get_odoo_source(branch, odoo_installs_dir, repo='enterprise')


    if not os.path.exists(f'{odoo_version_path}/odoorc.conf'):
        with open(f'{FILES_DIR}/odoorc.conf') as f_read:
            data = f_read.read()

        with open(f'{odoo_version_path}/odoorc.conf', 'w') as f_write:
            f_write.write(
                data.format(
                    odoo_version=_branch_name(branch),
                    odoo_installs_dir=odoo_installs_dir,
                )
            )

    odoo_venv(branch)

def _get_odoo_source(branch, odoo_installs_dir, repo, owner='odoo'):
    import glob
    from distutils.dir_util import copy_tree
    odoo_path = _get_odoo_path(branch, odoo_installs_dir, repo)
    odoo_base_path = os.path.dirname(odoo_path)
    os.makedirs(odoo_base_path, exist_ok=True)

    cleaning_args = [
        f'cd {odoo_path}',
        f'git reset --hard',
        f'git checkout {branch}',
        f'git pull',
    ]
    if os.path.isdir(odoo_path):
        try:
            _run(cleaning_args)
            print(f"Latest pull done.. exiting now")
            return
        except:
            pass

    folders = [path for path in glob.glob(_path(f'{odoo_installs_dir}/*/*')) if os.path.isdir(path)]
    print("Checking folders for existing odoo installations:\n", ' \n'.join(folders))
    for full_path in folders:
        name = os.path.basename(full_path)
        if name == repo:
            print(f"Found existing '{repo}' installation at {full_path}")
            print("Copying the installation is faster than cloning..")
            copy_tree(full_path, odoo_path)
            _run(cleaning_args)
            _run(['git clean -xfdf'])
            break
    else:
        _run([
            f'cd {odoo_base_path}',
            f'git clone https://github.com/{owner}/{repo}.git {odoo_path} -b {branch}',
        ])

def _filter_locals(locals_dict):
    return {k: v for k, v in locals_dict.items() if \
        callable(v) \
        and v.__module__ == __name__ \
        and not k.startswith('_') \
        and k != 'main'
    }

def _print_functions(locals_dict):
    '''Lists the available functions
    '''
    import inspect
    try:
        import colorama
        colorama.init()
        C = {
            'B': colorama.Fore.BLUE,
            'Y': colorama.Fore.YELLOW,
            'R': colorama.Fore.RESET,
        }
    except ImportError:
        print("For color support: $ pip install colorama")
        from collections import defaultdict
        C = defaultdict(str)

    for fname, func in locals_dict.items():
        sign = inspect.signature(func)
        params = []
        for string_name, parameter in sign.parameters.items():
            params.append(str(parameter))
        print(f"{C['B']}def {C['Y']}{func.__name__}{C['R']}({C['B']}{', '.join(params)}{C['R']}):")
        doc = func.__doc__
        assert doc, f"Docstring missing for {fname}: '{doc}'"
        if not doc.endswith('\n    '):
            doc += '\n    '
        print("    {}".format(doc))





LOCALS = locals()

def main():
    if sys.version_info[0] < 3:
        print("Only supported in python 3")
        return -1

    import argparse

    global LOCALS
    LOCALS = _filter_locals(LOCALS)

    if len(sys.argv) == 1:
        _print_functions(LOCALS)

    parser = argparse.ArgumentParser(description='Setup your Linux system')

    parser.add_argument(
        'function', help="Install function to run (use 0 params to list function signatures)")

    parser.add_argument('args', metavar='arg', type=str, nargs='*',
                        help='argument for the function')

    args = parser.parse_args()

    func = LOCALS[args.function]
    with _quittable():
        func(*args.args)

    return 0

if __name__ == '__main__':
    sys.exit(main())
