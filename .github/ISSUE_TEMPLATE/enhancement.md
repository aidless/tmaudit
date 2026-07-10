---
name: Enhancement
description: Improve an existing check, performance, or ergonomics (e.g., C6 threshold, cache).
title: "[Enhancement]: "
labels: ["enhancement", "needs-triage"]
assignees: []
---

<!--
Thanks for proposing an enhancement!

An **enhancement** is different from a **feature**:
  - A *feature* adds something new (e.g., a new audit
    category, a new CLI subcommand).
  - An *enhancement* improves something that already exists
    (e.g., make an existing check faster, more accurate,
    or more configurable).

Examples of enhancements:
  - Add a `min_count` threshold to the C6 blacklist (this
    is what the existing C6 check does, but with a tweak).
  - Make the audit cache invalidation smarter.
  - Add a `--quiet` flag to the CLI.
  - Improve the error message when a paper config is
    missing a required key.
  - Add a progress bar to the audit.

If your proposal is for a NEW audit category or NEW CLI
subcommand, use the "Feature request" template instead.
-->

## What needs improvement?

<!--
A clear, one-sentence description of the improvement.

GOOD: "Add a min_count threshold to the C6 blacklist so that
       1-2 occurrences of a blacklisted word are not reported."
GOOD: "Cache audit results in SQLite so re-running on
       unchanged content is instant."
BAD:  "Make C6 better."
-->

## Why is this an enhancement, not a feature?

<!--
Explain why this is an *enhancement* (improves something
existing) and not a *feature* (adds something new).
Reference the specific existing code/file/line that this
enhancement would improve.

GOOD: "This enhances the existing C6 check in
       `src/tmaudit/templates/verify_TEMPLATE.py:check_c6_blacklist`.
       We are not adding a new check; we are tuning the
       behaviour of the existing one."
BAD:  "It would be useful to have."
-->

## Current behaviour

<!--
Describe what the system does today. Be specific: cite
file names, function names, and the exact output / behaviour
the user sees.

GOOD: "Today, `tmaudit verify --paper 5` reports a C6 finding
       on the word 'yield' (line 234) even when it appears
       only 2 times in idiomatic English ('yields a strictly
       lower $\Gamma$')."
BAD:  "The audit is too aggressive."
-->

## Proposed behaviour

<!--
Describe what the system should do after this enhancement.
Be specific: cite the new behaviour, the new flag, the new
threshold, the new error message, etc.

GOOD: "After this enhancement, `check_c6_blacklist` should
       only report a finding if a blacklisted word appears
       3+ times. 1-2 occurrences are considered idiomatic
       English and are not reported."
BAD:  "It should be smarter."
-->

## Example: before vs after

<!--
If the enhancement is user-visible, show a concrete example
of the old and new behaviour. This is the most helpful
section for reviewers.

GOOD:

  Before:
  ```
  $ tmaudit verify --paper 5
  ...
  [LOW] C6  (line 233)
      Blacklist word "yield" appears 2x in main.tex.
  ```

  After:
  ```
  $ tmaudit verify --paper 5
  ...
  C6  [OK]     0 finding(s)
  All checks passed.
  ```
-->

## Migration path

<!--
How do users transition from the old behaviour to the new
behaviour? Is the change:
  - **Automatic**: the new behaviour is the default; users
    get it by upgrading.
  - **Opt-in**: a new flag controls the new behaviour; the
    old behaviour is the default until the flag is set.
  - **Breaking**: the old behaviour is removed entirely.

If automatic, no migration is needed — say so.
If opt-in, show the new flag and the old equivalent.
If breaking, list the affected users and the workaround.

GOOD (opt-in): "Add a new flag `--c6-min-count N` (default
  `1` to preserve the old behaviour). Users who want the
  new behaviour set `--c6-min-count 3`."
GOOD (automatic): "No migration needed. The new behaviour
  is the default; users get it by upgrading tmaudit."
