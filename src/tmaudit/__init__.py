"""tmaudit — config-driven TMLR paper audit + LaTeX compile pipeline.

This package bundles:
  * The generic 6-category audit template
  * The generic 4-pass LaTeX compile script
  * The generic abstract-Unicode -> LaTeX-math fixer
  * Per-paper PAPER_CONFIGS for all five TMLR papers

and exposes a single CLI:

    tmaudit --list
    tmaudit verify --paper N [--paper-dir PATH]
    tmaudit compile --paper N
    tmaudit fix-unicode --paper N
    tmaudit audit-all

The package can be installed with `pip install tmaudit/` (or
`pip install -e .` for editable mode) and shipped as a single
executable .pyz file with `python -m zipapp`.
"""
__version__ = '0.1.0'