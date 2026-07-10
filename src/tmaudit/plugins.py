"""tmaudit.plugins — plugin API for user-written audit checks.

This module defines the public surface for plugins. The three
primitives are:

1. ``Finding`` — a frozen dataclass representing one audit
   finding. Plugins return ``List[Finding]`` instead of the
   legacy ``(category, message, line)`` tuple, which C1..C10
   still use internally for backward compatibility.

2. ``@check`` — a decorator that turns a function into a
   registered plugin. The decorator attaches metadata
   (name, severity, requires_config, help_text) without
   requiring the user to write boilerplate.

3. ``load_plugins()`` — discovers every plugin registered
   via the ``tmaudit.plugins`` entry-point group and returns
   them as a ``dict[str, CheckFn]``.

Plugins are **side-effect-free** (no file writes, no
network calls, no global state mutation). They take a single
``Finding`` list back, keeping the audit reproducible and
the cache safe.

Usage (caller side):

    from tmaudit.plugins import load_plugins
    plugins = load_plugins()
    for name, check_fn in plugins.items():
        findings = check_fn(tex=tex, config=paper_config)

Usage (author side):

    from tmaudit.plugins import Finding, check

    @check(name='no-todo', severity='MEDIUM', help_text='Flag TODO markers')
    def find_todos(tex, config=None):
        return [Finding('TODO', 'MED',
                        f'TODO at line {i+1}', i+1)
                for i, line in enumerate(tex.splitlines())
                if 'TODO' in line]
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib.metadata import EntryPoint, entry_points
from typing import Any, Callable, Dict, List, Optional, Protocol

log = logging.getLogger(__name__)

# The standard entry-point group that plugins must register under.
PLUGIN_GROUP = "tmaudit.plugins"

# Valid severity values. Reused by Finding.__post_init__.
# Note: "MED" is accepted as a short-form alias for "MEDIUM" for
# ergonomic reasons (the legacy C1..C10 code uses "MED" because
# the messages contain "MED" too). Both forms are normalised to
# the canonical "MEDIUM" by Finding.__post_init__.
VALID_SEVERITIES = ("HIGH", "MEDIUM", "LOW", "MED")


# ============================================================================
# Finding dataclass
# ============================================================================

@dataclass(frozen=True)
class Finding:
    """A single audit finding produced by a check.

    Attributes:
        category: short identifier (e.g. "C8", "TODO", "NIPS-PC").
        severity: "HIGH", "MEDIUM", or "LOW".
        message: human-readable finding message.
        line: 1-based line number, or -1 for global findings.
        paper_id: set by the loader, not the plugin. Used by the
            audit-all Markdown report to attribute findings to
            a specific paper when one tmaudit run covers many.

    The dataclass is frozen=True so plugins cannot mutate a
    finding after it has been emitted. This makes the audit
    reproducible and the cache safe.
    """
    category: str
    severity: str
    message: str
    line: int = -1
    paper_id: Optional[str] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        # Validate severity early so a plugin bug surfaces as
        # an ImportError-style traceback rather than a runtime
        # breakage 50 audit-finds later.
        s = self.severity.upper()
        if s not in VALID_SEVERITIES:
            raise ValueError(
                f"Finding.severity must be one of {VALID_SEVERITIES}, "
                f"got {self.severity!r}"
            )
        # Normalize "MED" -> "MEDIUM" (short-form -> canonical).
        if s == "MED":
            s = "MEDIUM"
        # Normalize to canonical case.
        object.__setattr__(self, "severity", s)
        if not self.category or not isinstance(self.category, str):
            raise ValueError(f"Finding.category must be a non-empty str")

    def to_tuple(self) -> tuple:
        """Backward-compat shim for the C1..C10 tuple-based code.

        Returns (category, message, line). ``paper_id`` is
        dropped because the legacy tuple shape doesn't carry it.
        """
        return (self.category, self.message, self.line)


# ============================================================================
# CheckFn protocol + @check decorator
# ============================================================================

class CheckFn(Protocol):
    """The protocol that every registered plugin must satisfy.

    A ``CheckFn`` is a callable taking ``(tex, config)`` and
    returning ``List[Finding]``. The ``__tmaudit_meta__``
    attribute carries the decorator-supplied metadata.

    Plugins are stored as instance of ``_DecoratedCheck`` (below),
    which implements this protocol and provides the metadata.
    """
    __tmaudit_meta__: Dict[str, Any]

    def __call__(
        self,
        tex: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        ...


@dataclass(frozen=True)
class _DecoratedCheck:
    """The runtime representation of a @check-decorated function.

    Wraps the user-supplied function with metadata so the
    loader can introspect it without re-importing the source
    (which would be costly and may not be available in a
    zipapp install).
    """
    fn: Callable[[str, Optional[Dict[str, Any]]], List[Finding]]
    name: str
    severity: str
    requires_config: bool
    help_text: str
    version: str

    def __call__(
        self,
        tex: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        return self.fn(tex, config)

    @property
    def __tmaudit_meta__(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "requires_config": self.requires_config,
            "help_text": self.help_text,
            "version": self.version,
        }


def check(
    name: str,
    severity: str = "MEDIUM",
    requires_config: bool = False,
    help_text: str = "",
    version: str = "0.1.0",
) -> Callable[[Callable], CheckFn]:
    """Decorator: register a function as a tmaudit plugin.

    Args:
        name: the unique plugin identifier (used by ``tmaudit
            plugins list`` and by per-paper disable lists).
            Must be non-empty.
        severity: the default severity when the plugin emits a
            finding. Plugins may also emit findings with their
            own severity (e.g. ``Finding(severity="HIGH")``);
            the decorator's ``severity`` is the *plugin's*
            default, used by ``plugins info``.
        requires_config: True if the plugin reads ``config``
            (per-paper `CHECKS_CONFIG['plugin_specific']` or
            similar). Plugins that ignore ``config`` should
            leave this False for clarity.
        help_text: a one-line description, used by
            ``tmaudit plugins info <name>``.
        version: the plugin's semver. Used by the cache key
            so a plugin update invalidates stale cached
            findings.

    Returns:
        A decorator that wraps the input function and returns
        a ``CheckFn`` (``_DecoratedCheck`` instance).

    Example::

        @check(name='no-todo', severity='LOW', help_text='Flag TODO markers')
        def find_todos(tex, config=None):
            return [
                Finding('TODO', 'LOW', f'TODO at line {i}', i)
                for i, line in enumerate(tex.splitlines())
                if 'TODO' in line
            ]
    """
    if not name or not isinstance(name, str):
        raise ValueError(f"@check name must be a non-empty str, got {name!r}")
    sev_upper = severity.upper()
    if sev_upper not in VALID_SEVERITIES:
        raise ValueError(
            f"@check severity must be one of {VALID_SEVERITIES}, "
            f"got {severity!r}"
        )
    # Normalize "MED" -> "MEDIUM" (short-form -> canonical).
    if sev_upper == "MED":
        sev_upper = "MEDIUM"

    def decorator(fn: Callable) -> CheckFn:
        # Validation: the function must accept (tex, config=None).
        # We don't introspect signature strictly because
        # plugins are deliberately duck-typed; we just check
        # that the function is callable.
        if not callable(fn):
            raise TypeError(
                f"@check target must be callable, got {type(fn).__name__}"
            )
        return _DecoratedCheck(
            fn=fn,
            name=name,
            severity=sev_upper,
            requires_config=requires_config,
            help_text=help_text,
            version=version,
        )

    return decorator


# ============================================================================
# Plugin loader (entry-points discovery)
# ============================================================================

# A loader-level cache so multiple calls to load_plugins() within
# the same tmaudit invocation don't re-import the same plugins.
# Reset by force_reload=True or by import invalidation in tests.
_LOADER_CACHE: Dict[str, CheckFn] = {}
_LOADER_CACHE_LOADED = False


def _load_entry_point(ep: EntryPoint) -> Optional[CheckFn]:
    """Load a single entry-point, returning the CheckFn or None.

    A None return means the entry-point either failed to import
    or didn't yield a valid CheckFn. The error is logged but
    never raised — a buggy plugin should not break the audit.
    """
    try:
        obj = ep.load()
    except Exception as e:
        log.warning(
            "tmaudit plugin %r failed to import: %s",
            ep.name, e,
        )
        return None
    if not isinstance(obj, _DecoratedCheck):
        log.warning(
            "tmaudit plugin %r is not a @check-decorated function "
            "(got %r); skipping",
            ep.name, obj,
        )
        return None
    return obj


def load_plugins(force_reload: bool = False) -> Dict[str, CheckFn]:
    """Discover every tmaudit plugin registered via entry_points.

    Discovers plugins from the ``tmaudit.plugins`` entry-point
    group (PEP 621). Returns a dict ``{name: check_fn}`` where
    ``check_fn`` is the loaded ``_DecoratedCheck`` instance.

    Args:
        force_reload: if True, ignore the in-process cache and
            re-discover. Used by tests.

    Returns:
        ``Dict[str, CheckFn]``. The keys are plugin names (the
        entry-point name, e.g., ``nips_pagecheck``). The values
        are the loaded check functions.

    A failing entry-point is logged but does not raise; the
    audit continues with the successfully-loaded plugins.
    """
    global _LOADER_CACHE, _LOADER_CACHE_LOADED
    if _LOADER_CACHE_LOADED and not force_reload:
        return dict(_LOADER_CACHE)

    plugins: Dict[str, CheckFn] = {}
    try:
        eps = entry_points(group=PLUGIN_GROUP)
    except Exception as e:
        log.warning(
            "tmaudit could not enumerate entry-points for %s: %s",
            PLUGIN_GROUP, e,
        )
        eps = []

    for ep in eps:
        loaded = _load_entry_point(ep)
        if loaded is None:
            continue
        if ep.name in plugins:
            # Duplicate plugin name; the second wins and the
            # first is dropped. Logged so the user can fix it.
            log.warning(
                "tmaudit plugin %r is registered twice; "
                "the later definition wins",
                ep.name,
            )
        plugins[ep.name] = loaded

    _LOADER_CACHE = dict(plugins)
    _LOADER_CACHE_LOADED = True
    return plugins


def reset_loader_cache() -> None:
    """Clear the in-process plugin cache. For tests."""
    global _LOADER_CACHE_LOADED
    _LOADER_CACHE.clear()
    _LOADER_CACHE_LOADED = False


# ============================================================================
# Plugin runtime helpers
# ============================================================================

def filter_active(
    plugins: Dict[str, CheckFn],
    disabled: Optional[List[str]] = None,
) -> Dict[str, CheckFn]:
    """Return a subset of plugins with disabled ones removed.

    Args:
        plugins: full plugin dict from load_plugins().
        disabled: per-paper list of plugin names to skip
            (from ``CHECKS_CONFIG['c11_plugins_disabled']`` or
            ``--disable-plugin`` flags).

    Returns:
        A new dict containing only the active plugins.
    """
    if not disabled:
        return dict(plugins)
    return {n: c for n, c in plugins.items() if n not in set(disabled)}


def run_plugin(
    plugin: CheckFn,
    tex: str,
    config: Optional[Dict[str, Any]] = None,
    paper_id: Optional[str] = None,
) -> List[Finding]:
    """Run a single plugin and stamp the paper_id on each finding.

    A wrapper around the callable that:
    1. Calls the plugin.
    2. Stamps every finding with ``paper_id`` so downstream
       reports can attribute findings to a specific paper.

    This is the canonical entry point for running a plugin
    during the audit. Direct calls to the plugin function
    bypass the ``paper_id`` stamping.
    """
    findings = plugin(tex, config)
    if paper_id is None:
        return findings
    out = []
    for f in findings:
        if f.paper_id is None:
            # Bypass __setattr__ immutability by constructing a new
            # Finding with the same fields plus paper_id. This
            # preserves our frozen=True invariant.
            out.append(Finding(
                category=f.category,
                severity=f.severity,
                message=f.message,
                line=f.line,
                paper_id=paper_id,
            ))
        else:
            # Plugin already set a paper_id (e.g. a re-run
            # over multiple papers). Don't overwrite.
            out.append(f)
    return out


def run_all_plugins(
    plugins: Dict[str, CheckFn],
    tex: str,
    config: Optional[Dict[str, Any]] = None,
    paper_id: Optional[str] = None,
) -> List[Finding]:
    """Run every plugin in the dict, returning a flat list of findings.

    A plugin that raises an exception is logged and skipped;
    the remaining plugins still run. A failure in one plugin
    cannot break the audit.
    """
    out: List[Finding] = []
    for name, plugin in plugins.items():
        try:
            out.extend(run_plugin(plugin, tex, config, paper_id))
        except Exception as e:
            log.warning(
                "tmaudit plugin %r raised during execution: %s",
                name, e,
            )
    return out
