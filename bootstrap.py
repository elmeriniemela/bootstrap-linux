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

def aur():
    '''
    Install aur packages.
    '''
    _aur([
        'arcolinux-logout',
        'arc-gtk-theme',
    ])
    _packages([
        'brave-bin',
        'visual-studio-code-bin'
    ])


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
        'ttf-bitstream-vera',  # Fix vscode fonts
        'ttf-droid',
        'ttf-roboto',
        'ttf-dejavu',
        'ttf-liberation',
        'noto-fonts',
        'less',
        'noto-fonts-emoji',  # emoji support for chromium based browsers, discord, etc
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
    _packages([
        'xfce4-clipman-plugin',
        'rofi',
        'rofi-calc',
        'picom',
        'signal-desktop',
        'udisks2',
        'gvfs',  # For automount
        'udiskie',  # For automount
        # 'pyenv', # https://github.com/pyenv/pyenv?tab=readme-ov-file#install-additional-python-versions
        'python-qdarkstyle', # Electrum dark style
        'bluez', # Bluetooth protocol stack for Linux.
        'bluez-libs', # Libraries for Bluetooth functionality.
        'bluez-tools', # Additional tools for managing Bluetooth devices.
        'bluez-utils', # Utilities for interacting with Bluetooth devices.
        # 'blueman',
        'thunar',
        'pavucontrol', # Volume/audio control
        'openconnect',  # work
        'openvpn',  # personal
        'networkmanager-openvpn',
        'syncthing',
        'thunderbird',
        'veracrypt',
        'gocryptfs',
        # 'sardi-icons',
        # 'adwaita-icon-theme',
        # 'hicolor-icon-theme',
        # 'papirus-icon-theme',  # Icon theme
        'tumbler', # thunar image thumbnails
        'ffmpegthumbnailer', # thunar video thumbnails
        'flameshot',
        'volumeicon',
        'alsa-utils',
        'pipewire-alsa',
        'polkit',  # privilege escalation
        'polkit-gnome',  # privilege escalation gui 'auth agent'
    ])
    _enable([
        'bluetooth',
        'syncthing@elmeri',
    ], try_now=True)

