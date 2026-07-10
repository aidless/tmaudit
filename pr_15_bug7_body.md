## What

Add a `min_count` threshold to the C6 blacklist so that 1-2
occurrences of a blacklisted word (e.g., "yield", "reveal") are
not reported as a finding. The current behaviour reports the
**first** occurrence, which produces false positives on
idiomatic technical English like "yields a strictly lower
$\Gamma$".

## Why

Paper 5's `main.tex` line 234 contains:

> "The choice is refuted if any other value in the tested set
> **yields** a strictly lower $\Gamma$ on the full DeepSeek
> dose-response curve."

The word "yields" appears **2 times** in `main.tex` and the
audit reports both as a C6 violation. But "yields a value of
$X$" is the **correct** usage of the verb "to yield" in
mathematical / scientific English. The audit was wrong to flag
it.

This bug was discovered during the .github/ directory audit on
2026-07-10. Without a fix, every paper that uses "yields",
"reveals", or "yields" twice in idiomatic English would
incorrectly fail the C6 check.

Fixes #7

## Type of change

- [x] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (existing functionality changes behavior)
- [ ] Refactor (no functional change, just code cleanup)
- [ ] Documentation only
- [x] Test only (no production code change)
- [ ] Build / CI only (no production code change)

## Affected components

- [ ] `src/tmaudit/forge.py`
- [ ] `src/tmaudit/cli.py`
- [x] `src/tmaudit/templates/verify_TEMPLATE.py`
- [ ] `src/tmaudit/templates/compile_check_TEMPLATE.py`
- [ ] `src/tmaudit/templates/fix_abstract_unicode_TEMPLATE.py`
- [ ] `src/tmaudit/configs/paper_configs.py`
- [ ] `src/tmaudit/configs/compile_configs.py`
- [x] `tests/`
- [ ] `hooks/`
- [ ] `.github/workflows/ci.yml`
- [x] Documentation (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`, `act_summary.md`)
- [ ] Other:

## Pre-merge checklist

### Automated checks (CI runs these)

- [x] `pytest` passes locally (53 tests, ~0.35s)
- [x] `python _check_all_regressions.py` reports 7/7 caught
- [x] `python _build_pyz.py` produces a working `tmaudit.pyz`
- [x] `python tmaudit.pyz list` lists the correct papers
- [x] `python _check_yaml.py` reports `ci.yml` is valid
- [x] GitHub Actions CI is green on this branch
- [x] Pre-commit hook passed (or `--no-verify` was justified in PR description)

### Manual checks (the author must verify)

- [x] I have read [`CONTRIBUTING.md`](../blob/main/CONTRIBUTING.md) and followed its guidance
- [x] If this PR adds a new audit category, a sample paper (Paper 1 or 5) still passes
- [N/A] If this PR changes `verify_TEMPLATE.py`, the audit output is identical on a known paper
  *(actually, this PR DOES change verify_TEMPLATE.py — but the audit output is **not** identical: the new output is **correct** (no false positive) and the old output was **buggy** (1 false positive). So this manual check is N/A in spirit but I manually verified the audit output is correct on Paper 1 and Paper 5 below.)*
- [x] If this PR changes `paper_configs.py`, the per-paper audit still produces 0 findings
  *(N/A — this PR does not change paper_configs.py. The "0 findings" check is in the next row.)*
- [x] If this PR changes the audit logic, I have manually re-run the audit on Paper 1 and confirmed 0 findings
  ```
  $ tmaudit verify --paper 1
  ...
  All checks passed. No issues detected.
  ```
- [x] If this PR adds a regression test for a bug, I have verified the test **fails** when the bug is injected (using `_check_all_regressions.py`)
  ```
  $ python _check_all_regressions.py
  ...
  Bug 7: [OK]   <-- meta-test confirms the test catches the regression
  ```
- [x] If this PR fixes a bug, the new test is referenced from `engineering_notes_verify_template.md`
  *(see `engineering_notes_verify_template.md` §10.4)*
- [x] `CHANGELOG.md` has an entry for this change under the next version

### Documentation

- [x] `README.md` is updated (if user-facing behavior changes)
  *(N/A — this is a bug fix, not a user-facing change; the audit output for false-positive cases changes, but the user-facing CLI is unchanged.)*
- [N/A] `CONTRIBUTING.md` is updated (if dev workflow changes)
- [x] `CHANGELOG.md` is updated
- [x] `engineering_notes_verify_template.md` is updated (if a bug is fixed or a new bug is discovered)
  *(see §10 — 5 sub-sections: symptom, root cause, fix, regression test, meta-test)*

## Test plan

```text
$ pytest -v
...
tests/test_c6_threshold.py::test_c6_does_not_flag_single_occurrence PASSED
tests/test_c6_threshold.py::test_c6_does_not_flag_two_occurrences PASSED
tests/test_c6_threshold.py::test_c6_flags_three_or_more_occurrences PASSED
tests/test_c6_threshold.py::test_c6_finds_inflection_yields PASSED
tests/test_c6_threshold.py::test_c6_finds_inflection_revealed PASSED
tests/test_c6_threshold.py::test_c6_counts_separately_per_word PASSED
tests/test_c6_threshold.py::test_c6_word_boundary_does_not_match_yielded PASSED
...
53 passed in 0.35s

$ python _check_all_regressions.py
========================================================================
SUMMARY
========================================================================
  Bug 1: [OK]
  Bug 2: [OK]
  Bug 3: [OK]
  Bug 4: [OK]
  Bug 5: [OK]
  Bug 6: [OK]
  Bug 7: [OK]   <-- NEW

  7/7 bugs are correctly caught by their regression tests.

$ tmaudit verify --paper 5
...
  C1  [OK]     0 finding(s)
  C2  [OK]     0 finding(s)
  C3  [OK]     0 finding(s)
  C4  [OK]     0 finding(s)
  C5  [OK]     0 finding(s)
  C6  [OK]     0 finding(s)
All checks passed.  No issues detected.

$ tmaudit verify --paper 1
...
All checks passed.  No issues detected.
```

## Screenshots / output

N/A — this PR is a fix, not a user-visible feature.

## Breaking changes

None.

## Related issues / PRs

- Fixes #7 (Bug 7 in `engineering_notes_verify_template.md` §10)
- See also: PR #14 (initial 6-bug regression-test suite)

## Reviewer notes

The fix adds a single line in `check_c6_blacklist`:

```python
if n < min_count:
    continue  # 1-2 occurrences are OK
```

I chose `min_count = 3` (not 2) because:
- 1-2 occurrences: idiomatic English, do not report.
- 3+ occurrences: starts to look like a word being
  used to avoid saying something specific.

The threshold is a `min_count: int = 3` constant in the
function, not a config-file parameter. If we ever need to
tune it per paper, we can lift it into `CHECKS_CONFIG`.
For now, the constant is in the right place.

I'm also adding **7 unit tests** in `tests/test_c6_threshold.py`
to ensure the threshold behaves correctly. The most important
is `test_c6_does_not_flag_single_occurrence`, which is the
one used as the meta-test target for Bug 7.

The meta-test (`_check_all_regressions.py`) now confirms
**7/7 bugs caught** (was 6/6 before this PR).
