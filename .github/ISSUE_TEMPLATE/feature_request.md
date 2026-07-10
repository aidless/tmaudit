---
name: Feature request
description: Propose a new feature, audit category, or improvement to tmaudit.
title: "[Feature]: "
labels: ["enhancement", "needs-triage"]
assignees: []
---

<!--
Thanks for proposing a feature!

A good feature request answers four questions:
  1. WHAT do you want to add? (specific change)
  2. WHY does it matter? (use case / business motivation)
  3. WHAT ALTERNATIVES have you considered? (e.g., workarounds)
  4. HOW does it fit the project? (scope, breaking changes)

The maintainer will review during the next triage cycle
(usually within 1 week). If accepted, it will be added to
the project backlog.
-->

## What do you want?

<!--
Describe the feature in 1-3 sentences. Be specific.

GOOD: "Add a `tmaudit fix` subcommand that automatically
       applies the recommended fix for each C1..C6 finding,
       rather than just reporting them."
BAD:  "Make it better."
-->

## Why does it matter?

<!--
What real problem does this solve? Who benefits?

GOOD: "I currently run `tmaudit verify --paper 1` and then
       manually edit main.tex to fix each finding. With
       5 papers, this takes 2 hours. An auto-fix would
       cut this to minutes."
BAD:  "It would be cool."
-->

## Use case

<!--
Describe a concrete scenario. Walk through the user's
journey with the new feature.

  - Who is the user? (paper author, reviewer, etc.)
  - What is their workflow today?
  - How does the new feature improve it?
-->

## Proposed solution

<!--
How do you imagine this should work? Sketch the CLI,
API, or config changes. If you can, write a short
example of what the user would type.

GOOD: "Add a new subcommand:
        tmaudit fix --paper 1 --auto-apply
       which would edit main.tex in place to resolve
       each C1..C6 finding that has a known fix."

If you have a code sketch, paste it below.
-->

## Alternatives considered

<!--
What other approaches have you considered? Why is the
proposed solution better?

GOOD: "I considered a separate `tmaudit-fix` package,
       but that would fragment the toolchain. An
       integrated subcommand keeps the surface small."
-->

## Scope

<!--
How big is this change? Does it affect public API?
-->

- [ ] Purely additive (no existing functionality changes)
- [ ] Internal refactor (no public API change)
- [ ] Public API change (breaking — list in the section below)

### Breaking changes

<!--
If you checked "Public API change" above, describe:
  - What changes?
  - Who is affected?
  - What is the migration path?
-->

## Affected components

<!--
Tick the files / modules this feature would touch.
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
- [ ] Documentation (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`, `act_summary.md`)
- [ ] Other: <!-- describe below -->

## Effort estimate

<!--
Optional. If you have a rough idea of effort, share it.
Maintainers will refine during triage.
-->

- [ ] Small (< 1 day)
- [ ] Medium (1-3 days)
- [ ] Large (1-2 weeks)
- [ ] X-Large (> 2 weeks)

## Are you willing to implement it?

<!--
Maintainers prioritize PRs over plain requests. If you
can submit a PR, the feature is much more likely to be
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

## Checklist

<!--
Tick what you've already done. Maintainers will not act
on a request where none of these are checked.
-->

- [ ] I have searched existing issues and this is not a duplicate
- [ ] I have described a concrete use case (not "would be nice")
- [ ] I have considered alternatives
- [ ] I have described how this fits the project scope
- [ ] I have indicated whether I am willing to submit a PR