def all_packages():
    "All packages from previous install"
    _aur([
        # 'a52dec', # Library for decoding ATSC A/52 (AC-3) audio streams.
        # 'aalib', # Library for creating ASCII art from images and videos.
        # 'abseil-cpp', # Collection of C++ library code for common utilities like string manipulation.
        # 'accountsservice', # D-Bus service for managing user accounts.
        # 'acl', # Library for managing access control lists (file permissions).
        # 'acpica', # Tools for ACPI (Advanced Configuration and Power Interface) development and debugging.
        'acpilight', # Backlight control for laptops and desktops, replacing xbacklight.
        # 'adobe-source-code-pro-fonts', # Monospaced font designed for coding environments.
        # 'adobe-source-han-sans-cn-fonts', # Sans-serif font for Chinese text.
        # 'adobe-source-han-sans-jp-fonts', # Sans-serif font for Japanese text.
        # 'adobe-source-han-sans-kr-fonts', # Sans-serif font for Korean text.
        # 'adobe-source-sans-fonts', # General-purpose sans-serif font family.
        # 'adobe-source-serif-fonts', # Serif font family for professional typography.
        # 'adwaita-cursors', # Default cursor theme for GNOME environments.
        # 'adwaita-fonts', # Default font set for GNOME environments.
        # 'adwaita-icon-theme', # Default icon theme for GNOME desktop.
        # 'adwaita-icon-theme-legacy', # Legacy icons for older GNOME applications.
        # 'aic94xx-firmware', # Firmware for Adaptec AIC94xx SAS/SATA controllers.
        'alacritty', # Fast, GPU-accelerated terminal emulator written in Rust.
        'alsa-card-profiles', # ALSA configuration profiles for sound cards.
        'alsa-firmware', # Firmware files for ALSA-supported sound hardware.
        'alsa-lib', # Core library for Advanced Linux Sound Architecture (ALSA).
        'alsa-plugins', # Additional plugins for ALSA, like upmixing and JACK support.
        'alsa-topology-conf', # Configuration files for ALSA topology data.
        'alsa-ucm-conf', # ALSA Use Case Manager configuration files.
        'alsa-utils', # Utilities for managing ALSA audio devices (e.g., alsamixer).
        # 'aom', # Alliance for Open Media AV1 video codec library.
        # 'appstream', # Standard for metadata about software applications.
        # 'appstream-glib', # Library for reading and writing AppStream metadata.
        'arandr', # GUI for managing screen resolution and layout (XRandR frontend).
        'arc-gtk-theme', # Flat GTK theme with customizable colors.
        'arch-install-scripts', # Scripts for installing Arch Linux (e.g., pacstrap, arch-chroot).
        'archlinux-keyring', # GPG keys for verifying Arch Linux packages.
        'archlinux-logout-git', # Custom logout scripts for Arch Linux.
        'archlinux-tweak-tool-git', # Tool for tweaking and configuring Arch Linux settings.
        # 'arcolinux-alacritty-git', # ArcoLinux-specific configuration for Alacritty terminal.
        # 'arcolinux-arc-dawn-git', # Dawn theme for ArcoLinux desktop environment.
        # 'arcolinux-awesome-git', # Customized Awesome WM configuration for ArcoLinux.
        # 'arcolinux-bootloader-grub-git', # GRUB bootloader configuration for ArcoLinux.
        # 'arcolinux-config-all-desktops-git', # Configuration files for various ArcoLinux desktops.
        # 'arcolinux-dconf-all-desktops-git', # Dconf settings for ArcoLinux desktop environments.
        # 'arcolinux-desktop-trasher-git', # Tool for managing desktop trash in ArcoLinux.
        # 'arcolinuxd-system-config-git', # System configuration tool for ArcoLinux.
        # 'arcolinuxd-welcome-app-git', # Welcome application for ArcoLinux users.
        # 'arcolinux-grub-theme-vimix-git', # Vimix theme for GRUB bootloader in ArcoLinux.
        # 'arcolinux-gtk-surfn-arc-git', # Surfn Arc GTK theme for ArcoLinux.
        # 'arcolinux-keyring', # GPG keyring for ArcoLinux package verification.
        # 'arcolinux-local-xfce4-git', # Local XFCE4 configuration for ArcoLinux.
        # 'arcolinux-mirrorlist-git', # Mirrorlist for ArcoLinux package repositories.
        # 'arcolinux-paru-git', # Customized Paru AUR helper for ArcoLinux.
        # 'arcolinux-powermenu-git', # Power menu for ArcoLinux desktop environments.
        # 'arcolinux-rofi-git', # Customized Rofi application launcher for ArcoLinux.
        # 'arcolinux-rofi-themes-git', # Themes for Rofi in ArcoLinux.
        # 'arcolinux-root-git', # Root-level configuration scripts for ArcoLinux.
        # 'arcolinux-sddm-futuristic-git', # Futuristic SDDM theme for ArcoLinux.
        # 'arcolinux-sddm-materia-git', # Materia SDDM theme for ArcoLinux.
        # 'arcolinux-sddm-simplicity-git', # Simplicity SDDM theme for ArcoLinux.
        # 'arcolinux-sddm-slice-git', # Slice SDDM theme for ArcoLinux.
        # 'arcolinux-sddm-sugar-candy-git', # Sugar Candy SDDM theme for ArcoLinux.
        # 'arcolinux-sddm-urbanlifestyle-git', # Urban Lifestyle SDDM theme for ArcoLinux.
        # 'arcolinux-systemd-services-git', # Custom systemd services for ArcoLinux.
        # 'arcolinux-volumeicon-git', # Volume control icon for ArcoLinux.
        # 'arcolinux-wallpapers-git', # Wallpaper collection for ArcoLinux.
        # 'arconet-variety-config', # Configuration for Variety wallpaper changer in ArcoLinux.
        # 'arconet-xfce', # XFCE desktop configuration for ArcoLinux.
        # 'arcopro-wallpapers', # Wallpaper collection for ArcoLinux.
        # 'argon2', # Memory-hard function for password hashing and key derivation.
        # 'aribb24', # Library for decoding ARIB STD-B24 subtitles.
        # 'ast-firmware', # Firmware for AST (Aspeed) BMC chips.
        # 'atkmm', # C++ bindings for ATK accessibility toolkit.
        # 'at-spi2-core', # Accessibility framework for assistive technologies.
        # 'attr', # Library for extended file attributes.
        # 'audit', # Security auditing framework for tracking system events.
        # 'autoconf', # Tool for generating configure scripts for software builds.
        # 'automake', # Tool for generating Makefiles for software builds.
        # 'avahi', # Service discovery protocol for local network devices (mDNS/DNS-SD).
        'awesome', # Highly configurable, lightweight window manager.
        # 'awesome-terminal-fonts', # Iconic fonts for terminals and code editors.
        # 'aws-cli-bin', # Command-line interface for Amazon Web Services (binary).
        # 'aws-cli-v2-python-awscrt', # AWS SDK for Python used by AWS CLI v2.
        # 'aws-cli-v2-python-awscrt-debug', # Debug version of AWS SDK for Python.
        # 'babl', # Library for dynamic pixel format conversion (used by GIMP/GEGL).
        # 'base', # Minimal package set for a basic Arch Linux system.
        # 'base-devel', # Essential development tools for building software.
        # 'bash', # Bourne-Again SHell, a popular command-line shell.
        # 'bash-completion', # Programmable completion for bash commands.
        # 'bat', # Cat clone with syntax highlighting and Git integration.
        # 'bc', # Arbitrary-precision arithmetic calculator.
        'betterlockscreen', # Customizable lock screen for i3 window manager.
        # 'bibata-cursor-theme-bin', # Modern cursor theme for Linux desktops.
        # 'bind', # DNS server and tools (BIND suite).
        # 'binutils', # GNU binary utilities (assembler, linker, etc.).
        # 'bison', # Parser generator for creating syntax parsers.
        # 'bisq', # Decentralized Bitcoin exchange and trading platform.
        # 'blas', # Basic Linear Algebra Subprograms for scientific computing.
        'blueberry', # Bluetooth configuration tool with a GUI.
        # 'blueman', # GTK-based Bluetooth manager.
        'bluez', # Bluetooth protocol stack for Linux.
        'bluez-libs', # Libraries for Bluetooth functionality.
        'bluez-tools', # Additional tools for managing Bluetooth devices.
        'bluez-utils', # Utilities for interacting with Bluetooth devices.
        # 'boost-libs', # Runtime libraries for the Boost C++ libraries.
        # 'botan2', # Cryptographic library for secure communication and encryption.
        'brave-bin', # Privacy-focused web browser with built-in ad-blocker.
        # 'broadcom-wl-dkms', # Broadcom wireless driver for DKMS.
        # 'brotli', # Compression library for web content (Brotli algorithm).
        # 'btop', # Resource monitor with a modern, colorful interface.
        # 'btrfs-progs', # Tools for managing Btrfs filesystems.
        # 'bubblewrap', # Sandboxing utility for running unprivileged containers.
        # 'bzip2', # Compression library and tools for bzip2 format.
        # 'ca-certificates', # Common CA certificates for SSL/TLS verification.
        # 'ca-certificates-mozilla', # Mozilla's CA certificate bundle.
        # 'ca-certificates-utils', # Utilities for managing CA certificates.
        # 'cairo', # 2D graphics library for rendering vector graphics.
        # 'cairomm', # C++ bindings for the Cairo graphics library.
        # 'cairomm-1.16', # C++ bindings for Cairo (version 1.16).
        # 'cantarell-fonts', # Humanist sans-serif font used by GNOME.
        # 'c-ares', # Asynchronous DNS resolver library.
        # 'cblas', # C interface to BLAS (Basic Linear Algebra Subprograms).
        # 'cdparanoia', # Audio CD ripping library.
        # 'chaotic-keyring', # GPG keyring for Chaotic-AUR repository.
        # 'chaotic-mirrorlist', # Mirrorlist for Chaotic-AUR repository.
        # 'chromaprint', # Audio fingerprinting library for identifying music.
        # 'cifs-utils', # Tools for mounting and managing SMB/CIFS shares.
        'cloc', # Counts lines of code in various programming languages.
        # 'clonezilla', # Disk cloning and imaging tool.
        # 'clucene', # C++ full-text search engine library.
        'cmake', # Cross-platform build system generator.
        # 'colord', # Color management daemon for device color profiles.
        # 'containerd', # Daemon for managing container lifecycles.
        'coreutils', # Basic GNU utilities for file, text, and shell operations.
        # 'cppdap', # C++ implementation of the Debug Adapter Protocol.
        'cronie', # Lightweight cron daemon for scheduling tasks.
        # 'cryptsetup', # Tool for setting up encrypted filesystems (LUKS).
        'curl', # Command-line tool and library for transferring data via URLs.
        # 'dav1d', # Fast AV1 video decoder library.
        # 'db5.3', # Berkeley DB embedded database (version 5.3).
        # 'dbus', # Message bus system for inter-process communication.
        # 'dbus-broker', # High-performance D-Bus message broker.
        # 'dbus-broker-units', # Systemd units for dbus-broker.
        # 'dbus-glib', # GLib bindings for D-Bus messaging.
        # 'dbus-units', # Systemd units for D-Bus.
        # 'dconf', # Configuration database system for GNOME applications.
        # 'ddcutil', # Tool for controlling monitor settings via DDC/CI.
        # 'ddrescue', # Data recovery tool for copying data from failing drives.
        # 'debugedit', # Tool for editing debug information in ELF binaries.
        'default-cursors', # Default cursor set for X11 environments.
        # 'desktop-file-utils', # Utilities for managing .desktop files.
        # 'device-mapper', # Library for managing logical volumes (LVM).
        # 'dex', # Desktop Entry execution tool for running .desktop files.
        # 'dialog', # Tool for creating text-based dialog boxes in scripts.
        # 'diffutils', # GNU utilities for comparing and diffing files.
        # 'ding-libs', # Libraries for identity and authentication (SSSD dependencies).
        # 'dkms', # Dynamic Kernel Module Support for managing kernel modules.
        # 'dmidecode', # Tool for retrieving hardware information from DMI/SMBIOS.
        # 'dmraid', # Software RAID management for device-mapper RAID.
        # 'dnsmasq', # Lightweight DNS and DHCP server.
        # 'dnssec-anchors', # DNSSEC trust anchors for secure DNS resolution.
        # 'docker', # Platform for containerized applications.
        # 'dosfstools', # Tools for managing FAT filesystems.
        # 'double-conversion', # Library for fast floating-point to string conversion.
        # 'downgrade', # Script for downgrading Arch Linux packages.
        # 'drbl', # Diskless Remote Boot in Linux for network booting.
        # 'duf', # Disk usage utility with a user-friendly interface.
        # 'duktape', # Embeddable JavaScript engine.
        # 'e2fsprogs', # Tools for managing ext2/ext3/ext4 filesystems.
        # 'ecryptfs-utils', # Tools for managing eCryptfs encrypted filesystems.
        # 'edk2-shell', # UEFI shell for debugging and testing UEFI environments.
        # 'efibootmgr', # Tool for managing UEFI boot entries.
        # 'efivar', # Library for managing UEFI variables.
        # 'eglexternalplatform', # Interface for external EGL platform implementations.
        # 'egl-wayland', # EGL implementation for Wayland compositors.
        # 'electrum', # Lightweight Bitcoin wallet with GUI.
        # 'elementary-icon-theme', # Icon theme inspired by elementary OS.
        # 'ell', # Embedded Linux Library for wireless and networking.
        # 'enchant', # Spell-checking library for multiple backends.
        # 'endeavouros-keyring', # GPG keyring for EndeavourOS repositories.
        # 'endeavouros-mirrorlist', # Mirrorlist for EndeavourOS repositories.
        # 'ethtool', # Utility for configuring network interfaces.
        # 'exfatprogs', # Tools for managing exFAT filesystems.
        # 'exiv2', # Library for handling image metadata (EXIF, IPTC, XMP).
        # 'exo', # Extension library for XFCE applications.
        # 'expac', # Pacman database extraction tool for querying package info.
        # 'expat', # XML parsing library.
        # 'f2fs-tools', # Tools for managing F2FS filesystems.
        # 'faac', # AAC audio encoder.
        # 'faad2', # AAC audio decoder.
        # 'fail2ban', # Intrusion prevention tool for banning malicious IPs.
        # 'fakeroot', # Tool for simulating root privileges in builds.
        # 'fatresize', # Tool for resizing FAT filesystems.
        # 'fcitx5', # Input method framework for multilingual text input.
        # 'feh', # Lightweight image viewer and wallpaper setter.
        'ffmpeg', # Multimedia framework for encoding, decoding, and streaming.
        # 'ffmpeg4.4', # FFmpeg version 4.4 for legacy compatibility.
        'ffmpegthumbnailer', # Library for generating video thumbnails.
        # 'fftw', # Library for fast Fourier transforms.
        # 'file', # Utility for identifying file types.
        # 'filesystem', # Base filesystem structure for Arch Linux.
        # 'findutils', # GNU utilities for searching files (find, xargs).
        'firefox', # Mozilla Firefox web browser.
        # 'flac', # Free Lossless Audio Codec library.
        # 'flameshot-git', # Screenshot tool with annotation features.
        # 'flex', # Fast lexical analyzer generator.
        # 'fluidsynth', # Software synthesizer for MIDI playback.
        'fontconfig', # Library for configuring and managing fonts.
        'font-manager', # GUI for managing and previewing fonts.
        # 'freeglut', # Open-source OpenGL utility toolkit.
        # 'freetype2', # Font rendering library for TrueType fonts.
        # 'fribidi', # Library for handling bidirectional text (e.g., Arabic, Hebrew).
        # 'fsarchiver', # Tool for backing up and restoring filesystems.
        # 'fuse2', # Filesystem in Userspace (FUSE) for mounting virtual filesystems.
        # 'fuse3', # Updated version of FUSE with improved features.
        # 'fuse-common', # Common files for FUSE2 and FUSE3.
        # 'fuseiso', # Tool for mounting ISO files as filesystems.
        # 'fzf', # Command-line fuzzy finder for searching files and commands.
        # 'garcon', # XFCE menu library for desktop environments.
        # 'gawk', # GNU implementation of the AWK programming language.
        # 'gc', # Garbage collector library for C/C++.
        # 'gcc', # GNU Compiler Collection for C/C++.
        # 'gcc-libs', # Runtime libraries for GCC.
        # 'gconf', # Legacy GNOME configuration system.
        # 'gcr-4', # Library for cryptography and certificate handling (GNOME).
        # 'gdb', # GNU Debugger for debugging applications.
        # 'gdb-common', # Common files for GDB.
        # 'gdbm', # GNU database library for key-value storage.
        # 'gdk-pixbuf2', # Image loading and manipulation library.
        # 'gegl', # Graph-based image processing library (used by GIMP).
        # 'gendesk', # Tool for generating .desktop files for applications.
        # 'gettext', # Tools for internationalization and localization.
        # 'giflib', # Library for handling GIF images.
        # 'gimp', # GNU Image Manipulation Program for image editing.
        # 'git', # Version control system for tracking code changes.
        'git-lfs', # Git extension for versioning large files.
        # 'gksu', # Graphical frontend for running commands as root (deprecated).
        # 'glib2', # Core library for GNOME and GTK applications.
        # 'glibc', # GNU C Library for system calls and basic functions.
        # 'glibmm', # C++ bindings for GLib.
        # 'glibmm-2.68', # C++ bindings for GLib (version 2.68).
        # 'glib-networking', # Networking support for GLib (TLS, proxy, etc.).
        # 'glslang', # Shader compiler for OpenGL and Vulkan.
        # 'glu', # OpenGL utility library.
        # 'gmp', # Library for arbitrary-precision arithmetic.
        # 'gnome-bluetooth', # GNOME Bluetooth management tools and libraries.
        # 'gnome-themes-extra', # Extra themes for GNOME desktop environments.
        # 'gnulib-l10n', # Localization files for GNU libraries.
        # 'gnupg', # GNU Privacy Guard for encryption and signing.
        # 'gnutls', # TLS/SSL library for secure communications.
        # 'gobject-introspection-runtime', # Runtime for GObject introspection (language bindings).
        # 'gocryptfs', # Encrypted overlay filesystem written in Go.
        # 'gpart', # Partition recovery tool.
        # 'gparted', # GUI for managing disk partitions.
        # 'gperftools', # Performance profiling and memory allocation tools.
        # 'gpgme', # Library for interacting with GnuPG.
        # 'gpgmepp', # C++ bindings for GPGME.
        # 'gpm', # Mouse support for text-based environments.
        # 'gptfdisk', # Partitioning tool for GPT disks.
        # 'graphene', # Library for high-performance graphics abstractions.
        # 'graphite', # Font rendering library for complex scripts.
        # 'grep', # GNU utility for searching text patterns.
        # 'groff', # Document formatting system for man pages and more.
        # 'grub', # GRand Unified Bootloader for booting operating systems.
        # 'gsettings-desktop-schemas', # GSettings schemas for desktop settings.
        # 'gsettings-system-schemas', # GSettings schemas for system-wide settings.
        # 'gsm', # Library for GSM audio codec.
        # 'gspell', # Spell-checking library for GTK applications.
        # 'gssdp', # Library for SSDP (Simple Service Discovery Protocol).
        # 'gssproxy', # Proxy for GSSAPI security credentials.
        # 'gst-plugins-bad', # GStreamer plugins for less stable multimedia features.
        # 'gst-plugins-bad-libs', # Libraries for gst-plugins-bad.
        # 'gst-plugins-base', # Core GStreamer plugins for multimedia processing.
        # 'gst-plugins-base-libs', # Libraries for gst-plugins-base.
        # 'gst-plugins-good', # High-quality GStreamer plugins for multimedia.
        # 'gst-plugins-ugly', # GStreamer plugins for proprietary codecs.
        # 'gstreamer', # Multimedia framework for streaming and processing media.
        # 'gtest', # Google Test framework for C++ unit testing.
        # 'gtk2', # GTK+ 2.x toolkit for graphical user interfaces.
        # 'gtk3', # GTK+ 3.x toolkit for graphical user interfaces.
        # 'gtk4', # GTK 4.x toolkit for modern graphical interfaces.
        # 'gtk-layer-shell', # Library for creating Wayland shell components.
        # 'gtkmm3', # C++ bindings for GTK+ 3.
        # 'gtkmm-4.0', # C++ bindings for GTK 4.
        # 'gtksourceview3', # Text widget for syntax highlighting in GTK 3.
        # 'gtk-update-icon-cache', # Tool for updating GTK icon cache.
        # 'guile', # GNU Scheme interpreter and scripting language.
        # 'gupnp', # Library for UPnP (Universal Plug and Play) functionality.
        # 'gupnp-igd', # Library for UPnP Internet Gateway Device control.
        # 'gvfs', # Virtual filesystem for GNOME applications.
        # 'gzip', # GNU compression utility for .gz files.
        # 'harfbuzz', # Text shaping library for complex scripts.
        # 'harfbuzz-icu', # Harfbuzz with ICU support for internationalization.
        # 'hdparm', # Utility for configuring and monitoring hard drives.
        'hicolor-icon-theme', # Default fallback icon theme for freedesktop.
        # 'hidapi', # Library for communicating with HID devices (e.g., gamepads).
        # 'highway', # Performance-portable SIMD library for data processing.
        # 'htop', # Interactive system process viewer.
        # 'http-parser', # Lightweight HTTP message parser.
        # 'hunspell', # Spell-checking library with dictionary support.
        # 'hwdata', # Hardware identification data (PCI, USB, etc.).
        # 'hwinfo', # Hardware information and diagnostic tool.
        # 'hwloc', # Library for portable hardware locality information.
        # 'hw-probe', # Tool for probing and reporting hardware details.
        # 'hyperv', # Tools for Hyper-V virtual machine integration.
        # 'hyphen', # Library for text hyphenation.
        # 'i2c-tools', # Tools for interacting with I2C devices.
        # 'i3lock-color', # Customizable lock screen for i3 with color support.
        # 'i3lock-fancy-dualmonitors-git', # Fancy lock screen for i3 with dual-monitor support.
        # 'iana-etc', # IANA protocol and port number assignments.
        'ib-tws', # Interactive Brokers Trader Workstation for trading.
        'ib-tws-debug', # Debug version of Interactive Brokers Trader Workstation.
        # 'ibus', # Intelligent Input Bus for multilingual input methods.
        # 'icu', # International Components for Unicode library.
        # 'imagemagick', # Image manipulation library and tools.
        # 'imath', # Math library for 3D graphics and animation.
        # 'imlib2', # Image loading and rendering library.
        # 'inetutils', # GNU network utilities (ftp, telnet, etc.).
        # 'intel-ucode', # Microcode updates for Intel CPUs.
        'inxi', # System information tool for hardware and software details.
        # 'iproute2', # Advanced networking tools for Linux (ip, tc, etc.).
        # 'iptables', # Firewall and packet filtering tools.
        # 'iputils', # Network diagnostic tools (ping, traceroute, etc.).
        # 'iso-codes', # ISO standards for country, language, and currency codes.
        # 'iw', # Tool for configuring wireless network interfaces.
        # 'iwd', # Internet Wireless Daemon for wireless networking.
        # 'jansson', # C library for encoding and decoding JSON.
        # 'jasper', # Library for handling JPEG-2000 images.
        # 'java-environment-common', # Common files for Java development environments.
        # 'java-runtime-common', # Common files for Java runtime environments.
        # 'jbigkit', # Library for JBIG1 image compression.
        # 'jdk11-openjdk', # OpenJDK 11 Java Development Kit.
        # 'jemalloc', # Memory allocator for improved performance.
        # 'jfsutils', # Tools for managing JFS filesystems.
        # 'json-c', # C library for handling JSON data.
        # 'jsoncpp', # C++ library for JSON data manipulation.
        # 'json-glib', # Library for JSON handling in GLib-based applications.
        # 'kbd', # Keyboard mapping and font utilities.
        # 'keyutils', # Linux key management utilities.
        # 'kguiaddons5', # KDE framework for GUI utilities (Qt5).
        # 'kmod', # Kernel module management tools.
        # 'krb5', # Kerberos authentication protocol implementation.
        # 'lame', # MP3 audio encoder.
        # 'lapack', # Linear Algebra PACKage for scientific computing.
        'laptop-detect', # Tool to detect if the system is a laptop.
        # 'lbzip2', # Multithreaded bzip2 compression tool.
        # 'lcms2', # Little Color Management System for color profiles.
        # 'ldns', # DNS library for advanced DNS operations.
        # 'leancrypto', # Lightweight cryptographic library.
        # 'lensfun', # Library for correcting lens distortions in images.
        'less', # Terminal pager for viewing text files.
        # 'libabw', # Library for parsing AbiWord documents.
        # 'libadwaita-without-adwaita-git', # Adwaita library for GNOME without default theme.
        # 'libaio', # Asynchronous I/O library for Linux.
        # 'libappindicator-gtk3', # Library for system tray indicators (GTK3).
        # 'libarchive', # Library for handling various archive formats (tar, zip, etc.).
        # 'libass', # Library for rendering ASS/SSA subtitles.
        # 'libassuan', # IPC library for GnuPG and related tools.
        # 'libasyncns', # Asynchronous name resolution library.
        # 'libatasmart', # Library for querying SMART data from storage devices.
        # 'libatomic_ops', # Library for atomic memory operations.
        # 'libavc1394', # Library for controlling AVC-compliant FireWire devices.
        # 'libavif', # Library for AVIF image format encoding/decoding.
        # 'libavtp', # Library for Audio Video Transport Protocol.
        # 'libb2', # Blake2 cryptographic hash library.
        # 'libblockdev', # Library for manipulating block devices (partitions, LVM, etc.).
        # 'libblockdev-crypto', # Block device encryption plugin for libblockdev.
        # 'libblockdev-fs', # Filesystem plugin for libblockdev.
        # 'libblockdev-loop', # Loop device plugin for libblockdev.
        # 'libblockdev-mdraid', # MD RAID plugin for libblockdev.
        # 'libblockdev-nvme', # NVMe plugin for libblockdev.
        # 'libblockdev-part', # Partitioning plugin for libblockdev.
        # 'libblockdev-swap', # Swap plugin for libblockdev.
        # 'libbluray', # Library for Blu-ray disc playback.
        # 'libbpf', # Library for handling BPF (Berkeley Packet Filter) programs.
        # 'libbs2b', # Bauer stereophonic-to-binaural audio filter library.
        # 'libbsd', # BSD compatibility library for Linux.
        # 'libbytesize', # Library for handling human-readable byte sizes.
        # 'libcaca', # Library for colored ASCII art graphics.
        # 'libcanberra', # Library for desktop event sounds (e.g., login sounds).
        # 'libcap', # Library for POSIX capabilities (privilege management).
        # 'libcap-ng', # Simplified library for POSIX capabilities.
        # 'libcbor', # CBOR (Concise Binary Object Representation) library.
        # 'libcdio', # Library for CD-ROM and CD image access.
        # 'libcdio-paranoia', # CD audio extraction library with error correction.
        # 'libcdr', # Library for parsing CorelDRAW documents.
        # 'libcloudproviders', # Library for cloud provider integration.
        # 'libcmis', # Library for CMIS (Content Management Interoperability Services).
        # 'libcolord', # Library for color management and device profiles.
        # 'libconfig', # Library for parsing configuration files.
        # 'libcups', # CUPS (Common UNIX Printing System) client library.
        # 'libdaemon', # Lightweight library for creating daemons.
        # 'libdatrie', # Library for double-array trie data structure.
        # 'libdbusmenu-glib', # Library for D-Bus menu integration (GLib).
        # 'libdbusmenu-gtk3', # Library for D-Bus menu integration (GTK3).
        # 'libdc1394', # Library for controlling FireWire cameras.
        # 'libdca', # Library for decoding DTS audio.
        # 'libde265', # HEVC (H.265) video decoder library.
        # 'libdecor', # Library for Wayland client-side decorations.
        # 'libdeflate', # Fast compression/decompression library.
        # 'libdisplay-info', # Library for display information (EDID parsing).
        # 'libdovi', # Library for Dolby Vision metadata handling.
        # 'libdrm', # Direct Rendering Manager library for graphics hardware.
        # 'libdv', # Library for decoding DV (Digital Video) streams.
        # 'libdvbpsi', # Library for decoding MPEG TS and PSI tables.
        # 'libdvdnav', # Library for DVD navigation and playback.
        # 'libdvdread', # Library for reading DVD video discs.
        # 'libebml', # Library for handling EBML (Extensible Binary Meta Language).
        # 'libe-book', # Library for parsing e-book formats.
        # 'libebur128', # Library for loudness normalization (EBU R128 standard).
        # 'libedit', # Command-line editing library (alternative to readline).
        # 'libelf', # Library for handling ELF (Executable and Linkable Format) files.
        # 'libepoxy', # Library for handling OpenGL function pointers.
        # 'libepubgen', # Library for generating EPUB documents.
        # 'libetonyek', # Library for parsing Apple Keynote documents.
        # 'libev', # Event loop library for asynchronous operations.
        # 'libevdev', # Library for handling input devices (mice, keyboards, etc.).
        # 'libevent', # Event notification library for asynchronous I/O.
        # 'libexif', # Library for handling EXIF metadata in images.
        # 'libexttextcat', # Library for language identification in text.
        # 'libfdk-aac', # Fraunhofer FDK AAC codec library.
        # 'libffi', # Foreign function interface library for calling code across languages.
        # 'libfido2', # Library for FIDO2/WebAuthn authentication.
        # 'libfontenc', # Library for font encoding in X11.
        # 'libfreeaptx', # Library for aptX audio codec.
        # 'libfreehand', # Library for parsing FreeHand documents.
        # 'libgcrypt', # Cryptographic library for encryption and hashing.
        # 'libgexiv2', # Library for handling image metadata (EXIF, IPTC).
        # 'libgirepository', # Library for GObject introspection data.
        # 'libgit2', # Library for Git version control operations.
        # # 'libgksu', # Library for graphical privilege escalation (deprecated).
        # 'libglvnd', # Vendor-neutral OpenGL dispatch library.
        # 'libgme', # Library for video game music file emulation.
        # 'libgnomekbd', # GNOME keyboard layout library.
        # 'libgnome-keyring', # Legacy GNOME keyring library (deprecated).
        # 'libgpg-error', # Error handling library for GnuPG.
        # 'libgtop', # System monitoring library for CPU, memory, and disk usage.
        # 'libgudev', # Udev library for device information (GLib-based).
        # 'libgusb', # Library for USB device access.
        # 'libheif', # Library for HEIF (High Efficiency Image Format) handling.
        # 'libibus', # Library for IBus input method framework.
        # 'libice', # X11 Inter-Client Exchange library.
        # 'libidn', # Library for Internationalized Domain Names (IDN).
        # 'libidn2', # Updated library for Internationalized Domain Names.
        # 'libiec61883', # Library for controlling and communicating with IEEE 1394 (FireWire) devices, often used for audio/video capture.
        # 'libimagequant', # Library for image quantization (PNG optimization).
        # 'libimobiledevice', # Library for communicating with Apple iOS devices.
        # 'libimobiledevice-glue', # Helper library for libimobiledevice.
        # 'libinih', # Simple INI file parsing library.
        # 'libinput', # Library for handling input devices (touchpads, mice, etc.).
        # 'libinstpatch', # Library for handling soundfont and MIDI patches.
        # 'libisl', # Integer Set Library for polyhedral compilation.
        # 'libixion', # Library for spreadsheet formula parsing.
        # 'libjpeg6-turbo', # JPEG image compression library (version 6).
        # 'libjpeg-turbo', # JPEG image compression library (modern version).
        # 'libjxl', # JPEG XL image format library.
        # 'libksba', # Library for X.509 certificate and CMS handling.
        # 'liblangtag', # Library for handling language tags.
        # 'liblc3', # Library for LC3 (Low Complexity Communications Codec).
        # 'libldac', # Library for LDAC audio codec (Sony Bluetooth).
        # 'libldap', # OpenLDAP client library for LDAP operations.
        # 'liblqr', # Library for content-aware image resizing.
        # 'liblrdf', # Library for RDF metadata in audio applications.
        # 'libltc', # Library for Linear Timecode (LTC) handling.
        # 'libmad', # MPEG audio decoder library.
        # 'libmanette', # Library for game controller input.
        # 'libmatroska', # Library for handling Matroska (MKV) media containers.
        # 'libmaxminddb', # Library for GeoIP database access.
        # 'libmbim', # Library for Mobile Broadband Interface Model (MBIM).
        # 'libmd', # Message Digest library for cryptographic hashes.
        # 'libmfx', # Intel Media SDK for hardware-accelerated video.
        # 'libmicrodns', # Library for mDNS (multicast DNS) service discovery.
        # 'libmm-glib', # ModemManager library for mobile broadband devices.
        # 'libmng', # Library for MNG (Multiple-image Network Graphics) format.
        # 'libmnl', # Minimal netlink library for kernel communication.
        # 'libmodplug', # Library for playing MOD music files.
        # 'libmpc', # Library for multiple-precision arithmetic.
        # 'libmpcdec', # Musepack audio decoder library.
        # 'libmpeg2', # MPEG-2 video decoder library.
        # 'libmspack', # Library for Microsoft compression formats (CAB, CHM).
        # 'libmspub', # Library for parsing Microsoft Publisher documents.
        # 'libmwaw', # Library for parsing legacy Mac document formats.
        # 'libmypaint', # Library for digital painting brush engines.
        # 'libmysofa', # Library for HRTF (Head-Related Transfer Function) audio.
        # 'libndp', # Library for Neighbor Discovery Protocol (IPv6).
        # 'libnet', # Library for low-level network packet manipulation.
        # 'libnetfilter_conntrack', # Library for connection tracking in netfilter.
        # 'libnewt', # Library for text-based user interfaces.
        # 'libnfnetlink', # Netlink library for netfilter communication.
        # 'libnftnl', # Library for low-level netfilter NFTables interaction.
        # 'libnghttp2', # Library for HTTP/2 protocol support.
        # 'libnghttp3', # Library for HTTP/3 protocol support.
        # 'libngtcp2', # Library for QUIC protocol support.
        # 'libnice', # Library for ICE (Interactive Connectivity Establishment).
        # 'libnl', # Netlink library for kernel communication.
        # 'libnm', # NetworkManager library for network configuration.
        # 'libnma', # NetworkManager applet library for GUI integration.
        # 'libnma-common', # Common files for libnma.
        # 'libnotify', # Library for desktop notifications.
        # 'libnsl', # Network Services Library for NIS compatibility.
        # 'libnumbertext', # Library for converting numbers to text (e.g., spell-out).
        # 'libnvme', # Library for managing NVMe storage devices.
        # 'libodfgen', # Library for generating ODF (OpenDocument) files.
        # 'libogg', # Library for Ogg multimedia container format.
        # 'libomxil-bellagio', # OpenMAX IL implementation for multimedia processing.
        # 'libopenmpt', # Library for playing tracker music files (MOD, XM, etc.).
        # 'liborcus', # Library for parsing spreadsheet documents.
        # 'libp11-kit', # Library for PKCS#11 module management.
        # 'libpagemaker', # Library for parsing Adobe PageMaker documents.
        # 'libpcap', # Packet capture library for network traffic analysis.
        # 'libpciaccess', # Library for accessing PCI hardware.
        # 'libpgm', # Library for PGM (Pragmatic General Multicast) protocol.
        # 'libpipeline', # Library for manipulating pipelines of subprocesses.
        # 'libpipewire', # Library for PipeWire multimedia server.
        # 'libplacebo', # Library for video rendering and processing.
        # 'libplist', # Library for handling Apple Property List files.
        # 'libpng', # Library for handling PNG images.
        # 'libproxy', # Library for automatic proxy configuration.
        # 'libpsl', # Library for Public Suffix List handling (domains).
        # 'libpulse', # PulseAudio client library for audio handling.
        # 'libqalculate', # Library for advanced mathematical calculations.
        # 'libqmi', # Library for Qualcomm Mobile Interface (QMI) devices.
        # 'libqrtr-glib', # Library for Qualcomm Remote Procedure Call (QRTR).
        # 'libqxp', # Library for parsing QuarkXPress documents.
        # 'libraqm', # Library for complex text layout and shaping.
        # 'libraw', # Library for decoding RAW image files.
        # 'libraw1394', # Library for raw IEEE 1394 (FireWire) access.
        # 'libreoffice-fresh', # Full-featured office suite (latest version).
        # 'librevenge', # Library for document format conversion.
        # 'librsvg', # Library for rendering SVG images.
        # 'libsamplerate', # Library for audio sample rate conversion.
        # 'libsasl', # Simple Authentication and Security Layer library.
        # 'libseccomp', # Library for seccomp (secure computing) filtering.
        # 'libsecp256k1', # Cryptographic library for Bitcoin’s ECDSA.
        # 'libsecret', # Library for storing and retrieving passwords.
        # 'libshout', # Library for streaming audio to Icecast servers.
        # 'libsigc++', # C++ callback framework library.
        # 'libsigc++-3.0', # Updated version of libsigc++ for C++ callbacks.
        # 'libsm', # X11 Session Management library.
        # 'libsndfile', # Library for reading and writing audio files.
        # 'libsodium', # Cryptographic library for encryption and signatures.
        # 'libsoup3', # HTTP client/server library for GNOME (version 3).
        # 'libsoxr', # Library for high-quality audio resampling.
        # 'libspiro', # Library for Spiro curve rendering (font design).
        # 'libsrtp', # Library for Secure Real-time Transport Protocol.
        # 'libssh', # Library for SSH protocol implementation.
        # 'libssh2', # Library for SSH2 protocol implementation.
        # 'libstaroffice', # Library for parsing StarOffice documents.
        # 'libstemmer', # Library for stemming algorithms (text analysis).
        # 'libsysprof-capture', # Library for system profiling data capture.
        # 'libtar', # Library for manipulating tar archives.
        # 'libtasn1', # Library for ASN.1 parsing and handling.
        # 'libteam', # Library for network teaming (link aggregation).
        # 'libthai', # Library for Thai language text processing.
        # 'libtheora', # Library for Theora video codec.
        # 'libtiff', # Library for handling TIFF images.
        # 'libtirpc', # Transport Independent RPC library.
        # 'libtommath', # Library for multiple-precision integer arithmetic.
        # 'libtool', # Generic library support script for building software.
        # 'libunibreak', # Library for Unicode line and word breaking.
        # 'libunistring', # Library for Unicode string handling.
        # 'libunwind', # Library for stack unwinding (debugging).
        # 'libupnp', # Library for Universal Plug and Play (UPnP).
        # 'liburcu', # Userspace RCU (Read-Copy-Update) library for concurrency.
        # 'liburing', # Library for io_uring (Linux asynchronous I/O).
        # 'libusb', # Library for USB device access.
        # 'libusb-compat', # Compatibility layer for older libusb versions.
        # 'libusbmuxd', # Library for multiplexing connections to iOS devices.
        # 'libutempter', # Library for terminal session management.
        # 'libuv', # Cross-platform asynchronous I/O library.
        # 'libva', # Video Acceleration API for hardware video decoding.
        # 'libvdpau', # VDPAU (Video Decode and Presentation API) library.
        # 'libverto', # Event loop abstraction library.
        # 'libvisio', # Library for parsing Microsoft Visio documents.
        # 'libvlc', # VLC media player library for embedding.
        # 'libvorbis', # Library for Vorbis audio codec.
        # 'libvpl', # Intel Video Processing Library for hardware acceleration.
        # 'libvpx', # Library for VP8/VP9 video codecs.
        # 'libwacom', # Library for Wacom tablet configuration.
        # 'libwbclient', # Samba client library for Windows networking.
        # 'libwebp', # Library for WebP image format.
        # 'libwireplumber', # Library for PipeWire session management.
        # 'libwmf', # Library for handling WMF (Windows Metafile) images.
        # 'libwnck3', # Library for window navigation and task management (GTK3).
        # 'libwpd', # Library for parsing WordPerfect documents.
        # 'libwps', # Library for parsing Microsoft Works documents.
        # 'libx11', # X11 client-side library for X Window System.
        # 'libx86emu', # x86 emulation library.
        # 'libxau', # X11 Authorization Protocol library.
        # 'libxaw', # X11 Athena Widget library for GUI components.
        # 'libxcb', # X11 C Binding library for low-level X11 access.
        # 'libxcomposite', # X11 Composite extension library.
        # 'libxcrypt', # Modern library for password hashing.
        # 'libxcrypt-compat', # Compatibility layer for older crypt libraries.
        # 'libxcursor', # X11 cursor management library.
        # 'libxcvt', # Library for X11 CVT (Coordinated Video Timing).
        # 'libxdamage', # X11 Damage extension library.
        # 'libxdg-basedir', # Library for XDG Base Directory specification.
        # 'libxdmcp', # X11 Display Manager Control Protocol library.
        # 'libxext', # X11 miscellaneous extensions library.
        # 'libxfce4ui', # XFCE user interface library.
        # 'libxfce4util', # XFCE utility library.
        # 'libxfce4windowing', # XFCE windowing library for Wayland/X11.
        # 'libxfixes', # X11 Fixes extension library.
        # 'libxfont2', # X11 font handling library.
        # 'libxft', # X11 FreeType font rendering library.
        # 'libxi', # X11 Input extension library.
        # 'libxinerama', # X11 Xinerama extension library for multi-monitor.
        # 'libxkbcommon', # Keyboard handling library for X11 and Wayland.
        # 'libxkbcommon-x11', # X11 support for libxkbcommon.
        # 'libxkbfile', # X11 keyboard file manipulation library.
        # 'libxklavier', # Library for keyboard layout management.
        # 'libxml2', # XML parsing and manipulation library.
        # 'libxml2-legacy', # Legacy version of libxml2 for compatibility.
        # 'libxmlb', # Library for handling XML binary data.
        # 'libxmu', # X11 miscellaneous utilities library.
        # 'libxpm', # X11 Pixmap library for handling XPM images.
        # 'libxrandr', # X11 RandR (Resize and Rotate) extension library.
        # 'libxrender', # X11 Render extension library.
        # 'libxres', # X11 Resource extension library.
        # 'libxshmfence', # X11 shared memory fence library.
        # 'libxslt', # XSLT transformation library for XML.
        # 'libxss', # X11 Screen Saver extension library.
        # 'libxt', # X11 Toolkit Intrinsics library.
        # 'libxtst', # X11 Testing extension library.
        # 'libxv', # X11 Video extension library.
        # 'libxxf86vm', # X11 XF86VidMode extension library.
        # 'libyaml', # YAML parsing and emission library.
        # 'libyuv', # Library for YUV image format conversion.
        # 'libzmf', # Library for parsing Zoner Callisto/Draw documents.
        # 'licenses', # Common open-source license files.
        # 'lilv', # Library for LV2 audio plugin hosting.
        # 'linux', # Latest Linux kernel and modules.
        # 'linux-api-headers', # Kernel headers for user-space API development.
        # 'linux-atm', # Drivers and tools for ATM networking.
        # 'linux-firmware', # Firmware files for Linux hardware support.
        # 'linux-firmware-bnx2x', # Firmware for Broadcom NetXtreme II devices.
        # 'linux-firmware-liquidio', # Firmware for Cavium LiquidIO network adapters.
        # 'linux-firmware-marvell', # Firmware for Marvell wireless devices.
        # 'linux-firmware-mellanox', # Firmware for Mellanox network adapters.
        # 'linux-firmware-nfp', # Firmware for Netronome Flow Processors.
        # 'linux-firmware-qlogic', # Firmware for QLogic devices.
        # 'linux-firmware-whence', # Metadata for Linux firmware files.
        # 'linux-headers', # Headers for the latest Linux kernel.
        # 'linux-lts', # Long-term support Linux kernel and modules.
        # 'linux-lts-headers', # Headers for the LTS Linux kernel.
        # 'llhttp', # HTTP parser library written in C.
        # 'llvm-libs', # Runtime libraries for LLVM compiler infrastructure.
        # 'lmdb', # Lightning Memory-Mapped Database library.
        # 'lm_sensors', # Hardware monitoring tools (temperature, voltage, etc.).
        # 'logrotate', # Utility for rotating and managing log files.
        # 'lohit-fonts', # Font family for Indian languages.
        # 'lpsolve', # Linear programming solver library.
        # 'lrzip', # Compression tool for large files with long-distance redundancy.
        'lsb-release', # Utility for displaying LSB (Linux Standard Base) information.
        # 'lshw', # Hardware lister for system components.
        # 'l-smash', # Library for MP4/MOV container handling.
        # 'lsof', # Lists open files and their associated processes.
        # 'lsscsi', # Lists SCSI devices and their attributes.
        # 'lua53', # Lua 5.3 scripting language interpreter.
        # 'lua53-lgi', # Lua bindings for GObject-based libraries.
        # 'lua', # Latest Lua scripting language interpreter.
        # 'luajit', # Just-In-Time compiler for Lua scripting.
        # 'lv2', # Audio plugin standard for effects and instruments.
        # 'lvm2', # Logical Volume Manager for managing disk partitions.
        'lxappearance', # GUI for customizing GTK themes and appearance.
        # 'lz4', # Fast compression library.
        # 'lzo', # LZO compression library for real-time compression.
        # 'lzop', # Command-line tool for LZO compression.
        # 'm4', # GNU macro processor for text processing.
        # 'mailcap', # MIME type configuration for file handling.
        # 'make', # GNU utility for building software from source.
        # 'man-db', # Man page viewer and database.
        # 'man-pages', # Linux manual pages for system calls and commands.
        # 'md4c', # Markdown parsing library.
        # 'mdadm', # Tool for managing Linux software RAID arrays.
        # 'memtest86+', # Memory testing tool for diagnosing RAM issues.
        # 'memtest86+-efi', # EFI version of Memtest86+ for UEFI systems.
        # 'mesa', # Open-source OpenGL, Vulkan, and OpenCL implementation.
        # 'micro', # Modern, intuitive terminal-based text editor.
        # 'minizip', # Library for handling ZIP archives.
        # 'mjpegtools', # Tools for MJPEG video processing.
        # 'mkinitcpio', # Tool for generating initial ramdisk (initramfs).
        # 'mkinitcpio-busybox', # Minimal BusyBox for mkinitcpio initramfs.
        # 'mkinitcpio-firmware', # Firmware files for mkinitcpio initramfs.
        # 'mkinitcpio-nfs-utils', # NFS utilities for mkinitcpio initramfs.
        # 'mkinitcpio-openswap', # Swap support for mkinitcpio initramfs.
        # 'mobile-broadband-provider-info', # Database for mobile broadband settings.
        # 'modemmanager', # Daemon for managing mobile broadband devices.
        # 'most', # Pager for viewing text files (alternative to less).
        # 'mpdecimal', # Library for decimal arithmetic.
        # 'mpfr', # Library for multiple-precision floating-point arithmetic.
        # 'mpg123', # Command-line MP3 audio player.
        # 'mtdev', # Library for multitouch device events.
        # 'mtools', # Tools for manipulating MS-DOS filesystems.
        # 'mycrypto-bin', # Desktop cryptocurrency wallet (binary).
        # 'mycrypto-bin-debug', # Debug version of MyCrypto wallet.
        # 'mypaint-brushes1', # Brush set for MyPaint digital painting (version 1).
        # 'nano', # Simple terminal-based text editor.
        # 'nbd', # Network Block Device client and server.
        'ncdu', # Disk usage analyzer with a curses interface.
        # 'ncurses', # Library for text-based user interfaces.
        # 'ndisc6', # IPv6 Neighbor Discovery tools.
        # 'neon', # HTTP and WebDAV client library.
        # 'nettle', # Cryptographic library for low-level crypto operations.
        # 'net-tools', # Legacy networking tools (ifconfig, netstat, etc.).
        'networkmanager', # Network connection manager for Wi-Fi, Ethernet, etc.
        'network-manager-applet', # System tray applet for NetworkManager.
        'networkmanager-openconnect', # OpenConnect VPN plugin for NetworkManager.
        'networkmanager-openvpn', # OpenVPN plugin for NetworkManager.
        'networkmanager-pptp', # PPTP VPN plugin for NetworkManager.
        'networkmanager-qt5', # Qt5 bindings for NetworkManager.
        'networkmanager-vpnc', # VPNC plugin for NetworkManager.
        # 'nfsidmap', # NFSv4 ID mapping library.
        # 'nfs-utils', # Tools for Network File System (NFS).
        # 'nftables', # Netfilter-based firewall and packet filtering tool.
        # 'nilfs-utils', # Tools for managing NILFS2 filesystems.
        # 'ninja', # Build system optimized for speed.
        'nm-connection-editor', # GUI for editing NetworkManager connections.
        # 'node-gyp', # Node.js native addon build tool.
        # 'nodejs', # JavaScript runtime environment.
        # 'nodejs-nopt', # Node.js option parsing library.
        # 'nomacs', # Lightweight image viewer with editing capabilities.
        'nordvpn-bin', # NordVPN client for secure VPN connections.
        # 'noto-fonts', # Google’s Noto font family for global language support.
        # 'noto-fonts-emoji', # Emoji fonts from Google’s Noto family.
        # 'npm', # Node.js package manager for JavaScript libraries.
        # 'npth', # Non-preemptive thread library for GnuPG.
        # 'nspr', # Netscape Portable Runtime for platform abstraction.
        # 'nss', # Network Security Services for SSL/TLS and cryptography.
        # 'ntfs-3g', # NTFS filesystem driver with read/write support.
        # 'ntp', # Network Time Protocol client and server.
        # 'numlockx', # Tool for enabling NumLock on startup.
        # 'nvidia-390xx-utils', # Legacy NVIDIA drivers (version 390).
        # 'nvme-cli', # Tools for managing NVMe storage devices.
        # 'oath-toolkit', # Tools for OATH (TOTP/HOTP) authentication.
        # 'ocl-icd', # OpenCL ICD (Installable Client Driver) loader.
        # 'onetbb', # Intel oneAPI Threading Building Blocks for parallelism.
        # 'oniguruma', # Regular expression library.
        # 'openal', # Cross-platform 3D audio library.
        # 'openconnect', # VPN client for Cisco AnyConnect and other protocols.
        # 'opencore-amr', # AMR audio codec library.
        # 'opencv', # Computer vision and machine learning library.
        # 'openexr', # Library for handling OpenEXR high-dynamic-range images.
        # 'openh264', # H.264 video codec library.
        # 'open-iscsi', # Tools for iSCSI storage networking.
        # 'open-isns', # iSNS (Internet Storage Name Service) library and tools.
        # 'openjpeg2', # JPEG 2000 image compression library.
        'openssh', # Secure Shell (SSH) client and server.
        # 'openssl-1.1', # Legacy OpenSSL 1.1 for TLS/SSL (compatibility).
        # 'openssl', # OpenSSL library for TLS/SSL and cryptography.
        # 'openvpn', # Open-source VPN client and server.
        # 'opus', # Opus audio codec library.
        # 'orc', # Optimized Inner Loop Runtime Compiler for multimedia.
        # 'os-prober', # Tool for detecting other operating systems for GRUB.
        # 'otf-libertinus', # Libertinus font family ( serif, sans, and math).
        # 'p11-kit', # Library for managing PKCS#11 modules.
        # 'pacman', # Arch Linux package manager.
        # 'pacman-contrib', # Additional tools for pacman (e.g., paccache).
        # 'pacman-mirrorlist', # Default mirrorlist for Arch Linux repositories.
        # 'pahole', # Tool for inspecting and analyzing ELF debug info.
        # 'pam', # Pluggable Authentication Modules for authentication.
        # 'pambase', # Base PAM configuration for Arch Linux.
        # 'pango', # Library for text layout and rendering.
        # 'pangomm', # C++ bindings for Pango.
        # 'pangomm-2.48', # C++ bindings for Pango (version 2.48).
        # 'partclone', # Tool for cloning and restoring disk partitions.
        # 'parted', # Disk partitioning and management tool.
        # 'partimage', # Disk partition imaging tool.
        # 'paru-git', # AUR helper for managing Arch User Repository packages.
        # 'patch', # Tool for applying patch files to source code.
        'pavucontrol', # PulseAudio volume control GUI.
        # 'pbzip2', # Parallel bzip2 compression tool.
        # 'pciutils', # Tools for listing and managing PCI devices.
        # 'pcre2', # Perl-Compatible Regular Expressions library (version 2).
        # 'pcre', # Perl-Compatible Regular Expressions library (version 1).
        # 'pcsclite', # Middleware for smart card communication.
        # 'perl', # Perl programming language interpreter.
        # 'perl-algorithm-diff', # Perl module for computing differences between files.
        # 'perl-class-method-modifiers', # Perl module for method modifiers.
        # 'perl-clone', # Perl module for deep cloning of data structures.
        # 'perl-data-optlist', # Perl module for handling option lists.
        # 'perl-devel-globaldestruction', # Perl module for global destruction utilities.
        # 'perl-encode-locale', # Perl module for locale encoding support.
        # 'perl-error', # Perl module for error handling.
        # 'perl-file-listing', # Perl module for parsing directory listings.
        # 'perl-html-parser', # Perl module for parsing HTML documents.
        # 'perl-html-tagset', # Perl module for HTML tag definitions.
        # 'perl-http-cookiejar', # Perl module for handling HTTP cookies.
        # 'perl-http-cookies', # Perl module for managing HTTP cookies.
        # 'perl-http-daemon', # Perl module for simple HTTP server.
        # 'perl-http-date', # Perl module for handling HTTP date formats.
        # 'perl-http-message', # Perl module for HTTP message objects.
        # 'perl-http-negotiate', # Perl module for HTTP content negotiation.
        # 'perl-import-into', # Perl module for importing packages into namespaces.
        # 'perl-io-html', # Perl module for parsing HTML input/output.
        # 'perl-libwww', # Perl module for WWW client/server operations.
        # 'perl-lwp-mediatypes', # Perl module for handling media types in LWP.
        # 'perl-mailtools', # Perl module for email-related utilities.
        # 'perl-module-runtime', # Perl module for runtime module handling.
        # 'perl-moo', # Perl module for object-oriented programming.
        # 'perl-net-http', # Perl module for low-level HTTP connections.
        # 'perl-parallel-forkmanager', # Perl module for managing parallel processes.
        # 'perl-params-util', # Perl module for parameter validation utilities.
        # 'perl-regexp-common', # Perl module for common regular expressions.
        # 'perl-role-tiny', # Perl module for lightweight role-based OOP.
        # 'perl-sub-exporter', # Perl module for exporting subroutines.
        # 'perl-sub-exporter-progressive', # Perl module for progressive sub exporting.
        # 'perl-sub-install', # Perl module for installing subroutines.
        # 'perl-sub-quote', # Perl module for efficient string quoting.
        # 'perl-timedate', # Perl module for date and time manipulation.
        # 'perl-try-tiny', # Perl module for lightweight exception handling.
        # 'perl-uri', # Perl module for handling URIs.
        # 'perl-www-robotrules', # Perl module for robots.txt parsing.
        # 'perl-xml-parser', # Perl module for parsing XML documents.
        # 'perl-xml-writer', # Perl module for writing XML documents.
        'picom', # Lightweight compositor for X11 with animations and effects.
        # 'pigz', # Parallel gzip compression tool.
        # 'pinentry', # PIN or passphrase entry dialog for GnuPG.
        'pipewire', # Multimedia server for audio and video handling.
        'pipewire-alsa', # ALSA compatibility for PipeWire.
        'pipewire-audio', # Audio processing components for PipeWire.
        'pipewire-jack', # JACK compatibility for PipeWire.
        'pipewire-pulse', # PulseAudio compatibility for PipeWire.
        'pipewire-session-manager', # Session manager for PipeWire.
        'pipewire-zeroconf', # Zeroconf (mDNS) support for PipeWire.
        # 'pixman', # Low-level pixel manipulation library.
        # 'pixz', # Parallel XZ compression tool.
        # 'pkcs11-helper', # Library for PKCS#11 cryptographic token support.
        # 'pkgconf', # Package compiler and linker metadata tool.
        # 'pkgfile', # Tool for searching files in installed packages.
        # 'playerctl', # Command-line tool for controlling media players.
        # 'plocate', # Fast file locator (updated locate implementation).
        'polkit', # Framework for managing system privileges.
        'polkit-gnome', # GNOME authentication agent for Polkit.
        # 'poppler', # PDF rendering library.
        # 'poppler-data', # Encoding data for Poppler PDF library.
        # 'poppler-glib', # GLib bindings for Poppler.
        # 'popt', # Command-line option parsing library.
        # 'portaudio', # Cross-platform audio I/O library.
        'postgresql', # PostgreSQL database server.
        'postgresql-libs', # Libraries for PostgreSQL client applications.
        'postgresql-old-upgrade', # Tools for upgrading older PostgreSQL databases.
        'powertop', # Power consumption monitoring and optimization tool.
        # 'ppp', # Point-to-Point Protocol for dial-up and VPN connections.
        # 'pptpclient', # PPTP VPN client.
        # 'procps-ng', # System and process monitoring utilities (ps, top, etc.).
        # 'protobuf', # Protocol Buffers for data serialization.
        # 'psmisc', # Miscellaneous process utilities (killall, fuser, etc.).
        # 'pv', # Pipe viewer for monitoring data through pipelines.
        # 'pwgen', # Password generator for secure passwords.
        # 'pyenv', # Python version management tool.
        # 'python310', # Python 3.10 interpreter.
        # 'python310-debug', # Debug version of Python 3.10.
        # 'python312', # Python 3.12 interpreter.
        # 'python312-debug', # Debug version of Python 3.12.
        # 'python', # Latest Python interpreter (currently 3.x).
        # 'python38', # Python 3.8 interpreter.
        # 'python38-debug', # Debug version of Python 3.8.
        # 'python-aiohappyeyeballs', # Python library for Happy Eyeballs algorithm (networking).
        # 'python-aiohttp', # Asynchronous HTTP client/server framework for Python.
        # 'python-aiohttp-socks', # SOCKS proxy support for aiohttp.
        # 'python-aiorpcx', # Asynchronous RPC library for Python.
        # 'python-aiosignal', # Signal handling for Python async applications.
        # 'python-attrs', # Library for attribute-based classes in Python.
        # 'python-autocommand', # Library for creating CLI applications in Python.
        # 'python-cairo', # Python bindings for the Cairo graphics library.
        # 'python-certifi', # Python library for SSL certificate verification.
        # 'python-cffi', # Foreign function interface for Python.
        # 'python-charset-normalizer', # Library for detecting text encoding.
        # 'python-colorama', # Cross-platform colored terminal output for Python.
        # 'python-cryptography', # Cryptographic library for Python.
        # 'python-dateutil', # Date and time utilities for Python.
        # 'python-dbus', # Python bindings for D-Bus inter-process communication.
        # 'python-distro', # Library for detecting Linux distribution details.
        # 'python-dnspython', # DNS toolkit for Python.
        # 'python-docopt', # Command-line argument parser for Python.
        # 'python-docutils', # Python library for processing plaintext documentation.
        # 'python-execnet', # Distributed Python execution framework.
        # 'python-filelock', # Platform-independent file locking for Python.
        # 'python-frozenlist', # Immutable list implementation for Python.
        # 'python-gobject', # Python bindings for GObject (GLib/GTK).
        # 'python-helpdev', # Hardware information library for Python.
        # 'python-idna', # Library for Internationalized Domain Names in Python.
        # 'python-iniconfig', # Simple INI file parsing for Python.
        # 'python-jaraco.collections', # Collection utilities for Python.
        # 'python-jaraco.context', # Context manager utilities for Python.
        # 'python-jaraco.functools', # Functional programming utilities for Python.
        # 'python-jaraco.text', # Text manipulation utilities for Python.
        # 'python-jmespath', # JSON query language for Python.
        # 'python-jsonpatch', # Library for applying JSON patches.
        # 'python-jsonpointer', # Library for JSON Pointer resolution.
        # 'python-jsonschema', # JSON schema validation for Python.
        # 'python-jsonschema-specifications', # JSON schema specification files.
        # 'python-keyutils', # Python bindings for Linux keyring utilities.
        # 'python-more-itertools', # Iterator utilities for Python.
        # 'python-multidict', # Multidict implementation for Python (HTTP headers).
        # 'python-numpy', # Numerical computing library for Python.
        # 'python-packaging', # Core utilities for Python packaging.
        # 'python-pillow', # Python Imaging Library (PIL) for image processing.
        # 'python-pip', # Package installer for Python.
        # 'python-platformdirs', # Platform-specific directory handling for Python.
        # 'python-pluggy', # Plugin and hook system for Python.
        # 'python-prompt_toolkit', # Library for building interactive CLI apps in Python.
        # 'python-propcache', # Property caching decorator for Python.
        # 'python-protobuf', # Python bindings for Protocol Buffers.
        # 'python-psutil', # System monitoring library for Python.
        # 'python-pyaes', # Pure-Python AES encryption library.
        # 'python-pycparser', # C parser for Python.
        # 'python-pygments', # Syntax highlighting library for Python.
        # 'python-pyinotify', # File system event monitoring for Python.
        # 'python-pyqt5', # Python bindings for Qt5.
        # 'python-pyqt5-sip', # SIP bindings for PyQt5.
        # 'python-pytest', # Testing framework for Python.
        # 'python-pytest-xdist', # Parallel test execution for pytest.
        # 'python-python-socks', # SOCKS proxy client for Python.
        # 'python-qdarkstyle', # Dark theme for PyQt applications.
        # 'python-qrcode', # QR code generation library for Python.
        # 'python-qtpy', # Abstraction layer for PyQt/PySide in Python.
        # 'python-referencing', # JSON referencing library for Python.
        # 'python-requests', # HTTP request library for Python.
        # 'python-rpds-py', # Rust-based data structures for Python.
        # 'python-ruamel-yaml', # YAML parser/emitter for Python.
        # 'python-ruamel.yaml.clib', # C-based YAML library for Python.
        # 'python-setproctitle', # Library for setting process titles in Python.
        # 'python-setuptools', # Tools for packaging Python projects.
        # 'python-six', # Compatibility library for Python 2/3 transitions.
        # 'python-systemd', # Python bindings for systemd.
        # 'python-urllib3', # HTTP client library for Python.
        # 'python-wcwidth', # Library for calculating text width in terminals.
        # 'python-websockets', # WebSocket implementation for Python.
        # 'python-wheel', # Wheel packaging format for Python.
        # 'python-yaml', # YAML parsing library for Python.
        # 'python-yarl', # URL manipulation library for Python.
        # 'qrencode', # Library and tool for generating QR codes.
        # 'qt5-base', # Core Qt5 framework for GUI applications.
        # 'qt5ct', # Tool for customizing Qt5 applications.
        # 'qt5-declarative', # Qt5 QML and JavaScript engine.
        # 'qt5-graphicaleffects', # Graphical effects for Qt5 QML applications.
        # 'qt5-location', # Qt5 location and geolocation services.
        # 'qt5-quickcontrols2', # Qt5 controls for QML-based interfaces.
        # 'qt5-quickcontrols', # Legacy Qt5 controls for QML.
        # 'qt5-remoteobjects', # Qt5 library for remote object communication.
        # 'qt5-svg', # Qt5 library for rendering SVG images.
        # 'qt5-translations', # Translations for Qt5 applications.
        # 'qt5-virtualkeyboard', # Virtual keyboard for Qt5 applications.
        # 'qt5-wayland', # Qt5 support for Wayland compositors.
        # 'qt5-webchannel', # Qt5 library for WebSocket-based communication.
        # 'qt5-webengine', # Qt5 web engine based on Chromium.
        # 'qt5-x11extras', # Qt5 utilities for X11 integration.
        # 'qt6-5compat', # Compatibility module for Qt6 and Qt5.
        # 'qt6-base', # Core Qt6 framework for GUI applications.
        # 'qt6-declarative', # Qt6 QML and JavaScript engine.
        # 'qt6-shadertools', # Qt6 tools for shader processing.
        # 'qt6-svg', # Qt6 library for rendering SVG images.
        # 'qt6-translations', # Translations for Qt6 applications.
        # 'quazip-qt6', # Qt6 library for handling ZIP archives.
        # 'raptor', # RDF syntax library for parsing and serializing RDF.
        # 'rasqal', # RDF query library for SPARQL and RDQL.
        'rate-mirrors-bin', # Tool for ranking and selecting Arch Linux mirrors.
        # 'rav1e', # AV1 video encoder written in Rust.
        # 'readline', # Library for command-line editing.
        # 'rebornos-keyring', # GPG keyring for RebornOS repositories.
        # 'rebornos-mirrorlist', # Mirrorlist for RebornOS repositories.
        # 'redland', # Library for RDF storage and querying.
        # 'refind', # UEFI boot manager with a graphical interface.
        # 'reflector', # Tool for retrieving and ranking Arch Linux mirrors.
        # 'rhash', # Utility for computing and verifying hash sums.
        # 'ripgrep', # Fast, regex-based file search tool.
        'rofi', # Application launcher and window switcher.
        'rofi-calc', # Calculator plugin for Rofi.
        # 'rpcbind', # RPC portmapper for NFS and other RPC services.
        # 'rp-pppoe', # PPPoE client for broadband connections.
        'rsync', # File synchronization and transfer tool.
        # 'rtl8821cu-morrownr-dkms-git', # Driver for Realtek RTL8821CU Wi-Fi chip.
        # 'rtmpdump', # Tool for downloading and streaming RTMP media.
        # 'rubberband', # Library for audio time-stretching and pitch-shifting.
        # 'runc', # CLI tool for running containers (OCI runtime).
        # 'run-parts', # Utility for running scripts in a directory.
        # 'sardi-icons', # Customizable icon theme for Linux desktops.
        # 'sbc', # Sub-band codec library for Bluetooth audio.
        # 'screen', # Terminal multiplexer for session management.
        # 'scrot', # Command-line screenshot tool.
        # 'sddm', # Simple Desktop Display Manager for login screens.
        # 'sdl2-compat', # Compatibility layer for SDL 2 applications.
        # 'sdl2-debug', # Debug version of SDL 2 library.
        # 'sdl3', # Simple DirectMedia Layer for multimedia applications.
        # 'sdparm', # Utility for configuring SCSI device parameters.
        # 'sed', # Stream editor for text manipulation.
        # 'semver', # Semantic versioning parser and library.
        # 'serd', # Lightweight RDF serialization library.
        # 'sg3_utils', # Utilities for SCSI device management.
        # 'shaderc', # Library for compiling GLSL/HLSL shaders.
        # 'shadow', # Tools for managing user accounts and passwords.
        # 'shared-mime-info', # Database for MIME type associations.
        'signal-desktop', # Secure messaging application (Signal).
        # 'simdjson', # High-performance JSON parsing library.
        'slack-desktop', # Slack client for team communication.
        # 'slang', # Library for text-based user interfaces (S-Lang).
        # 'smartmontools', # Tools for monitoring SMART data on storage devices.
        # 'snappy', # Fast compression/decompression library.
        # 'sof-firmware', # Firmware for Sound Open Firmware (audio).
        # 'sofirem-git', # Tool for managing Sound Open Firmware.
        # 'sord', # Lightweight RDF storage and querying library.
        # 'sound-theme-freedesktop', # Freedesktop sound theme for desktop events.
        # 'soundtouch', # Library for audio pitch and tempo manipulation.
        # 'source-highlight', # Syntax highlighting for source code.
        # 'spandsp', # Library for telephony signal processing (fax, modem).
        # 'sparrow-wallet', # Bitcoin wallet focused on privacy and security.
        # 'sparrow-wallet-debug', # Debug version of Sparrow Wallet.
        # 'speex', # Audio codec optimized for speech.
        # 'speexdsp', # DSP library for Speex audio processing.
        # 'spirv-tools', # Tools for SPIR-V shader manipulation (Vulkan/OpenGL).
        # 'sqlite', # Lightweight SQL database engine.
        # 'squashfs-tools', # Tools for creating and managing SquashFS filesystems.
        # 'sratom', # Library for serializing LV2 atoms to RDF.
        # 'srt', # Secure Reliable Transport protocol library for streaming.
        'sshfs', # Filesystem for mounting remote directories over SSH.
        'sshpass', # Non-interactive SSH password authentication tool.
        'sshuttle', # Transparent proxy server for VPN-like SSH tunneling.
        # 'startup-notification', # Library for application startup feedback.
        # 'stoken', # Software token for two-factor authentication.
        # 'sudo', # Tool for running commands with elevated privileges.
        # 'suitesparse', # Suite of sparse matrix algorithms.
        # 'surfn-icons-git', # Custom icon theme for Linux desktops.
        # 'svt-av1', # Scalable Video Technology AV1 encoder.
        # 'svt-hevc', # Scalable Video Technology HEVC (H.265) encoder.
        'syncthing', # File synchronization tool for decentralized syncing.
        # 'sysfsutils', # Utilities for interacting with sysfs.
        # 'syslinux', # Lightweight bootloader for Linux systems.
        # 'systemd', # System and service manager for Linux.
        # 'systemd-libs', # Libraries for systemd.
        # 'systemd-resolvconf', # Systemd-based resolvconf for DNS resolution.
        # 'systemd-sysvcompat', # SysV init compatibility for systemd.
        # 'taglib', # Library for reading and editing audio file metadata.
        # 'talloc', # Hierarchical memory allocation library.
        # 'tar', # GNU utility for creating and extracting tar archives.
        # 'tcl', # Tcl scripting language interpreter.
        # 'tcpdump', # Network packet analyzer.
        # 'tdb', # Trivial Database library for key-value storage.
        # 'terminus-font', # Monospaced bitmap font for terminals.
        # 'testdisk', # Data recovery and partition repair tool.
        # 'texinfo', # GNU documentation system for creating manuals.
        # 'the_silver_searcher', # Fast code-searching tool (ag).
        # 'thin-provisioning-tools', # Tools for managing thin-provisioned LVM volumes.
        'thunar', # File manager for the XFCE desktop.
        'thunar-archive-plugin', # Archive support for Thunar file manager.
        'thunar-volman', # Volume management plugin for Thunar.
        'thunderbird', # Mozilla Thunderbird email client.
        # 'tinysparql', # Lightweight SPARQL RDF query library.
        # 'tk', # Tcl/Tk graphical toolkit for GUI applications.
        'tlp', # Power management tool for laptops.
        'tmux', # Terminal multiplexer for session management.
        # 'tpm2-tss', # Trusted Platform Module 2.0 software stack.
        # 'tslib', # Touchscreen library for embedded systems.
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
        'tumbler', # Thumbnail service for XFCE file manager (Thunar).
        # 'twolame', # MPEG Audio Layer 2 (MP2) encoder.
        # 'tzdata', # Time zone and daylight saving time data.
        # 'udftools', # Tools for managing UDF filesystems (DVDs, Blu-rays).
        'udiskie', # Automount utility for removable drives.
        'udisks2', # Disk management service for mounting and querying drives.
        'ufw', # Uncomplicated Firewall for managing iptables rules.
        'unrar', # Tool for extracting RAR archives.
        'unzip', # Tool for extracting ZIP archives.
        # 'upd72020x-fw', # Firmware for Renesas uPD72020x USB controllers.
        'upower', # Power management and battery monitoring daemon.
        # 'usb_modeswitch', # Tool for switching USB device modes (e.g., modems).
        # 'usbmuxd', # Daemon for multiplexing iOS device connections.
        # 'usbutils', # Utilities for listing and managing USB devices.
        # 'util-linux', # Essential Linux utilities (mount, fdisk, etc.).
        # 'util-linux-libs', # Libraries for util-linux utilities.
        # 'v4l-utils-git', # Video4Linux utilities for webcams and TV tuners.
        # 'vapoursynth', # Video processing framework for scripting.
        'ventoy-bin', # Tool for creating bootable USB drives with multiple ISOs.
        'veracrypt', # Disk encryption software with cross-platform support.
        # 'verdict', # C++ library for handling assertions and errors.
        # 'vicious', # Modular widget library for Awesome WM.
        # 'vid.stab', # Video stabilization library.
        'vim', # Highly configurable text editor.
        # 'vimix-cursors', # Modern cursor theme for Linux desktops.
        # 'vim-runtime', # Runtime files for Vim editor.
        'visual-studio-code-bin', # Microsoft’s Visual Studio Code editor (binary).
        'vlc', # VLC media player for multimedia playback.
        # 'vmaf', # Video Multi-Method Assessment Fusion for video quality.
        'volumeicon', # System tray volume control for ALSA/PulseAudio.
        # 'volume_key', # Library for managing encrypted volume keys.
        # 'vpnc', # VPN client for Cisco VPN3000 concentrators.
        # 'vte3', # Terminal emulator widget for GTK3 applications.
        # 'vte-common', # Common files for VTE terminal emulator.
        # 'vulkan-headers', # Headers for Vulkan API development.
        # 'vulkan-icd-loader', # Vulkan Installable Client Driver loader.
        # 'wasabi-wallet-bin', # Privacy-focused Bitcoin wallet.
        # 'wavpack', # Audio compression format and library.
        # 'wayland', # Wayland display server protocol.
        # 'wayland-protocols', # Wayland protocol definitions.
        # 'wd719x-firmware', # Firmware for Western Digital WD719x SCSI controllers.
        # 'webkit2gtk-4.1', # WebKit-based web engine for GTK (version 4.1).
        # 'webkitgtk-6.0', # WebKit-based web engine for GTK (version 6.0).
        # 'webrtc-audio-processing-1', # Audio processing library for WebRTC.
        # 'wget', # Command-line tool for downloading files via HTTP/HTTPS/FTP.
        # 'whatsapp-nativefier', # Desktop wrapper for WhatsApp web interface.
        # 'which', # Utility to locate executables in the system PATH.
        # 'whois', # Tool for querying WHOIS databases for domain information.
        # 'wildmidi', # Software synthesizer for playing MIDI files using soundfonts.
        # 'wireless-regdb', # Regulatory database for wireless devices.
        # 'wireless_tools', # Tools for configuring wireless network interfaces (deprecated).
        'wireplumber', # Session and policy manager for PipeWire multimedia server.
        'wkhtmltopdf-bin', # Tool for converting HTML to PDF using WebKit (binary).
        # 'woff2', # Library for compressing and decompressing WOFF2 font files.
        # 'wpa_supplicant', # Tool for connecting to WPA/WPA2 Wi-Fi networks.
        # 'wvdial', # PPP dialer for modem connections.
        # 'wvstreams', # C++ library for network and stream handling.
        # 'wxwidgets-common', # Common files for wxWidgets GUI toolkit.
        # 'wxwidgets-gtk3', # wxWidgets library for GTK3-based GUI applications.
        # 'x264', # H.264/MPEG-4 AVC video codec library.
        # 'x265', # H.265/HEVC video codec library.
        # 'xapp', # Common library for Xfce and other lightweight desktops.
        'xarchiver', # Lightweight archive manager with GUI.
        # 'xcb-imdkit', # Input method development kit for XCB applications.
        # 'xcb-proto', # Protocol definitions for XCB (X protocol C bindings).
        # 'xcb-util', # Utility libraries for XCB (X protocol C bindings).
        # 'xcb-util-cursor', # XCB library for cursor management.
        # 'xcb-util-image', # XCB library for handling images.
        # 'xcb-util-keysyms', # XCB library for key symbol mappings.
        # 'xcb-util-renderutil', # XCB library for rendering utilities.
        # 'xcb-util-wm', # XCB library for window manager functions.
        # 'xcb-util-xrm', # XCB library for X Resource Manager utilities.
        'xclip', # Command-line tool for copying/pasting to X11 clipboard.
        # 'xdg-dbus-proxy', # D-Bus proxy for sandboxed applications.
        'xdg-user-dirs', # Tool for managing standard user directories (e.g., Desktop, Documents).
        # 'xdg-utils', # Utilities for desktop integration (e.g., opening URLs, files).
        # 'xf86-input-elographics', # X.Org driver for Elographics touchscreens.
        # 'xf86-input-libinput', # X.Org driver for libinput-based input devices.
        'xfce4-clipman-plugin', # Clipboard manager plugin for Xfce panel.
        # 'xfce4-notifyd', # Notification daemon for Xfce desktop.
        # 'xfce4-panel', # Desktop panel for Xfce environment.
        # 'xfce4-power-manager', # Power management tool for Xfce.
        # 'xfce4-screenshooter', # Screenshot tool for Xfce desktop.
        # 'xfce4-settings', # Configuration manager for Xfce desktop settings.
        # 'xfce4-taskmanager', # Task manager for monitoring system processes in Xfce.
        # 'xfce4-terminal', # Terminal emulator for Xfce desktop.
        # 'xfconf', # Configuration storage system for Xfce.
        # 'xfsprogs', # Tools for managing XFS filesystems.
        # 'xkeyboard-config', # Keyboard layout and model configuration for X11.
        # 'xl2tpd', # Layer 2 Tunneling Protocol daemon for VPNs.
        'xmlsec', # Library for XML encryption and digital signatures.
        # 'xorg-bdftopcf', # Tool to convert BDF fonts to PCF format for X11.
        # 'xorg-fonts-encodings', # Font encoding files for X11.
        # 'xorg-iceauth', # Tool for managing ICE (Inter-Client Exchange) authentication.
        # 'xorg-mkfontscale', # Utility for creating font scale files for X11.
        # 'xorgproto', # X11 protocol header files for development.
        # 'xorg-server', # X.Org server for X11 display system.
        # 'xorg-server-common', # Common files for X.Org server.
        # 'xorg-sessreg', # Utility for managing session registration in X11.
        # 'xorg-setxkbmap', # Tool to set keyboard layout in X11.
        # 'xorg-smproxy', # Session manager proxy for X11 applications.
        # 'xorg-x11perf', # Performance testing tool for X11 servers.
        # 'xorg-xauth', # Tool for managing X11 authentication files.
        # 'xorg-xcmsdb', # Utility for managing X11 color management database.
        # 'xorg-xcursorgen', # Tool for creating X11 cursor files from PNGs.
        # 'xorg-xdpyinfo', # Utility for displaying X11 display information.
        # 'xorg-xdriinfo', # Tool for querying DRI (Direct Rendering Infrastructure) info.
        # 'xorg-xev', # Utility for displaying X11 events (e.g., key presses).
        # 'xorg-xgamma', # Tool for adjusting gamma correction in X11.
        # 'xorg-xhost', # Utility for controlling X11 server access.
        # 'xorg-xinit', # X11 session initializer (startx/xinit).
        # 'xorg-xinput', # Tool for configuring X11 input devices.
        # 'xorg-xkbcomp', # Utility for compiling XKB keyboard layouts.
        # 'xorg-xkbevd', # X11 keyboard event daemon.
        # 'xorg-xkbprint', # Tool for printing XKB keyboard layouts.
        # 'xorg-xkbutils', # Utilities for managing XKB keyboard configurations.
        # 'xorg-xkill', # Tool to terminate X11 clients by clicking.
        # 'xorg-xlsatoms', # Utility to list X11 server atoms.
        # 'xorg-xlsclients', # Tool to list active X11 clients.
        # 'xorg-xmessage', # Utility for displaying simple message boxes in X11.
        # 'xorg-xmodmap', # Tool for modifying X11 keymaps and pointer mappings.
        # 'xorg-xpr', # Utility for printing X11 window contents.
        # 'xorg-xprop', # Tool for displaying X11 window and font properties.
        # 'xorg-xrandr', # Utility for managing screen resolution and rotation in X11.
        # 'xorg-xrdb', # Tool for managing X11 resource database.
        # 'xorg-xrefresh', # Utility to refresh X11 screen.
        # 'xorg-xset', # Tool for setting X11 user preferences (e.g., display settings).
        # 'xorg-xsetroot', # Utility for setting X11 root window properties.
        # 'xorg-xvinfo', # Tool for querying X11 video extension information.
        # 'xorg-xwd', # Utility for capturing X11 window dumps.
        # 'xorg-xwininfo', # Tool for displaying X11 window information.
        # 'xorg-xwud', # Utility for displaying X11 window dumps from xwd.
        # 'xvidcore', # Xvid MPEG-4 video codec library.
        # 'xxhash', # Fast non-cryptographic hash algorithm library.
        # 'xz', # Compression library and tools for XZ and LZMA formats.
        # 'yad', # GUI dialog tool for shell scripts (Yet Another Dialog).
        # 'yay-git', # AUR helper for managing Arch User Repository packages.
        'yt-dlp', # Tool for downloading videos from YouTube and other sites.
        'zbar', # Library for reading barcodes and QR codes.
        # 'zeromq', # High-performance messaging library for distributed systems.
        # 'zimg', # Library for image scaling and colorspace conversion.
        'zip', # Tool for creating and extracting ZIP archives.
        # 'zix', # Lightweight C library for data structures and utilities.
        # 'zlib', # Compression library for data compression (zlib format).
        # 'zlib-ng', # Optimized fork of zlib for better performance.
        'zoom', # Video conferencing application.
        # 'zstd', # Fast compression library (Zstandard algorithm).
        # 'zvbi', # Library for handling Vertical Blanking Interval data (teletext, subtitles).
        # 'zxing-cpp', # C++ library for barcode and QR code processing.
    ])


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



def local_machine():
    ''' Machine with only local network connections. Use with archinstall d base installation.
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
    awesome_archinstall()

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
