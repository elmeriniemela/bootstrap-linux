#!/usr/bin/python3

import subprocess
import os
import sys
from contextlib import contextmanager
import re

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FILES_DIR = os.path.join(CURRENT_DIR, 'files')
HOME_DIR = os.path.expanduser('~')

@contextmanager
def _quittable():
    try:
        yield
    except (EOFError, KeyboardInterrupt):
        print("Bye")


class _lazyfunction:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.func(*self.args, **self.kwargs)


def _path(path):
    if path.startswith('~/'):
        formatted = os.path.join(os.path.expanduser('~'), path[2:])
    else:
        formatted = path
    return formatted


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
                    if callable(dependencies):
                        dependencies()
                    elif isinstance(dependencies, list):
                        _run(dependencies, **kwargs)
                    else:
                        raise TypeError(f'Expected a list or a function for dependencies, got {type(dependencies)!r}')
                    _run([command], **kwargs)
                else:
                    raise


def _description(desc_str):
    print(desc_str)

def _packages(list_of_packages):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '
    _run([
        f'{prepend}pacman -S --noconfirm ' + ' '.join(list_of_packages)
    ])

def _aur(list_of_packages):
    _run([
        'yay -S --noconfirm ' + ' '.join(list_of_packages)
    ])


def _copy(files_dict):
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '
    for fname, dest_path in files_dict.items():
        _run([f'{prepend}cp {os.path.join(FILES_DIR, fname)} {dest_path}'])


class _Monitor():
    def __init__(self, name, width, height, x=0, y=0):
        self.name = name
        self.width = int(width)
        self.height = int(height)
        self.x = int(x)
        self.y = int(y)
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
        prim_flag = ' --primary' if self.primary else ''
        return f'--output {self.name}{prim_flag} --mode {self.width}x{self.height} --pos {self.x}x{self.y}'

    def __repr__(self):
        return str(self)


def monitor():
    '''Autoconfigure dual monitor with xrandr
    '''

    output = subprocess.check_output("xrandr -q --current", shell=True, encoding='utf-8')
    monitors = []
    lines = output.splitlines()
    for i, line in enumerate(lines):
        match = re.findall(r'^([\w-]+) connected', line)
        if match and i < len(lines):
            name = match[0]
            max_res_line = lines[i+1]
            res_match = re.findall(r'[\s]*(\d+)x(\d+)', max_res_line)
            if res_match:
                width, height = res_match[0]
                monitors.append(_Monitor(name, width, height))

    if len(monitors) != 2:
        command = 'xrandr --auto'
    else:
        below = min(monitors)
        below.primary = True

        above = max(monitors)

        below.x = above.width // 2 - below.width // 2
        below.y = above.height

        command = 'xrandr ' + ' '.join(str(m) for m in monitors)

    _run([command])



def tmc_cli():
    '''Installs TMC CLI
    '''
    _run(['curl -0 https://raw.githubusercontent.com/testmycode/tmc-cli/master/scripts/install.sh | bash'])




def battery():
    '''Linux tlp install
    '''
    _run([
        'sudo pacman -S tlp',
        'sudo systemctl enable --now tlp',
        # 'sudo systemctl enable --now tlp-sleep.service',
    ])



def pyflame():
    '''Install pyflame
    '''
    INSTALL_PATH = _path('~/.local/lib')
    _run([
        'sudo pacman -S autoconf automake autotools-dev g++ pkg-config python-dev python3-dev libtool make',
        f'git clone https://github.com/uber/pyflame.git {INSTALL_PATH}',
        f'cd {INSTALL_PATH}/pyflame',
        'sudo ./autogen.sh',
        'sudo ./configure',
        'sudo make',
        'sudo make install'
    ])


def update():
    '''Update the system
    '''
    _run([
        'sudo pacman-mirrors -f',
        'sudo pacman -Syyu --noconfirm',
        'yay -Syu  --noconfirm',
        'inxi -Fxxxza --no-host',
        # FIX: Device-2: NVIDIA GM108M [GeForce 940MX] driver: N/A
        # 'sudo modprobe nvidia',
    ])


def serial():
    '''Print machine serial number
    '''
    _packages(['dmidecode'])
    _run([
        'dmidecode -s system-serial-number',
    ])


