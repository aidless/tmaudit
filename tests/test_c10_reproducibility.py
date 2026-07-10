"""Regression / TDD tests for the C10 (reproducibility) check.

Background:

C10 is the 10th audit category. It checks that the paper
includes a code/data availability statement, and that the
statement is consistent with the paper's claims.

This test file is the **TDD red phase** — it specifies the
contract that `check_c10_reproducibility` must satisfy.
The implementation is not yet written; the tests will fail
with AttributeError until the function is implemented.

Heuristic constants (documented here so the
implementation and tests share the same source of
truth):
  - C10 checks 3 sub-categories:
    1. Availability statement (HIGH severity if missing)
    2. Statement consistency with claims (MED severity)
    3. Reproducibility metadata (LOW severity for each missing)
  - Recognized availability patterns:
    \section{...Availability...}  (e.g., Code Availability,
                                     Data Availability)
    URLs to GitHub, GitLab, Hugging Face, Zenodo, etc.
    Phrases: "code is available at", "we release", "open
    source", "publicly available", etc.
  - Recognized metadata patterns:
    "learning rate", "batch size", "optimizer"  (hyperparameters)
    "seed", "random seed", "torch.manual_seed"  (random seed)
    "GPU", "RTX", "A100", "V100", "T4"  (hardware)
    "PyTorch X.Y", "TensorFlow X.Y", "transformers X.Y"
    (library versions)

Acceptance criteria (from ROADMAP.md):
  1. C10 detects missing availability statements.
  2. C10 detects inconsistencies between claims and the
     availability statement.
  3. C10 detects missing reproducibility metadata.
  4. C10 is opt-in (disabled by default if no
     `c10_reproducibility_claims` config).

Function signature (planned):
  def check_c10_reproducibility(
      tex: str,
      c10_reproducibility_claims: list = None,
  ) -> list[tuple[str, str, int]]:
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.tmaudit.templates import verify_TEMPLATE


# =====================================================================
# Test fixtures: sample tex strings
# =====================================================================

# A tex file with NO availability statement and NO metadata.
TEX_NO_AVAILABILITY = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.
Our model achieves 95\% accuracy.
\end{document}
"""

# A tex file with an Availability section.
TEX_WITH_AVAILABILITY_SECTION = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.

\section{Availability}
The code and data are available at https://github.com/author/repo.
\end{document}
"""

# A tex file with a Code Availability section.
TEX_WITH_CODE_AVAILABILITY = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.

\section{Code Availability}
Source code is released at https://github.com/author/repo.
\end{document}
"""

# A tex file with a Data Availability section.
TEX_WITH_DATA_AVAILABILITY = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.

\section{Data Availability}
The dataset is publicly available on Zenodo (DOI: 10.5281/zenodo.12345).
\end{document}
"""

# A tex file with a GitHub URL in the body.
TEX_WITH_GITHUB_URL = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.
The implementation is available at \url{https://github.com/author/repo}.
\end{document}
"""

# A tex file with a Zenodo DOI.
TEX_WITH_ZENODO = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.
Data is at https://doi.org/10.5281/zenodo.12345.
\end{document}
"""

# A tex file with an anonymous submission URL.
TEX_WITH_ANONYMOUS_URL = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.
Code is at https://anonymous.4open.science/r/abc123.
\end{document}
"""

# A tex file with FULL reproducibility metadata.
TEX_WITH_ALL_METADATA = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.
Hyperparameters: learning rate 1e-4, batch size 32, Adam optimizer.
We use a random seed of 42 (torch.manual_seed(42)).
Hardware: 4x NVIDIA RTX 4090 GPUs for 24 hours.
We use PyTorch 2.0 and transformers 4.30.
\end{document}
"""

# A tex file with NO reproducibility metadata.
TEX_NO_METADATA = r"""
\documentclass{article}
\begin{document}
We train a model on dataset X.
Our model achieves 95\% accuracy.
\end{document}
"""

# A tex file with a claim "we achieve SOTA" but says "we do not release".
TEX_CLAIM_NO_RELEASE = r"""
\documentclass{article}
\begin{document}
We achieve state-of-the-art accuracy on ImageNet.

\section{Availability}
We do not release the code or data due to proprietary restrictions.
\end{document}
"""

# A tex file with a "we will release" future-tense claim.
TEX_FUTURE_TENSE = r"""
\documentclass{article}
\begin{document}
We achieve state-of-the-art accuracy on ImageNet.

