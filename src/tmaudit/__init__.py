"""tmaudit — config-driven TMLR paper audit + LaTeX compile pipeline.

This package bundles:
  * The generic 6-category audit template
  * The generic 4-pass LaTeX compile script
  * The generic abstract-Unicode -> LaTeX-math fixer
  * Per-paper PAPER_CONFIGS for all five TMLR papers
  * A plugin API (added in v0.4.0) for user-written audit checks

and exposes a single CLI:

    tmaudit --list
    tmaudit verify --paper N [--paper-dir PATH]
    tmaudit compile --paper N
    tmaudit fix-unicode --paper N
    tmaudit audit-all
    tmaudit plugins list

The package can be installed with `pip install tmaudit/` (or
`pip install -e .` for editable mode) and shipped as a single
executable .pyz file with `python -m zipapp`.
"""
__version__ = '0.5.0'

# Re-export the plugin API at the package level so users can
# `from tmaudit import Finding, check` instead of
# `from tmaudit.plugins import ...`. The submodule is still
# the canonical home for the implementation.
from .plugins import (
    Finding,
    CheckFn,
    PLUGIN_GROUP,
    VALID_SEVERITIES,
    audit_plugins,
    check,
    filter_active,
    load_plugins,
    reset_loader_cache,
    run_all_plugins,
    run_plugin,
)

__all__ = [
    "__version__",
    "Finding",
    "CheckFn",
    "PLUGIN_GROUP",
    "VALID_SEVERITIES",
    "audit_plugins",
    "check",
    "filter_active",
    "load_plugins",
    "reset_loader_cache",
    "run_all_plugins",
    "run_plugin",
    # Re-exported for plugin authors. CHANGELOG.md records them as public API, so
    # listing them here is what tells pyflakes they are not dead imports.
    "CacheDB",
    "cache_key",
    "plugin_cache_key",
]  # type: ignore

# Re-export cache helpers that plugin authors will need.
from .cache import (
    CacheDB,
    cache_key,
    plugin_cache_key,
)
