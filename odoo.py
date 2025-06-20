
import os
from functools import partial
from lib import (
    _path,
    _enable,
    _run,
    _packages,
    _aur,
    api,
)

ODOO_INSTALLS_DEFAULT_DIR = '~/Work'


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


@api
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

@api
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


@api
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


@api
def odoo_tests(db_name, modules=None):
    """Run odoo tests
    """
    ODOO_VERSION_DIR = os.environ['ODOO_VERSION_DIR']
    modules = modules or ','.join(os.listdir())
    _run([f'python {ODOO_VERSION_DIR}/odoo/odoo-bin --conf {ODOO_VERSION_DIR}/odoorc.conf -d {db_name} -i {modules} --test-tags={modules} --stop-after-init'])