#!/usr/bin/python3

import subprocess
import os
import sys
from contextlib import contextmanager
import re
import random
from functools import partial

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FILES_DIR = os.path.join(CURRENT_DIR, 'files')
HOME_DIR = os.path.expanduser('~')
ODOO_INSTALLS_DEFAULT_DIR = '~/Code/work/odoo'

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

def _run(commands, dependencies=None, **kwargs):
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
                else:
                    raise

def _installed_packages():
    return set(subprocess.check_output(
            "pacman -Qqe --groups | awk '{print $1}' && pacman -Qqe",
            shell=True,
            encoding='utf-8',
        ).splitlines())

def _packages(list_of_packages, flags=('-S', '--noconfirm')):
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
    dst = '/tmp/yay'
    _run([
        f'git clone https://aur.archlinux.org/yay.git {dst}',
        f'cd {dst}',
        'makepkg -si',
        f'rm -rf {dst}'
    ])

def _aur(list_of_packages, flags=('-S', '--noconfirm'), deps=False):
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
            f"grep -qxF $'{line}' {filename} || echo $'{line}' | {prepend}tee -a {filename}",
        ])

def _link(files_dict):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '
    for fname, dest_path in files_dict.items():
        if os.path.isfile(dest_path):
            _run([f'{prepend}rm {dest_path}'])
        _run([f'{prepend}ln {os.path.join(FILES_DIR, fname)} {dest_path}'])

def _copy(files_dict):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '
    for fname, dest_path in files_dict.items():
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
    _run([
        'sudo systemctl enable --now tlp',
    ])

def mirrors():
    '''Update mirrors
    '''
    import urllib.request
    import re
    print("Updating and ranking mirrors..")
    # Use urllib instead of curl to better handle errors
    url = (
        'https://www.archlinux.org/mirrorlist/'
        '?country=FI'
        '&protocol=http'
        '&protocol=https'
        '&ip_version=4'
        '&use_mirror_status=on'
    )
    with urllib.request.urlopen(url) as response:
        mirrors = response.read().decode()

    if mirrors:
        try:
            ranked_mirrors = _pipe(mirrors, "sed -e 's/^#Server/Server/' -e '/^#/d' | rankmirrors -n 5 - ")
        except:
            ranked_mirrors = _pipe(mirrors, "sed -e 's/^#Server/Server/' -e '/^#/d'")
        # First pipe into rank mirrors, and only if it succeeds then edit mirrorlist
        if ranked_mirrors:
            prepend = ''
            if os.geteuid() != 0:
                prepend = 'sudo '
            _pipe(ranked_mirrors, f"{prepend}tee /etc/pacman.d/mirrorlist")

def update():
    '''Update the system
    '''
    mirrors()
    _aur([], flags='-Syyu --noconfirm --overwrite "*" python-pip'.split())
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

def distro():
    '''Commands needed for empty arch based distro install
    Post-install dependencies
        * pacstrap /mnt base linux linux-firmware archlinux-keyring dhcpcd vim git python python-pip
        * genfstab -U /mnt >> /mnt/etc/fstab
        * arch-chroot /mnt
        * ln -sf /usr/share/zoneinfo/Europe/Helsinki /etc/localtime
        * hwclock --systohc
        * systemctl enable dhcpcd
        # For Intel processors, install the intel-ucode package. For AMD processors, install the amd-ucode package.
        * pacman -S grub efibootmgr intel-ucode
        * grub-install --target=x86_64-efi --efi-directory=boot --bootloader-id=GRUB
        * grub-mkconfig -o /boot/grub/grub.cfg
        * passwd
    '''
    USER = 'elmeri'
    _packages([
        'base-devel',
        'openssh', # SSH client
        'sudo',
        'pacman-contrib', # rank mirrors
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
        'ffmpeg', # screenrecorder, for preview generation

    ])
    _run([
        'systemctl enable cronie --now',
        '( crontab -l | grep -v -F "@hourly pacman -Sy" ; echo "@hourly pacman -Sy" ) | crontab -',
        f'grep {USER} /etc/passwd > /dev/null || (useradd -m -G video,wheel,rfkill -s /bin/bash {USER} && passwd {USER})',
        "sed -i '/^#en_US.UTF-8/s/^#//g' /etc/locale.gen",
        "sed -i '/^#fi_FI.UTF-8/s/^#//g' /etc/locale.gen",
        'locale-gen',
    ])

    _lineinfile({
        '/etc/sysctl.d/99-sysctl.conf': 'kernel.sysrq=1',
        '/etc/sysctl.d/99-swappiness.conf': 'vm.swappiness=10',
        '/etc/sudoers.d/wheel_group': '%wheel ALL=(ALL) ALL',
    })


