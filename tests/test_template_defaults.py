"""Tests for the v0.5.1 template fixes (defects D1-D6).

These defects were found by auditing the template itself against 25
real arXiv LaTeX sources (case-studies/arxiv-corpus/ in the repo):

  D1  The factory CHECKS_CONFIG was pre-filled with one specific
      paper's configuration, so a generic audit fired paper-specific
      checks (TTRL symbol definitions, a "Power analysis" section
      requirement, a 'liu2026' self-cite prefix) against any document
      it was pointed at. The factory default is now empty, and the
      paper-specific categories report "not applicable".

  D2  "Clean" was indistinguishable from "did not run": a category
      whose configuration was missing returned zero findings, which
      the summary printed as [OK]. The summary now distinguishes
      checked / not applicable / error.

  D3  main() called the ten checks unguarded and indexed
      CHECKS_CONFIG directly, so one missing config key aborted the
      whole audit with a KeyError. A crash now degrades that one
      category to an error (exit code 2) and the rest still run.

  D4  The BibTeX key regex `@\\w+\\{([^,]+),` swallowed whitespace
      and newlines, so a key on its own line was captured with its
      surrounding whitespace and a cite key that existed in refs.bib
      was reported as missing.

  D5  A non-raw docstring contained \\caption / \\includegraphics,
      producing a SyntaxWarning on every import.

  D6  C1 reported "No abstract environment found." as a HIGH finding;
      an observation failure is now an error, not a violation.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tmaudit.templates import verify_TEMPLATE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A minimal document that is clean under every generic check: an
# availability statement (C10 sub-check 1) with all four metadata
# categories (C10 sub-check 3), no p/d values, no figures, no cites.
CLEAN_TEX = (
    '\\documentclass{article}\n'
    '\\begin{document}\n'
    '\\begin{abstract}\n'
    'We study the method and find it is available and reproducible.\n'
    '\\end{abstract}\n'
    '\\section{Code availability}\n'
    'Code is available at https://github.com/example/repo. '
    'Hyperparameters (learning rate, batch size, optimizer), the random '
    'seed, the hardware (GPU), and the library version (PyTorch 2) are '
    'listed in the appendix.\n'
    '\\end{document}\n'
)
CLEAN_BIB = ''


def _run_main(tmp_path, monkeypatch, capsys, tex=CLEAN_TEX, bib=CLEAN_BIB):
    """Point MAIN/REFS at tmp files and run main(); return (rc, stdout)."""
    tex_file = tmp_path / 'main.tex'
    bib_file = tmp_path / 'refs.bib'
    tex_file.write_text(tex, encoding='utf-8')
    bib_file.write_text(bib, encoding='utf-8')
    monkeypatch.setattr(verify_TEMPLATE, 'MAIN', tex_file)
    monkeypatch.setattr(verify_TEMPLATE, 'REFS', bib_file)
    rc = verify_TEMPLATE.main()
    return rc, capsys.readouterr().out


def _category_lines(out: str, cat: str) -> list[str]:
    return [l for l in out.splitlines() if l.startswith(f'  {cat} ')]


# ---------------------------------------------------------------------------
# D1: the factory configuration is empty
# ---------------------------------------------------------------------------

def test_factory_config_is_empty():
    """The shipped CHECKS_CONFIG must be an empty dict.

    A pre-filled factory config made the generic audit fire one paper's
    checks against any document (v0.5.0 shipped with Paper 1's config
    baked in: a 'liu2026' self-cite prefix, TTRL symbol definitions,
    a "Power analysis" section requirement).
    """
    assert verify_TEMPLATE.CHECKS_CONFIG == {}


def test_main_empty_config_reports_not_applicable(tmp_path, monkeypatch, capsys):
    """With the factory config, the paper-specific categories must be
    reported as not applicable — not silently [OK] (D2) — and the
    generic categories must still run (D1)."""
    rc, out = _run_main(tmp_path, monkeypatch, capsys)
    assert rc == 0, out
    for cat in ('C1', 'C2', 'C3', 'C6'):
        lines = _category_lines(out, cat)
        assert len(lines) == 1, out
        assert '[OK]' in lines[0], out
        assert 'not applicable' in lines[0], (
            f'{cat} should be reported as not applicable, got:\n{lines[0]}'
        )
    # The generic checks still ran and are clean on this document:
    for cat in ('C4', 'C5', 'C7', 'C8', 'C9', 'C10'):
        lines = _category_lines(out, cat)
        assert len(lines) == 1 and '[OK]' in lines[0], out
        assert 'not applicable' not in lines[0], (
            f'{cat} is a generic check and should have run:\n{out}'
        )


def test_main_with_full_config_runs_everything(tmp_path, monkeypatch, capsys):
    """A fully configured run marks every category as checked (no
    'not applicable' note anywhere). The configuration here is chosen
    to be satisfiable by CLEAN_TEX, so the run is also finding-free."""
    monkeypatch.setattr(verify_TEMPLATE, 'CHECKS_CONFIG', {
        'c1_symbols': [{'name': 'X', 'token': r'\bmethod\b',
                        'definition': r'available'}],
        'c2_families': {'main': 3},
        'c2_section_pattern': r'\\section\*?\{[^}]*availability[^}]*\}',
        'c3_concept': 'X',
        'c3_concept_token': r'\bZebra\b',
        'c3_formal': r'Zebras.{0,80}',
        'c4_self_cite_prefix': 'selfcite',
        'c6_blacklist': ['paradigm'],
    })
    rc, out = _run_main(tmp_path, monkeypatch, capsys)
    assert rc == 0, out
    assert 'not applicable' not in out, out


# ---------------------------------------------------------------------------
# D3: a crashing check degrades to a category error, not a whole-audit abort
# ---------------------------------------------------------------------------

def test_main_crashing_check_becomes_category_error(tmp_path, monkeypatch, capsys):
    """One check raising must not abort the audit: the category is
    reported as [ERROR] and the remaining categories still run. Exit
    code 2 (a crashed check is not a passed check)."""
    monkeypatch.setattr(verify_TEMPLATE, 'CHECKS_CONFIG', {
        # Config present so C1 runs (and crashes) rather than skipping.
        'c1_symbols': [{'name': 'X', 'token': 'X', 'definition': 'X'}],
    })

    def boom(_tex):
        raise KeyError('c2_families')

    monkeypatch.setattr(verify_TEMPLATE, 'check_c1_abstract_definitions', boom)
    rc, out = _run_main(tmp_path, monkeypatch, capsys)
    assert rc == 2, out
    assert 'C1  [ERROR]' in out, out
    assert 'KeyError' in out, out
    # The other categories still reported:
    assert 'C4  [OK]' in out, out
    assert 'Findings by category:' in out, out


def test_main_no_abstract_with_c1_configured_is_error_not_finding(
        tmp_path, monkeypatch, capsys):
    """D6: C1 on a document without an abstract used to report a HIGH
    finding ('No abstract environment found.'). An observation failure
    is an error, not a violation."""
    monkeypatch.setattr(verify_TEMPLATE, 'CHECKS_CONFIG', {
        'c1_symbols': [{'name': 'X', 'token': r'\bX\b',
                        'definition': r'X.{0,80}='}],
    })
    # A document with no abstract environment at all.
    tex = (
        '\\documentclass{article}\n'
        '\\begin{document}\n'
        '\\section{Code availability}\n'
        'Code is available at https://github.com/example/repo.\n'
        '\\end{document}\n'
    )
    rc, out = _run_main(tmp_path, monkeypatch, capsys, tex=tex)
    assert rc == 2, out
    assert 'C1  [ERROR]' in out, out
    assert '[HIGH] C1' not in out, out


def test_c1_without_abstract_raises(monkeypatch):
    """The C1 check itself raises (instead of returning a finding) when
    the abstract cannot be located and the category is configured."""
    monkeypatch.setattr(verify_TEMPLATE, 'CHECKS_CONFIG', {
        'c1_symbols': [{'name': 'X', 'token': r'\bX\b',
                        'definition': r'X.{0,80}='}],
    })
    with pytest.raises(ValueError, match='no abstract'):
        verify_TEMPLATE.check_c1_abstract_definitions('no abstract here')


# ---------------------------------------------------------------------------
# D4: BibTeX keys on their own line are found
# ---------------------------------------------------------------------------

BIB_MULTILINE_KEY = (
    '@article{\n'
    '  keyA,\n'
    '  author = {Someone},\n'
    '  title = {Something},\n'
    '  year = {2024},\n'
    '}\n'
)


def test_bib_key_on_its_own_line_is_found():
    """D4 regression: `@article{\\n  keyA,` — the key exists in
    refs.bib, so citing it must NOT be reported as missing."""
    tex = 'See \\cite{keyA} for details.'
    findings = verify_TEMPLATE.check_c4_citation_hygiene(tex, BIB_MULTILINE_KEY)
    missing = [f for f in findings if 'missing from the bibliography' in f[1]]
    assert missing == [], findings


def test_bib_key_with_surrounding_whitespace_is_found():
    tex = 'See \\cite{keyA} for details.'
    bib = '@article{  keyA ,\n  author = {A},\n}\n'
    findings = verify_TEMPLATE.check_c4_citation_hygiene(tex, bib)
    missing = [f for f in findings if 'missing from the bibliography' in f[1]]
    assert missing == [], findings


def test_bib_key_inline_still_found():
    tex = 'See \\cite{keyA} for details.'
    bib = '@article{keyA,\n  author = {A},\n}\n'
    findings = verify_TEMPLATE.check_c4_citation_hygiene(tex, bib)
    missing = [f for f in findings if 'missing from the bibliography' in f[1]]
    assert missing == [], findings


def test_truly_missing_key_still_reported():
    """The relaxed regex must not over-match: a key that is genuinely
    absent from refs.bib is still reported."""
    tex = 'See \\cite{ghost2024} for details.'
    findings = verify_TEMPLATE.check_c4_citation_hygiene(
        tex, BIB_MULTILINE_KEY)
    assert any('missing from the bibliography' in f[1] for f in findings), findings


def test_self_cite_subcheck_silent_without_prefix():
    """With no c4_self_cite_prefix (factory default), the self-cite
    sub-check stays silent instead of crashing on a missing key."""
    tex = 'See \\cite{keyA} for details.'
    findings = verify_TEMPLATE.check_c4_citation_hygiene(
        tex, BIB_MULTILINE_KEY)
    assert not [f for f in findings if 'Self-cite' in f[1]], findings


def test_main_bib_key_count_uses_relaxed_regex(tmp_path, monkeypatch, capsys):
    """The 'Refs: N entries' line counts keys on their own lines too."""
    rc, out = _run_main(tmp_path, monkeypatch, capsys,
                        bib=BIB_MULTILINE_KEY)
    assert 'Refs:   1 entries in refs.bib' in out, out


# ---------------------------------------------------------------------------
# D5: the module imports without SyntaxWarning
# ---------------------------------------------------------------------------

def test_template_compiles_without_syntax_warning():
    source = Path(verify_TEMPLATE.__file__).read_text(encoding='utf-8')
    with warnings.catch_warnings():
        warnings.simplefilter('error', SyntaxWarning)
        compile(source, 'verify_TEMPLATE.py', 'exec')


# ---------------------------------------------------------------------------
# Factory-config sanity: the generic checks fire on real problems
# ---------------------------------------------------------------------------

def test_factory_config_still_detects_missing_cite_key(tmp_path, monkeypatch,
                                                       capsys):
    """Neutral factory config must not mean blind config: a genuinely
    missing cite key still produces a C4 finding."""
    tex = 'See \\cite{notinbib} for details.'
    rc, out = _run_main(tmp_path, monkeypatch, capsys, tex=tex)
    assert '[MEDIUM] C4' in out, out


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
