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

def _yay(src=False):
    if not os.path.exists('/usr/bin/yay'):
        if src:
            dst = '/tmp/yay'
            _run([
                f'git clone https://aur.archlinux.org/yay.git {dst}',
                f'cd {dst}',
                'makepkg -si',
                f'rm -rf {dst}'
            ])
        else:
            # https://aur.chaotic.cx/docs
            _run([
                'sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com',
                'sudo pacman-key --lsign-key 3056513887B78AEB',
                "sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst'",
                "sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'",
            ])
            _lineinfile({'/etc/pacman.conf': '[chaotic-aur]'})
            _lineinfile({'/etc/pacman.conf': 'Include = /etc/pacman.d/chaotic-mirrorlist'})
            _packages([], flags='-Syy'.split())
            _packages(['yay'])


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
        'openssh', # Secure Shell (SSH) client and server.
        'sudo',
        'cronie',
        'rsync',
        'ncdu', # diskspace
        'htop',
        'bash-completion',
        'tmux',
        'unrar', # Tool for extracting RAR archives.
        'unzip',
        'zip',
        'wget',
        'syncthing',
        'reflector',
        'rate-mirrors-bin', # Tool for ranking and selecting Arch Linux mirrors.
        'ttf-anonymous-pro', # Monospaced font for programming and terminals.
        'ttf-bitstream-vera', # Classic sans-serif and serif font family.
        'ttf-caladea', # Serif font similar to Cambria.
        'ttf-carlito', # Sans-serif font similar to Calibri.
        'ttf-cascadia-code', # Monospaced font for coding with ligatures.
        'ttf-cormorant', # Elegant serif font family.
        'ttf-croscore', # Chrome OS core fonts (Arimo, Tinos, Cousine).
        'ttf-dejavu', # Versatile font family with broad language support.
        'ttf-droid', # Android’s Droid font family.
        'ttf-eurof', # Eurofurence font for stylized text.
        'ttf-fantasque-sans-mono', # Monospaced font with a quirky design.
        'ttf-fira-code', # Monospaced font with programming ligatures.
        'ttf-fira-mono', # Monospaced font for coding and terminals.
        'ttf-fira-sans', # Sans-serif font with modern design.
        'ttf-font-awesome', # Iconic font for scalable vector icons.
        'ttf-hack', # Monospaced font optimized for coding.
        'ttf-hactor', # Stylized font for creative projects.
        'ttf-hellvetica', # Helvetica-inspired font with unique style.
        'ttf-ibm-plex', # IBM’s versatile font family for various styles.
        'ttf-inconsolata', # Monospaced font for coding and terminals.
        'ttf-iosevka-nerd', # Iosevka font with Nerd Fonts symbols.
        'ttf-jetbrains-mono', # Monospaced font for developers by JetBrains.
        'ttf-jetbrains-mono-nerd', # JetBrains Mono with Nerd Fonts symbols.
        'ttf-joypixels', # Color emoji font for modern applications.
        'ttf-lato', # Modern sans-serif font family.
        'ttf-liberation', # Free alternative to Microsoft fonts (Arial, Times, etc.).
        'ttf-linux-libertine', # High-quality serif font family.
        'ttf-linux-libertine-g', # Graphite-enabled version of Linux Libertine.
        'ttf-mac-fonts', # Apple’s macOS fonts for Linux.
        'ttf-meslo-nerd-font-powerlevel10k', # Meslo font with Nerd Fonts for Powerlevel10k.
        'ttf-monofur', # Monospaced font with a retro style.
        'ttf-ms-fonts', # Microsoft core fonts (Arial, Times New Roman, etc.).
        'ttf-nerd-fonts-symbols', # Symbol-only Nerd Fonts for icons.
        'ttf-nerd-fonts-symbols-common', # Common symbols for Nerd Fonts.
        'ttf-nerd-fonts-symbols-mono', # Monospaced Nerd Fonts symbols.
        'ttf-opensans', # Clean sans-serif font by Google.
        'ttf-roboto', # Google’s Roboto font family for modern interfaces.
        'ttf-roboto-mono', # Monospaced version of Roboto for coding.
        'ttf-sourcecodepro-nerd', # Source Code Pro with Nerd Fonts symbols.
        'ttf-ubuntu-font-family', # Ubuntu’s default font family.
        'noto-fonts',
        'noto-fonts-emoji',  # emoji support for chromium based browsers, discord, etc
        'curl', # Command-line tool and library for transferring data via URLs.
        'less',
    ])
    _enable([
        'cronie',
        'systemd-timesyncd',
    ])
    _run([
        '( sudo crontab -l | grep -v -F "@hourly pacman -Sy" ; echo "@hourly pacman -Sy" ) | sudo crontab -',
        "sudo sed -i '/^#en_US.UTF-8/s/^#//g' /etc/locale.gen",
        "sudo sed -i '/^#fi_FI.UTF-8/s/^#//g' /etc/locale.gen",
        'sudo locale-gen',
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


def awesome_archinstall():
    """ Configure awesome for archinstall
    """
    if not os.path.exists(_path('~/.config/awesome/.git')):
        import shutil
        awesome_path = _path('~/.config/awesome')
        shutil.rmtree(awesome_path, ignore_errors=True)
        os.makedirs(awesome_path)
        os.chdir(awesome_path)
        _run([
            f'git clone --recursive https://github.com/elmeriniemela/awesome-config.git {awesome_path}',
        ])

def archinstall():
    "Setup archinstall laptop"
    distro()
    awesome_archinstall()
    link_files()
    ui_packages()

def ui_packages():
    "Packages for UI installation"
    _yay() # enable chaotic-aur

    _packages([
        'alacritty', # Fast, GPU-accelerated terminal emulator written in Rust.
        'awesome', # Highly configurable, lightweight window manager.
        'betterlockscreen', # Customizable lock screen for i3 window manager.
        'brave-bin', # Privacy-focused web browser with built-in ad-blocker.
        'cloc', # Counts lines of code in various programming languages.
        'default-cursors', # Default cursor set for X11 environments.
        'xfce4-clipman-plugin',
        'rofi',
        'rofi-calc',
        'picom',
        'signal-desktop',
        'slack-desktop', # Slack client for team communication.
        'udisks2',
        'gvfs',  # For automount
        'udiskie',  # For automount
        'python-qdarkstyle', # Electrum dark style
        'bluez', # Bluetooth protocol stack for Linux.
        'bluez-libs', # Libraries for Bluetooth functionality.
        'bluez-tools', # Additional tools for managing Bluetooth devices.
        'bluez-utils', # Utilities for interacting with Bluetooth devices.
        'blueberry', # Bluetooth configuration tool with a GUI.
        'thunar',
        'thunar-archive-plugin', # Archive support for Thunar file manager.
        'thunar-volman', # Volume management plugin for Thunar.
        'pavucontrol', # Volume/audio control
        'openconnect',  # work
        'openvpn',  # personal
        'syncthing',
        'thunderbird',
        'veracrypt',
        'ventoy-bin', # Tool for creating bootable USB drives with multiple ISOs.
        'gocryptfs',
        'papirus-icon-theme',  # Icon theme
        'hicolor-icon-theme', # Default fallback icon theme for freedesktop.
        'tumbler', # thunar image thumbnails
        'firefox', # Mozilla Firefox web browser.
        'ffmpeg', # Multimedia framework for encoding, decoding, and streaming.
        'ffmpegthumbnailer', # thunar video thumbnails
        'flameshot',
        'fontconfig', # Library for configuring and managing fonts.
        'font-manager', # GUI for managing and previewing fonts.
        'git-lfs', # Git extension for versioning large files.
        'volumeicon',
        'alsa-card-profiles', # ALSA configuration profiles for sound cards.
        'alsa-firmware', # Firmware files for ALSA-supported sound hardware.
        'alsa-lib', # Core library for Advanced Linux Sound Architecture (ALSA).
        'alsa-plugins', # Additional plugins for ALSA, like upmixing and JACK support.
        'alsa-topology-conf', # Configuration files for ALSA topology data.
        'alsa-ucm-conf', # ALSA Use Case Manager configuration files.
        'alsa-utils', # Utilities for managing ALSA audio devices (e.g., alsamixer).
        'pipewire-alsa',
        'pipewire', # Multimedia server for audio and video handling.
        'pipewire-alsa', # ALSA compatibility for PipeWire.
        'pipewire-audio', # Audio processing components for PipeWire.
        'pipewire-jack', # JACK compatibility for PipeWire.
        'pipewire-pulse', # PulseAudio compatibility for PipeWire.
        'pipewire-session-manager', # Session manager for PipeWire.
        'pipewire-zeroconf', # Zeroconf (mDNS) support for PipeWire.
        'polkit',  # privilege escalation
        'polkit-gnome',  # privilege escalation gui 'auth agent'
        'postgresql', # PostgreSQL database server.
        'postgresql-libs', # Libraries for PostgreSQL client applications.
        'postgresql-old-upgrade', # Tools for upgrading older PostgreSQL databases.
        'powertop', # Power consumption monitoring and optimization tool.
        'networkmanager', # Network connection manager for Wi-Fi, Ethernet, etc.
        'network-manager-applet', # System tray applet for NetworkManager.
        'networkmanager-openconnect', # OpenConnect VPN plugin for NetworkManager.
        'networkmanager-openvpn', # OpenVPN plugin for NetworkManager.
        'networkmanager-pptp', # PPTP VPN plugin for NetworkManager.
        'networkmanager-qt5', # Qt5 bindings for NetworkManager.
        'networkmanager-vpnc', # VPNC plugin for NetworkManager.
        'nm-connection-editor', # GUI for editing NetworkManager connections.
        'acpilight', # Backlight control for laptops and desktops, replacing xbacklight.
        'arandr', # GUI for managing screen resolution and layout (XRandR frontend).
        'ib-tws', # Interactive Brokers Trader Workstation for trading.
        'ib-tws-debug', # Debug version of Interactive Brokers Trader Workstation.
        'laptop-detect', # Tool to detect if the system is a laptop.
        'inxi', # System information tool for hardware and software details.
        'lxappearance-gtk3', # GUI for customizing GTK themes and appearance.
        'nordvpn-bin', # NordVPN client for secure VPN connections.
        'tlp', # Power management tool for laptops.
        'upower', # Power management and battery monitoring daemon.
        'visual-studio-code-bin', # Microsoft’s Visual Studio Code editor (binary).
        'vlc', # VLC media player for multimedia playback.
        'sshfs', # Filesystem for mounting remote directories overs SSH.
        'sshpass', # Non-interactive SSH password authentication tool.
        'sshuttle', # Transparent proxy server for VPN-like SSH tunneling.
        'wireplumber', # Session and policy manager for PipeWire multimedia server.
        'xarchiver', # Lightweight archive manager with GUI.
        'xclip', # Command-line tool for copying/pasting to X11 clipboard.
        'xdg-user-dirs', # Tool for managing standard user directories (e.g., Desktop, Documents).
        'xmlsec', # Library for XML encryption and digital signatures.
        'yt-dlp', # Tool for downloading videos from YouTube and other sites.
        'zbar', # Library for reading barcodes and QR codes.
        'zoom', # Video conferencing application.
    ])

    _aur([
        'arc-gtk-theme', # Flat GTK theme with customizable colors.
        'archlinux-logout-git', # Custom logout scripts for Arch Linux.
        'archlinux-tweak-tool-git', # Tool for tweaking and configuring Arch Linux settings.
        'wkhtmltopdf-bin', # Tool for converting HTML to PDF using WebKit (binary).
    ])

    _enable([
        'NetworkManager',
        'bluetooth',
        'syncthing@elmeri',
        'tlp',
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
    _run([
        'sudo usermod -a -G video elmeri'
    ])


def server():
    '''Setup server.
    '''
    _packages([
        'php',
        'php-pgsql',
        'nginx',
        'nginx-mod-stream', # for electrs
        'php-apcu',
        'php-gd',
        'php-intl',
        'php-cgi',
        'php-fpm',
        'php-imagick',
        'php-sodium',
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
        'ums',
    ], deps=True)

    php_extensions = [
        'bcmath',
        'curl',
        'exif',
        'gd',
        'gmp',
        'intl',
        'opcache',
        'pdo_pgsql',
        'pgsql',
        'sodium',
        'sysvsem',
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



def ufw_local():
    ''' Machine with only local network connections. Use with archinstall d base installation.
    '''
    _enable(['ufw'], try_now=True)
    _run([
        'sudo ufw default deny incoming',
        'sudo ufw default deny outgoing',
        'sudo ufw allow out to 192.168.1.250',
        'sudo ufw enable',
    ])


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
            f'ssh-keygen -t ed25519 -N "" -f ~/.ssh/{filename}',
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
            python = python or 'python3'
            _run([
                f'{python} -m venv ~/.venv/{venv_name}'
            ])


    assert os.path.exists(f'{odoo_path}/requirements.txt'), f'{odoo_path}/requirements.txt'
    _run([
        f'sed "/psycopg2/d;/lxml/d;/greenlet/d;/gevent/d;/reportlab/d;/ldap/d" {odoo_path}/requirements.txt | /home/elmeri/.venv/{venv_name}/bin/pip install -r /dev/stdin psycopg2 lxml greenlet gevent reportlab wheel setuptools',
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
    _aur(['wkhtmltopdf-bin'])

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
    C = _colors()
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



def _colors():
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
    return C


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
    retcode = 0
    with _quittable():
        try:
            func(*args.args)
        except subprocess.CalledProcessError as error:
            print("EXIT without traceback after subprocess.CalledProcessError.")
            retcode = 1

    return retcode

if __name__ == '__main__':
    sys.exit(main())
