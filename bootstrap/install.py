
import os
import shutil

from .lib import (
    _path,
    _lineinfile,
    _copy,
    _enable,
    _run,
    _packages,
    _aur,
    _yay,
    api,
)

@api
def distro():
    '''Base setup. Use laptop() or server() after this.'''
    _packages([
        'base-devel',
        'openssh', # Secure Shell (SSH) client and server.
        'sudo',
        'cronie',
        'rsync',
        'ncdu', # diskspace
        'htop',
        'openvpn',  # personal vpn
        'bash-completion',
        'tmux',
        'unrar', # Tool for extracting RAR archives.
        'unzip',
        'zip',
        'ffmpeg', # Multimedia framework for encoding, decoding, and streaming.
        'wget',
        'syncthing',
        'reflector',
        'python-colorama', # color support for this app
        'curl', # Command-line tool and library for transferring data via URLs.
        'less',
        'plocate',
        'man-db',
        'dnsutils',
        'vim',
        'certbot',
        'certbot-dns-cloudflare',
        'composer',
        'npm',
        'ripgrep',
        'jq',
        '7zip', # archiving tool
    ])
    _yay() # enable chaotic-aur
    _enable([
        'cronie',
        'systemd-timesyncd',
    ])
    _run([
        "sudo sed -i '/^#en_US.UTF-8/s/^#//g' /etc/locale.gen",
        "sudo sed -i '/^#fi_FI.UTF-8/s/^#//g' /etc/locale.gen",
        'sudo locale-gen',
    ])

    _lineinfile({'/etc/sudoers.d/wheel_group': '%wheel ALL=(ALL) ALL'})

    # https://lonesysadmin.net/2013/12/22/better-linux-disk-caching-performance-vm-dirty_ratio/
    # Contains the amount of dirty memory at which a process generating disk writes will itself start writeback.
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'kernel.sysrq=1'})
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'vm.dirty_background_ratio=5'})
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'vm.dirty_ratio=10'})
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'vm.swappiness=10'})
    _lineinfile({'/etc/sysctl.d/99-sysctl.conf': 'kernel.yama.ptrace_scope=2'})


    _copy({
        'vconsole.conf': '/etc/vconsole.conf',
        'locale.conf': '/etc/locale.conf',
    })


