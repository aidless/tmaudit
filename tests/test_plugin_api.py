"""Tests for the tmaudit plugin API (added in v0.4.0).

These tests cover the loader, the @check decorator, the
Finding dataclass, the lifecycle helpers, and the per-paper
disable mechanism. They do not depend on any installed
plugin; the test fixtures synthesise plugin functions
in-process.

Test layout:

- TestFinding — Finding dataclass semantics.
- TestCheckDecorator — @check behavior + validation.
- TestFilterActive — disabled-list subtraction.
- TestRunPlugin — paper_id stamping and exception safety.
- TestLoadPlugins — entry-points discovery (with mock).
- TestPerPaperDisable — the c11_plugins_disabled mechanism
  exercised by reading PAPER_CONFIGS.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tmaudit
from tmaudit.plugins import (
    Finding,
    VALID_SEVERITIES,
    PLUGIN_GROUP,
    _DecoratedCheck,
    check,
    filter_active,
    load_plugins,
    reset_loader_cache,
    run_plugin,
    run_all_plugins,
)


# =====================================================================
# Test fixtures: synthetic plugins (defined per test as needed)
# =====================================================================


def _no_op_plugin(tex, config=None):
    """A plugin that always returns an empty list."""
    return []


def _todo_plugin(tex, config=None):
    """A plugin that flags every TODO marker."""
    out = []
    for i, line in enumerate(tex.splitlines()):
        if "TODO" in line:
            out.append(Finding(
                category="TODO", severity="MED",
                message=f"TODO marker at line {i+1}",
                line=i + 1,
            ))
    return out


def _raising_plugin(tex, config=None):
    """A plugin that always raises (used to test exception safety)."""
    raise RuntimeError("synthetic failure")


# =====================================================================
# TestFinding: Finding dataclass semantics
# =====================================================================


def test_finding_basic_construction():
    """Finding() builds with the required fields."""
    f = Finding(category="X1", severity="HIGH", message="something")
    assert f.category == "X1"
    assert f.severity == "HIGH"
    assert f.message == "something"
    assert f.line == -1  # default
    assert f.paper_id is None  # default


def test_finding_to_tuple_backward_compat():
    """Finding.to_tuple() returns (category, message, line)."""
    f = Finding(category="X1", severity="HIGH",
                message="hi", line=42)
    assert f.to_tuple() == ("X1", "hi", 42)


def test_finding_med_normalises_to_medium():
    """'MED' short-form is accepted and normalised to 'MEDIUM'."""
    f = Finding(category="X1", severity="MED", message="x")
    assert f.severity == "MEDIUM"


def test_finding_rejects_invalid_severity():
    """Invalid severities raise ValueError at construction."""
    with pytest.raises(ValueError, match="severity"):
        Finding(category="X1", severity="WRONG", message="x")


def test_finding_lowercase_severity_normalises():
    """'high' / 'low' / 'medium' / 'med' are all accepted (case-folded)."""
    for s in ("high", "low", "medium", "med"):
        f = Finding(category="X1", severity=s, message="x")
        assert f.severity in ("HIGH", "LOW", "MEDIUM")


def test_finding_is_frozen():
    """Finding is frozen — attribute reassignment raises."""
    f = Finding(category="X1", severity="HIGH", message="x")
    with pytest.raises(Exception):  # FrozenInstanceError
        f.message = "different"  # type: ignore[misc]


def test_finding_rejects_empty_category():
    """Empty category raises ValueError."""
    with pytest.raises(ValueError, match="category"):
        Finding(category="", severity="HIGH", message="x")


# =====================================================================
# TestCheckDecorator: @check behavior + validation
# =====================================================================


def test_check_wraps_function_as_decorated_check():
    """The @check decorator returns a _DecoratedCheck, not the bare fn."""
    @check(name="noop", severity="LOW", help_text="does nothing")
    def noop(tex, config=None):
        return []
    assert isinstance(noop, _DecoratedCheck)
    assert noop.name == "noop"
    assert noop.severity == "LOW"
    assert noop.help_text == "does nothing"


def test_check_metadata_attached():
    """The decorator exposes metadata via __tmaudit_meta__."""
    @check(name="x", severity="HIGH",
           requires_config=True, help_text="hi", version="1.2.3")
    def f(tex, config=None):
        return []
    meta = f.__tmaudit_meta__
    assert meta["name"] == "x"
    assert meta["severity"] == "HIGH"
    assert meta["requires_config"] is True
    assert meta["help_text"] == "hi"
    assert meta["version"] == "1.2.3"


def test_check_rejects_empty_name():
    """An empty plugin name raises ValueError."""
    with pytest.raises(ValueError, match="name"):
        @check(name="", severity="LOW")
        def f(tex, config=None):
            return []


def test_check_rejects_invalid_severity():
    """An unknown severity in @check raises ValueError."""
    with pytest.raises(ValueError, match="severity"):
        @check(name="x", severity="WHATEVER")
        def f(tex, config=None):
            return []


def test_check_normalises_med_severity():
    """@check(name, severity='MED') normalises to 'MEDIUM'."""
    @check(name="x", severity="MED")
    def f(tex, config=None):
        return []
    assert f.severity == "MEDIUM"


def test_check_rejects_non_callable():
    """@check applied to a non-callable raises TypeError."""
    with pytest.raises(TypeError, match="callable"):
        check(name="x", severity="LOW")(42)  # type: ignore[arg-type]


def test_check_decorated_callable_invokes_original_fn():
    """Calling the wrapped plugin delegates to the original function."""
    captured = []

    @check(name="x", severity="LOW")
    def sample(tex, config=None):
        captured.append((tex, config))
        return [Finding(category="X", severity="LOW", message="ok")]

    fs = sample("hello", {"k": "v"})
    assert captured == [("hello", {"k": "v"})]
    assert len(fs) == 1
    assert fs[0].category == "X"


# =====================================================================
# TestFilterActive: disabled-list subtraction
# =====================================================================


def test_filter_active_removes_disabled():
    """filter_active() excludes names in the disabled list."""
    plugins = {
        "alpha": _DecoratedCheck(fn=_no_op_plugin, name="alpha", severity="LOW",
                                  requires_config=False, help_text="", version="0.1"),
        "beta":  _DecoratedCheck(fn=_no_op_plugin, name="beta",  severity="LOW",
                                  requires_config=False, help_text="", version="0.1"),
    }
    active = filter_active(plugins, disabled=["beta"])
    assert set(active) == {"alpha"}


def test_filter_active_empty_disabled_returns_full_dict():
    """When disabled is None or empty, all plugins are active."""
    plugins = {"a": object(), "b": object()}
    active = filter_active(plugins)
    assert set(active) == {"a", "b"}
    active = filter_active(plugins, disabled=[])
    assert set(active) == {"a", "b"}


def test_filter_active_with_unknown_disabled_keeps_unknown():
    """A name in disabled that isn't a known plugin is silently ignored."""
    plugins = {"a": object()}
    active = filter_active(plugins, disabled=["nonexistent"])
    assert set(active) == {"a"}