def desktop():
    '''User space apps, cannot be run as root. Run after distro.
    '''
    _packages([
        'xorg',
        'lightdm',
        'lightdm-gtk-greeter',
        'lightdm-gtk-greeter-settings',
        'networkmanager',
        'firefox',
        'veracrypt',
        'sshpass',
        'thunderbird',
        'bind', # bind-tools
        'terminator', # Terminal configured to awesome
        'ttf-bitstream-vera', # Fix vscode fonts
        'ttf-droid',
        'ttf-roboto',
        'alsa-utils',
        'pulseaudio',
        'pulseaudio-alsa',
        'pulseaudio-bluetooth', # bluetoothctl
        'bluez-utils', # bluetoothctl
        'blueman',
        'clipmenu',
        'pavucontrol',
        'arandr',
        'pcmanfm', # Light filemanager
        'udisks2', # For easy mount 'udisksctl mount -b /dev/sdb1'. GVFS uses udisks2 for mounting functionality and is the recommended solution for most file managers.
        'gvfs', # For automount
        'gvfs-mtp', # Media Transfer Protocol for pcmanfm to automount android devices and browse files
        'udiskie', # For automount
        'polkit', # privilege escalation
        'polkit-gnome', # privilege escalation gui 'auth agent'
        'lxqt-policykit',
        'network-manager-applet',
        'nm-connection-editor', # Wifi selections
        'xorg-xev',
        'xarchiver', # browse zip files
        'xclip', # To copy to clipboard from terminal
        'nomacs', # to view images
        'libreoffice-fresh', # to view docs
        'rofi', # application launcher
        'rofi-calc',
        'ntfs-3g', # Read/write implementation of windows filesystem
        'hicolor-icon-theme', # It is recommended to install the hicolor-icon-theme package as many programs will deposit their icons in /usr/share/icons/hicolor and most other icon themes will inherit icons from the Hicolor icon theme.
        'papirus-icon-theme', # Icon theme
        'arc-gtk-theme', # Gtk theme
        'lxappearance', # theme picker
        'deluge', # torrent
        'deluge-gtk',
        'gocryptfs',
        'syncthing',
        'telegram-desktop',
        'signal-desktop',
        'openvpn', # personal
        'openconnect',  # work
        'simplescreenrecorder',
        'vlc',
        'texlive-most', # Latex
        'galculator', # calculator
        'xdg-user-dirs',
        'xfce4-power-manager', # default launch application for battery widget
        'upower', # upower - UPower command line tool, Battery widget
        'redshift', # Sets color temperature of display according to time of day, Blue light widget
    ])
    _aur([
        'python38',
        'lightdm-webkit-theme-aether-git',
        'awesome-git',
        'picom-git',
        'whatsapp-nativefier',
        'slack-desktop',
        'teams',
        'inxi', # Command line system information script for console
        # 'timeshift',  # Backups
        'flameshot-git', # Screenshots
        'zoom',
        'visual-studio-code-bin',
        'light-git', #RandR-based backlight control application
        'qt5-styleplugins', # Same theme for Qt/KDE applications and GTK applications
        'lua-pam-git', # pam authentication for awesome wm lockscreen
        'zulip-desktop',
    ], deps=True)

    _run([
        'systemctl enable NetworkManager',
        'systemctl enable avahi-daemon',
        'systemctl enable lightdm',
        'localectl --no-convert set-x11-keymap fi pc104',
        'echo "arch" > /etc/hostname',
        # Set default lightdm-webkit2-greeter theme to Aether
        "sudo sed -E -i 's/^webkit_theme.*/webkit_theme = lightdm-webkit-theme-aether/' /etc/lightdm/lightdm-webkit2-greeter.conf",

        # Set default lightdm greeter to lightdm-webkit2-greeter.
        "sudo sed -E -i 's/^[#]?greeter-session=.*/greeter-session=lightdm-webkit2-greeter/' /etc/lightdm/lightdm.conf",

        # Unstable if python major version changes.
        # "sudo sed -E -i 's/^[#]?display-setup-script=.*/display-setup-script=bootstrap-linux monitor/' /etc/lightdm/lightdm.conf",
        "sudo sed -E -i '/HandlePowerKey/s/.*/HandlePowerKey=ignore/g' /etc/systemd/logind.conf",
        "sudo systemctl restart systemd-logind",
        "xdg-user-dirs-update", # Creating a full suite of localized default user directories within the $HOME directory can be done automatically by running
        f'if [ ! -d /media ]; then ln -s "/run/media/$USER" /media; fi' # veracrypt uses /media by default and this line links that folder show mounted filesystems are visible in pcmanfm. Other option would be 'VERACRYPT_MOUNT_PREFIX' env var.
    ])
    if not os.path.exists(_path('~/.config/awesome')):
        _run([
            'git clone --recursive https://github.com/elmeriniemela/awesome-floppy.git ~/.config/awesome',
        ])

    _link({
        'elmeri': '/var/lib/AccountsService/users/elmeri',
        'elmeri.png': '/var/lib/AccountsService/icons/elmeri',
        'backlight.rules': '/etc/udev/rules.d/backlight.rules',
        'hosts': '/etc/hosts',
        'locale.conf': '/etc/locale.conf',
        '30-touchpad.conf': '/etc/X11/xorg.conf.d/30-touchpad.conf',
        'environment': '/etc/environment',
    })