@api
def laptop():
    "Setup archinstall laptop"
    if not os.path.exists(_path('~/.config/awesome/.git')):
        awesome_path = _path('~/.config/awesome')
        shutil.rmtree(awesome_path, ignore_errors=True)
        os.makedirs(awesome_path)
        os.chdir(awesome_path)
        _run([
            f'git clone --recursive https://github.com/elmeriniemela/awesome-config.git {awesome_path}',
        ])


    _packages([
        'alacritty', # Fast, GPU-accelerated terminal emulator written in Rust.
        'awesome', # Highly configurable, lightweight window manager.
        'betterlockscreen', # Customizable lock screen for i3 window manager.
        'brave-bin', # Privacy-focused web browser with built-in ad-blocker.
        'cloc', # Counts lines of code in various programming languages.
        'default-cursors', # Default cursor set for X11 environments.
        'xfce4-clipman-plugin',
        'xdg-utils', # xdg-open command for opening file with default app
        'rofi',
        'tlp',
        'rofi-calc',
        'picom',
        'signal-desktop',
        # 'slack-desktop', # Slack client for team communication.
        'udisks2',
        'gvfs',  # For automount
        'udiskie',  # For automount
        'python-qdarkstyle', # Electrum dark style
        'python-coverage', # code test coverage repors
        'ruff', # automated python code formatting+linting.
        'bluez', # Bluetooth protocol stack for Linux.
        'bluez-libs', # Libraries for Bluetooth functionality.
        'bluez-tools', # Additional tools for managing Bluetooth devices.
        'bluez-utils', # Utilities for interacting with Bluetooth devices.
        'thunar',
        'thunar-archive-plugin', # Archive support for Thunar file manager.
        'thunar-volman', # Volume management plugin for Thunar.
        'pavucontrol', # Volume/audio control
        'openconnect',  # work vpn
        'mermaid-cli', # diagrams for github repo README's
        'thunderbird',
        'veracrypt',
        'ventoy-bin', # Tool for creating bootable USB drives with multiple ISOs.
        'gocryptfs',
        'papirus-icon-theme',  # Icon theme
        'hicolor-icon-theme', # Default fallback icon theme for freedesktop.
        'tumbler', # thunar image thumbnails
        'firefox', # Mozilla Firefox web browser.
        'ffmpegthumbnailer', # thunar video thumbnails
        'flameshot',
        'fontconfig', # Library for configuring and managing fonts.
        'font-manager', # GUI for managing and previewing fonts.
        'fprintd', # Fingerprint reader daemon + pam_fprintd.so (Goodix MOC reader on T14 Gen 5).
        'git-lfs', # Git extension for versioning large files.
        'alsa-card-profiles', # ALSA configuration profiles for sound cards.
        'alsa-firmware', # Firmware files for ALSA-supported sound hardware.
        'alsa-lib', # Core library for Advanced Linux Sound Architecture (ALSA).
        'alsa-plugins', # Additional plugins for ALSA, like upmixing and JACK support.
        'alsa-topology-conf', # Configuration files for ALSA topology data.
        'alsa-ucm-conf', # ALSA Use Case Manager configuration files.
        'alsa-utils', # Utilities for managing ALSA audio devices (e.g., alsamixer).
        'sof-firmware', # Sound Open Firmware DSP blobs; required for Intel SOF audio (no sound card without it).
        'pipewire', # Multimedia server for audio and video handling.
        'pipewire-alsa', # ALSA compatibility for PipeWire.
        'pipewire-audio', # Audio processing components for PipeWire.
        # 'pipewire-jack', # JACK compatibility for PipeWire.
        'pipewire-pulse', # PulseAudio compatibility for PipeWire.
        'pipewire-session-manager', # Session manager for PipeWire.
        'pipewire-zeroconf', # Zeroconf (mDNS) support for PipeWire.
        'polkit',  # privilege escalation
        'lxsession',  # privilege escalation gui 'auth agent' (we run lxpolkit)
        'postgresql', # PostgreSQL database server.
        'postgresql-libs', # Libraries for PostgreSQL client applications.
        'postgresql-old-upgrade', # Tools for upgrading older PostgreSQL databases.
        'powertop', # Power consumption monitoring and optimization tool.
        'networkmanager', # Network connection manager for Wi-Fi, Ethernet, etc.
        'network-manager-applet', # System tray applet for NetworkManager.
        'networkmanager-openconnect', # OpenConnect VPN plugin for NetworkManager.
        'networkmanager-openvpn', # OpenVPN plugin for NetworkManager.
        'networkmanager-pptp', # PPTP VPN plugin for NetworkManager.
        # 'networkmanager-qt5', # Qt5 bindings for NetworkManager.
        'networkmanager-vpnc', # VPNC plugin for NetworkManager.
        'nm-connection-editor', # GUI for editing NetworkManager connections.
        'arandr', # GUI for managing screen resolution and layout (XRandR frontend).
        'laptop-detect', # Tool to detect if the system is a laptop.
        'lxappearance', # GUI for customizing GTK themes and appearance.
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
        'ttf-ibm-plex', # IBM’s versatile font family for various styles.
        'ttf-inconsolata', # Monospaced font for coding and terminals.
        'ttf-iosevka-nerd', # Iosevka font with Nerd Fonts symbols.
        'ttf-jetbrains-mono', # Monospaced font for developers by JetBrains.
        'ttf-jetbrains-mono-nerd', # JetBrains Mono with Nerd Fonts symbols.
        'ttf-lato', # Modern sans-serif font family.
        'ttf-liberation', # Free alternative to Microsoft fonts (Arial, Times, etc.).
        'ttf-linux-libertine', # High-quality serif font family.
        'ttf-linux-libertine-g', # Graphite-enabled version of Linux Libertine.
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
        'discord',
        'dunst', # A highly configurable and lightweight notification daemon.
        'feh',
        'xorg-xkill', # Kill a client by its X resource modKey + Escape
        'xfce4-taskmanager', # CTRL+SHIFT+ESC
        'nomacs', # nomacs is a free, open source image viewer
        'gparted', # graphical partition tool
        'libreoffice-fresh',
        'vlc-plugin-ffmpeg',
        'breeze-gtk', # dark gtk theme
    ])

    _aur([
        'blueberry', # Bluetooth configuration tool with a GUI.
        'acpilight', # Backlight control for laptops and desktops, replacing xbacklight.
        'xautolock', # An automatic X screen-locker/screen-saver
        'archlinux-logout-git', # Custom logout scripts for Arch Linux.
        'arcolinux-logout',
        'wkhtmltopdf-bin', # Tool for converting HTML to PDF using WebKit (binary).
    ])

    # NOTE: this must run AFTER _packages/_aur above. Several of these paths are
    # package-owned (upower ships /etc/UPower/UPower.conf, i3lock-color ships
    # /etc/pam.d/i3lock), so deploying them before pacman installs those
    # packages means pacman silently overwrites our version with its default.
    # That is exactly how the custom UPower battery thresholds got lost.
    # _copy, never _link: everything here is root-owned config under /etc, and a
    # symlink into this repo (writable by elmeri) would let anything running as
    # elmeri rewrite config that root executes -- udev rules and PAM auth stacks
    # most of all. Tradeoff: editing files/ no longer takes effect immediately,
    # so re-run this to redeploy.
    _copy({
        # 'elmeri': '/var/lib/AccountsService/users/elmeri',
        # 'elmeri.png': '/var/lib/AccountsService/icons/elmeri',
        # '99-disable-sleep.sh': '/etc/X11/xinit/xinitrc.d/99-disable-sleep.sh',
        'backlight.rules': '/etc/udev/rules.d/backlight.rules',
        'hosts': '/etc/hosts',
        '30-touchpad.conf': '/etc/X11/xorg.conf.d/30-touchpad.conf',
        'environment': '/etc/environment',
        'UPower.conf': '/etc/UPower/UPower.conf',
        'awesome_sddm.conf': '/etc/sddm.conf.d/awesome_sddm.conf',

        # Fingerprint auth (pam_fprintd.so). Each of these is the distro default
        # plus one 'auth sufficient' line, which must sit above the include so
        # PAM reaches it before pam_unix prompts for a password.
        'sudo': '/etc/pam.d/sudo',
        'polkit-1': '/etc/pam.d/polkit-1',
        'i3lock': '/etc/pam.d/i3lock',

        # Fingerprint gate on every ssh-agent key use. Paired with
        # 'AddKeysToAgent confirm' in ~/.ssh/config, which is what makes
        # ssh-agent call the askpass helper before each signature.
        'ssh-agent-fprint-askpass.conf': '/etc/systemd/user/ssh-agent.service.d/fprint-askpass.conf',
    })

    # Separate call only because this one has to be executable. root-owned 755
    # is the whole gate: if elmeri can write it, anything running as elmeri
    # replaces it with 'exit 0'.
    _copy({'ssh-askpass-fprint': '/usr/local/bin/ssh-askpass-fprint'}, mode='755')

    _lineinfile({'/etc/pam.d/sddm': 'auth        sufficient  pam_succeed_if.so user ingroup nopasswdlogin'})
    try:
        _run([
            'sudo udevadm control --reload-rules',
            'sudo groupadd -r nopasswdlogin',
            'sudo usermod -a -G video elmeri',
            'sudo usermod -a -G nopasswdlogin elmeri',
        ])
    except:  # pragma: no cover - groups/rules may already be set up
        pass

    _enable([
        'NetworkManager',
        'bluetooth',
        'syncthing@elmeri',
        'tlp',
        'upower',
    ], try_now=True)

    _run([
        'systemctl --user enable --now ssh-agent.service', # no sudo! https://wiki.archlinux.org/title/SSH_keys#Start_ssh-agent_with_systemd_user
        'systemctl --user daemon-reload', # pick up fprint-askpass.conf drop-in
    ])


@api
def nvidia_prime():
    "Install nvidia prime"
    # https://wiki.archlinux.org/title/PRIME#PRIME_render_offload
    _packages([
        'nvidia-prime',
        'mesa-utils',
        'vulkan-tools',
    ])
    _aur([
        'nvidia-prime-rtd3pm', # Configure your discrete NVIDIA GPU to power down when not in use.
    ])
    # cat /sys/bus/pci/devices/0000:03:00.0/power/runtime_status


@api
def latex():
    "Install latex"
    _packages([
        'texlive-basic',
        'texlive-latex',
        'texlive-binextra',
        'texlive-latexrecommended',
        'texlive-fontsrecommended',
        'texlive-fontsextra',
        'texlive-xetex',
        'texlive-luatex',
        'texlive-latexextra',
        'texlive-pictures',
        'texlive-bibtexextra',
    ])

@api
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

    _run([
        'chmod 755 /home/elmeri' # nextcloud needs this.
    ])
    _run([f"sudo sed -i 's/;extension={ext}/extension={ext}/g' /etc/php/php.ini" for ext in php_extensions])


    _enable(['nginx', 'php-fpm'])