def distro():
    '''Commands needed for empty arch based distro install
    Post-install dependencies
        * ln -sf /usr/share/zoneinfo/Europe/Helsinki /etc/localtime
        * hwclock --systohc
        * pacman -S dhcpcd vim git python python-pip
        * systemctl enable dhcpcd --now
        * pacman -S grub efibootmgr
        * grub-install --target=x86_64-efi --efi-directory=boot --bootloader-id=GRUB
        * grub-mkconfig -o /boot/grub/grub.cfg
        * visudo # uncomment wheel
    '''
    _packages([
        'sudo',
        'xorg',
        'lightdm',
        'lightdm-gtk-greeter',
        'lightdm-gtk-greeter-settings',
        'awesome',
        'base-devel',
        'networkmanager',
        'code',
        'firefox',
        'veracrypt',
        'sshpass',
        'thunderbird',
        'bind-tools',
        'vim',
        'htop',
        'zathura-pdf-mupdf',
        'konsole', # Terminal configured to awesome
        'bash-completion',
        'ttf-bitstream-vera', # Fix vscode fonts
        'ttf-droid',
        'ttf-roboto',
        'pcmanfm', # Light filemanager
        'alsa-utils',
        'pulseaudio',
        'pulseaudio-alsa',
        'pavucontrol',
        'arandr',
        'udisks2', # For easy mount 'udisksctl mount -b /dev/sdb1',
        'unzip',
        'zip',
        'openssh', # SSH client
        'network-manager-applet',
        'notification-daemon',
        'nm-connection-editor', # Wifi selections
        'xorg-xev',
        'xarchiver', # browse zip files
        'slock',  # Screenlock
        'rtorrent',
    ])

    _run([
        'systemctl enable --now NetworkManager',
        'systemctl enable --now avahi-daemon',
        'systemctl enable --now lightdm',
        "sed -i '/^#en_US.UTF-8/s/^#//g' /etc/locale.gen",
        "sed -i '/^#fi_FI.UTF-8/s/^#//g' /etc/locale.gen",
        'locale-gen',
        'localectl --no-convert set-x11-keymap fi pc104',
        'echo "arch" > /etc/hostname',
        'useradd -m -G video,wheel -s /bin/bash elmeri',
        'passwd elmeri',
        'chown elmeri:elmeri /opt',
    ])
    _copy({
        'backlight.rules': '/etc/udev/rules.d/backlight.rules',
        'hosts': '/etc/hosts',
        'locale.conf': '/etc/locale.conf',
    })

def apps():
    '''User space apps, cannot be run as root. Run after distro.
    '''
    if os.geteuid() == 0:
        print("Do not run this as root")
        return

    if not os.path.exists(_path('/opt/yay')):
        _run([
            'git clone https://aur.archlinux.org/yay.git /opt/yay',
            'cd /opt/yay',
            'makepkg -si',
        ])

    _aur([
        'lightdm-webkit-theme-aether',
        'whatsapp-nativefier-dark',
        'slack-desktop',
        'teams',
        'inxi', # Command line system information script for console
        'timeshift',  # Backups
    ])

    if not os.path.exists(_path('~/.config/awesome-copycats')):
        _run([
            'git clone --recursive https://github.com/elmeriniemela/awesome-copycats.git ~/.config/awesome-copycats',
            'ln -s ~/.config/awesome-copycats ~/.config/awesome'
        ])




def dotfiles():
    ''' This setups basic configuration.
        * Generate global bashrc
        * Clone dotfiles
    '''
    if os.geteuid() == 0:
        print("Do not run this as root")
        return

    line = f'[ -r {FILES_DIR}/global.bashrc   ] && . {FILES_DIR}/global.bashrc'
    filename = '/etc/bash.bashrc'
    _run([
        f"grep -qxF '{line}' {filename} || echo '{line}' | sudo tee -a {filename}",
    ])
    if not os.path.exists(_path('~/.dotfiles')):
        _run([
            '/usr/bin/git clone --bare https://github.com/elmeriniemela/dotfiles.git $HOME/.dotfiles',
            '/usr/bin/git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME reset --hard',
            '/usr/bin/git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME config --local status.showUntrackedFiles no',
        ])

def material_awesome():
    '''Install material-awesome
    '''
    _run([
        'git clone https://github.com/HikariKnight/material-awesome.git ~/.config/material-awesome',
        'sudo pacman -S rofi compton xclip gnome-keyring polkit --noconfirm',
        'yay -S i3lock-fancy-git --noconfirm',
    ])


def flameshot():
    '''Build flameshot from source
    '''
    # Global shortcuts -> Spectacle -> Disable all
    # Add -> Graphics -> Flameshot
    INSTALL_DIR = '/opt/flameshot'
    _run([
        f'sudo mkdir {INSTALL_DIR} -p',
        # Compile-time
        'sudo pacman -S base-devel git qt5-base qt5-tools --noconfirm',

        # Run-time
        'sudo pacman -S qt5-svg --noconfirm',
    ])
    try:
        _run([
            f'sudo git clone https://github.com/lupoDharkael/flameshot.git {INSTALL_DIR}',
        ])
    except:
        _run([
            f'cd {INSTALL_DIR}',
            f'sudo git pull',
        ])

    _run([f'sudo mkdir {INSTALL_DIR}/build -p'])

    _run([
        f'cd {INSTALL_DIR}/build',
        'sudo qmake ../',
        'sudo make',
        'sudo make install',
    ])


def add_ssh(filename):
    '''Creates ssh private and public key pair,
    adds it to ~/.ssh/config,
    and copies the public key to clipboard
    '''
    _run(
        [
            f'ssh-keygen -C ansible@sprintit.fi -t rsa -b 4096 -N "" -f ~/.ssh/{filename}',
            f"cat {_path(f'~/.ssh/{filename}.pub')} | xclip -selection clipboard"
        ],
        dependencies=['sudo pacman -S --noconfirm xclip']
    )

