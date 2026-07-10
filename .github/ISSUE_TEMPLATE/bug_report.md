---
name: Bug report
description: Report a bug, regression, or unexpected behaviour in tmaudit.
title: "[Bug]: "
labels: ["bug", "needs-triage"]
assignees: []
---

<!--
Thanks for filing a bug report!

Before you submit, please:
  1. Search existing issues to avoid duplicates.
  2. Try the latest commit on `main` (some bugs are fixed
     before a release).
  3. Run `pytest` and `python _check_all_regressions.py`
     locally; attach the full output below.

The text below is what you, the reporter, will see and edit.
HTML comments are hidden in the rendered issue.
-->

## Summary

<!--
One-sentence description of the bug.

GOOD: "verify_TEMPLATE.py crashes on Paper 4 because main.tex
       contains a non-ASCII comment in line 12."
BAD:  "it doesn't work"
-->

## Environment

<!--
Fill in the relevant fields. Delete any that don't apply.
-->

- **tmaudit version**: <!-- run `tmaudit --version` or `python -c "import tmaudit; print(tmaudit.__version__)"` -->
- **Python version**: <!-- run `python --version` -->
- **Operating system**: <!-- Windows 10 / macOS 14 / Ubuntu 22.04 / WSL2 / ... -->
- **Installation method**: <!-- `pip install -e .` / `pip install tmaudit==0.1.0` / `python tmaudit.pyz` / Docker / ... -->
- **Paper affected** (if any): <!-- Paper 1 / Paper 2 / ... / N/A -->

## Steps to reproduce

<!--
Numbered, minimal steps. Assume the reader has never seen your
machine. Avoid "etc." and "..." — be explicit.

GOOD:
  1. `cd F:/Research/TEMPLATE`
  2. `pip install -e .`
  3. `tmaudit verify --paper 4`
  4. Observe: audit crashes with `KeyError: 'c2_section_pattern'`
BAD:
  1. Run tmaudit
  2. See error
-->

1.
2.
3.

## Expected behaviour

<!--
What did you expect to happen?
-->

## Actual behaviour

<!--
What actually happened? Paste the full error message and
stack trace (if any) below.
-->

```
# Paste error output here
```

## Diagnostic output

<!--
Please run the following commands and paste the full output.
This is the most helpful single thing you can include — it
gives maintainers everything they need to reproduce.

  pytest -v
  python _check_all_regressions.py
  python tmaudit.pyz list    (if you use the .pyz)
  python tmaudit verify --paper N  (the failing command)
  tmaudit --version
-->

```text
# Paste command output here
```

## Severity

<!--
Choose one. If unsure, pick "Medium" and a maintainer will
adjust during triage.
-->

- [ ] **Critical** — `tmaudit` is unusable, blocks submission of a paper
- [ ] **High** — Major feature broken, but a workaround exists
- [ ] **Medium** — Minor feature broken or inconvenience
- [ ] **Low** — Cosmetic, typo, or "would be nice to have"

## Regression

<!--
Did this work in a previous version? If yes, when did it
break? Run `git log --oneline -- src/tmaudit/...` to find
the suspect commit.
-->

- [ ] This is a regression — it worked before
- [ ] This has never worked (or I'm not sure)

If a regression, the last version where it worked:
<!-- e.g., v0.1.0, or commit abc1234 -->

## Workarounds

<!--
Have you found a temporary workaround? If so, what is it?
(Workarounds are valuable — they unblock other users.)
-->

## Related issues / PRs

<!--
Link any related issues, PRs, or commits. The maintainer
will add cross-references during triage.
-->

- Related to #
- See also #

## Checklist

<!--
Tick what you've already done. Maintainers will not act on
an issue where none of these are checked.
-->

- [ ] I have searched existing issues and this is not a duplicate
- [ ] I have tried the latest commit on `main` (not just the latest release)
- [ ] I have run `pytest` and `_check_all_regressions.py` and attached the output
- [ ] I have included the full error message and stack trace
- [ ] I have provided minimal, numbered steps to reproduce