#!/usr/bin/env python3
"""Smoke test: call every @api function with the system mocked out.

The point is only to prove the code is *executable* -- that every api function
imports, formats its strings and walks its branches without raising. There are
deliberately no assertions about behaviour: the logic here changes constantly
and maintaining expected-command assertions would cost more than it catches.
A function passes if it runs to completion.

Nothing touches the real system. subprocess is stubbed, and so are the handful
of calls that would otherwise mutate the filesystem directly -- os.makedirs,
os.chdir, shutil.rmtree and writes through open(). That last group matters:
laptop() calls shutil.rmtree() on ~/.config/awesome, so running this unmocked
would delete a real config.

Every api function runs once per entry in PASSES, which flips the filesystem
predicates and the euid to reach the "already installed / not yet installed"
and "running as root" branches. Two extra cases cover what the api functions
never reach: the argparse entry point, and private helpers.

Anything still uncovered after this is marked `# pragma: no cover` in the
source -- defensive `except: pass` blocks, the python2 guard and the
`__main__` block.

Usage:
    python tests/smoke.py          # quiet, one line per case
    python tests/smoke.py -v       # also dump captured output per case

Exits non-zero if any case raised.
"""

import builtins
import contextlib
import importlib
import inspect
import io
import operator
import os
import subprocess
import sys
import traceback
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

MODULES = ('lib', 'config', 'install', 'odoo', 'utils')

# Values for parameters that have no default. They only need to be plausible
# enough to survive string formatting -- no command is ever executed.
DUMMY_ARGS = {
    'branch': '17.0',
    'filename': 'smoke-test-key',
    'db_name': 'smoke_test_db',
}
FALLBACK_ARG = 'smoke'

# name, os.path.exists, os.path.isfile, os.path.isdir, os.geteuid
PASSES = (
    ('nothing installed yet', False, False, False, 1000),
    ('everything already there', True, True, True, 1000),
    ('running as root', False, False, False, 0),
)

# A command containing this marker makes the fake subprocess raise, which is
# how the error handling inside _run() gets exercised.
FAIL_MARKER = 'SMOKE_SHOULD_FAIL'

# Fake xrandr output: two connected monitors plus one disconnected, so
# monitor() walks both the len(connected) == 2 branch and the disconnected one.
FAKE_XRANDR = """Screen 0: minimum 320 x 200, current 3840 x 2160, maximum 16384 x 16384
eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 344mm x 194mm
   1920x1080     60.05*+  59.93
DP-1 connected 3840x2160+1920+0 (normal left inverted right x axis y axis) 600mm x 340mm
   3840x2160     60.00*+  59.97
HDMI-1 disconnected (normal left inverted right x axis y axis)
"""

# Only commands whose output actually gets parsed need an entry here; anything
# else gets ''. Keep this list as short as the code allows.
CANNED_OUTPUT = (
    ('MemTotal', '32768000\n'),        # config.swapfile() does int() on this
    ('xrandr', FAKE_XRANDR),           # utils.monitor() parses this
    ('pacman -Qqe', 'coreutils\nbash\n'),  # _installed_packages()
)

# Variables the code reads out of the environment. Normally exported by the
# `oo` helper in global.bashrc, so they are absent in a bare shell.
FAKE_ENV = {
    'ODOO_VERSION_DIR': '/home/smoke/Odoo/src/17.0',
}

_real_open = builtins.open


def _command_text(command):
    if isinstance(command, str):
        return command
    return ' '.join(str(part) for part in command)


def _fake_check_output(command, *args, **kwargs):
    text = _command_text(command)
    for needle, output in CANNED_OUTPUT:
        if needle in text:
            return output
    return ''


def _fake_run(command, *args, **kwargs):
    text = _command_text(command)
    if FAIL_MARKER in text:
        raise subprocess.CalledProcessError(1, text)
    return subprocess.CompletedProcess(text, 0)


class _FakePopen:
    """Guard rather than a fixture.

    Nothing in bootstrap/ uses Popen since _pipe was deleted, but leaving the
    patch in place means a future Popen call cannot escape to the real system
    without someone noticing here first.
    """

    returncode = 0

    def __init__(self, *args, **kwargs):
        pass

    def communicate(self, input=None):
        return ('smoke stdout', 'smoke stderr')


def _fake_open(file, mode='r', *args, **kwargs):
    if any(char in mode for char in 'wxa+'):
        return io.StringIO()  # discard writes
    try:
        return _real_open(file, mode, *args, **kwargs)
    except OSError:
        # The filesystem predicates are forced True in one pass, so code may
        # open a file that is not really there. A smoke test only cares that
        # the path runs.
        return io.StringIO()


@contextlib.contextmanager
def _mocked_system():
    patches = (
        mock.patch('subprocess.run', _fake_run),
        mock.patch('subprocess.check_output', _fake_check_output),
        mock.patch('subprocess.Popen', _FakePopen),
        mock.patch('subprocess.check_call', _fake_run),
        mock.patch('os.chdir'),
        mock.patch('os.makedirs'),
        mock.patch('shutil.rmtree'),
        mock.patch('shutil.copytree'),
        mock.patch('builtins.open', _fake_open),
        mock.patch('builtins.input', lambda *a, **kw: ''),
        mock.patch.dict(os.environ, FAKE_ENV),
    )
    with contextlib.ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        yield


