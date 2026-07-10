<!--
This is what a real GitHub issue would look like after the
author fills in the .github/ISSUE_TEMPLATE/docs.md template.

It would be filed via:

  gh issue create --body-file _demo_docs_filled.md

or copy-pasted into the GitHub web UI after clicking
"New issue" → "Documentation".

Use case: a small typo fix in CONTRIBUTING.md, line 87
("verison" → "version"). Real PR work, very low effort.
-->

---
name: Documentation
description: Propose a documentation-only change (typos, clarifications, new docs, restructured section). Use this for README, CONTRIBUTING, CHANGELOG, etc. — no code change.
title: "[Docs]: Fix typo 'verison' → 'version' in CONTRIBUTING.md"
labels: ["documentation", "needs-triage"]
assignees: []
---

## What documentation needs improvement?

Fix a typo in `CONTRIBUTING.md` line 87: "verison" → "version".

## Why is this a docs-only PR?

- [x] No `*.py` files
- [x] No `tests/` changes
- [x] No `src/tmaudit/` changes
- [x] No `.github/workflows/` changes
- [x] No `pyproject.toml` or other config changes

This PR changes exactly 1 word in 1 file.

## Type of change

- [x] Typo / grammar fix (1-2 word changes)

## Affected files

- [x] `CONTRIBUTING.md`

## Rendered output

Before:
```markdown
The pre-commit hook runs the test suite and the meta-test.
If you are on an older verison of Python (< 3.9), the hook
will warn but not abort.
```

After:
```markdown
The pre-commit hook runs the test suite and the meta-test.
If you are on an older version of Python (< 3.9), the hook
will warn but not abort.
```

Diff:
```diff
- older verison of Python
+ older version of Python
```

## Spell / grammar / style check

- [x] I have read the change aloud and it flows naturally
- [x] I have checked for common typos (e.g., "teh" instead
      of "the", "recieve" instead of "receive")
- [x] I have used consistent terminology (e.g., always
      "audit", not "scan" or "check")
- [x] I have followed the existing tone (terse, direct,
      no filler)
- [x] I have used the same heading style (H1 → H2 → H3,
      no skipping levels)
- [x] I have used sentence-case for headings, not Title Case
- [x] I have checked that all code blocks have a language
      tag (`bash`, `python`, `markdown`, etc.)
- [x] I have not introduced new jargon without defining it

## Link / cross-reference check

- [x] I have checked that all internal links resolve
      (e.g., `[CHANGELOG](./CHANGELOG.md)` points to a
      real file)
- [x] I have checked that all section anchors resolve
      (e.g., `## Section Name` exists and is reachable)
- [x] I have checked that all external links are still
      alive (e.g., the GitHub URL resolves to a real page)
- [x] I have not renamed any file that is referenced by
      another file (or, if I have, I have updated all
      references)
- [x] I have not moved any section that is referenced by
      another file (or, if I have, I have updated all
      references)

## Backwards compatibility

- [x] This change is purely internal (no external impact)

## Acceptance criteria

- [x] The change is implemented in the affected files
- [x] No other files are touched (only the ones ticked above)
- [x] The change is rendered correctly on GitHub
      (previewed locally if possible)
- [x] All internal links still resolve
- [x] All external links are still alive
- [x] The change follows the existing tone and structure
- [x] The change does not introduce new jargon
- [x] The change is consistent with the rest of the doc
      (e.g., same heading style, same terminology)
- [x] The CI is still green (no code was changed, so this
      should be automatic, but verify)

## Effort estimate

- [x] Trivial (< 30 minutes, e.g., 1-2 typos)

## Are you willing to implement it?

- [x] Yes, I plan to submit a PR

## Reviewer notes

This is a one-word typo fix. The PR can be merged as soon as
the CI is green (no review needed beyond a quick visual check
that the diff is correct). I have included the rendered
output (before / after) and the exact diff so the reviewer
can verify in 5 seconds.

## Related issues / PRs

- None.

## Checklist

- [x] I have searched existing issues and this is not a duplicate
- [x] I have described a concrete change (not "improve docs")
- [x] I have shown the rendered output (before vs after)
- [x] I have run the spell / grammar / style check
- [x] I have run the link / cross-reference check
- [x] I have confirmed this is a docs-only PR (no code change)
- [x] I have listed the affected files
- [x] I have indicated whether I am willing to submit a PR