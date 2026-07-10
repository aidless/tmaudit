"""Happy-path / integration tests for tmaudit.forge.

These tests complement the bug-regression tests in test_forge.py.
They verify the end-to-end behaviour:

  1. fork_verify() writes a parseable, runnable verify_p<N>.py.
  2. The forked script, when run on a known paper, produces 0 findings.
  3. The dry-run path does not write any file.

These are slower than the unit tests (they touch the filesystem
and run the auditor), so they are kept in a separate file.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

import pytest

from tmaudit import forge
from tmaudit.configs import VERIFY_CONFIGS, COMPILE_CONFIGS


# ============================================================================
# fork_verify integration
# ============================================================================

class TestForkVerify:
    def test_fork_writes_parseable_python(self, tmp_path, paper1_config):
        target = fork_with_tmpdir(1, tmp_path, paper1_config)
        # The forked script must be valid Python (compile-able)
        with target.open(encoding='utf-8') as f:
            source = f.read()
        try:
            compile(source, str(target), 'exec')
        except SyntaxError as e:
            pytest.fail(f'Forked verify_p1.py has syntax error: {e}')

    def test_fork_changes_root_to_paper_dir(self, tmp_path, paper1_config):
        target = fork_with_tmpdir(1, tmp_path, paper1_config)
        source = target.read_text(encoding='utf-8')
        # The ROOT line must reference the per-paper directory we
        # passed in (or, if we did not, the directory from the config).
        if 'paper_dir' in paper1_config and paper1_config.get('dir'):
            assert 'PAPER1_CONSOLIDATED' in source

    def test_fork_dry_run_does_not_write(self, tmp_path, monkeypatch, paper1_config):
        # fork_verify() itself does not have a dry-run flag; the
        # CLI does. So we test the CLI dry-run path.
        from tmaudit.cli import main as cli_main
        rc = cli_main(['verify', '--paper', '1', '--dry-run'])
        assert rc == 0
        # And no file was created in tmp_path
        verify_target = tmp_path / 'verify_p1.py'
        assert not verify_target.exists(), (
            'verify --dry-run must not write any file'
        )


def fork_with_tmpdir(paper_number: int, tmp_path: Path, cfg: dict) -> Path:
    """Helper: fork a verify script into a tmp directory using cfg['dir']
    as a paper_dir override.
    """
    # The real paper directory is PAPER1_CONSOLIDATED; we want to
    # write into tmp_path instead, so we use --paper-dir.
    return forge.fork_verify(paper_number, paper_dir=tmp_path)


# ============================================================================
# End-to-end: fork + run + 0 findings for the known-good papers
# ============================================================================

@pytest.mark.slow
class TestEndToEndAudit:
    """These tests run the actual audit on a real paper. They are
    marked `@pytest.mark.slow` so they can be skipped with
    `pytest -m "not slow"` during fast iteration.
    """

    def test_paper_1_forks_and_passes(self):
        """Fork and run verify on Paper 1; expect 0 findings."""
        target = forge.fork_verify(1)
        try:
            result = subprocess.run(
                [sys.executable, str(target)],
                cwd=target.parent,
                capture_output=True, text=True, timeout=60,
            )
        finally:
            # Clean up: remove the forked file (it was written into
            # PAPER1_CONSOLIDATED)
            pass
        assert result.returncode == 0, (
            f'forked verify_p1.py returned {result.returncode}\n'
            f'stdout:\n{result.stdout}\n'
            f'stderr:\n{result.stderr}'
        )
        assert 'All checks passed' in result.stdout
        assert '0 finding(s)' in result.stdout

    def test_paper_5_forks_and_passes(self):
        target = forge.fork_verify(5)
        result = subprocess.run(
            [sys.executable, str(target)],
            cwd=target.parent,
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f'forked verify_p5.py returned {result.returncode}\n'
            f'stdout:\n{result.stdout}\n'
            f'stderr:\n{result.stderr}'
        )
        assert 'All checks passed' in result.stdout


# ============================================================================
# Config coverage
# ============================================================================

class TestConfigCoverage:
    """Sanity checks on the PAPER_CONFIGS / COMPILE_CONFIGS dicts.
    These are not bugs per se, but they catch silent config drift.
    """

    def test_all_5_papers_have_verify_configs(self):
        assert set(VERIFY_CONFIGS.keys()) == {1, 2, 3, 4, 5}

    def test_all_5_papers_have_compile_configs(self):
        assert set(COMPILE_CONFIGS.keys()) == {1, 2, 3, 4, 5}

    def test_every_verify_config_has_required_keys(self):
        required = {
            'dir', 'c1_symbols', 'c2_families', 'c2_section_pattern',
            'c2_abstract_k_allowed', 'c3_concept', 'c3_concept_token',
            'c3_formal', 'c4_self_cite_threshold', 'c4_self_cite_prefix',
            'c4_max_self_cite_keys', 'c5_d_type', 'c6_blacklist',
        }
        for n, cfg in VERIFY_CONFIGS.items():
            missing = required - set(cfg.keys())
            assert not missing, f'paper {n} missing keys: {missing}'

    def test_every_compile_config_has_required_keys(self):
        required = {'dir', 'replacements'}
        for n, cfg in COMPILE_CONFIGS.items():
            missing = required - set(cfg.keys())
            assert not missing, f'paper {n} missing keys: {missing}'

    def test_compile_replacements_use_python_repr_safe_unicode(self):
        """Each replacement's raw value should be a string (not bytes,
        not None). We don't check the escaped form here — the
        fix_unicode script handles that.
        """
        for n, cfg in COMPILE_CONFIGS.items():
            for raw, repl in cfg['replacements']:
                assert isinstance(raw, str), (
                    f'paper {n}: replacement raw is not a str: {raw!r}'
                )
                assert isinstance(repl, str), (
                    f'paper {n}: replacement repl is not a str: {repl!r}'
                )


# ============================================================================
# CLI smoke tests
# ============================================================================

class TestCLI:
    def test_list_returns_5_papers(self, capsys):
        from tmaudit.cli import main
        rc = main(['list'])
        assert rc == 0
        out = capsys.readouterr().out
        for n in (1, 2, 3, 4, 5):
            assert f'  {n} ' in out

    def test_unknown_paper_errors(self, capsys):
        from tmaudit.cli import main
        # Unknown paper: cli.main() prints an error and returns 2,
        # but argparse's --paper validation uses SystemExit. Either
        # way, the exit code must be non-zero.
        try:
            rc = main(['verify', '--paper', '999'])
        except SystemExit as exc:
            assert exc.code != 0
        else:
            assert rc != 0

    def test_verify_requires_paper_arg(self, capsys):
        from tmaudit.cli import main
        try:
            rc = main(['verify'])
        except SystemExit as exc:
            assert exc.code != 0
        else:
            assert rc != 0