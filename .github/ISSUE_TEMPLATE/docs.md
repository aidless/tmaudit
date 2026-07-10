---
name: Documentation
description: Fix a typo, clarify a section, or add docs (README, CONTRIBUTING, CHANGELOG, etc.).
title: "[Docs]: "
labels: ["documentation", "needs-triage"]
assignees: []
---

<!--
Thanks for improving the documentation!

A **docs PR** is different from the other templates:
  - It changes ONLY documentation files (no Python, no
    tests, no configs, no GitHub Actions).
  - It should NOT change behaviour. The docs should
    describe what the code already does.
  - It is reviewed for *clarity, accuracy, and tone*, not
    for *correctness* (the CI is the source of truth for
    correctness).

Examples of docs PRs:
  - Fix a typo in the README.
  - Add a new example to the CONTRIBUTING guide.
  - Restructure the CHANGELOG to follow Keep a Changelog 1.1.0.
  - Add a "Troubleshooting" section to the docs.
  - Clarify an existing section that was unclear.

If your PR changes both docs AND code, use the appropriate
template (bug / feature / enhancement) and add "Updates the
docs for X" as a sub-bullet in the PR body.
-->

## What documentation needs improvement?

<!--
A clear, one-sentence description of the docs change.

GOOD: "Fix a typo in README.md: 'TEMPATE' → 'TEMPLATE'."
GOOD: "Add a 'Troubleshooting' section to CONTRIBUTING.md
       covering the 5 most common error messages."
GOOD: "Reformat CHANGELOG.md to follow Keep a Changelog
       1.1.0 conventions."
BAD:  "Improve docs."
-->

## Why is this a docs-only PR?

<!--
Confirm that this PR changes ONLY documentation files.
List the file types you will NOT touch:

  - [ ] No `*.py` files
  - [ ] No `tests/` changes
  - [ ] No `src/tmaudit/` changes
  - [ ] No `.github/workflows/` changes
  - [ ] No `pyproject.toml` or other config changes

If you need to change code, use a different template.
-->

## Type of change

<!--
Choose the closest match. Most docs PRs are 'Improvement'
or 'New content'.
-->

- [ ] Typo / grammar fix (1-2 word changes)
- [ ] Clarification (existing section is unclear)
- [ ] Improvement (existing section could be better)
- [ ] New content (a new section or file)
- [ ] Restructure (reorganize existing content)
- [ ] Translation (translate to another language)
- [ ] Other: <!-- describe -->

## Affected files

<!--
Tick the documentation files this PR will touch.
A docs PR should affect 1-3 files. If you tick more than
5, you may be proposing a code change too.
-->

- [ ] `README.md`
- [ ] `CONTRIBUTING.md`
- [ ] `CHANGELOG.md`
- [ ] `RELEASE_NOTES_*.md`
- [ ] `ROADMAP.md`
- [ ] `engineering_notes_*.md`
- [ ] `SECURITY.md`
- [ ] `PUSH_INSTRUCTIONS.md`
- [ ] `LICENSE` / `LICENSE.md`
- [ ] `.github/ISSUE_TEMPLATE/*.md`
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] `.github/CODE_OF_CONDUCT.md`
- [ ] `.github/SUPPORT.md`
- [ ] `.github/CODEOWNERS` (only the comments)
- [ ] `docs/` (subdirectory)
- [ ] `tests/README.md` or similar test docs
- [ ] Other: <!-- path -->

## Rendered output

<!--
Show how the change will look once rendered on GitHub.
Use a fenced code block with the language tag (usually
`markdown` or omit).

This is the most helpful section for reviewers: they can
see the exact change in context.

GOOD:

  Before:
  ```markdown
  ## Installation

  Run `pip install tmaudit`.
  ```

  After:
  ```markdown
  ## Installation

  Install via pip:

  ```bash
  pip install tmaudit
  ```

  Or, download `tmaudit.pyz` directly from the
  [Releases page](https://github.com/liumingrui/tmaudit/releases).
  ```
-->

## Spell / grammar / style check

<!--
Documentation PRs are reviewed for *clarity* and *tone*,
not just *correctness*. Tick the checks you have done.

If you are not a native English speaker, do not worry —
the reviewer will help with grammar. Focus on the
*technical accuracy* and the *structure* of the change.
-->

- [ ] I have read the change aloud and it flows naturally
- [ ] I have checked for common typos (e.g., "teh" instead
      of "the", "recieve" instead of "receive")