# =====================================================================
# TestRunPlugin: paper_id stamping and exception safety
# =====================================================================


def test_run_plugin_stamps_paper_id():
    """run_plugin() stamps paper_id on every emitted Finding."""
    plugin = _DecoratedCheck(fn=_todo_plugin, name="todo-flag",
                              severity="MEDIUM",
                              requires_config=False, help_text="",
                              version="0.1")
    findings = run_plugin(plugin, tex="hello\nTODO: fix\nbye\n",
                          paper_id="paper-7")
    assert len(findings) == 1
    assert findings[0].paper_id == "paper-7"
    assert findings[0].category == "TODO"
    assert findings[0].line == 2


def test_run_plugin_no_paper_id_keeps_none():
    """run_plugin() with paper_id=None does not stamp anything."""
    plugin = _DecoratedCheck(fn=_todo_plugin, name="todo-flag",
                              severity="MEDIUM",
                              requires_config=False, help_text="",
                              version="0.1")
    findings = run_plugin(plugin, tex="hello\nTODO\n", paper_id=None)
    assert findings[0].paper_id is None


def test_run_plugin_does_not_overwrite_existing_paper_id():
    """If a plugin already set paper_id (rare), we don't overwrite."""
    def pre_stamped(tex, config=None):
        return [Finding(category="X", severity="LOW", message="x",
                        paper_id="preset")]
    plugin = _DecoratedCheck(fn=pre_stamped, name="x",
                              severity="LOW",
                              requires_config=False, help_text="",
                              version="0.1")
    findings = run_plugin(plugin, tex="any",
                          paper_id="outer")
    # 'preset' wins (pre-stamped by the plugin).
    assert findings[0].paper_id == "preset"


