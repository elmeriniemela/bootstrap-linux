import subprocess, os
current_dir = os.path.dirname(os.path.realpath(__file__))

def path(path):
    if path.startswith('~/'):
        formatted = os.path.join(os.path.expanduser('~'), path[2:])
    else:
        formatted = path
    return formatted

def run(commands):
    for command in commands:
        if command.startswith('cd'):
            folder = command[3:]
            os.chdir(path(folder))
        else:
            try:
                output = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, encoding='utf-8')
            except subprocess.CalledProcessError as e:
                print(e.stdout)
                raise e
            print(output.stdout)


def tmc_cli():
    '''Installs TMC CLI
    '''
    run(['curl -0 https://raw.githubusercontent.com/testmycode/tmc-cli/master/scripts/install.sh | bash'])

def onedrive():
    '''Installs OneDrive cli
    '''
    import git
    run([
        'sudo apt-get install -y libcurl4-openssl-dev',
        'sudo apt-get install -y libsqlite3-dev',
        'sudo snap install --classic dmd && sudo snap install --classic dub',
    ])
    repo = git.Git(path('~/'))
    repo.clone('https://github.com/skilion/onedrive.git')
    run([
        'cd ~/onedrive',
        'make',
        'sudo make install',
        'systemctl --user enable onedrive',
        'systemctl --user start onedrive',
    ])


def togl(deb_dir='/home/elmeri/Downloads'):
    '''Installs toggl
    '''
    run([
        'cd {}'.format(deb_dir),
        'wget http://fr.archive.ubuntu.com/ubuntu/pool/main/g/gst-plugins-base0.10/libgstreamer-plugins-base0.10-0_0.10.36-1_amd64.deb',
        'wget http://fr.archive.ubuntu.com/ubuntu/pool/universe/g/gstreamer0.10/libgstreamer0.10-0_0.10.36-1.5ubuntu1_amd64.deb',
        'sudo dpkg -i libgstreamer*.deb',
        'sudo dpkg -i toggldesktop*.deb',
    ])

def python(version='3.7.2'):
    '''Installs specified python version
    '''
    run([
        'sudo apt-get install -y build-essential',
        'sudo apt-get install -y checkinstall',
        'sudo apt-get install -y libreadline-gplv2-dev',
        'sudo apt-get install -y libncursesw5-dev',
        'sudo apt-get install -y libssl-dev',
        'sudo apt-get install -y libsqlite3-dev',
        'sudo apt-get install -y tk-dev',
        'sudo apt-get install -y libgdbm-dev',
        'sudo apt-get install -y libc6-dev',
        'sudo apt-get install -y libbz2-dev',
        'sudo apt-get install -y zlib1g-dev',
        'sudo apt-get install -y openssl',
        'sudo apt-get install -y libffi-dev',
        'sudo apt-get install -y python3-dev',
        'sudo apt-get install -y python3-setuptools',
        # for python 2 
        'sudo apt-get install -y python-dev',
        'sudo apt-get install -y python-setuptools',
        'sudo apt-get install -y wget',
        'mkdir /tmp/Python{}'.format(version),
        'cd /tmp/Python{}'.format(version),
        'wget https://www.python.org/ftp/python/{}/Python-{}.tar.xz'.format(version, version),
        'tar xvf Python-{}.tar.xz'.format(version),
        'cd /tmp/Python{}/Python-{}'.format(version, version),
        './configure',
        'sudo make altinstall',
    ])

def pip36():
    '''Installs pip3.6 since ubuntu 18.06 python 3 doesn't have pip
    '''
    run(['curl https://bootstrap.pypa.io/get-pip.py | sudo -H python3.6'])

def apps():
    '''Installs all useful apps 
    i.e git, vim, slack, chromium, vscode etc..
    '''
    run([
        'sudo apt-get -y update',
        'sudo apt-get -y upgrade',
        'sudo apt-get install -y vim',
        'sudo apt-get install -y git',
        'sudo apt-get install snapd'
        'sudo snap install slack --classic',
        'sudo apt-get install -y vim',
        'sudo apt-get install -y chromium-browser',

        # VSCode
        'sudo apt-get -y install software-properties-common apt-transport-https wget',
        'wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | apt-key add -',
        'sudo add-apt-repository "deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main"',
        'sudo apt-get -y install code',
    ])

def add_ssh(filename):
    '''Creates ssh private and public key pair,
    adds it to ~/.ssh/config,
    and copies the public key to clipboard
    '''
    import pyperclip
    run([
        'ssh-keygen -t rsa -N "" -f ~/.ssh/{}'.format(filename),
    ])
    with open(os.path.join(os.path.expanduser('~'), '.ssh', 'config'), 'a') as f:
        f.write('IdentityFile ~/.ssh/{}\n'.format(filename))
    with open(path('~/.ssh/{}.pub'.format(filename))) as f:
        pyperclip.copy(f.read())


def odoo_dependencies():
    '''Installs odoo dependencies
    Should be ran only once per system
    '''
    # Odoo dependencies
    run([
        'sudo apt-get install postgresql -y',
        'sudo su - postgres -c "createuser -s $USER"',
        'sudo apt-get install libxml2-dev -y',
        'sudo apt-get install libxslt-dev -y',
        'sudo apt-get install libevent-dev -y',
        'sudo apt-get install libsasl2-dev -y',
        'sudo apt-get install libldap2-dev -y',
    ])

def odoo(branch='12.0', python='python3.7'):
    '''Installs odoo
    '''
    print(branch, python)
    return
    import git
    odoo_folder = 'odoo{}'.format(int(branch))
    odoo_path = path('~/Sites/' + odoo_folder)
    if not os.path.isdir(path('~/.venv')):
        run(['mkdir ~/.venv'])
    if not os.path.isdir(path('~/Sites')):
        run(['mkdir ~/Sites'])
    if not os.path.isdir(path('~/.venv/' + odoo_folder)):
        run([
            'sudo apt install virtualenv -y',
            'cd ~/.venv',
            'virtualenv -p {} {}'.format(python, odoo_folder),
        ])

    if branch == '10.0':
        run([
           'sudo apt-get install nodejs',
           'sudo apt-get install npm',
           'sudo npm install -g less',
        ])

    folders = os.listdir(path('~/Sites'))
    for folder in folders:
        if 'odoo' in folder:
            run([
                'cp -r {} {}'.format(path('~/Sites/'+folder), odoo_path)
            ])
            repo = git.Git(odoo_path)
            repo.reset('--hard')
            repo.checkout(branch)
            break
    else:
        repo = git.Git('.')
        repo.clone('https://github.com/odoo/odoo.git', odoo_path, branch=branch)
    run([
        'cp {}/.odoorc {}/'.format(current_dir, odoo_path),
        '/home/elmeri/.venv/{}/bin/pip install -r {}/requirements.txt'.format(odoo_folder, odoo_path),
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
            FUNCTION_MAP.update({key:value})
    
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

    

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Setup your Ubuntu system')

    parser.add_argument('function', help="Install function to run (use 'functions' to list function signatures)")

    parser.add_argument('args', metavar='arg', type=str, nargs='*',
                    help='argument for the function')


    args = parser.parse_args()

    FUNCTION_MAP = functions_map(locals().items())
    func = FUNCTION_MAP[args.function]
    func(*args.args)

