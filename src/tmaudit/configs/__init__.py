"""tmaudit.configs — re-export PAPER_CONFIGS and COMPILE_CONFIGS.

This is the single source of truth for which papers are supported
and what per-paper rules apply. To add a new paper, edit
src/tmaudit/configs/paper_configs.py and/or
src/tmaudit/configs/compile_configs.py and re-install the package.

Naming:
  - VERIFY_CONFIGS  — from paper_configs.py (used by verify template)
  - COMPILE_CONFIGS — from compile_configs.py (used by compile + fix-unicode
                       templates). Originally called PAPER_CONFIGS in
                       the legacy gen_compile_scripts.py; renamed for
                       clarity after the package split.
"""
from .paper_configs import PAPER_CONFIGS as VERIFY_CONFIGS
from .compile_configs import PAPER_CONFIGS as COMPILE_CONFIGS

__all__ = ['VERIFY_CONFIGS', 'COMPILE_CONFIGS']