def server():
    '''Setup server.
    '''
    _packages([
        'docker',
        'docker-compose',
        'nextcloud',
        'php-pgsql',
        'nginx',
        'php-apcu',
    ])

    _aur([
        'ethminer-cuda',
        'python38',
    ], deps=True)

    _lineinfile({'/etc/php/php.ini': 'extension=pdo_pgsql'})
    _lineinfile({'/etc/php/php.ini': 'extension=pgsql'})
    # _lineinfile({'/etc/webapps/nextcloud/config/config.php': "'memcache.local' => '\OC\Memcache\APCu',"})

    odoo_kwargs = dict(branch='13.0', odoo_installs_dir='~/Odoo')
    odoo(**odoo_kwargs)
    _get_odoo_source(**odoo_kwargs, repo='muk_base', owner='muk-it')
    _get_odoo_source(**odoo_kwargs, repo='muk_web', owner='muk-it')
    _get_odoo_source(**odoo_kwargs, repo='auto_backup', owner='Yenthe666')
    _get_odoo_source(**odoo_kwargs, repo='odoo_addons', owner='elmeriniemela')


    if not os.path.exists(_path('~/thecodebase')):
        _run([
            'git clone https://github.com/elmeriniemela/thecodebase.git',
            'cd thecodebase',
            'git submodule update --init',
        ])

    _run([
        # 'echo "homeserver" > /etc/hostname', # sudo
        'sudo systemctl enable httpd.service --now',
    ])

    _link({
        'locale.conf': '/etc/locale.conf',
    })


    secure()


def secure():
    ''' Install and setup ufw and fail2ban.
    '''
    _packages(['ufw', 'fail2ban'])
    _run([
        'sudo systemctl enable fail2ban --now',
        'sudo systemctl enable ufw --now',
        'sudo ufw allow 22/tcp',
        'sudo ufw allow 80/tcp',
        'sudo ufw allow 443/tcp',
        'sudo ufw default deny incoming',
        'sudo ufw default allow outgoing',
        'sudo ufw enable',
    ])

    _lineinfile({
        # https://forums.whonix.org/t/enforce-kernel-module-software-signature-verification-module-signing-disallow-kernel-module-loading-by-default/7880/11
        # THIS CAUSES BOOT PARTITION NOT TO LOAD
        # '/etc/sysctl.d/99-modules-disabled.conf': 'kernel.modules_disabled=1',
    })

def backlight_fix():
    ''' Fix the backlight control on a laptop.
    '''
    _packages([
        'acpilight', # https://unix.stackexchange.com/a/507333   (xbacklight is still the correct command)
    ], flags=('-S',))

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

def dotfiles():
    ''' This setups basic configuration.
        * Generate global bashrc
        * Clone dotfiles
    '''
    if os.geteuid() == 0:
        print("Do not run this as root")
        return

    _lineinfile({
        '/etc/bash.bashrc': f'[ -r {FILES_DIR}/global.bashrc   ] && . {FILES_DIR}/global.bashrc',
    })

    unlink = [
        _path('~/.bashrc'),
        _path('~/.bash_profile'),
    ]

    for path in unlink:
        if os.path.exists(path):
            os.unlink(path)


    if not os.path.exists(_path('~/.dotfiles')):
        _run([
            'git clone --bare https://github.com/elmeriniemela/dotfiles.git $HOME/.dotfiles',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME reset --hard',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME submodule update --init',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME config --local status.showUntrackedFiles no',
        ])

