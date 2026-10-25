"""_build_pyz.py — package the tmaudit install into a single .pyz.

After `pip install --editable .` (which we already did), we can use
the installed `tmaudit` package as the source for a zipapp. This
produces a single `tmaudit.pyz` file that can be run on any
Python 3.9+ system without any prior install.

Usage:
    python _build_pyz.py
    python tmaudit.pyz --help
    python tmaudit.pyz verify --paper 1
"""
import os
import shutil
import subprocess
import sys
import zipapp
from pathlib import Path

# The author's development tree, which holds the same src/tmaudit/ layout as this
# repository — so this resolves here by default and can be pointed elsewhere with
# TMAUDIT_TEMPLATE_DIR, as the configs modules and _check_all_regressions.py are.
ROOT = Path(os.environ.get('TMAUDIT_TEMPLATE_DIR',
                           str(Path(__file__).resolve().parent)))
PKG = ROOT / 'src' / 'tmaudit'
BUILD = ROOT / 'build_pyz'
OUT = ROOT / 'tmaudit.pyz'


def main() -> int:
    if not PKG.exists():
        print(f'ERROR: {PKG} does not exist; run `pip install --editable .` first',
              file=sys.stderr)
        return 1

    # Clean build dir
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()

    # Copy tmaudit package tree (preserve structure)
    #
    # `__pycache__` must not go in. It never used to matter because the
    # archive was built on a clean tree, but any run of the test suite or an
    # editable install leaves bytecode in src/, and copytree copies it
    # verbatim: the archive grows, carries .pyc compiled against whatever
    # interpreter built it, and CI's freshness gate (_check_pyz_fresh.py)
    # rejects it outright.
    target_pkg = BUILD / 'tmaudit'
    shutil.copytree(
        PKG, target_pkg,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'),
    )

    # Build the .pyz
    if OUT.exists():
        OUT.unlink()
    zipapp.create_archive(
        source=BUILD,
        target=str(OUT),
        main='tmaudit.__main__:main',
        compressed=True,
    )
    size = OUT.stat().st_size
    print(f'Built {OUT} ({size:,} bytes)')

    # Smoke test
    print()
    print('=== smoke test: tmaudit.pyz list ===')
    rc = subprocess.run(
        [sys.executable, str(OUT), 'list'],
    ).returncode
    print(f'rc = {rc}')
    return rc


if __name__ == '__main__':
    sys.exit(main())