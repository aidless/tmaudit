<!--
This is what a real GitHub issue would look like after the
author fills in the .github/ISSUE_TEMPLATE/enhancement.md
template. We are showing this as a usage example for the
enhancement template: it would be filed via

  gh issue create --body-file _demo_c7_enhancement_filled.md

or copy-pasted into the GitHub web UI after clicking
"New issue" → "Enhancement".
-->

---
name: Enhancement
description: Propose an improvement to an existing audit category, CLI subcommand, or other tmaudit feature. Use this for C7, the cache, performance, ergonomics, etc.
title: "[Enhancement]: Add min_count threshold to C6 blacklist "
labels: ["enhancement", "needs-triage"]
assignees: []
---

## What needs improvement?

Add a `min_count` threshold to the C6 blacklist so that 1-2
occurrences of a blacklisted word (e.g., "yield", "reveal")
are not reported as a finding.

## Why is this an enhancement, not a feature?

This enhances the existing C6 check in
`src/tmaudit/templates/verify_TEMPLATE.py::check_c6_blacklist`
(line 496-519). We are not adding a new check; we are
tuning the threshold of the existing one. The audit
already has 6 categories (C1..C6); after this enhancement
it will still have 6 categories.

If we wanted to ADD a new check (e.g., a citation-context
check, which would be C7), we would use the "Feature
request" template instead.

## Current behaviour

Today, `tmaudit verify --paper 5` reports a C6 finding on
the word "yield" even when it appears only 2 times in
idiomatic English:

```
[LOW] C6  (line 233)
    Blacklist word "yield" appears 2x in main.tex.
```

The current behaviour treats the **first** occurrence of any
blacklisted word as reportable. The line 234 in Paper 5's
main.tex contains the phrase "yields a strictly lower
$\Gamma$" which is correct mathematical English ("yields a
value of $X$"), but the audit does not know that.

## Proposed behaviour

After this enhancement, `check_c6_blacklist` should only
report a finding if a blacklisted word appears **3 or more**
times. 1-2 occurrences are considered idiomatic English and
are not reported.

```python
# NEW (fixed)
min_count: int = 3
for word, n in sorted(counts.items()):
    if n < min_count:
        continue  # 1-2 occurrences are OK
    findings.append(...)
```

The threshold is `3` (not 2) because:

- **1-2 occurrences**: idiomatic English, do not report.
- **3+ occurrences**: starts to look like a word being used
  to avoid saying something specific.

## Example: before vs after

Before:
```
$ tmaudit verify --paper 5
...
[LOW] C6  (line 233)
    Blacklist word "yield" appears 2x in main.tex (e.g., line 233).
...
TOTAL: 1 findings (HIGH=0, MEDIUM=0, LOW=1)
```

After:
```
$ tmaudit verify --paper 5
...
  C1  [OK]     0 finding(s)
  C2  [OK]     0 finding(s)
  C3  [OK]     0 finding(s)
  C4  [OK]     0 finding(s)
  C5  [OK]     0 finding(s)
  C6  [OK]     0 finding(s)
All checks passed.  No issues detected.
```

## Migration path

**Automatic** — no migration is needed. The new behaviour is
the default; users get it by upgrading `tmaudit`.

The threshold is a constant (`min_count: int = 3`) in the
function, not a config-file parameter. We will NOT expose it
in `paper_configs.py` because it is a property of the C6
check, not a per-paper setting. If a future user needs a
different threshold, we can lift it to a config parameter
in v0.2.0.

## Risk assessment

**Risk 1: False negatives**. By raising the threshold to 3,
we may miss papers that abuse a blacklisted word 2 times in
non-idiomatic English (e.g., "The model yield better results
and yield higher accuracy."). The original threshold (1)
would catch this; the new threshold (3) would not.

  **Mitigation**: 2 occurrences of a blacklisted word in a
  short span (e.g., 1 paragraph) is still suspicious. We
  could add a "density" check (e.g., 2 occurrences in < 100
  words) as a follow-up enhancement, but for v0.1.1 we
  prioritize avoiding the false-positive on idiomatic
  English.

**Risk 2: Unintended paper regressions**. Papers that
currently fail the C6 check might pass after this change,
but for the wrong reason (the actual bug in the paper is
still there, but the threshold masks it). For example, a
paper with "yields yield yield" (3 occurrences) would be
flagged; a paper with "yields yield" (2 occurrences) would
not.

  **Mitigation**: We are explicit in the commit message
  and release notes that 2-occurrence cases are now
  considered idiomatic. Users who want strict checking can
  add a custom check via the planned v0.3.0 plugin API.

**Risk 3: Backward incompatibility**. Existing user scripts
that grep for "C6 LOW" in the audit output would no longer
see the false-positive entries. This is a behavioural change
that the release notes will document.

  **Mitigation**: Document the change in `RELEASE_NOTES_v0.1.1.md`
  (the "Breaking changes" section) and call it out in the
  PR description. In practice, the false-positive entries
  were spurious, so removing them is a net improvement.

## Acceptance criteria

- [ ] `check_c6_blacklist` in `verify_TEMPLATE.py` has a
      `min_count: int = 3` threshold.
- [ ] 1-2 occurrences of any blacklisted word are not reported.
- [ ] 3+ occurrences are reported as before.
- [ ] All existing tests still pass.
- [ ] New unit tests cover: 1-occurrence, 2-occurrence,
      3-occurrence, 10-occurrence, inflections, per-word
      counting, word boundary (target: 7+ tests).
- [ ] `_check_all_regressions.py` has an `inject_bug7` that
      sets `min_count = 0` and asserts the new test catches
      the regression.
- [ ] `engineering_notes_verify_template.md` has a new
      section documenting the C6 threshold design.
- [ ] `CHANGELOG.md` v0.1.1 entry added.

## Affected components

- [x] `src/tmaudit/templates/verify_TEMPLATE.py`
- [x] `tests/`
- [x] `_check_all_regressions.py`
- [ ] `hooks/`
- [ ] `.github/workflows/ci.yml`
- [x] Documentation (`README.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`)

## Effort estimate

- [x] Medium (1-3 days)

## Are you willing to implement it?

- [x] Yes, I plan to submit a PR
- [ ] Yes, but I need help / mentorship
- [ ] No, but I'd be happy to review
- [ ] No, asking for someone else to implement

## Related issues / PRs

- Fixes #7
- Supersedes #6 (initial Bug 6 fix without the threshold)
- See also: `engineering_notes_verify_template.md` §6

## Checklist

- [x] I have searched existing issues and this is not a duplicate
- [x] I have described a concrete use case (not "would be nice")
- [x] I have shown the before/after behaviour with an example
- [x] I have described the migration path
- [x] I have assessed the risks
- [x] I have listed the acceptance criteria
- [x] I have indicated whether I am willing to submit a PR