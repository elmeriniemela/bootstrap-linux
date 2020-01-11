#!/usr/bin/python3

import subprocess
import os
import sys

current_dir = os.path.dirname(os.path.realpath(__file__))
home_dir = os.path.expanduser('~')


def _path(path):
    if path.startswith('~/'):
        formatted = os.path.join(os.path.expanduser('~'), path[2:])
    else:
        formatted = path
    return formatted


def _run(commands, **kwargs):
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
            output = subprocess.run(command, **default_kwargs)


def tmc_cli():
    '''Installs TMC CLI
    '''
    _run(['curl -0 https://raw.githubusercontent.com/testmycode/tmc-cli/master/scripts/install.sh | bash'])


def onedrive():
    '''Installs OneDrive cli
    '''
    _run([
        'sudo apt install -y libcurl4-openssl-dev',
        'sudo apt install -y libsqlite3-dev',
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
    '''Ubuntu performance related fixes
    '''
    _run([
        'sudo apt install cpufrequtils -y',
        '''grep -qxF 'GOVERNOR="performance"' /etc/default/cpufrequtils || echo 'GOVERNOR="performance"' | sudo tee -a /etc/default/cpufrequtils  ''',
        'sudo apt install indicator-cpufreq -y',
        'sudo apt install htop',
    ])


def pyflame():
    '''Install pyflame
    '''
    INSTALL_PATH = _path('~/.local/lib')
    _run([
        'sudo apt install autoconf automake autotools-dev g++ pkg-config python-dev python3-dev libtool make',
        f'git clone https://github.com/uber/pyflame.git {INSTALL_PATH}',
        f'cd {INSTALL_PATH}/pyflame',
        'sudo ./autogen.sh',
        'sudo ./configure',
        'sudo make',
        'sudo make install'
    ])


def apps():
    '''Installs all useful apps 
    i.e git, vim, slack, thunderbird, vscode etc..
    '''
    _run([
        'sudo apt -y update',
        'sudo apt -y upgrade',
        'sudo apt install -y vim',
        'sudo apt install pinta -y',
        'sudo apt install -y arandr',
        'sudo apt install -y autorandr',
        'sudo apt install -y thunderbird'
        'sudo apt install -y libreoffice',
        'sudo apt install -y python3-pip',
        'pip3 install virtualenv',

        'sudo apt install snapd',
        'sudo snap install slack --classic',
        'sudo snap install code --classic',
        ])


def add_ssh(filename):
    '''Creates ssh private and public key pair,
    adds it to ~/.ssh/config,
    and copies the public key to clipboard
    '''
    import pyperclip
    _run([
        'ssh-keygen -C ansible@sprintit.fi -t rsa -b 4096 -N "" -f ~/.ssh/{}'.format(filename),
    ])
    with open(_path('~/.ssh/{}.pub'.format(filename))) as f:
        pyperclip.copy(f.read())


def _get_odoo_path(branch='13.0', repo='odoo'):
    return _path(f'~/Code/work/odoo/{branch[:-2]}/{repo}')

def _odoo_venv(branch='13.0', python='python3.6'):
    '''Creates odoo venv
    '''
    os.makedirs(_path('~/.venv'), exist_ok=True)
    venv_name = 'odoo{}'.format(branch[:-2])
    odoo_path = _get_odoo_path(branch)

    if not os.path.isdir(_path('~/.venv/' + venv_name)):
        _run([
            'cd ~/.venv',
            'python3 -m virtualenv -p {} {}'.format(python, venv_name),
        ])
    _run([
        '/home/elmeri/.venv/{}/bin/pip install -r {}/requirements.txt'.format(
            venv_name, odoo_path),
    ])

def _odoo_deps(branch='12.0'):
    '''Installs odoo deps
    '''
    if float(branch) < 12.0:
        _run([
            'sudo apt install nodejs -y',
            'sudo apt install libssl1.0-dev -y',
            'sudo apt install nodejs-dev -y',
            'sudo apt install node-gyp -y',
            'sudo apt install npm -y',
            'sudo npm install -g less -y',
        ])

    if float(branch) <= 10.0:
        _run([
            'sudo apt install python-dev -y',
            'sudo apt install libjpeg-dev -y',
            'sudo apt install libjpeg8-dev -y',
        ])
    _run([
        'sudo apt install libxml2-dev -y',
        'sudo apt install libxslt-dev -y',
        'sudo apt install libevent-dev -y',
        'sudo apt install libsasl2-dev -y',
        'sudo apt install libldap2-dev -y',

        'sudo apt install postgresql -y',
    ])
    try:
        _run([
            'sudo su - postgres -c "createuser -s $USER"',
        ])
    except:
        pass


def odoo(branch='13.0', python='python3.6'):
    '''Installs odoo, enterprise and all the dependencies
    '''
    
    _odoo_deps(branch)
    odoo_path = _get_odoo_path(branch, repo='odoo')
    
    _get_odoo_source(repo='odoo', branch=branch)
    _get_odoo_source(repo='enterprise', branch=branch)

    _run([
        'cp {}/.odoorc.conf {}/'.format(current_dir, odoo_path),
    ])
    _odoo_venv(branch, python)


def _get_odoo_source(repo='odoo', branch='13.0'):
    import glob
    from distutils.dir_util import copy_tree
    odoo_path = _get_odoo_path(branch, repo=repo)
    odoo_base_path = os.path.dirname(odoo_path)
    os.makedirs(odoo_base_path, exist_ok=True)
    folders = [path for path in glob.glob(_path('~/Code/work/odoo/*/*')) if os.path.isdir(path)]
    print("Checking folders for existing odoo installations:\n", ' \n'.join(folders))
    for full_path in folders:
        name = os.path.basename(full_path)
        if name == repo:
            print(f"Found existing '{repo}' installation at {full_path}")
            print("Copying the installation is faster than cloning..")
            copy_tree(full_path, odoo_path)
            _run([
                f'cd {odoo_path}',
                f'/usr/bin/git reset --hard',
                f'/usr/bin/git checkout {branch}',
                f'/usr/bin/git pull',
            ])
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
        and not k.startswith('_')
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
    to ~/
    '''
    try:
        os.symlink(
            src=os.path.join(current_dir, ".bash_aliases"),
            dst=os.path.join(home_dir, ".bash_aliases")
        )

    except Exception as error:
        print(error)

    try:
        os.symlink(
            src=os.path.join(current_dir, ".notes"),
            dst=os.path.join(home_dir, ".notes")
        )
    except Exception as error:
        print(error)


if __name__ == '__main__':
    if sys.version_info[0] < 3:
        print("Only supported in python 3")
        exit()

    import argparse

    local_functions = _filter_locals(locals())
    
    if len(sys.argv) == 1:
        _print_functions(local_functions)
        
    parser = argparse.ArgumentParser(description='Setup your Ubuntu system')

    parser.add_argument(
        'function', help="Install function to run (use 0 params to list function signatures)")

    parser.add_argument('args', metavar='arg', type=str, nargs='*',
                        help='argument for the function')

    args = parser.parse_args()


    func = local_functions[args.function]
    func(*args.args)
