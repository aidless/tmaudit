"""Regression / TDD test for C7 (citation context validation).

This is the *test* half of the v0.1.2 milestone. The
*implementation* half (check_c7_citation_context in
verify_TEMPLATE.py) is not yet written. This file defines
the contract the implementation must satisfy.

Background (Issue #16, ROADMAP v0.1.2):

A citation is "ceremonial" if it appears in the text but
the citing sentence does not actually engage with the cited
work (no verb of engagement, no comparison, no elaboration).
A citation is "engaged" if the citing sentence contains:

  - an "engage" verb (show, demonstrate, extend, build on,
    follow, use, apply, compare, improve, outperform,
    validate, verify, propose, argue, claim, find, observe,
    measure, report, ...);
  - a comparison word (however, in contrast, unlike, while,
    although, whereas);
  - or is long enough to be considered engagement (>= 30
    words in the citing sentence).

The function `check_c7_citation_context(tex) -> list[
  tuple[str, str, int]
]` (in `src/tmaudit.templates.verify_TEMPLATE`) returns
one finding per ceremonial citation that exceeds the
per-paper `c7_max_ceremonial` threshold (default 2).

Acceptance criteria for this test file:
  1. All tests pass once `check_c7_citation_context` is
     implemented.
  2. The implementation must be **purely additive** (no
     change to existing C1..C6 behaviour).
  3. The implementation must be **threshold-aware** (the
     c7_max_ceremonial config controls when to flag).
  4. The implementation must be **lenient** (default
     threshold of 2 means 1-2 ceremonial cites are OK, only
     3+ get flagged).

Heuristic constants (documented here so the implementation
and tests share the same source of truth):
  - ENGAGE_VERBS = [
      'show', 'demonstrate', 'extend', 'build on', 'follow',
      'use', 'apply', 'compare', 'improve', 'outperform',
      'validate', 'verify', 'propose', 'argue', 'claim',
      'find', 'observe', 'measure', 'report', 'confirm',
      'extend', 'exploit', 'leverage', 'utilize', 'adopt',
      'generalize', 'specialize', 'reduce', 'combine',
    ]
  - COMPARISON_WORDS = [
      'however', 'in contrast', 'unlike', 'while',
      'although', 'whereas', 'but', 'conversely',
  ]
  - MIN_CITED_SENTENCE_WORDS = 30
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tmaudit.templates import verify_TEMPLATE


# =====================================================================
# Test 1: engaged cite (verb present) -> 0 findings
# =====================================================================
def test_c7_engaged_cite_with_extend_verb_no_finding():
    """A cite in a sentence with 'extend' is engaged.

    Example:
        We extend the framework of Smith et al. \cite{smith2020} by
        introducing a new loss function.

    Expected: 0 findings (the citing sentence engages with the
    cited work via the verb 'extend').
    """
    tex = (
        "We extend the framework of Smith et al. \\cite{smith2020} "
        "by introducing a new loss function that reduces the bias "
        "from 30% to 5%.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex)
    assert findings == [], (
        f"Expected no findings for engaged cite, got: {findings}"
    )


# =====================================================================
# Test 2: ceremonial cite (basic) -> 1 finding (with threshold=0)
# =====================================================================
def test_c7_ceremonial_cite_basic_finding():
    """A cite in a short sentence with no engaged signal is ceremonial.

    Example:
        Recent work has studied this problem \cite{smith2020}.

    With c7_max_ceremonial=0, even 1 ceremonial cite is flagged
    (useful for strict mode or for users who want to fix every
    ceremonial cite). The default threshold is 2, so under the
    default 1 ceremonial cite is OK (see test_c7_default_threshold).
    """
    tex = "Recent work has studied this problem \\cite{smith2020}.\n"
    findings = verify_TEMPLATE.check_c7_citation_context(
        tex, c7_max_ceremonial=0
    )
    assert len(findings) == 1, (
        f"Expected 1 finding for ceremonial cite (threshold=0), got: {findings}"
    )
    assert findings[0][0] == 'C7'
    assert 'smith2020' in findings[0][1], (
        f"Expected cite key in finding message, got: {findings[0][1]!r}"
    )
    assert findings[0][2] == 1, (
        f"Expected line 1, got: {findings[0][2]}"
    )


# =====================================================================
# Test 3: cite with comparison word -> 0 findings
# =====================================================================
def test_c7_cite_with_comparison_word_engaged():
    """A cite in a sentence with 'however' is engaged.

    Example:
        However, the method of Smith \cite{smith2020} requires
        careful tuning of the regularisation parameter.
    """
    tex = (
        "However, the method of Smith \\cite{smith2020} requires "
        "careful tuning of the regularisation parameter to "
        "achieve competitive performance on standard benchmarks.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex)
    assert findings == [], (
        f"Expected no findings for 'however' cite, got: {findings}"
    )


# =====================================================================
# Test 4: cite with long sentence (no verb) -> 0 findings
# =====================================================================
def test_c7_cite_with_long_sentence_no_verb_engaged():
    """A cite in a sentence >= 30 words (no verb) is engaged by length.

    Example:
        A recent line of research (e.g., \cite{smith2020}, focusing
        on the problem of distribution shift in deep neural networks
        under realistic non-stationary conditions) has explored
        various mitigation strategies.

    This sentence is 30+ words, which we consider evidence of
    engagement (the author is elaborating on the cited work).
    """
    tex = (
        "A recent line of research (e.g., \\cite{smith2020}, focusing "
        "on the problem of distribution shift in deep neural "
        "networks under realistic non-stationary conditions) has "
        "explored various mitigation strategies in the literature.\n"
    )
    # The citing sentence is roughly 40+ words.
    n_words = len(tex.split())
    assert n_words >= 30, (
        f"Test setup error: need >= 30 words, got {n_words}"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex)
    assert findings == [], (
        f"Expected no findings for long-sentence cite, got: {findings}"
    )


# =====================================================================
# Test 5: cite with short sentence (no signal) -> 1 finding (threshold=0)
# =====================================================================
def test_c7_cite_with_short_sentence_no_signal_ceremonial():
    """A cite in a short sentence with no engaged signal is ceremonial.

    Example:
        Prior work \cite{smith2020} exists.

    With c7_max_ceremonial=0, even 1 ceremonial cite is flagged.
    """
    tex = "Prior work \\cite{smith2020} exists.\n"
    findings = verify_TEMPLATE.check_c7_citation_context(
        tex, c7_max_ceremonial=0
    )
    assert len(findings) == 1
    assert findings[0][0] == 'C7'


# =====================================================================
# Test 6: per-paper threshold respected (2 OK, 3+ flagged)
# =====================================================================
def test_c7_threshold_2_allows_2_ceremonial_cites():
    """With c7_max_ceremonial=2, exactly 2 ceremonial cites are OK."""
    tex = (
        "Work A \\cite{a2020} exists.\n"
        "Work B \\cite{b2020} exists.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex, c7_max_ceremonial=2)
    # With threshold=2, having 2 ceremonial cites should produce 0
    # findings (2 is at the threshold, not above).
    assert findings == [], (
        f"Expected no findings at threshold, got: {findings}"
    )


def test_c7_threshold_2_flags_3_ceremonial_cites():
    """With c7_max_ceremonial=2, 3 ceremonial cites produce 1 finding."""
    tex = (
        "Work A \\cite{a2020} exists.\n"
        "Work B \\cite{b2020} exists.\n"
        "Work C \\cite{c2020} exists.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex, c7_max_ceremonial=2)
    # 3 ceremonial cites - threshold is 2 - so 1 finding
    assert len(findings) == 1, (
        f"Expected 1 finding for 3 ceremonial cites, got: {findings}"
    )
    # The finding should mention the count and list the keys
    msg = findings[0][1]
    assert '3' in msg or 'ceremonial' in msg.lower(), (
        f"Expected message to mention 3 ceremonial cites, got: {msg!r}"
    )


# =====================================================================
# Test 7: multiple cites mixed (engaged + ceremonial) -> only ceremonial reported
# =====================================================================
def test_c7_mixed_cites_classified_independently():
    """Engaged cites and ceremonial cites are classified separately.

    Example:
        We extend Smith \cite{smith2020} by ... (engaged)
        Prior work \cite{jones2020} exists. (ceremonial)
    """
    tex = (
        "We extend the framework of Smith et al. \\cite{smith2020} "
        "by introducing a new loss function that reduces bias.\n"
        "Prior work \\cite{jones2020} exists.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex, c7_max_ceremonial=0)
    # 1 ceremonial cite (jones2020), 0 engaged
    # With threshold=0, even 1 ceremonial is flagged
    assert len(findings) == 1, (
        f"Expected 1 finding, got: {findings}"
    )
    assert 'jones2020' in findings[0][1]


# =====================================================================
# Test 8: \citep, \citet, \cite all detected
# =====================================================================
def test_c7_detects_cite_variants():
    """All cite variants (\cite, \citep, \citet) are detected.

    Example:
        \citep is parenthetical: (Smith, 2020)
        \citet is textual: Smith (2020)
        \cite is generic
    """
    tex = (
        "Prior work \\cite{a2020} exists.\n"
        "Prior work \\citep{b2020} exists.\n"
        "Prior work \\citet{c2020} exists.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex, c7_max_ceremonial=0)
    # All 3 are ceremonial -> all 3 should be flagged
    n_cited = sum(1 for f in findings if f[0] == 'C7')
    assert n_cited == 3, (
        f"Expected 3 C7 findings, got: {findings}"
    )


# =====================================================================
# Test 9: cite with multiple keys (\cite{a,b,c})
# =====================================================================
def test_c7_cite_with_multiple_keys():
    """A \\cite{a,b,c} counts each key independently."""
    tex = "Prior work \\cite{a2020,b2020,c2020} exists.\n"
    findings = verify_TEMPLATE.check_c7_citation_context(tex, c7_max_ceremonial=0)
    # All 3 keys are ceremonial -> 3 findings
    n_cited = sum(1 for f in findings if f[0] == 'C7')
    assert n_cited == 3, (
        f"Expected 3 findings for 3 keys, got: {findings}"
    )


# =====================================================================
# Test 10: empty / no cites -> 0 findings
# =====================================================================
def test_c7_no_cites_no_findings():
    """A tex with no \\cite commands produces 0 findings."""
    tex = (
        "This is a paper without any citations.\n"
        "It discusses methodology, results, and conclusion.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex)
    assert findings == [], (
        f"Expected no findings for no-cite paper, got: {findings}"
    )


# =====================================================================
# Test 11: cite inside long sentence IS engaged even with no verb
# =====================================================================
def test_c7_engaged_via_length_alone():
    """A 30+ word sentence with a cite is engaged even without verbs.

    This is the 'engagement by elaboration' heuristic: a long
    citing sentence indicates the author is engaging with the
    cited work.
    """
    # Construct a sentence with 30+ words, no engage verb,
    # no comparison word, but a cite inside.
    long_sentence = (
        "There is a substantial body of literature on the topic "
        "of robust optimisation under uncertainty, and recent "
        "contributions to this area have included the work of "
        "many researchers including \\cite{smith2020} who have "
        "explored different facets of the problem in detail.\n"
    )
    # Verify the test setup is correct: 30+ words, no engage verb
    assert len(long_sentence.split()) >= 30
    findings = verify_TEMPLATE.check_c7_citation_context(long_sentence, c7_max_ceremonial=0)
    assert findings == [], (
        f"Expected no findings for 30+ word sentence, got: {findings}"
    )


# =====================================================================
# Test 12: cite inside math/LaTeX command not detected as cite
# =====================================================================
def test_c7_does_not_match_cite_inside_command():
    """A word 'cite' inside a LaTeX command (not \\cite) is not a cite.

    Example:
        \\multicolumn{2}{c}{...} - 'cite' is in the command name but
        not a citation.
    """
    tex = (
        "\\multicolumn{2}{c}{This cell has cite in the command name}.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex)
    assert findings == [], (
        f"Expected no findings for non-cite, got: {findings}"
    )


# =====================================================================
# Test 13: paper 5 actual case (regression-style)
# =====================================================================
def test_c7_paper5_style_engaged_cite():
    """Paper 5-style engaged cite: 'We adopt the framework of X'."""
    tex = (
        "We adopt the framework of Smith et al. \\cite{smith2020} and "
        "extend it to handle non-stationary distributions in the "
        "online learning setting.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex)
    assert findings == [], (
        f"Expected no findings for 'adopt' cite, got: {findings}"
    )


# =====================================================================
# Test 14: default threshold is 2 (NOT 0, NOT 1)
# =====================================================================
def test_c7_default_threshold_is_2():
    """Without explicit threshold, the default c7_max_ceremonial is 2.

    This means: 1-2 ceremonial cites are OK (no finding),
    3+ ceremonial cites produce 1 finding.
    """
    tex_2 = (
        "Work A \\cite{a2020} exists.\n"
        "Work B \\cite{b2020} exists.\n"
    )
    # Default threshold (2) - 2 ceremonial cites are OK
    findings_2 = verify_TEMPLATE.check_c7_citation_context(tex_2)
    assert findings_2 == [], (
        f"Default threshold (2) should allow 2 ceremonial cites, "
        f"got: {findings_2}"
    )

    tex_3 = (
        "Work A \\cite{a2020} exists.\n"
        "Work B \\cite{b2020} exists.\n"
        "Work C \\cite{c2020} exists.\n"
    )
    # 3 ceremonial cites - default threshold - should produce 1 finding
    findings_3 = verify_TEMPLATE.check_c7_citation_context(tex_3)
    assert len(findings_3) == 1, (
        f"Default threshold (2) should flag 3+ ceremonial cites, "
        f"got: {findings_3}"
    )


# =====================================================================
# Test 15: ceremonial count is on UNIQUE keys, not occurrences
# =====================================================================
def test_c7_ceremonial_count_is_unique_keys():
    """A key cited 3 times in ceremonial sentences counts as 1 ceremonial.

    Example:
        Smith \cite{s2020} exists.     (ceremonial #1)
        Smith \cite{s2020} exists.     (still 1 unique key)
        Smith \cite{s2020} exists.     (still 1 unique key)
    """
    tex = (
        "Smith \\cite{s2020} exists.\n"
        "Smith \\cite{s2020} exists.\n"
        "Smith \\cite{s2020} exists.\n"
    )
    findings = verify_TEMPLATE.check_c7_citation_context(tex, c7_max_ceremonial=0)
    # 1 unique key, ceremonial -> 1 finding
    assert len(findings) == 1, (
        f"Expected 1 finding for 1 unique ceremonial key, got: {findings}"
    )


# =====================================================================
# Test 16: severity reflects engagement level
# =====================================================================
def test_c7_severity_is_medium():
    """All C7 findings should be MEDIUM severity (not HIGH, not LOW).

    Rationale: ceremonial citations are a stylistic concern, not
    a correctness issue. Reviewer can request the author to fix,
    but it's not a blocker.
    """
    tex = "Prior work \\cite{a2020} exists.\n"
    findings = verify_TEMPLATE.check_c7_citation_context(tex, c7_max_ceremonial=0)
    assert len(findings) == 1
    # C7 findings are MEDIUM by convention
    # (the message should mention MED or 'medium')
    assert 'MED' in findings[0][1] or 'medium' in findings[0][1].lower(), (
        f"Expected MED severity in message, got: {findings[0][1]!r}"
    )


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))