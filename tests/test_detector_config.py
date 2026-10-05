"""Unit tests for tmaudit.detector_config.

Covers:
  T1: DEFAULT_CONFIG structure & values
  T2: load_config(yaml in repo)  -> values from yaml
  T3: load_config(missing file)  -> DEFAULT_CONFIG (deep copy, no mutation)
  T4: load_config(partial yaml)  -> deep_merge: override wins, missing keys filled
  T5: load_config(broken yaml)   -> DEFAULT_CONFIG + stderr warning
  T6: deep_merge immutability    -> base & override not mutated
  T7: deep_merge type rules      -> dict recurses, non-dict replaces
  T8: detect_arxiv_year_issues_min uses CONFIG['arxiv']['safe_window_months']
"""
from __future__ import annotations
import sys
from pathlib import Path


# Make src/ importable without installing
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tmaudit.detector_config import (
    DEFAULT_CONFIG,
    load_config,
    _deep_merge,
    detect_arxiv_year_issues_min,
)
from tmaudit.detector_config.detector_min import CONFIG_FILE_DEFAULT


# ─────────────────────────── T1: DEFAULT_CONFIG shape ───────────────────────────

def test_default_config_has_expected_keys():
    assert set(DEFAULT_CONFIG.keys()) == {"arxiv", "internal", "log"}
    assert DEFAULT_CONFIG["arxiv"]["safe_window_months"] == 2
    assert DEFAULT_CONFIG["arxiv"]["verify_online"] is True
    assert DEFAULT_CONFIG["arxiv"]["api_timeout_sec"] == 8
    assert DEFAULT_CONFIG["internal"]["soft_down_paragraph"] is True
    assert DEFAULT_CONFIG["log"]["file_enabled"] is True
    assert DEFAULT_CONFIG["log"]["file_path"] == "detector.log"


# ─────────────────────── T2: load_config from shipped yaml ──────────────────────

def test_load_config_reads_shipped_yaml(tmp_path):
    """The detector.yaml in the package must exist and be loadable."""
    assert CONFIG_FILE_DEFAULT.exists(), (
        f"detector.yaml missing at {CONFIG_FILE_DEFAULT}"
    )
    cfg = load_config(CONFIG_FILE_DEFAULT)
    # All override-able keys from the shipped yaml are reflected
    assert cfg["arxiv"]["safe_window_months"] == 2
    assert cfg["arxiv"]["verify_online"] is True
    assert cfg["log"]["file_path"] == "detector.log"
    # Same number of top-level keys (no missing sections)
    assert set(cfg.keys()) == set(DEFAULT_CONFIG.keys())


# ─────────────────────── T3: load_config missing file ───────────────────────────

def test_load_config_missing_file_returns_default(tmp_path):
    missing = tmp_path / "no_such.yaml"
    cfg = load_config(missing)
    # Same values
    assert cfg == DEFAULT_CONFIG
    # And critically: it's a deep copy, not the SAME object
    assert cfg is not DEFAULT_CONFIG
    assert cfg["arxiv"] is not DEFAULT_CONFIG["arxiv"]
    # Mutating the returned config must not poison DEFAULT_CONFIG
    cfg["arxiv"]["safe_window_months"] = 99
    assert DEFAULT_CONFIG["arxiv"]["safe_window_months"] == 2


# ─────────────────────── T4: load_config partial yaml ──────────────────────────

def test_load_config_partial_yaml_deep_merges(tmp_path):
    partial = tmp_path / "partial.yaml"
    partial.write_text(
        "arxiv:\n"
        "  safe_window_months: 6\n"
        "  api_timeout_sec: 20\n"
        "log:\n"
        "  file_path: custom.log\n",
        encoding="utf-8",
    )
    cfg = load_config(partial)
    # Overridden:
    assert cfg["arxiv"]["safe_window_months"] == 6
    assert cfg["arxiv"]["api_timeout_sec"] == 20
    assert cfg["log"]["file_path"] == "custom.log"
    # Filled from default:
    assert cfg["arxiv"]["verify_online"] is True       # not in partial
    assert cfg["arxiv"]["user_agent"] == "mm3-detector/1.0"
    assert cfg["internal"]["soft_down_paragraph"] is True
    assert cfg["log"]["console_level"] == "INFO"
    # Top-level keys still all present
    assert set(cfg.keys()) == {"arxiv", "internal", "log"}


# ─────────────────────── T5: load_config broken yaml ───────────────────────────

def test_load_config_broken_yaml_returns_default_with_warning(tmp_path, capsys):
    broken = tmp_path / "broken.yaml"
    # Unterminated flow mapping -> yaml.YAMLError
    broken.write_text("arxiv: {safe_window_months: 5\n  bad: oops", encoding="utf-8")
    cfg = load_config(broken)
    # Falls back to default
    assert cfg["arxiv"]["safe_window_months"] == 2
    # Stderr should mention the read failure
    err = capsys.readouterr().err
    assert "detector.config" in err
    assert "cannot read" in err
    assert str(broken) in err


# ─────────────────────── T6: deep_merge immutability ───────────────────────────

def test_deep_merge_does_not_mutate_inputs():
    base = {"a": {"x": 1, "y": 2}, "b": 10}
    override = {"a": {"x": 99}, "c": 20}
    merged = _deep_merge(base, override)
    # base unchanged
    assert base == {"a": {"x": 1, "y": 2}, "b": 10}
    # override unchanged
    assert override == {"a": {"x": 99}, "c": 20}
    # merged is right
    assert merged == {"a": {"x": 99, "y": 2}, "b": 10, "c": 20}
    # merged containers are NEW objects
    assert merged["a"] is not base["a"]
    assert merged["a"] is not override["a"]


# ─────────────────────── T7: deep_merge type rules ─────────────────────────────

def test_deep_merge_type_rules():
    # Non-dict override REPLACES dict base
    m1 = _deep_merge({"x": {"a": 1}}, {"x": "string"})
    assert m1 == {"x": "string"}
    # Non-dict base + dict override -> dict
    m2 = _deep_merge({"x": "string"}, {"x": {"a": 1}})
    assert m2 == {"x": {"a": 1}}
    # None override is treated as empty
    m3 = _deep_merge({"x": 1}, None)
    assert m3 == {"x": 1}
    # Empty override keeps base
    m4 = _deep_merge({"x": 1, "y": 2}, {})
    assert m4 == {"x": 1, "y": 2}


# ─────────────────────── T8: detector honors safe_window_months ────────────────

def test_detector_uses_safe_window_from_config():
    # Default config: safe_window_months=2 -> safe = [5, 9] for month=7
    text = "see arXiv:2604.11581 for details"  # month=4 < 5
    issues = detect_arxiv_year_issues_min(text, current_year=2026, current_month=7)
    assert len(issues) == 1
    assert issues[0]["month"] == 4
    assert issues[0]["severity"] == "HIGH"
    assert issues[0]["safe_window"] == (5, 9)
    assert issues[0]["type"] == "arxiv_year_outside_safe_window"

    # Override config: safe_window_months=4 -> safe = [3, 11] -> 4 is in window
    cfg = {"arxiv": {"safe_window_months": 4}, "internal": {}, "log": {}}
    issues2 = detect_arxiv_year_issues_min(text, config=cfg,
                                            current_year=2026, current_month=7)
    assert len(issues2) == 1
    assert issues2[0]["severity"] == "MEDIUM"
    assert issues2[0]["type"] == "arxiv_year_safe_window"
    assert issues2[0]["safe_window"] == (3, 11)
