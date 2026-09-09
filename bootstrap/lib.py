import subprocess
import os
import sys
from contextlib import contextmanager

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FILES_DIR = os.path.join(os.path.dirname(CURRENT_DIR), 'files')
HOME_DIR = os.path.expanduser('~')


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

def _link(files_dict, allow_sudo=True):
    prepend = ''
    if os.geteuid() != 0 and allow_sudo:
        prepend = 'sudo '
    for fname, dest_path in files_dict.items():
        if os.path.isfile(dest_path):
            _run([f'{prepend}rm {dest_path}'])
        _run([f'{prepend}ln -s {os.path.join(FILES_DIR, fname)} {dest_path}'], ignore_errors=True)

def _copy(files_dict, owner='root', group='root', mode='644'):
    """Deploy files from FILES_DIR to system paths, root-owned 644 by default.

    Uses install(1) rather than cp for three reasons:
      * ownership and mode are applied as the file is written, so the
        permissions are never a side effect of the repo file's own mode or of
        a later chmod that might be forgotten;
      * -D creates any missing parent directories, so callers do not need to
        mkdir -p first;
      * install unlinks the destination before writing, so a symlink left over
        from _link is replaced with a real file instead of being followed --
        cp would write straight through it back into FILES_DIR.

    Pass mode='755' for anything that has to be executable.
    """
    prepend = ''
    if os.geteuid() != 0:
        prepend = 'sudo '
    for fname, dest_path in files_dict.items():
        _run([
            f'{prepend}install -D -o {owner} -g {group} -m {mode} {os.path.join(FILES_DIR, fname)} {dest_path}'
        ])

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


def api(func):
    func._api = True
    return func

def _filter_locals(locals_dict):
    return {k: v for k, v in locals_dict.items() if \
        callable(v) \
        and getattr(v, '_api', False) \
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
        doc = ' '.join(d.strip() for d in doc.split('\n'))
        assert doc, f"Docstring missing for {fname}: '{doc}'"
        if not doc.endswith('\n    '):
            doc += '\n    '
        print("    {}".format(doc))


def _autocmp(locals_dict):
    with open(f'{FILES_DIR}/autocomplete', 'w') as fobj:
        fobj.write('\n'.join(sorted(locals_dict.keys())))


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
