"""Regression test for the C6 min_count threshold.

Bug 7 (discovered 2026-07-10): C6_blacklist was reporting
"yields" as a finding on Paper 5 even though "yields" appears
only 2 times and is idiomatic technical English ("yields a
strictly lower Gamma", "yields a spread within pi"). The fix
adds a `min_count` threshold so that 1-2 occurrences are not
flagged. 3+ occurrences still trigger (to catch over-use of
vague words like "paradigm" / "reveal").

This test is the meta-test target for Bug 7.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tmaudit.templates import verify_TEMPLATE


def test_c6_does_not_flag_single_occurrence():
    """A blacklist word appearing once should NOT be reported."""
    tex = (
        "This is a paper that uses the word paradigm once.\n"
    )
    findings = verify_TEMPLATE.check_c6_blacklist(tex)
    assert findings == [], (
        f"Expected no findings for single occurrence, got: {findings}"
    )


def test_c6_does_not_flag_two_occurrences():
    """A blacklist word appearing twice should NOT be reported.

    1-2 occurrences are common in idiomatic technical English
    ('yields a value of X').
    """
    tex = (
        "This paper yields a result. The model yields a better fit.\n"
    )
    findings = verify_TEMPLATE.check_c6_blacklist(tex)
    assert findings == [], (
        f"Expected no findings for 2 occurrences, got: {findings}"
    )


def test_c6_flags_three_or_more_occurrences():
    """A blacklist word appearing 3+ times SHOULD be reported."""
    tex = "yield " * 10
    findings = verify_TEMPLATE.check_c6_blacklist(tex)
    # Should report 1 finding for "yield"
    yield_findings = [f for f in findings if 'yield' in f[1]]
    assert len(yield_findings) == 1, (
        f"Expected 1 finding for 'yield' (10 occurrences), got: {yield_findings}"
    )
    # The finding message should mention the count
    assert '10x' in yield_findings[0][1], (
        f"Expected '10x' in finding message, got: {yield_findings[0][1]!r}"
    )


def test_c6_finds_inflection_yields():
    """The 'yields' inflection should also be counted (not just 'yield')."""
    tex = "yields " * 5
    findings = verify_TEMPLATE.check_c6_blacklist(tex)
    yield_findings = [f for f in findings if 'yield' in f[1]]
    assert len(yield_findings) == 1
    assert '5x' in yield_findings[0][1]


def test_c6_finds_inflection_revealed():
    """The 'revealed' inflection should be counted."""
    tex = "revealed " * 5
    findings = verify_TEMPLATE.check_c6_blacklist(tex)
    reveal_findings = [f for f in findings if 'reveal' in f[1]]
    assert len(reveal_findings) == 1


def test_c6_counts_separately_per_word():
    """Each blacklist word is counted independently.

    'paradigm' 1x and 'yield' 3x should produce 1 finding (yield only).
    """
    tex = "paradigm " + "yield " * 3
    findings = verify_TEMPLATE.check_c6_blacklist(tex)
    # Only 'yield' should be flagged (paradigm 1x is below threshold)
    yield_findings = [f for f in findings if 'yield' in f[1]]
    paradigm_findings = [f for f in findings if 'paradigm' in f[1]]
    assert len(yield_findings) == 1
    assert len(paradigm_findings) == 0


def test_c6_word_boundary_does_not_match_yielded():
    """The 'yield' blacklist should NOT match 'yielded' (a different word)."""
    tex = "yielded " * 5  # 'yielded' is a different word from 'yield'
    findings = verify_TEMPLATE.check_c6_blacklist(tex)
    # 'yielded' should NOT be matched (no inflection rule for it)
    yield_findings = [f for f in findings if 'yield' in f[1]]
    # 'yield' (without -ed) is not in 'yielded' so this should be 0
    # But the regex `\byields?\b` does match the prefix 'yield' of
    # 'yielded'? No -- \b is a word boundary, 'yield' is followed by
    # 'ed' which is a word char, so the match fails.
    assert len(yield_findings) == 0, (
        f"Expected no findings for 'yielded', got: {yield_findings}"
    )


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))