\section{Availability}
We will release the code upon paper acceptance.
\end{document}
"""


def _fresh_check(tex: str, c10_claims: list = None) -> list:
    """Convenience: call check_c10_reproducibility with default args."""
    return verify_TEMPLATE.check_c10_reproducibility(tex, c10_claims)


# =====================================================================
# Sub-check 1: Availability statement exists
# =====================================================================

# Test 1: no availability statement -> HIGH finding
def test_c10_no_availability_statement_emits_high():
    """A tex with no availability statement should emit a HIGH finding.

    Per ROADMAP.md: this is a real reviewer concern. Many
    papers claim SOTA results but provide no way for
    others to verify them.
    """
    findings = _fresh_check(TEX_NO_AVAILABILITY)
    assert len(findings) >= 1
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 1, (
        f'Expected 1 HIGH finding, got: {findings}'
    )
    assert 'availability' in high_findings[0][1].lower() or \
           'code' in high_findings[0][1].lower() or \
           'data' in high_findings[0][1].lower()


# Test 2: Availability section -> no HIGH finding
def test_c10_with_availability_section_recognized():
    """A tex with \\section{Availability} should NOT emit a HIGH finding.

    Sub-check 1 satisfied: an Availability section is the
    most common way to declare reproducibility.
    """
    findings = _fresh_check(TEX_WITH_AVAILABILITY_SECTION)
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings, got: {high_findings}'
    )


# Test 3: Code Availability section -> no HIGH finding
def test_c10_with_code_availability_section_recognized():
    """A tex with \\section{Code Availability} should be recognized."""
    findings = _fresh_check(TEX_WITH_CODE_AVAILABILITY)
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings, got: {high_findings}'
    )


# Test 4: Data Availability section -> no HIGH finding
def test_c10_with_data_availability_section_recognized():
    """A tex with \\section{Data Availability} should be recognized."""
    findings = _fresh_check(TEX_WITH_DATA_AVAILABILITY)
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings, got: {high_findings}'
    )


# Test 5: GitHub URL -> no HIGH finding
def test_c10_with_github_url_recognized():
    """A tex with a GitHub URL should be recognized as a code release."""
    findings = _fresh_check(TEX_WITH_GITHUB_URL)
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings, got: {high_findings}'
    )


# Test 6: Zenodo DOI -> no HIGH finding
def test_c10_with_zenodo_doi_recognized():
    """A tex with a Zenodo DOI should be recognized as a data release."""
    findings = _fresh_check(TEX_WITH_ZENODO)
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings, got: {high_findings}'
    )


# Test 7: Anonymous submission URL -> no HIGH finding
def test_c10_with_anonymous_url_recognized():
    """A tex with an anonymous.4open.science URL should be recognized.

    This is the URL pattern used by ICLR/NeurIPS anonymous
    submissions. We should accept it as a code release
    even though the URL is not GitHub.
    """
    findings = _fresh_check(TEX_WITH_ANONYMOUS_URL)
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 0, (
        f'Expected 0 HIGH findings, got: {high_findings}'
    )


# =====================================================================
# Sub-check 2: Statement consistency with claims
# =====================================================================

# Test 8: claim consistent with release -> no MED finding
def test_c10_claim_consistent_with_release():
    """A paper that claims SOTA AND releases code/data -> no inconsistency."""
    # The default c10_reproducibility_claims contains a
    # 'claims_sota' example that the test should pass.
    findings = _fresh_check(TEX_WITH_AVAILABILITY_SECTION, [
        {'type': 'claims_sota', 'dataset': 'ImageNet', 'expected_section': 'data'},
    ])
    inconsistency_findings = [
        f for f in findings
        if f[0] == 'C10' and 'inconsist' in f[1].lower()
    ]
    assert len(inconsistency_findings) == 0, (
        f'Expected 0 inconsistency findings, got: {inconsistency_findings}'
    )


# Test 9: claim inconsistent with no-release -> MED finding
def test_c10_claim_inconsistent_with_no_release():
    """A paper that claims SOTA but says 'we do not release' -> MED finding.

    This is a real reviewer concern: the paper makes a
    strong claim but provides no way to verify it.
    """
    findings = _fresh_check(TEX_CLAIM_NO_RELEASE, [
        {'type': 'claims_sota', 'dataset': 'ImageNet', 'expected_section': 'data'},
    ])
    inconsistency_findings = [
        f for f in findings
        if f[0] == 'C10' and 'inconsist' in f[1].lower()
    ]
    assert len(inconsistency_findings) >= 1, (
        f'Expected >= 1 inconsistency finding, got: {findings}'
    )


# Test 10: future-tense release -> MED finding
def test_c10_future_tense_release_emits_med():
    """A paper that says 'we will release' (future tense) -> MED finding.

    Sub-check 1 satisfied (Availability section exists),
    but the release is conditional on acceptance, which
    is not a real release. A MED finding is appropriate.
    """
    findings = _fresh_check(TEX_FUTURE_TENSE)
    # We expect a MED finding (no HIGH since there's an
    # Availability section, but the content is future-tense).
    med_findings = [f for f in findings if f[0] == 'C10' and 'MED' in f[1]]
    assert len(med_findings) >= 1, (
        f'Expected >= 1 MED finding, got: {findings}'
    )


# =====================================================================
# Sub-check 3: Reproducibility metadata
# =====================================================================

# Test 11: no metadata -> LOW finding
def test_c10_no_reproducibility_metadata_emits_low():
    """A tex with no hyperparameters / seed / hardware / version
    should emit LOW findings (one per missing category)."""
    findings = _fresh_check(TEX_NO_METADATA)
    low_findings = [f for f in findings if f[0] == 'C10' and 'LOW' in f[1]]
    # Expect at least 4 LOW findings (one for each missing
    # metadata category).
    assert len(low_findings) >= 4, (
        f'Expected >= 4 LOW findings (one per metadata category), '
        f'got {len(low_findings)}: {low_findings}'
    )


# Test 12: with all metadata -> no LOW finding
def test_c10_with_all_metadata_recognized():
    """A tex with all 4 metadata categories should not emit LOW findings.

    Sub-check 3 satisfied: hyperparameters, random seed,
    hardware, and library version are all reported.
    """
    findings = _fresh_check(TEX_WITH_ALL_METADATA)
    low_findings = [f for f in findings if f[0] == 'C10' and 'LOW' in f[1]]
    assert len(low_findings) == 0, (
        f'Expected 0 LOW findings, got: {low_findings}'
    )


# Test 13: with hyperparameters only -> 3 LOW findings
def test_c10_with_hyperparameters_only():
    """A tex with only hyperparameters should still flag missing
    random seed, hardware, and version."""
    tex = r"""
    We use learning rate 1e-4, batch size 32, Adam optimizer.
    """
    findings = _fresh_check(tex)
    # No HIGH (no claim), but 3 LOW (no seed, no hardware, no version)
    low_findings = [f for f in findings if f[0] == 'C10' and 'LOW' in f[1]]
    assert len(low_findings) == 3, (
        f'Expected 3 LOW findings, got {len(low_findings)}: {low_findings}'
    )


# Test 14: with hardware only -> 3 LOW findings
def test_c10_with_hardware_only():
    """A tex with only hardware should still flag missing
    hyperparameters, random seed, and version."""
    tex = r"""
    Hardware: 4x NVIDIA A100 GPUs for 24 hours.
    """
    findings = _fresh_check(tex)
    low_findings = [f for f in findings if f[0] == 'C10' and 'LOW' in f[1]]
    assert len(low_findings) == 3, (
        f'Expected 3 LOW findings, got: {low_findings}'
    )


# Test 15: with random seed only -> 3 LOW findings
def test_c10_with_random_seed_only():
    """A tex with only random seed should still flag missing
    hyperparameters, hardware, and version."""
    tex = r"""
    We use a random seed of 42.
    """
    findings = _fresh_check(tex)
    low_findings = [f for f in findings if f[0] == 'C10' and 'LOW' in f[1]]
    assert len(low_findings) == 3, (
        f'Expected 3 LOW findings, got: {low_findings}'
    )


# Test 16: with library version only -> 3 LOW findings
def test_c10_with_library_version_only():
    """A tex with only library version should still flag missing
    hyperparameters, random seed, and hardware."""
    tex = r"""
    We use PyTorch 2.0.
    """
    findings = _fresh_check(tex)
    low_findings = [f for f in findings if f[0] == 'C10' and 'LOW' in f[1]]
    assert len(low_findings) == 3, (
        f'Expected 3 LOW findings, got: {low_findings}'
    )


# =====================================================================
# Edge cases
# =====================================================================

# Test 17: disabled when config is empty (or only c10_reproducibility_claims is None)
def test_c10_disabled_when_no_claims_config():
    """When c10_reproducibility_claims is None or empty,
    C10 still runs the availability + metadata checks
    but does NOT run the consistency check (sub-check 2).
    """
    # With no claims config, we should still get
    # availability + metadata findings (the basic checks).
    findings = _fresh_check(TEX_NO_AVAILABILITY, None)
    # HIGH for missing availability
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 1


# Test 18: malformed LaTeX doesn't crash
def test_c10_malformed_latex_no_crash():
    """Malformed LaTeX (unclosed braces, unclosed sections)
    should not crash the audit. The function should
    gracefully skip the malformed parts."""
    malformed = r"""
    \begin{document
    We train a model on dataset X
    (unclosed brace: \section{Reproducibility
    """
    # Should not raise
    findings = _fresh_check(malformed)
    assert isinstance(findings, list)


# Test 19: empty tex -> 1 HIGH finding
def test_c10_empty_tex_emits_high():
    """An empty tex should emit a HIGH finding (no availability)."""
    findings = _fresh_check('')
    high_findings = [f for f in findings if f[0] == 'C10' and 'HIGH' in f[1]]
    assert len(high_findings) == 1


# Test 20: combined: has availability + has all metadata + no claim -> no findings
def test_c10_complete_no_claim_no_findings():
    """A paper with all 4 metadata + an Availability section
    AND no SOTA claim should have 0 findings."""
    complete_tex = TEX_WITH_ALL_METADATA + '\n\n' + r"""
\section{Availability}
Code: https://github.com/author/repo
Data: https://doi.org/10.5281/zenodo.12345
"""
    findings = _fresh_check(complete_tex)
    # No claims, so no MED for inconsistency
    # Has availability, so no HIGH
    # Has all metadata, so no LOW
    assert findings == [], f'Expected 0 findings, got: {findings}'


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
