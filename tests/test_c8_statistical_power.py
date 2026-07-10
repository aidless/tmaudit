"""Regression / TDD tests for the C8 (statistical power) check.

Background:

C8 is the 8th audit category. It re-derives the paper's
claimed effect size (Cohen's d) and statistical power
from the reported numbers, and flags if the paper's
claims are not supported.

This test file is the **TDD red phase** — it specifies the
contract that `check_c8_statistical_power` must satisfy.
The implementation is not yet written; the tests will fail
with AttributeError until the function is implemented.

Heuristic constants (documented here so the
implementation and tests share the same source of
truth):
  - Cohen's d = (mean1 - mean2) / pooled_sd
  - pooled_sd = sqrt(((n1-1)*sd1^2 + (n2-1)*sd2^2) / (n1+n2-2))
  - Power = Phi(|d| * sqrt(n/2) - z_alpha/2)
  - d-mismatch threshold: |d_actual - d_claimed| > 0.10 -> HIGH
  - Power thresholds:
      < 0.50 -> underpowered (MED)
      0.50-0.80 -> adequately powered (no finding)
      0.80-0.99 -> well-powered (no finding)
      > 0.99 -> overpowered (MED, suspicious)

Acceptance criteria (from ROADMAP.md):
  1. C8 detects inconsistencies between claimed d and
     computed d from reported (mean, sd, n) triples.
  2. C8 detects underpowered studies (n too small for
     the claimed d).
  3. C8 detects missing p-values for "significantly
     different" claims.
  4. C8 is opt-in (disabled by default if no
     `c8_claimed_effects` config).

Function signature (planned):
  def check_c8_statistical_power(
      tex: str,
      c8_claimed_effects: list = None,
  ) -> list[tuple[str, str, int]]:
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tmaudit.templates import verify_TEMPLATE


# =====================================================================
# Test fixtures: sample tex with results tables
# =====================================================================

# A tex with a results table where d=0.50 is achievable.
# mean1=10, mean2=8, sd1=2, sd2=2, n1=50, n2=50.
# pooled_sd = sqrt((49*4 + 49*4) / 98) = sqrt(4) = 2.0
# d = (10-8)/2.0 = 1.0  (this is large, not 0.50)
# Note: actual d=1.0; we test that mismatch is caught.
TEX_TABLE_D_1_0 = r"""
\begin{document}
\section{Results}
\begin{tabular}{lcc}
Condition & Mean & SD \\
A & 10.0 & 2.0 \\
B & 8.0 & 2.0 \\
\end{tabular}
n=50 per group.
\end{document}
"""

# A tex with a results table where d=0.50 is achievable.
# mean1=10, mean2=9, sd1=2, sd2=2, n1=50, n2=50.
# pooled_sd = 2.0
# d = (10-9)/2.0 = 0.5  (matches the claimed d)
TEX_TABLE_D_0_5 = r"""
\begin{document}
\section{Results}
\begin{tabular}{lcc}
Condition & Mean & SD \\
A & 10.0 & 2.0 \\
B & 9.0 & 2.0 \\
\end{tabular}
n=50 per group.
\end{document}
"""

# A tex with a results table where d=0.30 is achievable.
# mean1=10, mean2=9.6, sd1=2, sd2=2, n1=200, n2=200.
# pooled_sd = 2.0
# d = 0.4/2.0 = 0.2 (close to 0.30 but not exact)
# With n=200, power for d=0.30 is ~0.86 (well-powered)
TEX_TABLE_D_0_2 = r"""
\begin{document}
\section{Results}
\begin{tabular}{lcc}
Condition & Mean & SD \\
A & 10.0 & 2.0 \\
B & 9.6 & 2.0 \\
\end{tabular}
n=200 per group.
\end{document}
"""

# A tex with a significance claim and a p-value.
TEX_WITH_P_VALUE = r"""
\begin{document}
We find that A is significantly different from B
(t = 2.5, p < 0.001, Cohen's d = 0.50, n = 50).
\end{document}
"""

# A tex with a significance claim but no p-value.
TEX_NO_P_VALUE = r"""
\begin{document}
We find that A is significantly different from B
(t = 2.5, Cohen's d = 0.50, n = 50).
\end{document}
"""

# A tex with a significance claim and an inconsistent p-value.
# d=0.05 is tiny, but p=0.001 claims a significant result.
TEX_INCONSISTENT_P = r"""
\begin{document}
We find that A is significantly different from B
(p < 0.001, Cohen's d = 0.05, n = 100).
\end{document}
"""

# A tex with "significant" but no comparison ("significantly"
# alone is not a "significantly different" claim).
TEX_SIGNIFICANT_NOT_DIFFERENT = r"""
\begin{document}
This is a significant contribution to the field.
\end{document}
"""


def _fresh_check(tex: str, c8_claims: list = None) -> list:
    """Convenience: call check_c8_statistical_power with default args."""
    return verify_TEMPLATE.check_c8_statistical_power(tex, c8_claims)


# =====================================================================
# Sub-check 1: Effect size re-derivation
# =====================================================================

# Test 1: Effect with all numbers matching -> 0 findings
def test_c8_effect_numbers_match_no_finding():
    """If the claimed d matches the computed d, no finding."""
    findings = _fresh_check(TEX_TABLE_D_0_5, [
        {'name': 'main_effect', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05},
    ])
    high_findings = [
        f for f in findings
        if f[0] == 'C8' and 'HIGH' in f[1] and 'd' in f[1].lower()
    ]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH d-mismatch findings, got: {high_findings}'
    )


# Test 2: Effect with d=0.50 claimed but d=1.0 actual -> HIGH finding
def test_c8_effect_d_claimed_0_5_actual_1_0_emits_high():
    """If the claimed d is much smaller than the computed d,
    emit a HIGH finding. The d-mismatch is large enough to
    suggest the paper is misrepresenting the effect size."""
    findings = _fresh_check(TEX_TABLE_D_1_0, [
        {'name': 'main_effect', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05},
    ])
    high_findings = [
        f for f in findings
        if f[0] == 'C8' and 'HIGH' in f[1] and 'd' in f[1].lower()
    ]
    assert len(high_findings) >= 1, (
        f'Expected >= 1 HIGH d-mismatch finding, got: {findings}'
    )


# Test 3: Effect with d=0.50 claimed but d=0.10 actual -> HIGH finding
def test_c8_effect_d_claimed_0_5_actual_0_1_emits_high():
    """If the claimed d is much larger than the computed d,
    also emit a HIGH finding. The paper is over-claiming
    the effect size."""
    # mean1=10, mean2=9.8, sd1=2, sd2=2, n1=50, n2=50.
    # pooled_sd = 2.0
    # d = 0.2/2.0 = 0.1
    tex = r"""
\begin{document}
\begin{tabular}{lcc}
A & 10.0 & 2.0 \\
B & 9.8 & 2.0 \\
\end{tabular}
n=50 per group.
\end{document}
"""
    findings = _fresh_check(tex, [
        {'name': 'main_effect', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05},
    ])
    high_findings = [
        f for f in findings
        if f[0] == 'C8' and 'HIGH' in f[1] and 'd' in f[1].lower()
    ]
    assert len(high_findings) >= 1, (
        f'Expected >= 1 HIGH finding (d=0.1 vs claimed d=0.5), '
        f'got: {findings}'
    )


# Test 4: Effect with no c8_claimed_effects -> 0 findings (no-op)
def test_c8_disabled_when_no_claims_config():
    """When c8_claimed_effects is None or empty, C8 is a no-op."""
    findings = _fresh_check(TEX_TABLE_D_1_0, None)
    assert findings == [], (
        f'Expected 0 findings when c8_claimed_effects is None, '
        f'got: {findings}'
    )


# Test 5: Effect with missing table -> graceful skip
def test_c8_missing_table_no_finding():
    """If the tex has no \\begin{tabular}, C8 cannot extract
    numbers, so it should skip the effect (no finding)."""
    findings = _fresh_check(
        'This paper makes a claim but provides no table.',
        [{'name': 'main_effect', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05}],
    )
    # We expect 0 findings (graceful skip), not a crash
    assert findings == [], f'Expected 0 findings, got: {findings}'


# =====================================================================
# Sub-check 2: Statistical power computation
# =====================================================================

# Test 6: n=20 (underpowered) -> MED finding
def test_c8_underpowered_emits_med():
    """n=20 with d=0.5 gives power ~0.56, which is borderline.
    n=20 with d=0.2 gives power ~0.12, which is clearly
    underpowered."""
    # For d=0.5, n=20 (n/2=10), power = Phi(0.5*sqrt(10) - 1.96)
    #                       = Phi(1.58 - 1.96) = Phi(-0.38) = 0.35
    # That's < 0.50 -> underpowered -> MED
    findings = _fresh_check(TEX_TABLE_D_0_5, [
        {'name': 'main_effect', 'd': 0.50, 'n1': 10, 'n2': 10, 'alpha': 0.05},
    ])
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1] and 'power' in f[1].lower()
    ]
    assert len(med_findings) >= 1, (
        f'Expected >= 1 MED power finding, got: {findings}'
    )


# Test 7: n=200 (well-powered) -> 0 findings
def test_c8_well_powered_no_finding():
    """n=200 with d=0.5 gives power > 0.99, well-powered.
    But > 0.99 is suspiciously overpowered (MED finding).
    Let's use n=50 (d=0.5 -> power ~0.70), which is
    adequately powered (no finding)."""
    findings = _fresh_check(TEX_TABLE_D_0_5, [
        {'name': 'main_effect', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05},
    ])
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1] and 'power' in f[1].lower()
    ]
    assert len(med_findings) == 0, (
        f'Expected 0 MED power findings, got: {med_findings}'
    )


# Test 8: n=10000 (overpowered, suspicious) -> MED finding
def test_c8_overpowered_suspicious_emits_med():
    """n=10000 with d=0.5 gives power > 0.9999, which is
    suspiciously overpowered. Reviewers flag this as a
    sign of p-hacking or over-fitting."""
    findings = _fresh_check(TEX_TABLE_D_0_5, [
        {'name': 'main_effect', 'd': 0.50, 'n1': 5000, 'n2': 5000, 'alpha': 0.05},
    ])
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1] and ('power' in f[1].lower() or 'over' in f[1].lower())
    ]
    assert len(med_findings) >= 1, (
        f'Expected >= 1 MED overpowered finding, got: {findings}'
    )


# Test 9: d=0.05 with n=100 (underpowered tiny effect) -> MED finding
def test_c8_tiny_effect_underpowered_emits_med():
    """d=0.05 is a tiny effect, and n=100 gives power ~0.07.
    This is a classic underpowered study that would be
    flagged by C8."""
    # mean1=10, mean2=9.9, sd1=2, sd2=2, n1=50, n2=50.
    # d = 0.1/2.0 = 0.05
    tex = r"""
\begin{document}
\begin{tabular}{lcc}
A & 10.0 & 2.0 \\
B & 9.9 & 2.0 \\
\end{tabular}
n=50 per group.
\end{document}
"""
    findings = _fresh_check(tex, [
        {'name': 'tiny_effect', 'd': 0.05, 'n1': 50, 'n2': 50, 'alpha': 0.05},
    ])
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1]
    ]
    # Could be either power (underpowered) or d-mismatch
    # (d=0.05 claimed but d=0.05 actual, no mismatch).
    # The MED should be the power finding.
    assert len(med_findings) >= 1, (
        f'Expected >= 1 MED finding, got: {findings}'
    )


# =====================================================================
# Sub-check 3: Effect-size significance claim
# =====================================================================

# Test 10: "Significantly different" with p<0.001 -> 0 findings
def test_c8_significance_with_p_value_no_finding():
    """A claim with a consistent p-value (p<0.001 for d=0.5)
    is fine. No MED finding for missing p-value."""
    findings = _fresh_check(TEX_WITH_P_VALUE)
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1] and 'p' in f[1].lower()
    ]
    assert len(med_findings) == 0, (
        f'Expected 0 MED p-value findings, got: {med_findings}'
    )


# Test 11: "Significantly different" without p -> MED finding
def test_c8_significance_no_p_value_emits_med():
    """A 'significantly different' claim without a p-value
    is suspicious. Reviewers always want to see the
    p-value."""
    findings = _fresh_check(TEX_NO_P_VALUE)
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1] and 'p' in f[1].lower()
    ]
    assert len(med_findings) >= 1, (
        f'Expected >= 1 MED missing-p finding, got: {findings}'
    )


# Test 12: "Significantly different" with inconsistent p (tiny d, very small p) -> MED finding
def test_c8_significance_inconsistent_p_emits_med():
    """A 'significantly different' claim with d=0.05 and
    p<0.001 is internally inconsistent. Tiny d should
    produce large p, not small p. This suggests p-hacking
    or miscalculation."""
    findings = _fresh_check(TEX_INCONSISTENT_P)
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1] and 'p' in f[1].lower()
    ]
    assert len(med_findings) >= 1, (
        f'Expected >= 1 MED inconsistent-p finding, got: {findings}'
    )


# Test 13: "Significant" without "different" -> 0 findings
def test_c8_significant_word_alone_no_finding():
    """The word 'significant' alone is not a claim of
    statistical significance. C8 should only check
    'significantly different' claims."""
    findings = _fresh_check(TEX_SIGNIFICANT_NOT_DIFFERENT)
    assert findings == [], (
        f'Expected 0 findings for "significant" alone, got: {findings}'
    )


# =====================================================================
# Edge cases
# =====================================================================

# Test 14: Empty paper -> 0 findings
def test_c8_empty_tex_no_finding():
    """An empty tex should produce 0 findings (no claims to verify)."""
    findings = _fresh_check('')
    assert findings == [], f'Expected 0 findings, got: {findings}'


# Test 15: Malformed LaTeX -> no crash
def test_c8_malformed_latex_no_crash():
    """Malformed LaTeX (unclosed braces, unclosed tables)
    should not crash the audit."""
    malformed = r"""
    \begin{document
    We find A is significantly different from B
    (unclosed brace: \begin{tabular}{lcc
    """
    # Should not raise
    findings = _fresh_check(malformed)
    assert isinstance(findings, list)


# Test 16: Multiple effects, mixed pass/fail
def test_c8_multiple_effects_mixed_findings():
    """3 effects: 1 matches, 1 mismatched, 1 underpowered.
    Should produce 2 findings (mismatch + power)."""
    findings = _fresh_check(TEX_TABLE_D_1_0, [
        # Effect 1: matches (d=1.0 vs d=1.0) -> no finding
        {'name': 'matches', 'd': 1.00, 'n1': 50, 'n2': 50, 'alpha': 0.05},
        # Effect 2: d-mismatch (claimed d=0.5, actual d=1.0) -> HIGH
        {'name': 'mismatch', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05},
        # Effect 3: underpowered (n=10, d=0.5 -> power=0.35) -> MED
        {'name': 'underpowered', 'd': 0.50, 'n1': 5, 'n2': 5, 'alpha': 0.05},
    ])
    # Expect 2 findings
    high_findings = [
        f for f in findings
        if f[0] == 'C8' and 'HIGH' in f[1]
    ]
    med_findings = [
        f for f in findings
        if f[0] == 'C8' and 'MED' in f[1]
    ]
    assert len(high_findings) == 1, (
        f'Expected 1 HIGH finding (mismatch), got: {high_findings}'
    )
    assert len(med_findings) == 1, (
        f'Expected 1 MED finding (underpowered), got: {med_findings}'
    )


# Test 17: c8_claimed_effects is a list of dicts with extra fields
def test_c8_extra_fields_in_config_ignored():
    """Extra fields in c8_claimed_effects entries should be
    ignored. Only 'name', 'd', 'n1', 'n2', 'alpha' are used."""
    findings = _fresh_check(TEX_TABLE_D_0_5, [
        {
            'name': 'main_effect', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05,
            'extra_field': 'should be ignored',
            'note': 'this too',
        },
    ])
    # Should still pass (d=0.5 matches)
    high_findings = [
        f for f in findings
        if f[0] == 'C8' and 'HIGH' in f[1] and 'd' in f[1].lower()
    ]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings (extra fields ignored), '
        f'got: {high_findings}'
    )


# Test 18: per-paper config c8_min_d_mismatch (default 0.10)
def test_c8_d_mismatch_tolerance_0_10():
    """d-claimed=0.5, d-actual=0.45 -> diff=0.05 < 0.10 tolerance.
    No HIGH finding (within tolerance)."""
    # mean1=10, mean2=9.1, sd1=2, sd2=2, n1=50, n2=50.
    # d = 0.9/2.0 = 0.45
    tex = r"""
\begin{document}
\begin{tabular}{lcc}
A & 10.0 & 2.0 \\
B & 9.1 & 2.0 \\
\end{tabular}
n=50 per group.
\end{document}
"""
    findings = _fresh_check(tex, [
        {'name': 'main_effect', 'd': 0.50, 'n1': 50, 'n2': 50, 'alpha': 0.05},
    ])
    high_findings = [
        f for f in findings
        if f[0] == 'C8' and 'HIGH' in f[1] and 'd' in f[1].lower()
    ]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings (within 0.10 tolerance), '
        f'got: {high_findings}'
    )


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
