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

Every function is run twice, once with os.path.exists() forced False and once
True, which is what covers the "already installed / not yet installed" branches
(_yay, dotfiles, laptop, odoo_venv ...).

Usage:
    python tests/smoke.py          # quiet, one line per function
    python tests/smoke.py -v       # also dump captured output per function

Exits non-zero if any function raised.
"""

import builtins
import contextlib
import importlib
import inspect
import io
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
    ('MemTotal', '32768000\n'),   # config.pgtune() does int() on this
    ('xrandr', FAKE_XRANDR),      # utils.monitor() parses this
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
    # Callers split() this, so an empty string yields an empty set/list, which
    # keeps the "nothing installed yet" path live and exercises more code.
    return ''


def _fake_run(command, *args, **kwargs):
    return subprocess.CompletedProcess(_command_text(command), 0)


class _FakePopen:
    """Enough of Popen for _pipe(), which asserts returncode == 0."""

    returncode = 0

    def __init__(self, *args, **kwargs):
        pass

    def communicate(self, input=None):
        return ('', '')


def _fake_open(file, mode='r', *args, **kwargs):
    if any(char in mode for char in 'wxa+'):
        return io.StringIO()  # discard writes
    try:
        return _real_open(file, mode, *args, **kwargs)
    except OSError:
        # os.path.exists is forced True in one pass, so code may open a file
        # that is not really there. A smoke test only cares that the path runs.
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


def main():
    verbose = '-v' in sys.argv
    failures = []

    with _mocked_system():
        # Import inside the mock, not before it: bootstrap/__init__.py calls
        # _autocmp() at import time, which writes files/autocomplete. Harmless,
        # but the suite should not modify the repo it is testing.
        functions = sorted(_api_functions())
        for exists in (False, True):
            print(f'== pass: os.path.exists() -> {exists} ==')
            for label, func in functions:
                captured = io.StringIO()
                try:
                    with mock.patch('os.path.exists', return_value=exists), \
                            contextlib.redirect_stdout(captured):
                        func(*_args_for(func))
                except Exception:
                    failures.append((exists, label, captured.getvalue(),
                                     traceback.format_exc()))
                    print(f'  FAIL {label}')
                else:
                    print(f'  ok   {label}')
                if verbose and captured.getvalue():
                    for line in captured.getvalue().splitlines():
                        print(f'         | {line}')

    total = len(functions) * 2
    print(f'\n{total - len(failures)}/{total} calls ran clean '
          f'({len(functions)} api functions x 2 passes)')

    for exists, label, output, tb in failures:
        print(f'\n--- {label}  (os.path.exists -> {exists}) ---')
        if output:
            print(output.rstrip())
        print(tb.rstrip())

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
