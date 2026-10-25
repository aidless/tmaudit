"""Tests for external (on-disk) paper configs: `tmaudit verify --target`.

The contract being protected is the one that makes the tool usable by
someone who does not own a ``PAPER<N>_CONSOLIDATED`` directory: a config
file on disk must produce *the same* forked script shape as
``--paper N``, with validation strict enough that a typo cannot silently
disable a check.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tmaudit import forge
from tmaudit.cli import main as cli_main
from tmaudit.configs.target_config import (
    SCHEMA_ID,
    TargetConfigError,
    load_target_config,
)

TOML_MINIMAL = """\
schema = "tmaudit-target/1"

[paper]
name = "My Paper"
tex_basename = "paper"

[checks]
c4_self_cite_prefix = 'smith2025'
c6_blacklist = ['paradigm']
c4_max_self_cite_keys = 2

[[checks.c1_symbols]]
name = 'CAF'
token = '\\bCAF\\b'
definition = 'CAF.{0,80}='

[checks.c2_families]
main = 3
"""

TEX = r"""\documentclass{article}
\begin{document}
\begin{abstract}
We measure a coefficient we call CAF, defined as consensus agreement
across reviewers, and report how it behaves under perturbation.
\end{abstract}
\section{Introduction}
We study calibration.
\end{document}
"""

BIB = """@article{smith2020, title={X}, author={S}, year={2020}}\n"""


def _write_paper(tmp_path, name="paper.tex"):
    (tmp_path / name).write_text(TEX, encoding="utf-8")
    (tmp_path / "refs.bib").write_text(BIB, encoding="utf-8")


def _write_toml(tmp_path, text=TOML_MINIMAL, name="paper.toml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ============================================================================
# Loading and validation
# ============================================================================

class TestLoad:
    def test_minimal_toml_round_trips(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        assert spec.name == "My Paper"
        assert spec.tex_basename == "paper"
        assert spec.dir == tmp_path.resolve()
        assert spec.config["c4_self_cite_prefix"] == "smith2025"
        assert spec.config["c4_max_self_cite_keys"] == 2
        assert spec.config["c6_blacklist"] == ["paradigm"]
        assert spec.config["c2_families"] == {"main": 3}
        assert spec.config["c1_symbols"][0]["token"] == r"\bCAF\b"

    def test_script_name_is_slugified(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        assert spec.script_name() == "verify_my-paper.py"

    def test_defaults_are_neutral_not_author_specific(self, tmp_path):
        p = tmp_path / "min.toml"
        p.write_text('[paper]\nname = "x"\n', encoding="utf-8")
        spec = load_target_config(p)
        assert spec.config["c4_self_cite_prefix"] == ""
        assert spec.config["c4_self_cite_threshold"] == 0.30
        assert spec.config["c7_max_ceremonial"] == 2
        assert spec.config["c1_symbols"] == []

    def test_json_config_is_equivalent(self, tmp_path):
        payload = {
            "schema": SCHEMA_ID,
            "paper": {"name": "j", "tex_basename": "paper"},
            "checks": {"c4_self_cite_prefix": "smith2025",
                       "c4_max_self_cite_keys": 2},
        }
        p = tmp_path / "paper.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        spec = load_target_config(p)
        assert spec.config["c4_max_self_cite_keys"] == 2

    def test_relative_dir_resolves_against_config_file(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        p = tmp_path / "cfg.toml"
        p.write_text('[paper]\ndir = "sub"\n', encoding="utf-8")
        assert load_target_config(p).dir == sub.resolve()

    def test_absolute_dir_is_kept(self, tmp_path):
        other = tmp_path / "elsewhere"
        other.mkdir()
        p = tmp_path / "cfg.toml"
        p.write_text('[paper]\ndir = "%s"\n' % other.as_posix(), encoding="utf-8")
        assert load_target_config(p).dir == other.resolve()


class TestBibResolution:
    def test_defaults_to_refs_bib_when_nothing_else_exists(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text('[paper]\nname = "x"\n', encoding="utf-8")
        assert load_target_config(p).bib == "refs.bib"

    def test_finds_references_bib(self, tmp_path):
        (tmp_path / "references.bib").write_text("", encoding="utf-8")
        p = tmp_path / "cfg.toml"
        p.write_text('[paper]\nname = "x"\n', encoding="utf-8")
        assert load_target_config(p).bib == "references.bib"

    def test_falls_back_to_bbl_for_an_arxiv_tarball(self, tmp_path):
        (tmp_path / "main.bbl").write_text("", encoding="utf-8")
        p = tmp_path / "cfg.toml"
        p.write_text('[paper]\nname = "x"\n', encoding="utf-8")
        assert load_target_config(p).bib == "main.bbl"

    def test_bib_preferred_over_bbl_when_both_exist(self, tmp_path):
        (tmp_path / "main.bbl").write_text("", encoding="utf-8")
        (tmp_path / "references.bib").write_text("", encoding="utf-8")
        p = tmp_path / "cfg.toml"
        p.write_text('[paper]\nname = "x"\n', encoding="utf-8")
        assert load_target_config(p).bib == "references.bib"

    def test_explicit_bib_wins_over_detection(self, tmp_path):
        (tmp_path / "references.bib").write_text("", encoding="utf-8")
        (tmp_path / "custom.bib").write_text("", encoding="utf-8")
        p = tmp_path / "cfg.toml"
        p.write_text('[paper]\nname = "x"\nbib = "custom.bib"\n', encoding="utf-8")
        assert load_target_config(p).bib == "custom.bib"

    def test_bbl_is_reachable_in_the_forked_script(self, tmp_path):
        (tmp_path / "paper.tex").write_text(TEX, encoding="utf-8")
        (tmp_path / "main.bbl").write_text("", encoding="utf-8")
        p = tmp_path / "cfg.toml"
        p.write_text(
            '[paper]\nname = "x"\ntex_basename = "paper"\n', encoding="utf-8")
        src = forge.fork_verify_for_target(
            load_target_config(p)).read_text(encoding="utf-8")
        assert "REFS = ROOT / 'main.bbl'" in src


class TestValidationErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(TargetConfigError, match="not found"):
            load_target_config(tmp_path / "nope.toml")

    def test_directory_instead_of_file(self, tmp_path):
        with pytest.raises(TargetConfigError, match="directory"):
            load_target_config(tmp_path)

    def test_unsupported_suffix(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text("x: 1", encoding="utf-8")
        with pytest.raises(TargetConfigError, match="unsupported config format"):
            load_target_config(p)

    def test_unknown_checks_key_suggests_alternative(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("[checks]\nc6_blacklst = ['x']\n", encoding="utf-8")
        with pytest.raises(TargetConfigError) as ei:
            load_target_config(p)
        msg = str(ei.value)
        assert "unknown key" in msg
        assert "c6_blacklist" in msg

    def test_unknown_top_level_key(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("check = []\n", encoding="utf-8")
        with pytest.raises(TargetConfigError, match="top level"):
            load_target_config(p)

    def test_unknown_paper_key(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("[paper]\ntexbase = 'x'\n", encoding="utf-8")
        with pytest.raises(TargetConfigError, match=r"\[paper\]"):
            load_target_config(p)

    def test_bad_schema_version(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text('schema = "tmaudit-target/99"\n', encoding="utf-8")
        with pytest.raises(TargetConfigError, match="unsupported schema"):
            load_target_config(p)

    def test_wrong_type_for_int(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("[checks]\nc4_max_self_cite_keys = '3'\n", encoding="utf-8")
        with pytest.raises(TargetConfigError, match="must be an integer"):
            load_target_config(p)

    def test_wrong_type_for_float(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("[checks]\nc4_self_cite_threshold = 'high'\n", encoding="utf-8")
        with pytest.raises(TargetConfigError, match="must be a number"):
            load_target_config(p)

    def test_blacklist_must_be_string_list(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("[checks]\nc6_blacklist = [1, 2]\n", encoding="utf-8")
        with pytest.raises(TargetConfigError, match="list of strings"):
            load_target_config(p)

    def test_c1_symbol_requires_token(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text(
            "[[checks.c1_symbols]]\nname = 'X'\ndefinition = 'X='\n",
            encoding="utf-8",
        )
        with pytest.raises(TargetConfigError, match="missing required key"):
            load_target_config(p)

    def test_malformed_toml_reports_the_file(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text("[paper\nname = 'x'\n", encoding="utf-8")
        with pytest.raises(TargetConfigError, match="invalid TOML"):
            load_target_config(p)


class TestWarnings:
    def test_missing_tex_file_warns_but_loads(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        warns = "\n".join(spec.warnings())
        assert "tex file not found" in warns

    def test_missing_bib_warns(self, tmp_path):
        (tmp_path / "paper.tex").write_text(TEX, encoding="utf-8")
        spec = load_target_config(_write_toml(tmp_path))
        assert any("refs.bib" in w for w in spec.warnings())

    def test_clean_paper_has_no_warnings(self, tmp_path):
        _write_paper(tmp_path)
        spec = load_target_config(_write_toml(tmp_path))
        assert spec.warnings() == []


# ============================================================================
# Forking
# ============================================================================

class TestFork:
    def test_script_is_parseable_and_uses_spec_root(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        target = forge.fork_verify_for_target(spec)
        assert target.name == "verify_my-paper.py"
        src = target.read_text(encoding="utf-8")
        compile(src, str(target), "exec")
        assert "ROOT = Path(%r)" % tmp_path.resolve().as_posix() in src

    def test_tex_basename_reaches_the_main_constant(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        src = forge.fork_verify_for_target(spec).read_text(encoding="utf-8")
        assert "MAIN = ROOT / 'paper.tex'" in src

    def test_bib_override_reaches_the_refs_constant(self, tmp_path):
        p = tmp_path / "cfg.toml"
        p.write_text(
            '[paper]\nname = "x"\nbib = "references.bib"\n', encoding="utf-8")
        src = forge.fork_verify_for_target(
            load_target_config(p)).read_text(encoding="utf-8")
        assert "REFS = ROOT / 'references.bib'" in src

    def test_default_bib_leaves_refs_untouched(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        src = forge.fork_verify_for_target(spec).read_text(encoding="utf-8")
        assert "REFS = ROOT / 'refs.bib'" in src

    def test_extended_keys_are_emitted(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        src = forge.fork_verify_for_target(spec).read_text(encoding="utf-8")
        for key in ("c7_max_ceremonial", "c8_claimed_effects",
                    "c9_figure_keywords", "c10_reproducibility_claims",
                    "c11_plugins_enabled"):
            assert key in src, key

    def test_in_repo_fork_stays_byte_identical_without_extended(self):
        """include_extended=False must reproduce the pre-v0.6.0 output.

        The five in-repo papers have always shipped scripts without
        C7..C11 keys; turning that on by default would silently change
        five audited artifacts.
        """
        from tmaudit.configs.paper_configs import PAPER_CONFIGS

        template = forge._read_template("verify_TEMPLATE.py")
        cfg = PAPER_CONFIGS[1]
        plain = forge._substitute_verify(template, cfg)
        ext = forge._substitute_verify(template, cfg, include_extended=True)
        # Check for the emitted dict *key* (quoted, followed by a colon).
        # The template body also mentions c8_claimed_effects inside a
        # CHECKS_CONFIG.get(...) call, which must not be mistaken for an
        # injected key.
        key = "'c8_claimed_effects':"
        assert key not in plain
        assert key in ext

    def test_output_dir_override_does_not_move_root(self, tmp_path):
        spec = load_target_config(_write_toml(tmp_path))
        out = tmp_path / "out"
        target = forge.fork_verify_for_target(spec, out)
        assert target.parent == out
        src = target.read_text(encoding="utf-8")
        assert "ROOT = Path(%r)" % tmp_path.resolve().as_posix() in src


class TestPackageMetadata:
    def test_version_has_a_single_source_of_truth(self):
        """pyproject.toml and __init__.__version__ must agree.

        They drifted once (pyproject said 0.5.1, __init__ said 0.5.0, and
        the tag v0.5.1 shipped), which put the wrong version in every
        ``audit-all`` Markdown report, because report.py reads
        ``tmaudit.__version__``. Two declarations cannot be made into one
        without a build-time plugin, so they are checked instead.
        """
        import re
        from pathlib import Path

        import tmaudit

        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        declared = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        assert declared, "no [project].version in pyproject.toml"
        assert declared.group(1) == tmaudit.__version__, (
            "pyproject version %r != tmaudit.__version__ %r"
            % (declared.group(1), tmaudit.__version__)
        )

    def test_target_is_exported_from_package_root(self):
        import tmaudit

        for name in ("TexTarget", "TextTarget", "Target", "as_target", "as_text"):
            assert name in tmaudit.__all__, name
            assert hasattr(tmaudit, name), name


# ============================================================================
# CLI surface
# ============================================================================

class TestCli:
    def test_paper_and_target_are_mutually_exclusive(self, tmp_path):
        assert cli_main(["verify", "--paper", "1",
                         "--target", str(_write_toml(tmp_path))]) == 2

    def test_no_paper_no_target_errors(self):
        assert cli_main(["verify"]) == 2

    def test_invalid_target_returns_2_and_does_not_fork(self, tmp_path):
        bad = tmp_path / "bad.toml"
        bad.write_text("[checks]\nnope = 1\n", encoding="utf-8")
        assert cli_main(["verify", "--target", str(bad)]) == 2
        assert not list(tmp_path.glob("verify_*.py"))

    def test_dry_run_writes_nothing(self, tmp_path):
        rc = cli_main(["verify", "--target", str(_write_toml(tmp_path)), "--dry-run"])
        assert rc == 0
        assert not list(tmp_path.glob("verify_*.py"))

    def test_end_to_end_runs_the_forked_script(self, tmp_path):
        _write_paper(tmp_path)
        rc = cli_main(["verify", "--target", str(_write_toml(tmp_path))])
        # 0 = clean, 1 = findings reported. 2 would mean the forked script
        # could not find main.tex/refs.bib, i.e. the plumbing is wrong.
        assert rc in (0, 1)
        assert (tmp_path / "verify_my-paper.py").exists()

    def test_forked_script_is_directly_runnable(self, tmp_path):
        _write_paper(tmp_path)
        spec = load_target_config(_write_toml(tmp_path))
        target = forge.fork_verify_for_target(spec)
        proc = subprocess.run(
            [sys.executable, str(target)],
            cwd=str(target.parent),
            capture_output=True, text=True,
        )
        assert proc.returncode in (0, 1), proc.stderr
        assert "ERROR: missing" not in proc.stderr