def glorious_dotfiles():
    '''Install the glorious dotfiles
    '''

    _packages([
        'acpi',
        'acpid',
        'acpi_call',
        'mpd',
        'mpc',
        'maim',
        'feh',
        'xclip',
        'imagemagick',
        'blueman',
        'redshift',
        'xfce4-power-manager',
        'upower',
        'noto-fonts-emoji',
        'xdg-user-dirs',
        'iproute2',
        'iw',
        'ffmpeg',
    ])
    _aur([
        'awesome-git',
        'picom-git',
        'light-git',
        'nerd-fonts-fantasque-sans-mono',

    ], flags=('-S',))

    _run([
        'git clone https://github.com/manilarome/the-glorious-dotfiles.git ~/.config/the-glorious-dotfiles',
    ])

def material_awesome():
    '''Install material-awesome
    '''
    _packages('rofi xclip gnome-keyring polkit'.split())
    _aur(['i3lock-fancy-git'])
    _run([
        'git clone https://github.com/HikariKnight/material-awesome.git ~/.config/material-awesome',
    ])

def add_ssh(filename):
    '''Creates ssh private and public key pair,
    adds it to ~/.ssh/config,
    and copies the public key to clipboard
    '''
    _run(
        [
            f'ssh-keygeny -t rsa -b 4096 -N "" -f ~/.ssh/{filename}',
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

def _get_odoo_path(branch, odoo_installs_dir, repo):
    return _path(f'{odoo_installs_dir}/{branch[:-2]}/{repo}')

def odoo_venv(branch, odoo_installs_dir=ODOO_INSTALLS_DEFAULT_DIR):
    '''Creates odoo venv
    '''
    os.makedirs(_path('~/.venv'), exist_ok=True)
    venv_name = 'odoo{}'.format(branch[:-2])
    odoo_path = _get_odoo_path(branch, odoo_installs_dir, repo='odoo')

    if not os.path.isdir(_path('~/.venv/' + venv_name)):
        if float(branch) <= 10.0:
            _run(
                [
                    'python2 -m virtualenv -p python2 ~/.venv/{}'.format(venv_name),
                ],
                dependencies=partial(_packages, ['python2', 'python2-virtualenv'])
            )

        else:
            _run([
                'python3.8 -m venv ~/.venv/{}'.format(venv_name),
            ])



    _run([
        f'sed "/psycopg2/d;/lxml/d;/greenlet/d" {odoo_path}/requirements.txt | /home/elmeri/.venv/{venv_name}/bin/pip install -r /dev/stdin psycopg2 lxml greenlet',
    ], dependencies=partial(global_odoo_deps, branch=branch))

    if float(branch) >= 11.0:
        _run([
            f'/home/elmeri/.venv/{venv_name}/bin/pip install zeep cryptography xmlsec signxml py3o.template py3o.formats'
        ], dependencies=partial(global_odoo_deps, branch=branch))

def global_odoo_deps(branch):
    '''Installs odoo deps
    '''
    if float(branch) >= 11.0:
        venv_name = 'odoo{}'.format(branch[:-2])
        _packages([
            'xmlsec',
            'pwgen',
            'libxml2',
            'pkg-config',
        ])
    if float(branch) < 12.0:
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
            'sudo systemctl enable --now postgresql.service',
        ])
    except:
        pass

    try:
        _run([
            'sudo su - postgres -c "createuser -s $USER"',
            'sudo su - postgres -c "createuser -s root"',
        ])
    except:
        pass

def odoo(branch, odoo_installs_dir=ODOO_INSTALLS_DEFAULT_DIR):
    '''Installs odoo, enterprise and all the dependencies
    '''

    odoo_path = _get_odoo_path(branch, odoo_installs_dir, repo='odoo')

    _get_odoo_source(branch, odoo_installs_dir, repo='odoo')
    if float(branch) >= 9.0:
        _get_odoo_source(branch, odoo_installs_dir, repo='enterprise')


    if not os.path.exists(f'{odoo_path}/.odoorc.conf'):
        with open(f'{FILES_DIR}/.odoorc.conf') as f_read:
            data = f_read.read()

        with open(f'{odoo_path}/.odoorc.conf', 'w') as f_write:
            f_write.write(
                data.format(odoo_version=branch[:-2])
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
        assert func.__doc__ and func.__doc__.endswith('\n    '), f"Invalid docstring for {fname}: '{func.__doc__}'"
        print("    {}".format(func.__doc__))





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