- [ ] I have used consistent terminology (e.g., always
      "audit", not "scan" or "check")
- [ ] I have followed the existing tone (terse, direct,
      no filler)
- [ ] I have used the same heading style (H1 → H2 → H3,
      no skipping levels)
- [ ] I have used sentence-case for headings, not Title Case
- [ ] I have checked that all code blocks have a language
      tag (`bash`, `python`, `markdown`, etc.)
- [ ] I have not introduced new jargon without defining it

## Link / cross-reference check

<!--
Documentation often links to other files, sections, and
external resources. Tick the checks you have done.
-->

- [ ] I have checked that all internal links resolve
      (e.g., `[CHANGELOG](./CHANGELOG.md)` points to a
      real file)
- [ ] I have checked that all section anchors resolve
      (e.g., `## Section Name` exists and is reachable)
- [ ] I have checked that all external links are still
      alive (e.g., the GitHub URL resolves to a real page)
- [ ] I have not renamed any file that is referenced by
      another file (or, if I have, I have updated all
      references)
- [ ] I have not moved any section that is referenced by
      another file (or, if I have, I have updated all
      references)

## Backwards compatibility

<!--
Some docs changes are user-visible in a way that matters
to the community. Tick the relevant cases.

Examples of user-visible docs changes:
  - Renaming a public file (e.g., README.md → README_v2.md)
  - Moving a section that is bookmarked by users
  - Changing the CLI flags documented in the README
  - Updating the C1..C6 audit category names
-->

- [ ] This change is purely internal (no external impact)
- [ ] This change renames a file — I have updated all
      references in the repo AND in any external docs
- [ ] This change moves a section — I have updated all
      cross-references AND any external bookmarks
- [ ] This change updates the documented CLI behaviour —
      I have confirmed the CLI actually behaves this way
- [ ] This change updates the documented config schema —
      I have confirmed the schema actually matches the code
- [ ] This change is not backwards-compatible (explain
      in the "Reviewer notes" section)

## Acceptance criteria

<!--
Check ALL that apply. These define what "done" means.
-->

- [ ] The change is implemented in the affected files
- [ ] No other files are touched (only the ones ticked above)
- [ ] The change is rendered correctly on GitHub
      (previewed locally if possible)
- [ ] All internal links still resolve
- [ ] All external links are still alive
- [ ] The change follows the existing tone and structure
- [ ] The change does not introduce new jargon
- [ ] The change is consistent with the rest of the doc
      (e.g., same heading style, same terminology)
- [ ] The CI is still green (no code was changed, so this
      should be automatic, but verify)

## Effort estimate

<!--
Docs PRs are usually small. Pick the closest match.
-->

- [ ] Trivial (< 30 minutes, e.g., 1-2 typos)
- [x] Small (< 1 day)
- [ ] Medium (1-3 days, e.g., a new section)
- [ ] Large (1-2 weeks, e.g., a full rewrite)

## Are you willing to implement it?

<!--
Docs PRs are very welcome and easy to merge. If you can
submit a PR, it is more likely to be merged quickly.
-->

- [ ] Yes, I plan to submit a PR
- [ ] Yes, but I need help / mentorship
- [ ] No, but I'd be happy to review
- [ ] No, asking for someone else to implement

## Reviewer notes

<!--
Docs PRs benefit from specific reviewer focus. Tell the
reviewer what to look for:

  - "Please focus on technical accuracy — the wording is
    already clear."
  - "Please focus on tone — this is a beginner-facing
    section and I may have used too much jargon."
  - "Please focus on the new section 'Troubleshooting' —
    I want to make sure the 5 error messages I documented
    are the right ones to highlight."
  - "This is a translation; please verify the technical
    terms are translated consistently with the rest of
    the project."
-->

## Related issues / PRs

<!--
Link related discussions, duplicates, or prior art.
-->

- Related to #
- See also #
- Supersedes #

## Checklist

<!--
Tick what you've already done. Docs PRs with no ticks
will be closed as 'incomplete'.
-->

- [ ] I have searched existing issues and this is not a duplicate
- [ ] I have described a concrete change (not "improve docs")
- [ ] I have shown the rendered output (before vs after)
- [ ] I have run the spell / grammar / style check
- [ ] I have run the link / cross-reference check
- [ ] I have confirmed this is a docs-only PR (no code change)
- [ ] I have listed the affected files
- [ ] I have indicated whether I am willing to submit a PR