-->

## Risk assessment

<!--
What could go wrong? Be honest. Common risks:

  - **False positives**: the new behaviour flags things
    that should not be flagged.
  - **False negatives**: the new behaviour misses things
    that should be flagged.
  - **Performance regression**: the enhancement makes the
    audit slower.
  - **Backward incompatibility**: existing user scripts
    that depend on the old behaviour will break.
  - **Data loss**: the enhancement removes or invalidates
    existing data (e.g., cache entries, audit results).

For each risk, propose a mitigation.

GOOD: "Risk: false positives. We might flag a legitimate
  citation as ceremonial because our heuristic missed an
  'engage' signal. Mitigation: per-paper `c7_max_ceremonial`
  threshold (default 2) — 1-2 ceremonial cites are OK, 3+
  are flagged. This makes the check lenient rather than
  aggressive."
-->

## Acceptance criteria

<!--
Check ALL that apply. These define what "done" means.
The PR cannot be merged until all of these are checked.

A well-defined enhancement has 3-8 acceptance criteria. If
you have more than 8, the enhancement is probably too big
and should be split.
-->

- [ ] The enhancement is implemented and documented in
      the relevant file.
- [ ] All existing tests still pass.
- [ ] New unit tests cover the new behaviour (target: 3+ tests).
- [ ] The meta-test is updated to include this enhancement
      as a new "bug" (so future regressions are caught).
- [ ] `engineering_notes_verify_template.md` has a new
      section documenting the enhancement.
- [ ] `CHANGELOG.md` has a new entry for this enhancement.
- [ ] If the enhancement is user-visible, the README and
      CLI `--help` are updated.
- [ ] If the enhancement is opt-in, the default behaviour
      is preserved (no breaking changes for users who do
      not set the new flag).

## Affected components

<!--
Tick the files / modules this enhancement would touch.
An *enhancement* should affect 1-3 files. If you tick more
than 5, you may be proposing a feature, not an enhancement.
-->

- [ ] `src/tmaudit/forge.py`
- [ ] `src/tmaudit/cli.py`
- [ ] `src/tmaudit/templates/verify_TEMPLATE.py`
- [ ] `src/tmaudit/templates/compile_check_TEMPLATE.py`
- [ ] `src/tmaudit/templates/fix_abstract_unicode_TEMPLATE.py`
- [ ] `src/tmaudit/configs/paper_configs.py`
- [ ] `src/tmaudit/configs/compile_configs.py`
- [ ] `tests/`
- [ ] `hooks/`
- [ ] `.github/workflows/ci.yml`
- [ ] Documentation (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`)
- [ ] New file: <!-- name of the new file -->

## Effort estimate

<!--
Choose one. If unsure, pick "Medium" and a maintainer will
adjust during triage.
-->

- [ ] Small (< 1 day)
- [ ] Medium (1-3 days)
- [ ] Large (1-2 weeks)
- [ ] X-Large (> 2 weeks)

## Are you willing to implement it?

<!--
Maintainers prioritize PRs over plain requests. If you
can submit a PR, the enhancement is much more likely to be
merged.
-->

- [ ] Yes, I plan to submit a PR
- [ ] Yes, but I need help / mentorship
- [ ] No, but I'd be happy to review
- [ ] No, asking for someone else to implement

## Related issues / PRs

<!--
Link related discussions, duplicates, or prior art.
-->

- Related to #
- See also #
- Supersedes #

## Checklist

<!--
Tick what you've already done. Maintainers will not act
on a request where none of these are checked.
-->

- [ ] I have searched existing issues and this is not a duplicate
- [ ] I have described a concrete use case (not "would be nice")
- [ ] I have shown the before/after behaviour with an example
- [ ] I have described the migration path
- [ ] I have assessed the risks
- [ ] I have listed the acceptance criteria
- [ ] I have indicated whether I am willing to submit a PR