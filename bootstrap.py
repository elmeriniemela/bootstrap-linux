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
    _packages([
        'xfce4-clipman-plugin',
        'rofi',
        'rofi-calc',
        'picom',
        'signal-desktop',
        'udisks2',
        'gvfs',  # For automount
        'udiskie',  # For automount
        'pyenv', # https://github.com/pyenv/pyenv?tab=readme-ov-file#install-additional-python-versions
        'python-qdarkstyle', # Electrum dark style
        'bluez-utils',
        'blueman',
        'thunar',
        'pavucontrol', # Volume/audio control
        'openconnect',  # work
        'openvpn',  # personal
        'networkmanager-openvpn',
        'syncthing',
        'thunderbird',
        'veracrypt',
        'gocryptfs',
        'sardi-icons',
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
    _aur([
        'a52dec',
        'aalib',
        'abseil-cpp',
        'accountsservice',
        'acl',
        'acpica',
        'acpilight',
        'adobe-source-code-pro-fonts',
        'adobe-source-han-sans-cn-fonts',
        'adobe-source-han-sans-jp-fonts',
        'adobe-source-han-sans-kr-fonts',
        'adobe-source-sans-fonts',
        'adobe-source-serif-fonts',
        'adwaita-cursors',
        'adwaita-fonts',
        'adwaita-icon-theme',
        'adwaita-icon-theme-legacy',
        'aic94xx-firmware',
        'alacritty',
        'alsa-card-profiles',
        'alsa-firmware',
        'alsa-lib',
        'alsa-plugins',
        'alsa-topology-conf',
        'alsa-ucm-conf',
        'alsa-utils',
        'aom',
        'appstream',
        'appstream-glib',
        'arandr',
        'arc-gtk-theme',
        'arch-install-scripts',
        'archlinux-keyring',
        'archlinux-logout-git',
        'archlinux-tweak-tool-git',
        'arcolinux-alacritty-git',
        'arcolinux-arc-dawn-git',
        'arcolinux-awesome-git',
        'arcolinux-bootloader-grub-git',
        'arcolinux-config-all-desktops-git',
        'arcolinux-dconf-all-desktops-git',
        'arcolinux-desktop-trasher-git',
        'arcolinuxd-system-config-git',
        'arcolinuxd-welcome-app-git',
        'arcolinux-grub-theme-vimix-git',
        'arcolinux-gtk-surfn-arc-git',
        'arcolinux-keyring',
        'arcolinux-local-xfce4-git',
        'arcolinux-mirrorlist-git',
        'arcolinux-paru-git',
        'arcolinux-powermenu-git',
        'arcolinux-rofi-git',
        'arcolinux-rofi-themes-git',
        'arcolinux-root-git',
        'arcolinux-sddm-futuristic-git',
        'arcolinux-sddm-materia-git',
        'arcolinux-sddm-simplicity-git',
        'arcolinux-sddm-slice-git',
        'arcolinux-sddm-sugar-candy-git',
        'arcolinux-sddm-urbanlifestyle-git',
        'arcolinux-systemd-services-git',
        'arcolinux-volumeicon-git',
        'arcolinux-wallpapers-git',
        'arconet-variety-config',
        'arconet-xfce',
        'arcopro-wallpapers',
        'argon2',
        'aribb24',
        'ast-firmware',
        'atkmm',
        'at-spi2-core',
        'attr',
        'audit',
        'autoconf',
        'automake',
        'avahi',
        'awesome',
        'awesome-terminal-fonts',
        'aws-cli-bin',
        'aws-cli-v2-python-awscrt',
        'aws-cli-v2-python-awscrt-debug',
        'babl',
        'base',
        'base-devel',
        'bash',
        'bash-completion',
        'bat',
        'bc',
        'betterlockscreen',
        'bibata-cursor-theme-bin',
        'bind',
        'binutils',
        'bison',
        'bisq',
        'blas',
        'blueberry',
        'blueman',
        'bluez',
        'bluez-libs',
        'bluez-tools',
        'bluez-utils',
        'boost-libs',
        'botan2',
        'brave-bin',
        'broadcom-wl-dkms',
        'brotli',
        'btop',
        'btrfs-progs',
        'bubblewrap',
        'bzip2',
        'ca-certificates',
        'ca-certificates-mozilla',
        'ca-certificates-utils',
        'cairo',
        'cairomm',
        'cairomm-1.16',
        'cantarell-fonts',
        'c-ares',
        'cblas',
        'cdparanoia',
        'chaotic-keyring',
        'chaotic-mirrorlist',
        'chromaprint',
        'cifs-utils',
        'cloc',
        'clonezilla',
        'clucene',
        'cmake',
        'colord',
        'containerd',
        'coreutils',
        'cppdap',
        'cronie',
        'cryptsetup',
        'curl',
        'dav1d',
        'db5.3',
        'dbus',
        'dbus-broker',
        'dbus-broker-units',
        'dbus-glib',
        'dbus-units',
        'dconf',
        'ddcutil',
        'ddrescue',
        'debugedit',
        'default-cursors',
        'desktop-file-utils',
        'device-mapper',
        'dex',
        'dialog',
        'diffutils',
        'ding-libs',
        'dkms',
        'dmidecode',
        'dmraid',
        'dnsmasq',
        'dnssec-anchors',
        'docker',
        'dosfstools',
        'double-conversion',
        'downgrade',
        'drbl',
        'duf',
        'duktape',
        'e2fsprogs',
        'ecryptfs-utils',
        'edk2-shell',
        'efibootmgr',
        'efivar',
        'eglexternalplatform',
        'egl-wayland',
        'electrum',
        'elementary-icon-theme',
        'ell',
        'enchant',
        'endeavouros-keyring',
        'endeavouros-mirrorlist',
        'ethtool',
        'exfatprogs',
        'exiv2',
        'exo',
        'expac',
        'expat',
        'f2fs-tools',
        'faac',
        'faad2',
        'fail2ban',
        'fakeroot',
        'fatresize',
        'fcitx5',
        'feh',
        'ffmpeg',
        'ffmpeg4.4',
        'ffmpegthumbnailer',
        'fftw',
        'file',
        'filesystem',
        'findutils',
        'firefox',
        'flac',
        'flex',
        'fluidsynth',
        'fontconfig',
        'font-manager',
        'freeglut',
        'freetype2',
        'fribidi',
        'fsarchiver',
        'fuse2',
        'fuse3',
        'fuse-common',
        'fuseiso',
        'fzf',
        'garcon',
        'gawk',
        'gc',
        'gcc',
        'gcc-libs',
        'gconf',
        'gcr-4',
        'gdb',
        'gdb-common',
        'gdbm',
        'gdk-pixbuf2',
        'gegl',
        'gendesk',
        'gettext',
        'giflib',
        'gimp',
        'git',
        'git-lfs',
        'gksu',
        'glib2',
        'glibc',
        'glibmm',
        'glibmm-2.68',
        'glib-networking',
        'glslang',
        'glu',
        'gmp',
        'gnome-bluetooth',
        'gnome-themes-extra',
        'gnulib-l10n',
        'gnupg',
        'gnutls',
        'gobject-introspection-runtime',
        'gocryptfs',
        'gpart',
        'gparted',
        'gperftools',
        'gpgme',
        'gpgmepp',
        'gpm',
        'gptfdisk',
        'graphene',
        'graphite',
        'grep',
        'groff',
        'grub',
        'gsettings-desktop-schemas',
        'gsettings-system-schemas',
        'gsm',
        'gspell',
        'gssdp',
        'gssproxy',
        'gst-plugins-bad',
        'gst-plugins-bad-libs',
        'gst-plugins-base',
        'gst-plugins-base-libs',
        'gst-plugins-good',
        'gst-plugins-ugly',
        'gstreamer',
        'gtest',
        'gtk2',
        'gtk3',
        'gtk4',
        'gtk-layer-shell',
        'gtkmm3',
        'gtkmm-4.0',
        'gtksourceview3',
        'gtk-update-icon-cache',
        'guile',
        'gupnp',
        'gupnp-igd',
        'gvfs',
        'gzip',
        'harfbuzz',
        'harfbuzz-icu',
        'hdparm',
        'hicolor-icon-theme',
        'hidapi',
        'highway',
        'htop',
        'http-parser',
        'hunspell',
        'hwdata',
        'hwinfo',
        'hwloc',
        'hw-probe',
        'hyperv',
        'hyphen',
        'i2c-tools',
        'i3lock-color',
        'i3lock-fancy-dualmonitors-git',
        'iana-etc',
        'ib-tws',
        'ib-tws-debug',
        'ibus',
        'icu',
        'imagemagick',
        'imath',
        'imlib2',
        'inetutils',
        'intel-ucode',
        'inxi',
        'iproute2',
        'iptables',
        'iputils',
        'iso-codes',
        'iw',
        'iwd',
        'jansson',
        'jasper',
        'java-environment-common',
        'java-runtime-common',
        'jbigkit',
        'jdk11-openjdk',
        'jemalloc',
        'jfsutils',
        'json-c',
        'jsoncpp',
        'json-glib',
        'kbd',
        'keyutils',
        'kguiaddons5',
        'kmod',
        'krb5',
        'lame',
        'lapack',
        'laptop-detect',
        'lbzip2',
        'lcms2',
        'ldns',
        'leancrypto',
        'lensfun',
        'less',
        'libabw',
        'libadwaita-without-adwaita-git',
        'libaio',
        'libappindicator-gtk3',
        'libarchive',
        'libass',
        'libassuan',
        'libasyncns',
        'libatasmart',
        'libatomic_ops',
        'libavc1394',
        'libavif',
        'libavtp',
        'libb2',
        'libblockdev',
        'libblockdev-crypto',
        'libblockdev-fs',
        'libblockdev-loop',
        'libblockdev-mdraid',
        'libblockdev-nvme',
        'libblockdev-part',
        'libblockdev-swap',
        'libbluray',
        'libbpf',
        'libbs2b',
        'libbsd',
        'libbytesize',
        'libcaca',
        'libcanberra',
        'libcap',
        'libcap-ng',
        'libcbor',
        'libcdio',
        'libcdio-paranoia',
        'libcdr',
        'libcloudproviders',
        'libcmis',
        'libcolord',
        'libconfig',
        'libcups',
        'libdaemon',
        'libdatrie',
        'libdbusmenu-glib',
        'libdbusmenu-gtk3',
        'libdc1394',
        'libdca',
        'libde265',
        'libdecor',
        'libdeflate',
        'libdisplay-info',
        'libdovi',
        'libdrm',
        'libdv',
        'libdvbpsi',
        'libdvdnav',
        'libdvdread',
        'libebml',
        'libe-book',
        'libebur128',
        'libedit',
        'libelf',
        'libepoxy',
        'libepubgen',
        'libetonyek',
        'libev',
        'libevdev',
        'libevent',
        'libexif',
        'libexttextcat',
        'libfdk-aac',
        'libffi',
        'libfido2',
        'libfontenc',
        'libfreeaptx',
        'libfreehand',
        'libgcrypt',
        'libgexiv2',
        'libgirepository',
        'libgit2',
        'libgksu',
        'libglvnd',
        'libgme',
        'libgnomekbd',
        'libgnome-keyring',
        'libgpg-error',
        'libgtop',
        'libgudev',
        'libgusb',
        'libheif',
        'libibus',
        'libice',
        'libidn',
        'libidn2',
        'libiec61883',
        'libimagequant',
        'libimobiledevice',
        'libimobiledevice-glue',
        'libinih',
        'libinput',
        'libinstpatch',
        'libisl',
        'libixion',
        'libjpeg6-turbo',
        'libjpeg-turbo',
        'libjxl',
        'libksba',
        'liblangtag',
        'liblc3',
        'libldac',
        'libldap',
        'liblqr',
        'liblrdf',
        'libltc',
        'libmad',
        'libmanette',
        'libmatroska',
        'libmaxminddb',
        'libmbim',
        'libmd',
        'libmfx',
        'libmicrodns',
        'libmm-glib',
        'libmng',
        'libmnl',
        'libmodplug',
        'libmpc',
        'libmpcdec',
        'libmpeg2',
        'libmspack',
        'libmspub',
        'libmwaw',
        'libmypaint',
        'libmysofa',
        'libndp',
        'libnet',
        'libnetfilter_conntrack',
        'libnewt',
        'libnfnetlink',
        'libnftnl',
        'libnghttp2',
        'libnghttp3',
        'libngtcp2',
        'libnice',
        'libnl',
        'libnm',
        'libnma',
        'libnma-common',
        'libnotify',
        'libnsl',
        'libnumbertext',
        'libnvme',
        'libodfgen',
        'libogg',
        'libomxil-bellagio',
        'libopenmpt',
        'liborcus',
        'libp11-kit',
        'libpagemaker',
        'libpcap',
        'libpciaccess',
        'libpgm',
        'libpipeline',
        'libpipewire',
        'libplacebo',
        'libplist',
        'libpng',
        'libproxy',
        'libpsl',
        'libpulse',
        'libqalculate',
        'libqmi',
        'libqrtr-glib',
        'libqxp',
        'libraqm',
        'libraw',
        'libraw1394',
        'libreoffice-fresh',
        'librevenge',
        'librsvg',
        'libsamplerate',
        'libsasl',
        'libseccomp',
        'libsecp256k1',
        'libsecret',
        'libshout',
        'libsigc++',
        'libsigc++-3.0',
        'libsm',
        'libsndfile',
        'libsodium',
        'libsoup3',
        'libsoxr',
        'libspiro',
        'libsrtp',
        'libssh',
        'libssh2',
        'libstaroffice',
        'libstemmer',
        'libsysprof-capture',
        'libtar',
        'libtasn1',
        'libteam',
        'libthai',
        'libtheora',
        'libtiff',
        'libtirpc',
        'libtommath',
        'libtool',
        'libunibreak',
        'libunistring',
        'libunwind',
        'libupnp',
        'liburcu',
        'liburing',
        'libusb',
        'libusb-compat',
        'libusbmuxd',
        'libutempter',
        'libuv',
        'libva',
        'libvdpau',
        'libverto',
        'libvisio',
        'libvlc',
        'libvorbis',
        'libvpl',
        'libvpx',
        'libwacom',
        'libwbclient',
        'libwebp',
        'libwireplumber',
        'libwmf',
        'libwnck3',
        'libwpd',
        'libwps',
        'libx11',
        'libx86emu',
        'libxau',
        'libxaw',
        'libxcb',
        'libxcomposite',
        'libxcrypt',
        'libxcrypt-compat',
        'libxcursor',
        'libxcvt',
        'libxdamage',
        'libxdg-basedir',
        'libxdmcp',
        'libxext',
        'libxfce4ui',
        'libxfce4util',
        'libxfce4windowing',
        'libxfixes',
        'libxfont2',
        'libxft',
        'libxi',
        'libxinerama',
        'libxkbcommon',
        'libxkbcommon-x11',
        'libxkbfile',
        'libxklavier',
        'libxml2',
        'libxml2-legacy',
        'libxmlb',
        'libxmu',
        'libxpm',
        'libxrandr',
        'libxrender',
        'libxres',
        'libxshmfence',
        'libxslt',
        'libxss',
        'libxt',
        'libxtst',
        'libxv',
        'libxxf86vm',
        'libyaml',
        'libyuv',
        'libzmf',
        'licenses',
        'lilv',
        'linux',
        'linux-api-headers',
        'linux-atm',
        'linux-firmware',
        'linux-firmware-bnx2x',
        'linux-firmware-liquidio',
        'linux-firmware-marvell',
        'linux-firmware-mellanox',
        'linux-firmware-nfp',
        'linux-firmware-qlogic',
        'linux-firmware-whence',
        'linux-headers',
        'linux-lts',
        'linux-lts-headers',
        'llhttp',
        'llvm-libs',
        'lmdb',
        'lm_sensors',
        'logrotate',
        'lohit-fonts',
        'lpsolve',
        'lrzip',
        'lsb-release',
        'lshw',
        'l-smash',
        'lsof',
        'lsscsi',
        'lua53',
        'lua53-lgi',
        'lua',
        'luajit',
        'lv2',
        'lvm2',
        'lxappearance',
        'lz4',
        'lzo',
        'lzop',
        'm4',
        'mailcap',
        'make',
        'man-db',
        'man-pages',
        'md4c',
        'mdadm',
        'memtest86+',
        'memtest86+-efi',
        'mesa',
        'micro',
        'minizip',
        'mjpegtools',
        'mkinitcpio',
        'mkinitcpio-busybox',
        'mkinitcpio-firmware',
        'mkinitcpio-nfs-utils',
        'mkinitcpio-openswap',
        'mobile-broadband-provider-info',
        'modemmanager',
        'most',
        'mpdecimal',
        'mpfr',
        'mpg123',
        'mtdev',
        'mtools',
        'mycrypto-bin',
        'mycrypto-bin-debug',
        'mypaint-brushes1',
        'nano',
        'nbd',
        'ncdu',
        'ncurses',
        'ndisc6',
        'neon',
        'nettle',
        'net-tools',
        'networkmanager',
        'network-manager-applet',
        'networkmanager-openconnect',
        'networkmanager-openvpn',
        'networkmanager-pptp',
        'networkmanager-qt5',
        'networkmanager-vpnc',
        'nfsidmap',
        'nfs-utils',
        'nftables',
        'nilfs-utils',
        'ninja',
        'nm-connection-editor',
        'node-gyp',
        'nodejs',
        'nodejs-nopt',
        'nomacs',
        'nordvpn-bin',
        'noto-fonts',
        'noto-fonts-emoji',
        'npm',
        'npth',
        'nspr',
        'nss',
        'ntfs-3g',
        'ntp',
        'numlockx',
        'nvidia-390xx-utils',
        'nvme-cli',
        'oath-toolkit',
        'ocl-icd',
        'onetbb',
        'oniguruma',
        'openal',
        'openconnect',
        'opencore-amr',
        'opencv',
        'openexr',
        'openh264',
        'open-iscsi',
        'open-isns',
        'openjpeg2',
        'openssh',
        'openssl-1.1',
        'openssl',
        'openvpn',
        'opus',
        'orc',
        'os-prober',
        'otf-libertinus',
        'p11-kit',
        'pacman',
        'pacman-contrib',
        'pacman-mirrorlist',
        'pahole',
        'pam',
        'pambase',
        'pango',
        'pangomm',
        'pangomm-2.48',
        'partclone',
        'parted',
        'partimage',
        'paru-git',
        'patch',
        'pavucontrol',
        'pbzip2',
        'pciutils',
        'pcre2',
        'pcre',
        'pcsclite',
        'perl',
        'perl-algorithm-diff',
        'perl-class-method-modifiers',
        'perl-clone',
        'perl-data-optlist',
        'perl-devel-globaldestruction',
        'perl-encode-locale',
        'perl-error',
        'perl-file-listing',
        'perl-html-parser',
        'perl-html-tagset',
        'perl-http-cookiejar',
        'perl-http-cookies',
        'perl-http-daemon',
        'perl-http-date',
        'perl-http-message',
        'perl-http-negotiate',
        'perl-import-into',
        'perl-io-html',
        'perl-libwww',
        'perl-lwp-mediatypes',
        'perl-mailtools',
        'perl-module-runtime',
        'perl-moo',
        'perl-net-http',
        'perl-parallel-forkmanager',
        'perl-params-util',
        'perl-regexp-common',
        'perl-role-tiny',
        'perl-sub-exporter',
        'perl-sub-exporter-progressive',
        'perl-sub-install',
        'perl-sub-quote',
        'perl-timedate',
        'perl-try-tiny',
        'perl-uri',
        'perl-www-robotrules',
        'perl-xml-parser',
        'perl-xml-writer',
        'picom',
        'pigz',
        'pinentry',
        'pipewire',
        'pipewire-alsa',
        'pipewire-audio',
        'pipewire-jack',
        'pipewire-pulse',
        'pipewire-session-manager',
        'pipewire-zeroconf',
        'pixman',
        'pixz',
        'pkcs11-helper',
        'pkgconf',
        'pkgfile',
        'playerctl',
        'plocate',
        'polkit',
        'polkit-gnome',
        'poppler',
        'poppler-data',
        'poppler-glib',
        'popt',
        'portaudio',
        'postgresql',
        'postgresql-libs',
        'postgresql-old-upgrade',
        'powertop',
        'ppp',
        'pptpclient',
        'procps-ng',
        'protobuf',
        'psmisc',
        'pv',
        'pwgen',
        'pyenv',
        'python310',
        'python310-debug',
        'python312',
        'python312-debug',
        'python',
        'python38',
        'python38-debug',
        'python-aiohappyeyeballs',
        'python-aiohttp',
        'python-aiohttp-socks',
        'python-aiorpcx',
        'python-aiosignal',
        'python-attrs',
        'python-autocommand',
        'python-cairo',
        'python-certifi',
        'python-cffi',
        'python-charset-normalizer',
        'python-colorama',
        'python-cryptography',
        'python-dateutil',
        'python-dbus',
        'python-distro',
        'python-dnspython',
        'python-docopt',
        'python-docutils',
        'python-execnet',
        'python-filelock',
        'python-frozenlist',
        'python-gobject',
        'python-helpdev',
        'python-idna',
        'python-iniconfig',
        'python-jaraco.collections',
        'python-jaraco.context',
        'python-jaraco.functools',
        'python-jaraco.text',
        'python-jmespath',
        'python-jsonpatch',
        'python-jsonpointer',
        'python-jsonschema',
        'python-jsonschema-specifications',
        'python-keyutils',
        'python-more-itertools',
        'python-multidict',
        'python-numpy',
        'python-packaging',
        'python-pillow',
        'python-pip',
        'python-platformdirs',
        'python-pluggy',
        'python-prompt_toolkit',
        'python-propcache',
        'python-protobuf',
        'python-psutil',
        'python-pyaes',
        'python-pycparser',
        'python-pygments',
        'python-pyinotify',
        'python-pyqt5',
        'python-pyqt5-sip',
        'python-pytest',
        'python-pytest-xdist',
        'python-python-socks',
        'python-qdarkstyle',
        'python-qrcode',
        'python-qtpy',
        'python-referencing',
        'python-requests',
        'python-rpds-py',
        'python-ruamel-yaml',
        'python-ruamel.yaml.clib',
        'python-setproctitle',
        'python-setuptools',
        'python-six',
        'python-systemd',
        'python-urllib3',
        'python-wcwidth',
        'python-websockets',
        'python-wheel',
        'python-yaml',
        'python-yarl',
        'qrencode',
        'qt5-base',
        'qt5ct',
        'qt5-declarative',
        'qt5-graphicaleffects',
        'qt5-location',
        'qt5-quickcontrols2',
        'qt5-quickcontrols',
        'qt5-remoteobjects',
        'qt5-svg',
        'qt5-translations',
        'qt5-virtualkeyboard',
        'qt5-wayland',
        'qt5-webchannel',
        'qt5-webengine',
        'qt5-x11extras',
        'qt6-5compat',
        'qt6-base',
        'qt6-declarative',
        'qt6-shadertools',
        'qt6-svg',
        'qt6-translations',
        'quazip-qt6',
        'raptor',
        'rasqal',
        'rate-mirrors-bin',
        'rav1e',
        'readline',
        'rebornos-keyring',
        'rebornos-mirrorlist',
        'redland',
        'refind',
        'reflector',
        'rhash',
        'ripgrep',
        'rofi',
        'rofi-calc',
        'rpcbind',
        'rp-pppoe',
        'rsync',
        'rtl8821cu-morrownr-dkms-git',
        'rtmpdump',
        'rubberband',
        'runc',
        'run-parts',
        'sardi-icons',
        'sbc',
        'screen',
        'scrot',
        'sddm',
        'sdl2-compat',
        'sdl2-debug',
        'sdl3',
        'sdparm',
        'sed',
        'semver',
        'serd',
        'sg3_utils',
        'shaderc',
        'shadow',
        'shared-mime-info',
        'signal-desktop',
        'simdjson',
        'slack-desktop',
        'slang',
        'smartmontools',
        'snappy',
        'sof-firmware',
        'sofirem-git',
        'sord',
        'sound-theme-freedesktop',
        'soundtouch',
        'source-highlight',
        'spandsp',
        'sparrow-wallet',
        'sparrow-wallet-debug',
        'speex',
        'speexdsp',
        'spirv-tools',
        'sqlite',
        'squashfs-tools',
        'sratom',
        'srt',
        'sshfs',
        'sshpass',
        'sshuttle',
        'startup-notification',
        'stoken',
        'sudo',
        'suitesparse',
        'surfn-icons-git',
        'svt-av1',
        'svt-hevc',
        'syncthing',
        'sysfsutils',
        'syslinux',
        'systemd',
        'systemd-libs',
        'systemd-resolvconf',
        'systemd-sysvcompat',
        'taglib',
        'talloc',
        'tar',
        'tcl',
        'tcpdump',
        'tdb',
        'terminus-font',
        'testdisk',
        'texinfo',
        'the_silver_searcher',
        'thin-provisioning-tools',
        'thunar',
        'thunar-archive-plugin',
        'thunar-volman',
        'thunderbird',
        'tinysparql',
        'tk',
        'tlp',
        'tmux',
        'tpm2-tss',
        'tslib',
        'ttf-anonymous-pro',
        'ttf-bitstream-vera',
        'ttf-caladea',
        'ttf-carlito',
        'ttf-cascadia-code',
        'ttf-cormorant',
        'ttf-croscore',
        'ttf-dejavu',
        'ttf-droid',
        'ttf-eurof',
        'ttf-fantasque-sans-mono',
        'ttf-fira-code',
        'ttf-fira-mono',
        'ttf-fira-sans',
        'ttf-font-awesome',
        'ttf-hack',
        'ttf-hactor',
        'ttf-hellvetica',
        'ttf-ibm-plex',
        'ttf-inconsolata',
        'ttf-iosevka-nerd',
        'ttf-jetbrains-mono',
        'ttf-jetbrains-mono-nerd',
        'ttf-joypixels',
        'ttf-lato',
        'ttf-liberation',
        'ttf-linux-libertine',
        'ttf-linux-libertine-g',
        'ttf-mac-fonts',
        'ttf-meslo-nerd-font-powerlevel10k',
        'ttf-monofur',
        'ttf-ms-fonts',
        'ttf-nerd-fonts-symbols',
        'ttf-nerd-fonts-symbols-common',
        'ttf-nerd-fonts-symbols-mono',
        'ttf-opensans',
        'ttf-roboto',
        'ttf-roboto-mono',
        'ttf-sourcecodepro-nerd',
        'ttf-ubuntu-font-family',
        'tumbler',
        'twolame',
        'tzdata',
        'udftools',
        'udiskie',
        'udisks2',
        'ufw',
        'unrar',
        'unzip',
        'upd72020x-fw',
        'upower',
        'usb_modeswitch',
        'usbmuxd',
        'usbutils',
        'util-linux',
        'util-linux-libs',
        'v4l-utils-git',
        'vapoursynth',
        'ventoy-bin',
        'veracrypt',
        'verdict',
        'vicious',
        'vid.stab',
        'vim',
        'vimix-cursors',
        'vim-runtime',
        'visual-studio-code-bin',
        'vlc',
        'vmaf',
        'volumeicon',
        'volume_key',
        'vpnc',
        'vte3',
        'vte-common',
        'vulkan-headers',
        'vulkan-icd-loader',
        'wasabi-wallet-bin',
        'wavpack',
        'wayland',
        'wayland-protocols',
        'wd719x-firmware',
        'webkit2gtk-4.1',
        'webkitgtk-6.0',
        'webrtc-audio-processing-1',
        'wget',
        'whatsapp-nativefier',
        'which',
        'whois',
        'wildmidi',
        'wireless-regdb',
        'wireless_tools',
        'wireplumber',
        'wkhtmltopdf-bin',
        'woff2',
        'wpa_supplicant',
        'wvdial',
        'wvstreams',
        'wxwidgets-common',
        'wxwidgets-gtk3',
        'x264',
        'x265',
        'xapp',
        'xarchiver',
        'xcb-imdkit',
        'xcb-proto',
        'xcb-util',
        'xcb-util-cursor',
        'xcb-util-image',
        'xcb-util-keysyms',
        'xcb-util-renderutil',
        'xcb-util-wm',
        'xcb-util-xrm',
        'xclip',
        'xdg-dbus-proxy',
        'xdg-user-dirs',
        'xdg-utils',
        'xf86-input-elographics',
        'xf86-input-libinput',
        'xfce4-clipman-plugin',
        'xfce4-notifyd',
        'xfce4-panel',
        'xfce4-power-manager',
        'xfce4-screenshooter',
        'xfce4-settings',
        'xfce4-taskmanager',
        'xfce4-terminal',
        'xfconf',
        'xfsprogs',
        'xkeyboard-config',
        'xl2tpd',
        'xmlsec',
        'xorg-bdftopcf',
        'xorg-fonts-encodings',
        'xorg-iceauth',
        'xorg-mkfontscale',
        'xorgproto',
        'xorg-server',
        'xorg-server-common',
        'xorg-sessreg',
        'xorg-setxkbmap',
        'xorg-smproxy',
        'xorg-x11perf',
        'xorg-xauth',
        'xorg-xcmsdb',
        'xorg-xcursorgen',
        'xorg-xdpyinfo',
        'xorg-xdriinfo',
        'xorg-xev',
        'xorg-xgamma',
        'xorg-xhost',
        'xorg-xinit',
        'xorg-xinput',
        'xorg-xkbcomp',
        'xorg-xkbevd',
        'xorg-xkbprint',
        'xorg-xkbutils',
        'xorg-xkill',
        'xorg-xlsatoms',
        'xorg-xlsclients',
        'xorg-xmessage',
        'xorg-xmodmap',
        'xorg-xpr',
        'xorg-xprop',
        'xorg-xrandr',
        'xorg-xrdb',
        'xorg-xrefresh',
        'xorg-xset',
        'xorg-xsetroot',
        'xorg-xvinfo',
        'xorg-xwd',
        'xorg-xwininfo',
        'xorg-xwud',
        'xvidcore',
        'xxhash',
        'xz',
        'yad',
        'yt-dlp',
        'zbar',
        'zeromq',
        'zimg',
        'zip',
        'zix',
        'zlib',
        'zlib-ng',
        'zoom',
        'zstd',
        'zvbi',
        'zxing-cpp',
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
