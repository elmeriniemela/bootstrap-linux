#!/usr/bin/python3

import subprocess
import os
import sys
from contextlib import contextmanager
import distutils.spawn
import re
import random
from functools import partial

from lib import (
    _filter_locals,
    _print_functions,
    _quittable,
    _autocmp,
)

from odoo import (
    odoo,
    odoo_venv,
    global_odoo_deps,
    odoo_tests,
)

from utils import (
    monitor,
    mirrors,
    fix_t14_ethernet,
    update,
    serial,
    keymap,
    add_ssh,
    password,
)

from config import (
    pgtune,
    ufw_local,
    secure,
    swapfile,
    bashrc,
    dotfiles,
    gitconfig,
)

from install import (
    distro,
    laptop,
    server,
)

LOCALS = _filter_locals(locals())
_autocmp(LOCALS)

def main():
    if sys.version_info[0] < 3:
        print("Only supported in python 3")
        return -1

    import argparse

    global LOCALS
    if len(sys.argv) == 1:
        _print_functions(LOCALS)

    parser = argparse.ArgumentParser(description='Setup your Linux system')

    parser.add_argument(
        'function', help="Install function to run (use 0 params to list function signatures)")

    parser.add_argument('args', metavar='arg', type=str, nargs='*',
                        help='argument for the function')

    args = parser.parse_args()

    func = LOCALS[args.function]
    retcode = 0
    with _quittable():
        try:
            func(*args.args)
        except subprocess.CalledProcessError as error:
            print("EXIT without traceback after subprocess.CalledProcessError.")
            retcode = 1

    return retcode

if __name__ == '__main__':
    sys.exit(main())
