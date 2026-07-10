"""Tests for the tmaudit_example_plugin package.

This test file verifies that the in-repo example plugin
package actually works end-to-end. The tests assume the
plugin is installed (``pip install -e ./tmaudit_example_plugin``)
and that the entry points are registered.
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
    PLUGIN_GROUP,
    check,
    filter_active,
    load_plugins,
    reset_loader_cache,
)


# =====================================================================
# Discovery: the three demo plugins must be discoverable
# =====================================================================


def test_example_plugin_three_checks_discoverable():
    """After install, the three demo plugins show up via entry-points."""
    reset_loader_cache()
    plugins = load_plugins()
    for name in ("flag-todo-markers", "flag-xxx-markers",
                 "flag-long-abstract"):
        assert name in plugins, (
            f"Expected demo plugin {name!r} to be discoverable, "
            f"got: {sorted(plugins)}"
        )


def test_example_plugin_metadata_is_correct():
    """Each demo plugin has the expected name + severity + version."""
    reset_loader_cache()
    plugins = load_plugins()
    expected = {
        "flag-todo-markers": ("MEDIUM", "0.1.0"),
        "flag-xxx-markers": ("LOW", "0.1.0"),
        "flag-long-abstract": ("MEDIUM", "0.1.0"),
    }
    for name, (sev, ver) in expected.items():
        meta = plugins[name].__tmaudit_meta__
        assert meta["severity"] == sev, f"{name}: severity mismatch"
        assert meta["version"] == ver, f"{name}: version mismatch"


# =====================================================================
# Per-check semantics
# =====================================================================


def test_flag_todo_markers_emits_finding_on_todo():
    """The flag-todo-markers check returns a finding when 'TODO' appears."""
    reset_loader_cache()
    plugins = load_plugins()
    plugin = plugins["flag-todo-markers"]
    tex = "Body\nTODO: fix this\nMore body\n"
    findings = plugin(tex=tex)
    assert len(findings) == 1
    f = findings[0]
    assert f.category == "TODO"
    assert f.severity == "MEDIUM"
    assert f.line == 2


def test_flag_todo_markers_also_flags_fixme():
    """FIXME triggers the same check."""
    plugin = load_plugins()["flag-todo-markers"]
    findings = plugin(tex="line one\nFIXME: bug here\nline three\n")
    assert len(findings) == 1
    assert "FIXME" in findings[0].message


def test_flag_todo_markers_no_finding_on_clean():
    """A clean paper produces 0 findings."""
    plugin = load_plugins()["flag-todo-markers"]
    findings = plugin(tex="nothing here\nno markers\nat all\n")
    assert findings == []


def test_flag_xxx_markers_emits_on_xxx():
    """XXX in the body emits a LOW finding."""
    reset_loader_cache()
    plugin = load_plugins()["flag-xxx-markers"]
    findings = plugin(tex="draft\nXXX check this\n")
    assert len(findings) == 1
    f = findings[0]
    assert f.category == "XXX"
    assert f.severity == "LOW"
    assert f.line == 2


def test_flag_xxx_markers_does_not_match_within_words():
    """A word containing 'xxx' (e.g. 'xxx-thesis') does NOT match.

    The \\b boundary in the regex ensures we only match
    standalone XXX markers.
    """
    reset_loader_cache()
    plugin = load_plugins()["flag-xxx-markers"]
    findings = plugin(tex="xxx-thesis\nnot a marker\n")
    assert findings == [], (
        f"Expected 0 findings, got: {findings}"
    )


def test_flag_long_abstract_emits_on_too_many_words():
    """Abstracts > 300 words trigger a MEDIUM finding."""
    reset_loader_cache()
    plugin = load_plugins()["flag-long-abstract"]
    long_body = "alpha " * 350
    tex = f"\\begin{{abstract}}\n{long_body}\n\\end{{abstract}}\n"
    findings = plugin(tex=tex)
    assert len(findings) == 1
    f = findings[0]
    assert f.category == "ABSTRACT"
    assert f.severity == "MEDIUM"
    assert "350" in f.message


def test_flag_long_abstract_no_finding_on_short_abstract():
    """A short abstract (< 300 words) is silent."""
    reset_loader_cache()
    plugin = load_plugins()["flag-long-abstract"]
    short_body = "alpha beta gamma delta\n"
    tex = f"\\begin{{abstract}}\n{short_body}\\end{{abstract}}\n"
    findings = plugin(tex=tex)
    assert findings == []


def test_flag_long_abstract_no_abstract_present_no_finding():
    """A paper without an abstract returns 0 findings (skips cleanly)."""
    reset_loader_cache()
    plugin = load_plugins()["flag-long-abstract"]
    findings = plugin(tex="just body text, no abstract here\n")
    assert findings == []


def test_flag_long_abstract_respects_config_threshold():
    """A custom threshold is honoured."""
    reset_loader_cache()
    plugin = load_plugins()["flag-long-abstract"]
    # 50 words with a custom threshold of 30.
    body = " ".join(f"w{i}" for i in range(50))
    tex = f"\\begin{{abstract}}\n{body}\n\\end{{abstract}}\n"
    # Default threshold is 300; 50 < 300 → no finding.
    assert plugin(tex=tex) == []
    # With a tight threshold of 30, 50 > 30 → finding.
    findings = plugin(tex=tex, config={"c11_long_abstract_threshold": 30})
    assert len(findings) == 1
    assert "30" in findings[0].message


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
