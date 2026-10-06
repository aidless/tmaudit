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
import time as _time
from dataclasses import dataclass, field
from importlib.metadata import EntryPoint, entry_points
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger(__name__)

# The standard entry-point group that plugins must register under.
PLUGIN_GROUP = "tmaudit.plugins"

# Valid severity values. Reused by Finding.__post_init__.
VALID_SEVERITIES = ("HIGH", "MEDIUM", "LOW", "MED")


# ============================================================================
# Finding dataclass
# ============================================================================

@dataclass(frozen=True)
class Finding:
    """A single audit finding produced by a check."""
    category: str
    severity: str
    message: str
    line: int = -1
    paper_id: Optional[str] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        s = self.severity.upper()
        if s not in VALID_SEVERITIES:
            raise ValueError(
                f"Finding.severity must be one of {VALID_SEVERITIES}, "
                f"got {self.severity!r}"
            )
        if s == "MED":
            s = "MEDIUM"
        object.__setattr__(self, "severity", s)
        if not self.category or not isinstance(self.category, str):
            raise ValueError("Finding.category must be a non-empty str")

    def to_tuple(self) -> tuple:
        return (self.category, self.message, self.line)


# ============================================================================
# CheckFn protocol + @check decorator
# ============================================================================

class CheckFn(Protocol):
    __tmaudit_meta__: Dict[str, Any]

    def __call__(
        self,
        tex: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        ...


@dataclass(frozen=True)
class _DecoratedCheck:
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
    if not name or not isinstance(name, str):
        raise ValueError(f"@check name must be a non-empty str, got {name!r}")
    sev_upper = severity.upper()
    if sev_upper not in VALID_SEVERITIES:
        raise ValueError(
            f"@check severity must be one of {VALID_SEVERITIES}, "
            f"got {severity!r}"
        )
    if sev_upper == "MED":
        sev_upper = "MEDIUM"

    def decorator(fn: Callable) -> CheckFn:
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

_LOADER_CACHE: Dict[str, CheckFn] = {}
_LOADER_CACHE_LOADED = False


def _load_entry_point(ep: EntryPoint) -> Optional[CheckFn]:
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
    global _LOADER_CACHE, _LOADER_CACHE_LOADED
    if _LOADER_CACHE_LOADED and not force_reload:
        return dict(_LOADER_CACHE)

    plugins: Dict[str, CheckFn] = {}
    try:
        eps = entry_points(group=PLUGIN_GROUP)
    except TypeError:
        # Python 3.9's importlib.metadata.entry_points() takes no arguments. What it
        # hands back is not stable across environments, so handle both shapes rather
        # than assuming the stdlib one:
        #   * stock 3.9 stdlib -> a dict of group name -> list of entry points
        #   * importlib_metadata backport (still installed on some 3.9 CI images)
        #     -> an EntryPoints object, same as 3.10+, reached via .select()
        # Assuming the dict shape left plugin discovery empty on any runner with the
        # backport, which is what made every test in tests/test_example_plugin.py
        # fail on 3.9 while passing on 3.10 and up.
        try:
            all_eps = entry_points()
            if isinstance(all_eps, dict):
                eps = all_eps.get(PLUGIN_GROUP, [])
            else:
                eps = all_eps.select(group=PLUGIN_GROUP)
        except Exception as e:
            log.warning(
                "tmaudit could not enumerate entry-points for %s: %s",
                PLUGIN_GROUP, e,
            )
            eps = []
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
    global _LOADER_CACHE_LOADED
    _LOADER_CACHE.clear()
    _LOADER_CACHE_LOADED = False


# ============================================================================
# Plugin runtime helpers
# ============================================================================

def filter_active(
    plugins: Dict[str, CheckFn],
    disabled: Optional[List[str]] = None,
    enabled: Optional[List[str]] = None,
) -> Dict[str, CheckFn]:
    """Return a subset of plugins with disabled ones removed
    and (if enabled is non-empty) only enabled ones kept.

    Resolution rule (per §16.4 in the engineering notes):
    if `enabled` is non-empty, it takes precedence over
    `disabled`. A warning is logged if both are non-empty
    so the user notices the override.

    Args:
        plugins: full plugin dict from load_plugins().
        disabled: per-paper blacklist. Ignored if `enabled`
            is non-empty.
        enabled: per-paper whitelist. If non-empty, only
            plugins whose name is in this list are kept.

    Returns:
        A new dict containing only the active plugins.
    """
    enabled_set = set(enabled) if enabled else set()
    disabled_set = set(disabled) if disabled else set()

    if enabled_set:
        # Whitelist mode: enabled wins, disabled is ignored.
        if disabled_set:
            log.warning(
                "tmaudit: c11_plugins_enabled and "
                "c11_plugins_disabled are both set; "
                "enabled wins and disabled is ignored."
            )
        return {n: c for n, c in plugins.items()
                if n in enabled_set}

    if disabled_set:
        return {n: c for n, c in plugins.items()
                if n not in disabled_set}

    return dict(plugins)


def run_plugin(
    plugin: CheckFn,
    tex: str,
    config: Optional[Dict[str, Any]] = None,
    paper_id: Optional[str] = None,
) -> List[Finding]:
    findings = plugin(tex, config)
    if paper_id is None:
        return findings
    out = []
    for f in findings:
        if f.paper_id is None:
            out.append(Finding(
                category=f.category,
                severity=f.severity,
                message=f.message,
                line=f.line,
                paper_id=paper_id,
            ))
        else:
            out.append(f)
    return out


def run_all_plugins(
    plugins: Dict[str, CheckFn],
    tex: str,
    config: Optional[Dict[str, Any]] = None,
    paper_id: Optional[str] = None,
) -> List[Finding]:
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


# ============================================================================
# Bulk audit helper (added in v0.4.0)
# ============================================================================

def audit_plugins(
    paper_n: int,
    paper_dir: "Path",
    config: Optional[Dict[str, Any]] = None,
    disabled: Optional[List[str]] = None,
    enabled: Optional[List[str]] = None,
    use_cache: bool = True,
) -> List[Finding]:
    """Run all active plugins for a paper; cache results.

    The canonical entry point for ``audit-all`` and other
    bulk callers (added in v0.4.0). Behaviour:

    1. Discover every plugin via entry_points.
    2. Filter out the per-paper disabled list.
    3. For each active plugin:
       a. Build a cache key (paper_n, plugin_name,
          plugin_version, tex_hash).
       b. If a cached entry exists, reuse its findings.
       c. Otherwise run the plugin, cache the result, and
          return the findings.
    4. Aggregate all findings into one flat list, sorted by
       category then line.

    A plugin that errors at any step is logged and skipped.
    """
    from pathlib import Path as _Path
    from . import cache as _cache

    paper_dir = _Path(paper_dir)
    main_tex = paper_dir / "main.tex"
    if not main_tex.exists():
        log.warning(
            "audit_plugins: main.tex not found at %s; returning []",
            main_tex,
        )
    tex = (
        main_tex.read_text(encoding="utf-8", errors="replace")
        if main_tex.exists()
        else ""
    )

    # If `enabled` is not passed explicitly, read it from
    # the per-paper config. This is the canonical entry
    # point (per §16.3.3) — per-paper CHECKS_CONFIG carries
    # the whitelist, not the caller.
    if enabled is None and config:
        enabled = config.get('c11_plugins_enabled', [])

    plugins = filter_active(load_plugins(), disabled, enabled)
    if not plugins:
        return []

    db = _cache.CacheDB() if use_cache else None
    out: List[Finding] = []
    try:
        for name, plugin in plugins.items():
            meta = plugin.__tmaudit_meta__
            plugin_version = meta["version"]
            cache_key_str = (
                _cache.plugin_cache_key(
                    paper_n=paper_n,
                    plugin_name=name,
                    plugin_version=plugin_version,
                    main_tex=tex,
                )
                if use_cache
                else None
            )

            if db is not None and cache_key_str is not None:
                cached = db.get(cache_key_str)
                if cached is not None:
                    for f in cached.get("findings", []):
                        out.append(Finding(
                            category=f["category"],
                            severity=f["severity"],
                            message=f["message"],
                            line=f["line"],
                            paper_id=f.get("paper_id") or str(paper_n),
                        ))
                    log.debug(
                        "audit_plugins: cache hit for %s on paper %d",
                        name, paper_n,
                    )
                    continue

            findings = run_plugin(
                plugin, tex=tex, config=config,
                paper_id=str(paper_n),
            )
            if db is not None and cache_key_str is not None:
                db.put(cache_key_str, {
                    "findings": [
                        {
                            "category": f.category,
                            "severity": f.severity,
                            "message": f.message,
                            "line": f.line,
                            "paper_id": f.paper_id,
                        }
                        for f in findings
                    ],
                    "plugin_name": name,
                    "plugin_version": plugin_version,
                    "timestamp": _time.time(),
                })
            out.extend(findings)
    finally:
        if db is not None:
            db.close()

    out.sort(key=lambda f: (f.category, f.line if f.line >= 0 else 1_000_000))
    return out
