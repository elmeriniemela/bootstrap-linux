
import os
from functools import partial
from .lib import (
    _path,
    _enable,
    _run,
    _packages,
    _aur,
    _link,
    _copy,
    api,
    FILES_DIR,
)

ODOO_INSTALLS_DEFAULT_DIR = '~/Odoo/src'


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
def odoo_venv(branch, python=False, odoo_installs_dir=ODOO_INSTALLS_DEFAULT_DIR):
    '''Creates odoo venv
    '''
    venv_name = 'odoo{}'.format(_branch_name(branch))
    venv_home = _path('~/.venv')
    venv_dir = _path('~/.venv/' + venv_name)
    os.makedirs(venv_home, exist_ok=True)
    extra_requirements = _get_odoo_path(branch, odoo_installs_dir, repo='requirements.txt')

    if not os.path.isdir(venv_dir):
        if _odoo_version(branch) <= 10.0:
            _run(
                [
                    f'python2 -m virtualenv --system-site-packages -p python2 {venv_dir}'
                ],
                dependencies=partial(_packages, ['python2', 'python2-virtualenv'])
            )

        else:
            python = python or 'python3'
            _run([
                f'{python} -m venv --system-site-packages {venv_dir}'
            ])

    _run([f'{venv_dir}/bin/pip install dicttoxml num2words ofxparse python-stdnum rlPyCairo'], dependencies=partial(global_odoo_deps, branch=branch))

    if os.path.isfile(extra_requirements):
        _run([
            f'{venv_dir}/bin/pip install -r {extra_requirements}'
        ])

@api
def global_odoo_deps(branch):
    '''Installs odoo deps
    '''
    _packages([
        'npm',
    ])
    if _odoo_version(branch) >= 11.0:
        _packages([
            'xmlsec',
            'pwgen',
            'libxml2',
            'pkg-config',
            'chromium', # for browser tour tests
        ])
    if _odoo_version(branch) < 12.0:
        _run([
            'sudo npm install --global less@3.0.1 less-plugin-clean-css',
        ])

    _run([
        'sudo npm install --global rtlcss',
    ])


    _packages([
        'python-gevent',
        'python-wheel',
        'python-paramiko',
        'python-cryptography',
        'python-openpyxl',
        'python-numpy',
        'python-pandas',
        'python-xmltodict',
        'python-magic',
        'python-odfpy',
        'python-pdfminer',
        'python-pip',
        'python-phonenumbers',
        'python-ldap',
        'python-qrcode',
        # 'python-renderpm',
        'python-setuptools',
        'python-slugify',
        'python-vobject',
        'python-watchdog',
        'python-xlrd',
        'python-xlwt',
        'python-babel',
        'python-chardet',
        'python-dateutil',
        'python-decorator',
        'python-docutils',
        'python-freezegun',
        'python-geoip2',
        'python-pillow',
        'python-jinja',
        # 'python-libsass',
        'python-lxml',
        'python-lxml-html-clean',
        'python-xmlsec',
        'python-passlib',
        'python-polib',
        'python-psutil',
        'python-psycopg2',
        'python-pydot',
        'python-pyopenssl',
        'python-pypdf2',
        'python-rjsmin',
        'python-reportlab',
        'python-requests',
        'python-pytz',
        'python-werkzeug',
        'python-xlsxwriter',
        'python-zeep',
        'python-cbor2',
        'python-asn1crypto',
        'python-google-auth',
        'pgvector',
    ])

    _aur(['wkhtmltopdf-bin'])
    postgresql()



@api
def postgresql():
    '''Base postgresql setup to /home/postgres
    '''
    _packages(['postgresql'])
    # _copy passes install -D, which creates postgresql.service.d/ for us.
    _copy({'postgresql.service': '/etc/systemd/system/postgresql.service.d/override.conf'})
    _run([
        "sudo systemctl daemon-reload",
        "sudo mkdir -p /home/postgres/data",
        "sudo chown -R postgres:postgres /home/postgres",
        "sudo usermod -d /home/postgres postgres",
        "sudo chmod o+w /var/run",
    ])

    try:
        _run([
            "sudo -u postgres initdb --locale $LANG -E UTF8 -D '/home/postgres/data/'",
        ])
    except:  # pragma: no cover - cluster may already be initialised
        pass

    _enable(['postgresql'])

    try:
        _run([
            'sudo su - postgres -c "createuser -s $USER"',
            'sudo su - postgres -c "createuser -s root"',
        ])
    except:  # pragma: no cover - roles may already exist
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
    import shutil
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
        except:  # pragma: no cover - fall through to the copy/clone path below
            pass

    folders = [path for path in glob.glob(_path(f'{odoo_installs_dir}/*/*')) if os.path.isdir(path)]
    print("Checking folders for existing odoo installations:\n", ' \n'.join(folders))
    for full_path in folders:
        name = os.path.basename(full_path)
        if name == repo:
            print(f"Found existing '{repo}' installation at {full_path}")
            print("Copying the installation is faster than cloning..")
            # dirs_exist_ok mirrors distutils copy_tree, which merged into an
            # existing destination. odoo_path can already be there when the
            # pull above failed and we fell through.
            shutil.copytree(full_path, odoo_path, dirs_exist_ok=True)
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