def password(length=32):
    '''Generate secure password and copy to clipboard
    '''
    _run(
        [
            f'< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c{length} | xclip -selection clipboard',
        ],
        dependencies=['sudo pacman -S --noconfirm xclip']
    )



def _get_odoo_path(branch='13.0', repo='odoo'):
    return _path(f'~/Code/work/odoo/{branch[:-2]}/{repo}')

def odoo_venv(branch='13.0'):
    '''Creates odoo venv
    '''
    os.makedirs(_path('~/.venv'), exist_ok=True)
    venv_name = 'odoo{}'.format(branch[:-2])
    odoo_path = _get_odoo_path(branch)

    if not os.path.isdir(_path('~/.venv/' + venv_name)):
        if float(branch) <= 10.0:
            _run([
                'cd ~/.venv',
                'python2 -m virtualenv -p python2 {}'.format(venv_name),
            ], dependencies=[
                'sudo pacman -S --noconfirm python2',
                'sudo pacman -S --noconfirm python2-virtualenv',
            ])

        else:
            _run([
                'cd ~/.venv',
                'python3 -m venv {}'.format(venv_name),
            ])

    _run([
        f'sed "/psycopg2/d" {odoo_path}/requirements.txt | /home/elmeri/.venv/{venv_name}/bin/pip install -r /dev/stdin psycopg2',
    ], dependencies=_lazyfunction(_odoo_deps, branch=branch))

def odoo_deps(branch='12.0'):
    '''Installs odoo deps
    '''
    if float(branch) >= 11.0:
        # Bank connector deps
        venv_name = 'odoo{}'.format(branch[:-2])
        _run([
            'sudo pacman -S xmlsec pwgen libxml2 pkg-config --noconfirm',
            f'/home/elmeri/.venv/{venv_name}/bin/pip install zeep cryptography xmlsec'
        ])

    if float(branch) < 12.0:
        _run([
            'sudo pacman -S --noconfirm nodejs-less',
            'sudo pacman -S --noconfirm npm',
            'sudo npm install --global less-plugin-clean-css',
        ])

    _run([
        'sudo pacman -S postgresql --noconfirm',
        'yay -S wkhtmltopdf-static --noconfirm'
    ])
    try:
        _run([
            "sudo -u postgres initdb --locale $LANG -E UTF8 -D '/var/lib/postgres/data/'",
            'sudo systemctl enable --now postgresql.service',
            'sudo su - postgres -c "createuser -s $USER"',
        ])
    except:
        pass


def odoo(branch='13.0'):
    '''Installs odoo, enterprise and all the dependencies
    '''

    odoo_path = _get_odoo_path(branch, repo='odoo')

    _get_odoo_source(repo='odoo', branch=branch)
    if float(branch) >= 9.0:
        _get_odoo_source(repo='enterprise', branch=branch)


    with open(f'{FILES_DIR}/.odoorc.conf') as f_read:
        data = f_read.read()

    with open(f'{odoo_path}/.odoorc.conf', 'w') as f_write:
        f_write.write(
            data.format(odoo_version=branch[:-2])
        )

    _odoo_venv(branch)


def _get_odoo_source(repo='odoo', branch='13.0'):
    import glob
    from distutils.dir_util import copy_tree
    odoo_path = _get_odoo_path(branch, repo=repo)
    odoo_base_path = os.path.dirname(odoo_path)
    os.makedirs(odoo_base_path, exist_ok=True)

    cleaning_args = [
        f'cd {odoo_path}',
        f'/usr/bin/git reset --hard',
        f'/usr/bin/git clean -xfdf',
        f'/usr/bin/git checkout {branch}',
        f'/usr/bin/git pull',
    ]
    if os.path.isdir(odoo_path):
        try:
            _run(cleaning_args)
            print(f"Latest pull done.. exiting now")
            return
        except:
            pass

    folders = [path for path in glob.glob(_path('~/Code/work/odoo/*/*')) if os.path.isdir(path)]
    print("Checking folders for existing odoo installations:\n", ' \n'.join(folders))
    for full_path in folders:
        name = os.path.basename(full_path)
        if name == repo:
            print(f"Found existing '{repo}' installation at {full_path}")
            print("Copying the installation is faster than cloning..")
            copy_tree(full_path, odoo_path)
            _run(cleaning_args)
            break
    else:
        _run([
            f'cd {odoo_base_path}',
            f'/usr/bin/git clone https://github.com/odoo/{repo}.git {odoo_path} -b {branch}',
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
    for key, value in locals_dict.items():
        sign = inspect.signature(value)
        params = []
        for string_name, parameter in sign.parameters.items():
            params.append(str(parameter))
        print("def {}({}):".format(value.__name__, ', '.join(params)))
        print("    {}".format(value.__doc__))


def _bash_complete(completion_iterable, str_index='1', arg=''):
    if str_index == '1':
        available = [c for c in completion_iterable if c.startswith(arg)]
        print(f"[{', '.join(available)}]")
    else:
        print([])

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


    if args.function == '_bash_complete':
        _bash_complete(LOCALS, *args.args)
        return 0

    func = LOCALS[args.function]
    with _quittable():
        func(*args.args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
