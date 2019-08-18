import subprocess
import os
current_dir = os.path.dirname(os.path.realpath(__file__))
home_dir = os.path.expanduser('~')


def path(path):
    if path.startswith('~/'):
        formatted = os.path.join(os.path.expanduser('~'), path[2:])
    else:
        formatted = path
    return formatted


def run(commands, **kwargs):
    for command in commands:
        if command.startswith('cd'):
            folder = command[3:]
            os.chdir(path(folder))
        else:
            default_kwargs = {
                'shell': True,
                'stderr': subprocess.PIPE,
                'check': True,
                'encoding': 'utf-8'
            }
            default_kwargs.update(kwargs)
            output = subprocess.run(command, **default_kwargs)


def tmc_cli():
    '''Installs TMC CLI
    '''
    run(['curl -0 https://raw.githubusercontent.com/testmycode/tmc-cli/master/scripts/install.sh | bash'])


def onedrive():
    '''Installs OneDrive cli
    '''
    import git
    run([
        'sudo apt install -y libcurl4-openssl-dev',
        'sudo apt install -y libsqlite3-dev',
        'sudo snap install --classic dmd && sudo snap install --classic dub',
    ])
    repo = git.Git(path('/opt'))
    repo.clone('https://github.com/skilion/onedrive.git')
    run([
        'cd /opt/onedrive',
        'make',
        'sudo make install',
        'systemctl --user enable onedrive',
        'systemctl --user start onedrive',
    ])


def performance():
    '''Ubuntu performance related fixes
    '''
    run([
        'sudo apt install cpufrequtils -y',
        '''echo 'GOVERNOR="performance"' | sudo tee -a /etc/default/cpufrequtils''',
        'sudo apt install indicator-cpufreq -y',
        'sudo apt install htop',
    ])


def python(version='3.7.2'):
    '''Installs specified python version
    '''
    run([
        'sudo apt install -y build-essential',
        'sudo apt install -y checkinstall',
        'sudo apt install -y libreadline-gplv2-dev',
        'sudo apt install -y libncursesw5-dev',
        'sudo apt install -y libssl-dev',
        'sudo apt install -y libsqlite3-dev',
        'sudo apt install -y tk-dev',
        'sudo apt install -y libgdbm-dev',
        'sudo apt install -y libc6-dev',
        'sudo apt install -y libbz2-dev',
        'sudo apt install -y zlib1g-dev',
        'sudo apt install -y openssl',
        'sudo apt install -y libffi-dev',
        'sudo apt install -y python3-dev',
        'sudo apt install -y python3-setuptools',
        # for python 2
        'sudo apt install -y python-dev',
        'sudo apt install -y python-setuptools',
        'sudo apt install -y wget',
        'mkdir /tmp/Python{}'.format(version),
        'cd /tmp/Python{}'.format(version),
        'wget https://www.python.org/ftp/python/{}/Python-{}.tar.xz'.format(
            version, version),
        'tar xvf Python-{}.tar.xz'.format(version),
        'cd /tmp/Python{}/Python-{}'.format(version, version),
        './configure',
        'sudo make altinstall',
    ])


def pyflame():
    '''Install pyflame
    '''
    import git
    run([
        'sudo apt install autoconf automake autotools-dev g++ pkg-config python-dev python3-dev libtool make',
    ])
    repo = git.Git('/opt')
    repo.clone('https://github.com/uber/pyflame.git')
    run([
        'cd /opt',
        'sudo ./autogen.sh',
        'sudo ./configure',
        'sudo make',
        'sudo make install'
    ])


def apps():
    '''Installs all useful apps 
    i.e git, vim, slack, chromium, vscode etc..
    '''
    run([
        'cd /tmp',
        'wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb',
        'sudo dpkg -i google-chrome-stable_current_amd64.deb',

        'sudo apt -y update',
        'sudo apt -y upgrade',
        'sudo apt install -y vim',
        'sudo apt install pinta -y',
        'sudo apt install -y virtualenv',
        'sudo apt install -y arandr',
        'sudo apt install -y autorandr',

        # 'sudo apt install -y libreoffice',

        'sudo apt install snapd',
        'sudo snap install slack --classic',
        'sudo snap install code --classic',
        'sudo snap install mailspring',
    ])


