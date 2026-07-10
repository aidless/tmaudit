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
import shutil
import subprocess
import sys
import zipapp
from pathlib import Path

ROOT = Path('F:/Research/TEMPLATE')
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
    target_pkg = BUILD / 'tmaudit'
    shutil.copytree(PKG, target_pkg)

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