def _api_functions():
    for module_name in MODULES:
        module = importlib.import_module(f'bootstrap.{module_name}')
        for attr, value in vars(module).items():
            if callable(value) and getattr(value, '_api', False):
                yield f'{module_name}.{attr}', value


def _args_for(func):
    args = []
    for param in inspect.signature(func).parameters.values():
        if param.default is not inspect.Parameter.empty:
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        args.append(DUMMY_ARGS.get(param.name, FALLBACK_ARG))
    return args


def _exercise_cli():
    """Drive bootstrap.main(), the argparse entry point.

    Unreachable through the api functions, so it needs calling directly. With
    no arguments main() prints the function list and then still falls through
    to parse_args(), which exits -- hence the SystemExit guard.
    """
    import bootstrap

    def _raises():
        raise subprocess.CalledProcessError(1, 'smoke')

    argv_cases = (
        ['bootstrap-linux'],             # lists functions, then SystemExit
        ['bootstrap-linux', 'serial'],   # normal dispatch
        ['bootstrap-linux', 'add_ssh'],  # missing argument -> TypeError branch
    )
    for argv in argv_cases:
        with mock.patch.object(sys, 'argv', argv):
            with contextlib.suppress(SystemExit):
                bootstrap.main()

    # Substitute a failing function to reach the CalledProcessError branch.
    with mock.patch.dict(bootstrap.LOCALS, {'serial': _raises}), \
            mock.patch.object(sys, 'argv', ['bootstrap-linux', 'serial']):
        with contextlib.suppress(SystemExit):
            bootstrap.main()


def _exercise_helpers():
    """Call private helpers that no api function reaches."""
    from bootstrap import lib, odoo

    # _quittable swallows the interactive interrupts
    with lib._quittable():
        raise KeyboardInterrupt

    # _run's error handling: ignore_errors, retry-after-dependencies, re-raise
    lib._run([FAIL_MARKER], ignore_errors=True)
    for kwargs in ({'dependencies': lambda: None}, {}):
        with contextlib.suppress(subprocess.CalledProcessError):
            lib._run([FAIL_MARKER], **kwargs)

    lib._packages(['coreutils'])    # already installed -> early return

    with mock.patch('os.path.exists', return_value=False):
        lib._yay(src=True)          # build-from-source branch

    # _colors falls back to a blank palette when colorama is missing
    with mock.patch.dict(sys.modules, {'colorama': None}):
        lib._colors()

    # sort() only needs __lt__, so the other comparisons need calling directly
    left = lib._Monitor('eDP-1', 1920, 1080)
    right = lib._Monitor('DP-1', 3840, 2160)
    for compare in (operator.eq, operator.ne, operator.lt,
                    operator.le, operator.gt, operator.ge):
        compare(left, right)
    repr(left)
    str(left)

    # Version branches only reachable with older odoo releases
    odoo._odoo_version('master')
    odoo._branch_name('master')
    odoo.odoo_venv('10.0')          # python2 virtualenv branch
    odoo.global_odoo_deps('11.0')   # less@3.0.1 branch

    # The "copy an existing checkout instead of cloning" branch. It needs a
    # glob hit whose basename matches the repo, and isdir() true for that hit
    # but false for the destination, otherwise the pull path returns early.
    found = '/tmp/smoke/17.0/odoo'
    with mock.patch('glob.glob', return_value=[found]), \
            mock.patch('os.path.isdir', side_effect=lambda path: path == found):
        odoo._get_odoo_source('17.0', '~/Odoo/src', 'odoo')


def _attempt(label, thunk, failures, verbose):
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), \
                contextlib.redirect_stderr(captured):
            thunk()
    except Exception:
        failures.append((label, captured.getvalue(), traceback.format_exc()))
        print(f'  FAIL {label}')
    else:
        print(f'  ok   {label}')
    if verbose and captured.getvalue():
        for line in captured.getvalue().splitlines():
            print(f'         | {line}')


def main():
    verbose = '-v' in sys.argv
    failures = []
    total = 0

    with _mocked_system():
        # Import inside the mock, not before it: bootstrap/__init__.py calls
        # _autocmp() at import time, which writes files/autocomplete. Harmless,
        # but the suite should not modify the repo it is testing.
        functions = sorted(_api_functions())

        for name, exists, isfile, isdir, euid in PASSES:
            print(f'== pass: {name} ==')
            for label, func in functions:
                def thunk(func=func, args=_args_for(func), exists=exists,
                          isfile=isfile, isdir=isdir, euid=euid):
                    with mock.patch('os.path.exists', return_value=exists), \
                            mock.patch('os.path.isfile', return_value=isfile), \
                            mock.patch('os.path.isdir', return_value=isdir), \
                            mock.patch('os.geteuid', return_value=euid):
                        func(*args)
                _attempt(label, thunk, failures, verbose)
                total += 1

        print('== extra: paths no api function reaches ==')
        for label, thunk in (('cli.main', _exercise_cli),
                             ('private helpers', _exercise_helpers)):
            _attempt(label, thunk, failures, verbose)
            total += 1

    print(f'\n{total - len(failures)}/{total} cases ran clean '
          f'({len(functions)} api functions x {len(PASSES)} passes, plus 2 extra)')

    for label, output, tb in failures:
        print(f'\n--- {label} ---')
        if output:
            print(output.rstrip())
        print(tb.rstrip())

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
