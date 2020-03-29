#!/usr/bin/python3

import subprocess
import os
import sys
from contextlib import contextmanager


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


def tmc_cli():
    '''Installs TMC CLI
    '''
    _run(['curl -0 https://raw.githubusercontent.com/testmycode/tmc-cli/master/scripts/install.sh | bash'])


def git():
    '''Configure git
    '''
    _run([
        'git config --global user.email "niemela.elmeri@gmail.com"',
        'git config --global user.name "Elmeri Niemelä"',
        'git config --global credential.helper store',
    ])


def lightdm():
    '''Installs and configures lightdm
    '''
    _run([
        'sudo pacman -S --noconfirm lightdm',
        'sudo dpkg-reconfigure lightdm',
        'sudo pacman -S --noconfirm slick-greeter',
        'lightdm --show-config',
    ])



def onedrive():
    '''Installs OneDrive cli
    '''
    _run([
        'sudo pacman -S --noconfirm libcurl4-openssl-dev',
        'sudo pacman -S --noconfirm libsqlite3-dev',
        'sudo snap install --classic dmd && sudo snap install --classic dub',
        f'cd {_path("/opt")}'
        f'git clone https://github.com/skilion/onedrive.git'
        'cd /opt/onedrive',
        'make',
        'sudo make install',
        'systemctl --user enable onedrive',
        'systemctl --user start onedrive',
    ])


def performance():
    '''Linux performance related fixes
    '''
    _run([
        # 'sudo pacman -S cpufrequtils',
        # '''grep -qxF 'GOVERNOR="performance"' /etc/default/cpufrequtils || echo 'GOVERNOR="performance"' | sudo tee -a /etc/default/cpufrequtils  ''',
        # 'sudo pacman -S indicator-cpufreq',
        'sudo pacman -S --noconfirm htop',
    ])

def battery():
    '''Linux tlp install
    '''
    _run([
        'sudo pamac install tlp',
        'sudo systemctl enable --now tlp'
        'sudo systemctl enable --now tlp-sleep.service'
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
        'sudo pacman -Syyu',
        'yay -Syu'
        'inxi -Fxxxza --no-host',
        # FIX: Device-2: NVIDIA GM108M [GeForce 940MX] driver: N/A
        # 'sudo modprobe nvidia',
    ])



def apps():
    '''Installs all useful apps
    i.e git, vim, slack, thunderbird, vscode etc..
    '''
    _run([
        'sudo pacman -Syyu --noconfirm',
        'sudo pacman -S yay --noconfirm',
        'yay VSCode',
        'yay -S slack-desktop',
        'sudo pacman -S veracrypt --noconfirm',
        'sudo pacman -S sshpass --noconfirm',
        'sudo pacman -S bind-tools --noconfirm', # nslookup
        'sudo pacman -S vim --noconfirm',
        'sudo pacman -S zathura-pdf-mupdf --noconfirm', # Vim like .epub reader
    ])

def backups():
    '''Installs timeshift
    '''
    _run([
        'sudo pacman -S timeshift --noconfirm',
    ])



def flameshot():
    '''Build flameshot from source
    '''
    # Global shortcuts -> Spectacle -> Disable all
    # Add -> Graphics -> Flameshot
    INSTALL_DIR = '/opt/flameshot'
    os.makedirs(INSTALL_DIR, exist_ok=True)
    try:
        _run([
            f'sudo git clone https://github.com/lupoDharkael/flameshot.git {INSTALL_DIR}',
        ])
    except:
        _run([
            f'cd {INSTALL_DIR}',
            f'sudo git pull',
        ])

    os.makedirs(f'{INSTALL_DIR}/build', exist_ok=True)

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

def _odoo_venv(branch='13.0'):
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
        'sed "/psycopg2/d" {}/requirements.txt | /home/elmeri/.venv/{}/bin/pip install -r /dev/stdin psycopg2'.format(
            odoo_path, venv_name),
    ], dependencies=_lazyfunction(_odoo_deps, branch=branch))

def _odoo_deps(branch='12.0'):
    '''Installs odoo deps
    '''
    if float(branch) < 12.0:
        _run([
            'sudo pacman -S --noconfirm nodejs-less',
            'sudo pacman -S --noconfirm npm',
            'sudo npm install --global less-plugin-clean-css',
        ])

    _run([
        # TODO: Test if needed on manjaro
        # 'sudo pacman -S libxml2-dev',
        # 'sudo pacman -S libxslt-dev',
        # 'sudo pacman -S libevent-dev',
        # 'sudo pacman -S libsasl2-dev',
        # 'sudo pacman -S libldap2-dev',

        'sudo pacman -S postgresql',
        'sudo pacman -S wkhtmltopdf'
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


def bash():
    '''Symling .bash_aliases and .notes from this directory
    to '~/'
    '''
    def symlink_home(fname):
        dest = os.path.join(HOME_DIR, fname)
        if os.path.islink(dest):
            os.remove(dest)
        src = os.path.join(FILES_DIR, fname)
        print(f'Symlink: ~/{fname} -> {src}')
        try:
            os.symlink(src=src, dst=dest)
        except Exception as error:
            print(error)

    symlink_home('.notes')
    symlink_home('.bash_aliases')
    original = os.path.join(HOME_DIR, '.bashrc')
    if os.path.exists(original):
        os.remove(original)
    symlink_home('.bashrc')



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