def add_ssh(filename, host=None):
    '''Creates ssh private and public key pair,
    adds it to ~/.ssh/config,
    and copies the public key to clipboard
    '''
    import pyperclip
    run([
        'ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/{}'.format(filename),
    ])
    with open(os.path.join(os.path.expanduser('~'), '.ssh', 'config'), 'a') as f:
        data = 'IdentityFile ~/.ssh/{}\n'.format(filename)
        if host:
            data = "Host {}\n    ".format(host) + data
        f.write(data)
    with open(path('~/.ssh/{}.pub'.format(filename))) as f:
        pyperclip.copy(f.read())


def psql():
    '''Installs odoo dependencies, like postgres and some pkgs
    Should be ran only once per system
    '''
    # Odoo dependencies
    run([
        'sudo apt install postgresql -y',
        'sudo su - postgres -c "createuser -s $USER"',
        'sudo apt install libxml2-dev -y',
        'sudo apt install libxslt-dev -y',
        'sudo apt install libevent-dev -y',
        'sudo apt install libsasl2-dev -y',
        'sudo apt install libldap2-dev -y',
    ])


def odoo(branch='12.0', python='python3.6'):
    '''Installs odoo
    '''
    import glob
    from distutils.dir_util import copy_tree
    import git
    version = branch[:-2]
    venv_name = 'odoo{}'.format(version)
    odoo_path = path('~/Code/work/odoo/{}/odoo'.format(version))
    os.makedirs(path('~/.venv'), exist_ok=True)
    os.makedirs(odoo_path, exist_ok=True)

    if not os.path.isdir(path('~/.venv/' + venv_name)):
        run([
            'sudo apt install virtualenv -y',
            'cd ~/.venv',
            'virtualenv -p {} {}'.format(python, venv_name),
        ])

    if float(branch) < 12.0:
        run([
            'sudo apt install nodejs -y',
            'sudo apt install libssl1.0-dev -y',
            'sudo apt install nodejs-dev -y',
            'sudo apt install node-gyp -y',
            'sudo apt install npm -y',
            'sudo npm install -g less -y',
        ])

    if float(branch) <= 10.0:
        run([
            'sudo apt install python-dev -y',
            'sudo apt install libjpeg-dev -y',
            'sudo apt install libjpeg8-dev -y',
        ])

    folders = glob.glob(path('~/Code/work/odoo/*/*'))
    for full_path in folders:
        name = os.path.basename(full_path)
        if name == 'odoo':
            print("Found existing odoo installation at", full_path)
            print("Copying the installation is faster than cloning")
            copy_tree(full_path, odoo_path)
            repo = git.Git(odoo_path)
            repo.reset('--hard')
            repo.checkout(branch)
            break
    else:
        repo = git.Git('.')
        repo.clone('https://github.com/odoo/odoo.git',
                   odoo_path, branch=branch)
    run([
        'cp {}/.odoorc.conf {}/'.format(current_dir, odoo_path),
        '/home/elmeri/.venv/{}/bin/pip install -r {}/requirements.txt'.format(
            venv_name, odoo_path),
    ])


def functions_map(local_items):
    excluded = [
        'functions_map',
        'path',
        'run',
    ]
    FUNCTION_MAP = {}
    for key, value in local_items:
        if key not in excluded and callable(value) and value.__module__ == __name__:
            FUNCTION_MAP.update({key: value})

    return FUNCTION_MAP


LOCALS = locals()


def functions():
    '''Lists the available functions
    '''
    import inspect
    excluded = [
        'functions_map',
        'path',
        'run',
        'functions'
    ]
    for key, value in LOCALS.items():
        if key not in excluded and callable(value) and value.__module__ == __name__:
            sign = inspect.signature(value)
            params = []
            for string_name, parameter in sign.parameters.items():
                params.append(str(parameter))
            print("def {}({}):".format(value.__name__, ', '.join(params)))
            print("    {}".format(value.__doc__))


def bash():
    '''Symling .bash_aliases from this directory
    to ~/.bash_aliases
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
    run([
        # TODO: Fix this
        # 'bash {}'.format(path('~/.bash_aliases'))
    ])


if __name__ == '__main__':
    import sys
    import argparse
    if len(sys.argv) == 1:
        functions()
    parser = argparse.ArgumentParser(description='Setup your Ubuntu system')

    parser.add_argument(
        'function', help="Install function to run (use 'functions' to list function signatures)")

    parser.add_argument('args', metavar='arg', type=str, nargs='*',
                        help='argument for the function')

    args = parser.parse_args()

    FUNCTION_MAP = functions_map(locals().items())
    func = FUNCTION_MAP[args.function]
    func(*args.args)