def test_run_all_plugins_skips_raising_plugin():
    """A plugin that raises is logged and skipped, others still run."""
    plugins = {
        "raiser": _DecoratedCheck(fn=_raising_plugin, name="raiser",
                                   severity="HIGH",
                                   requires_config=False, help_text="",
                                   version="0.1"),
        "quiet":  _DecoratedCheck(fn=_no_op_plugin,  name="quiet",
                                   severity="LOW",
                                   requires_config=False, help_text="",
                                   version="0.1"),
    }
    findings = run_all_plugins(plugins, tex="anything")
    # The raising plugin is skipped, the quiet one returns []. No findings.
    assert findings == []


def test_run_all_plugins_collects_from_multiple():
    """Multiple plugins' findings are concatenated into one list."""
    plugins = {
        "todo": _DecoratedCheck(fn=_todo_plugin, name="todo",
                                  severity="MEDIUM",
                                  requires_config=False, help_text="",
                                  version="0.1"),
        "noop": _DecoratedCheck(fn=_no_op_plugin, name="noop",
                                  severity="LOW",
                                  requires_config=False, help_text="",
                                  version="0.1"),
    }
    findings = run_all_plugins(plugins, tex="first\nTODO\nsecond\nTODO\n")
    assert len(findings) == 2
    assert all(f.category == "TODO" for f in findings)


# =====================================================================
# TestLoadPlugins: entry-points discovery
# =====================================================================


def test_load_plugins_returns_dict():
    """load_plugins() returns a dict (possibly empty)."""
    reset_loader_cache()
    plugins = load_plugins()
    assert isinstance(plugins, dict)


def test_load_plugins_caches_result():
    """Second call returns the same content without re-importing."""
    reset_loader_cache()
    first = load_plugins()
    second = load_plugins()
    # The cached dict is reused; we verify by content equality.
    assert first == second


def test_load_plugins_force_reload_refreshes_cache_separately():
    """force_reload=True is a separate call path that rebuilds the cache."""
    reset_loader_cache()
    first = load_plugins()
    second = load_plugins(force_reload=True)
    # Both must be dicts; content is equal here because no
    # plugins are registered in the test environment.
    assert isinstance(first, dict)
    assert isinstance(second, dict)


def test_load_plugins_handles_entry_point_group():
    """The loader uses the documented entry-point group."""
    # We can't install a real plugin in tests, but we can
    # verify the constant.
    assert PLUGIN_GROUP == "tmaudit.plugins"


# =====================================================================
# TestPerPaperDisable: c11_plugins_disabled is read from PAPER_CONFIGS
# =====================================================================


def test_paper_configs_can_carry_c11_plugins_disabled():
    """PAPER_CONFIGS schema permits c11_plugins_disabled (it is optional)."""
    from tmaudit.configs.paper_configs import PAPER_CONFIGS
    # No assertion on actual values (any paper may or may not
    # have this field), but import must succeed and the field,
    # if present, must be a list of strings.
    for n, cfg in PAPER_CONFIGS.items():
        d = cfg.get("c11_plugins_disabled")
        assert d is None or (
            isinstance(d, list) and
            all(isinstance(x, str) for x in d)
        ), f"paper {n}: c11_plugins_disabled must be None or list[str]"


# =====================================================================
# TestReExports: the public surface is correct
# =====================================================================


def test_plugin_api_re_exported_at_package_root():
    """The plugin API is importable from `tmaudit` (not just `tmaudit.plugins`)."""
    assert tmaudit.Finding is Finding
    assert tmaudit.check is check
    assert tmaudit.PLUGIN_GROUP == PLUGIN_GROUP


def test_valid_severities_includes_canonical_forms():
    """The exposed VALID_SEVERITIES tuple lists the canonical strings."""
    for s in ("HIGH", "MEDIUM", "LOW"):
        assert s in VALID_SEVERITIES


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
