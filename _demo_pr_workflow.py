"""_demo_pr_workflow.py — simulate three realistic PR workflows
using the PULL_REQUEST_TEMPLATE.md.

This script:
  1. Loads the raw template.
  2. For each of three scenarios (bug fix, new paper, refactor),
     prints a "filled" PR body that demonstrates how the template
     is used in practice.
  3. Demonstrates GitHub's rendering (HTML comments stripped).
  4. Writes all three filled bodies into `pr_demo.md` as a
     permanent reference.
"""
import re
from pathlib import Path

ROOT = Path('F:/Research/TEMPLATE')
TEMPLATE = ROOT / '.github' / 'PULL_REQUEST_TEMPLATE.md'
OUTPUT = ROOT / 'pr_demo.md'


def render_github(text: str) -> str:
    """Simulate GitHub's PR body view by stripping HTML comments."""
    # Remove standalone comment paragraphs (multi-line `<!-- ... -->` blocks)
    out = re.sub(
        r'<!--[^\n]*\n(?:[^\n]*\n)*?-->',
        lambda m: '\n' * m.group(0).count('\n'),
        text,
    )
    # Remove inline comments (e.g., `<!-- describe below -->`)
    out = re.sub(r'<!--[^>]*-->', '', out)
    return out


def section(title: str) -> None:
    print()
    print('=' * 78)
    print(title)
    print('=' * 78)


def subsection(title: str) -> None:
    print()
    print('-' * 78)
    print(title)
    print('-' * 78)


# ---------------------------------------------------------------------------
# Read the template
# ---------------------------------------------------------------------------
raw_template = TEMPLATE.read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# Scenario 1: Bug fix PR (regression test for Paper 5 c2_section_pattern)
# ---------------------------------------------------------------------------
SCENARIO_1 = """## What

Add a per-paper `c2_section_pattern` regression test that catches a
re-introduction of Bug 6 (Paper 5's `Statistical Protocol` section
not matched by the audit).

## Why

Bug 6 was discovered when the audit failed to recognise the
`Statistical Protocol` section in Paper 5. The fix added a
per-paper `c2_section_pattern`, but no test directly verifies this
behaviour. A future refactor of `verify_TEMPLATE.py` could
inadvertently drop the per-paper pattern and the bug would
recur silently.

Fixes #6

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
- [ ] `src/tmaudit/templates/verify_TEMPLATE.py`
- [ ] `src/tmaudit/templates/compile_check_TEMPLATE.py`
- [ ] `src/tmaudit/templates/fix_abstract_unicode_TEMPLATE.py`
- [ ] `src/tmaudit/configs/paper_configs.py`
- [ ] `src/tmaudit/configs/compile_configs.py`
- [x] `tests/`
- [ ] `hooks/`
- [ ] `.github/workflows/ci.yml`
- [ ] Documentation (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`, `act_summary.md`)
- [ ] Other:

## Pre-merge checklist

### Automated checks (CI runs these)

- [x] `pytest` passes locally (46 tests, ~0.4s)
- [x] `python _check_all_regressions.py` reports 6/6 caught
- [x] `python _build_pyz.py` produces a working `tmaudit.pyz`
- [x] `python tmaudit.pyz list` lists the correct papers
- [x] `python _check_yaml.py` reports `ci.yml` is valid
- [x] GitHub Actions CI is green on this branch
- [x] Pre-commit hook passed (or `--no-verify` was justified in PR description)

### Manual checks (the author must verify)

- [x] I have read [`CONTRIBUTING.md`](../blob/main/CONTRIBUTING.md) and followed its guidance
- [x] If this PR adds a new audit category, a sample paper (Paper 1 or 5) still passes
- [N/A] If this PR changes `verify_TEMPLATE.py`, the audit output is identical on a known paper
- [x] If this PR changes `paper_configs.py`, the per-paper audit still produces 0 findings
- [x] If this PR adds a regression test for a bug, I have verified the test **fails** when the bug is injected (using `_check_all_regressions.py`)
- [x] If this PR fixes a bug, the new test is referenced from `engineering_notes_verify_template.md`
- [N/A] If this PR adds a paper (Paper 6+), the `TestEndToEndAudit` test for it is added
- [N/A] If this PR changes public API, the CLI still works (`tmaudit --help`, `tmaudit list`, `tmaudit verify --paper N`)
- [x] If this PR changes the audit logic, I have manually re-run the audit on Paper 1 and confirmed 0 findings
- [x] `CHANGELOG.md` has an entry for this change under the next version

### Documentation

- [x] `README.md` is updated (if user-facing behavior changes)
- [N/A] `CONTRIBUTING.md` is updated (if dev workflow changes)
- [x] `CHANGELOG.md` is updated
- [x] `engineering_notes_verify_template.md` is updated (if a bug is fixed or a new bug is discovered)

## Test plan

Added `tests/test_forge_happy.py::TestEndToEndAudit::test_paper_5_forks_and_passes`
and used it as the meta-test target for Bug 6. The test runs
the actual `tmaudit verify --paper 5` workflow.

```text
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

  6/6 bugs are correctly caught by their regression tests.

=== Final sanity: full test suite should pass ===
  OK: full test suite passes (rc=0)
```

## Screenshots / output

```
$ tmaudit verify --paper 5
============================================================
Running audit on: F:/Research/PAPER5_CONSOLIDATED
  C1: 0 finding(s)
  C2: 0 finding(s)
  C3: 0 finding(s)
  C4: 0 finding(s)
  C5: 0 finding(s)
  C6: 0 finding(s)
All checks passed. 0 finding(s).
```

## Breaking changes

None.

## Related issues / PRs

- Fixes #6 (Bug 6 from engineering_notes_verify_template.md)
- See also: PR #14 (initial Bug 6 fix without meta-test)

## Reviewer notes

The test is intentionally NOT a pure unit test -- it actually
forks and runs `tmaudit verify --paper 5`, which means it
depends on Paper 5's `main.tex` and `refs.bib` being present
in the repo. This is a deliberate trade-off: a pure unit
test would not catch the bug if someone refactored the
substitution logic and broke the per-paper pattern handling.
"""


# ---------------------------------------------------------------------------
# Scenario 2: New paper PR (Paper 6)
# ---------------------------------------------------------------------------
SCENARIO_2 = """## What

Add audit support for Paper 6 (a new TMLR submission about
LLM evaluation under bounded memory).

## Why

Paper 6 is the next paper in the series. It uses the same
TTRL framework as Papers 1, 3, 4, 5, but introduces a new
empirical family (memory-bounded evaluation). The audit
config needs a new entry to handle the new family and a
new c3_concept ("bounded-memory trade-off").

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [x] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (existing functionality changes behavior)
- [ ] Refactor (no functional change, just code cleanup)
- [ ] Documentation only
- [ ] Test only (no production code change)
- [ ] Build / CI only (no production code change)

## Affected components

- [ ] `src/tmaudit/forge.py`
- [ ] `src/tmaudit/cli.py`
- [ ] `src/tmaudit/templates/verify_TEMPLATE.py`
- [ ] `src/tmaudit/templates/compile_check_TEMPLATE.py`
- [ ] `src/tmaudit/templates/fix_abstract_unicode_TEMPLATE.py`
- [x] `src/tmaudit/configs/paper_configs.py`
- [ ] `src/tmaudit/configs/compile_configs.py`
- [x] `tests/`
- [ ] `hooks/`
- [ ] `.github/workflows/ci.yml`
- [x] Documentation (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`, `act_summary.md`)
- [ ] Other:

## Pre-merge checklist

### Automated checks (CI runs these)

- [x] `pytest` passes locally (46 tests, ~0.4s)
- [x] `python _check_all_regressions.py` reports 6/6 caught
- [x] `python _build_pyz.py` produces a working `tmaudit.pyz`
- [x] `python tmaudit.pyz list` lists the correct papers
- [x] `python _check_yaml.py` reports `ci.yml` is valid
- [x] GitHub Actions CI is green on this branch
- [x] Pre-commit hook passed (or `--no-verify` was justified in PR description)

### Manual checks (the author must verify)

- [x] I have read [`CONTRIBUTING.md`](../blob/main/CONTRIBUTING.md) and followed its guidance
- [x] If this PR adds a new audit category, a sample paper (Paper 1 or 5) still passes
- [N/A] If this PR changes `verify_TEMPLATE.py`, the audit output is identical on a known paper
- [x] If this PR changes `paper_configs.py`, the per-paper audit still produces 0 findings
- [N/A] If this PR adds a regression test for a bug, I have verified the test **fails** when the bug is injected (using `_check_all_regressions.py`)
- [N/A] If this PR fixes a bug, the new test is referenced from `engineering_notes_verify_template.md`
- [x] If this PR adds a paper (Paper 6+), the `TestEndToEndAudit` test for it is added
- [x] If this PR changes public API, the CLI still works (`tmaudit --help`, `tmaudit list`, `tmaudit verify --paper N`)
- [x] If this PR changes the audit logic, I have manually re-run the audit on Paper 1 and confirmed 0 findings
- [x] `CHANGELOG.md` has an entry for this change under the next version

### Documentation

- [x] `README.md` is updated (if user-facing behavior changes)
- [N/A] `CONTRIBUTING.md` is updated (if dev workflow changes)
- [x] `CHANGELOG.md` is updated
- [N/A] `engineering_notes_verify_template.md` is updated (if a bug is fixed or a new bug is discovered)

## Test plan

Added `tests/test_forge_happy.py::TestEndToEndAudit::test_paper_6_forks_and_passes`.

```text
$ tmaudit verify --paper 6
============================================================
Running audit on: F:/Research/PAPER6_CONSOLIDATED
  C1: 0 finding(s)
  C2: 0 finding(s)
  C3: 0 finding(s)
  C4: 0 finding(s)
  C5: 0 finding(s)
  C6: 0 finding(s)
All checks passed. 0 finding(s).

$ tmaudit list
Known paper configurations:
  Paper 1    OK  OK   F:/Research/PAPER1_CONSOLIDATED
  Paper 2    OK  -    F:/Research/PAPER2_CONSOLIDATED
  Paper 3    OK  -    F:/Research/PAPER3_CONSOLIDATED
  Paper 4    OK  -    F:/Research/PAPER4_CONSOLIDATED
  Paper 5    OK  OK   F:/Research/PAPER5_CONSOLIDATED
  Paper 6    OK  OK   F:/Research/PAPER6_CONSOLIDATED  <-- NEW
```

## Screenshots / output

Audit report for Paper 6 (full output of `tmaudit verify --paper 6`):
attached as `paper6_audit.txt` in the PR.

## Breaking changes

None.

## Related issues / PRs

- Tracks the "add paper 6" milestone
- See also: PR #11 (initial 5-paper support), PR #14 (Bug 6 fix)

## Reviewer notes

I'm uncertain about the choice of `c2_abstract_k_allowed = [3]`
for Paper 6. The abstract mentions both `n=30` and `n=100`
trials. Per CONTRIBUTING.md, `c2_abstract_k_allowed` is the
list of k values acceptable in the abstract. Paper 1's config
uses `[3]` (k=3 is the main family). I went with `[3]` for
Paper 6 to match, but if Paper 6 actually uses 5 families
(2 conditions x 3 settings), please flag this in review.
"""


# ---------------------------------------------------------------------------
# Scenario 3: Refactor PR
# ---------------------------------------------------------------------------
SCENARIO_3 = """## What

Extract the `_patched` context manager from `_check_all_regressions.py`
into a new shared module `_patched.py` so it can be reused by
`_act_simulate.py` and future meta-tests.

## Why

The same "backup file, run code, restore on exit" pattern was
duplicated in `_check_all_regressions.py` and
`_act_simulate.py`. Extracting it removes ~30 lines of
duplication and makes the failure semantics easier to reason
about (one place to fix bugs in the restore logic).

The behaviour is **unchanged** -- all 46 tests still pass and
all 6 meta-tests still catch their bugs. This is a pure
refactor.

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (existing functionality changes behavior)
- [x] Refactor (no functional change, just code cleanup)
- [ ] Documentation only
- [ ] Test only (no production code change)
- [ ] Build / CI only (no production code change)

## Affected components

- [x] `src/tmaudit/forge.py`
- [ ] `src/tmaudit/cli.py`
- [ ] `src/tmaudit/templates/verify_TEMPLATE.py`
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

- [x] `pytest` passes locally (46 tests, ~0.4s)
- [x] `python _check_all_regressions.py` reports 6/6 caught
- [x] `python _build_pyz.py` produces a working `tmaudit.pyz`
- [x] `python tmaudit.pyz list` lists the correct papers
- [x] `python _check_yaml.py` reports `ci.yml` is valid
- [x] GitHub Actions CI is green on this branch
- [x] Pre-commit hook passed (or `--no-verify` was justified in PR description)

### Manual checks (the author must verify)

- [x] I have read [`CONTRIBUTING.md`](../blob/main/CONTRIBUTING.md) and followed its guidance
- [x] If this PR adds a new audit category, a sample paper (Paper 1 or 5) still passes
- [N/A] If this PR changes `verify_TEMPLATE.py`, the audit output is identical on a known paper
- [N/A] If this PR changes `paper_configs.py`, the per-paper audit still produces 0 findings
- [N/A] If this PR adds a regression test for a bug, I have verified the test **fails** when the bug is injected (using `_check_all_regressions.py`)
- [N/A] If this PR fixes a bug, the new test is referenced from `engineering_notes_verify_template.md`
- [N/A] If this PR adds a paper (Paper 6+), the `TestEndToEndAudit` test for it is added
- [x] If this PR changes public API, the CLI still works (`tmaudit --help`, `tmaudit list`, `tmaudit verify --paper N`)
- [x] If this PR changes the audit logic, I have manually re-run the audit on Paper 1 and confirmed 0 findings
- [x] `CHANGELOG.md` has an entry for this change under the next version

### Documentation

- [x] `README.md` is updated (if user-facing behavior changes)
- [N/A] `CONTRIBUTING.md` is updated (if dev workflow changes)
- [x] `CHANGELOG.md` is updated
- [N/A] `engineering_notes_verify_template.md` is updated (if a bug is fixed or a new bug is discovered)

## Test plan

```text
$ pytest
..............................................                           [100%]
46 passed in 0.35s

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

  6/6 bugs are correctly caught by their regression tests.
```

No test changes -- the refactor is verified by the existing
tests + meta-test both still passing.

## Screenshots / output

N/A (no user-visible change).

## Breaking changes

None -- the public API of `tmaudit.forge` and `tmaudit.cli` is
unchanged. The only change is internal: `_check_all_regressions.py`
now imports `_patched` from a shared module.

## Related issues / PRs

- Refs #23 (technical-debt tracker for code duplication)

## Reviewer notes

I considered putting `_patched.py` in `src/tmaudit/`
(production code) vs at the repo root (tooling). I went with
the repo root because:
  1. `_patched` is only used by meta-tests and CI tooling,
     not by `tmaudit` itself.
  2. Keeping it out of the installed package keeps
     `pip install tmaudit` lean.
  3. The hook scripts (`hooks/pre-commit`, `_check_yaml.py`,
     `_act_*.py`) all live at the repo root already.

Happy to move it to `src/tmaudit/_internal/` if you'd prefer
the production/test split to match Python packaging
conventions. The behaviour is the same either way.
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
section('PART 1: THE RAW TEMPLATE (what the author sees when they open the file)')

subsection('Raw template (first 30 lines)')
for line in raw_template.splitlines()[:30]:
    print(line)

print()
print(f'(Total: {len(raw_template.splitlines())} lines, '
      f'{len(raw_template)} chars)')


section('PART 2: GITHUB RENDERED VERSION (what reviewers see in the PR body)')

rendered = render_github(raw_template)
for line in rendered.splitlines()[:50]:
    print(line)
print('... (etc)')
print()
print(f'After stripping HTML comments: {len(rendered.splitlines())} lines, '
      f'{len(rendered)} chars')
print(f'Removed {len(raw_template.splitlines()) - len(rendered.splitlines())} '
      f'lines of HTML comments.')


section('PART 3: SCENARIO 1 -- BUG FIX PR')
print(SCENARIO_1)

n_total = SCENARIO_1.count('- [ ]') + SCENARIO_1.count('- [x]')
n_checked = SCENARIO_1.count('- [x]')
n_na = SCENARIO_1.count('[N/A]')
n_remaining = n_total - n_checked - n_na
subsection('Checkbox count for scenario 1')
print(f'  Total checkboxes:   {n_total}')
print(f'  Checked:            {n_checked}')
print(f'  N/A:                {n_na}')
print(f'  Unchecked:          {n_remaining}')


section('PART 4: SCENARIO 2 -- NEW PAPER PR')
print(SCENARIO_2)

n_total = SCENARIO_2.count('- [ ]') + SCENARIO_2.count('- [x]')
n_checked = SCENARIO_2.count('- [x]')
n_na = SCENARIO_2.count('[N/A]')
n_remaining = n_total - n_checked - n_na
subsection('Checkbox count for scenario 2')
print(f'  Total checkboxes:   {n_total}')
print(f'  Checked:            {n_checked}')
print(f'  N/A:                {n_na}')
print(f'  Unchecked:          {n_remaining}')


section('PART 5: SCENARIO 3 -- REFACTOR PR')
print(SCENARIO_3)

n_total = SCENARIO_3.count('- [ ]') + SCENARIO_3.count('- [x]')
n_checked = SCENARIO_3.count('- [x]')
n_na = SCENARIO_3.count('[N/A]')
n_remaining = n_total - n_checked - n_na
subsection('Checkbox count for scenario 3')
print(f'  Total checkboxes:   {n_total}')
print(f'  Checked:            {n_checked}')
print(f'  N/A:                {n_na}')
print(f'  Unchecked:          {n_remaining}')


section('SUMMARY: checkbox counts across all 3 scenarios')

print(f'  {"Scenario":<20}  {"Total":<8}  {"Checked":<10}  {"N/A":<6}  {"Unchecked"}')
print(f'  {"-"*20}  {"-"*8}  {"-"*10}  {"-"*6}  {"-"*9}')
for label, text in [
    ('1. Bug fix', SCENARIO_1),
    ('2. New paper', SCENARIO_2),
    ('3. Refactor', SCENARIO_3),
]:
    n_total = text.count('- [ ]') + text.count('- [x]')
    n_checked = text.count('- [x]')
    n_na = text.count('[N/A]')
    n_remaining = n_total - n_checked - n_na
    print(f'  {label:<20}  {n_total:<8}  {n_checked:<10}  {n_na:<6}  {n_remaining}')


# Write a permanent demo file
demo_content = f'''# PR Demo -- Three Realistic PRs Using the Template

This file demonstrates how `.github/PULL_REQUEST_TEMPLATE.md` is
used in practice. It is generated by `_demo_pr_workflow.py`.

---

## How GitHub renders the template

GitHub strips `<!-- HTML comments -->` from the rendered PR body
but keeps everything else (heading, placeholder text, checkboxes).
The template uses HTML comments to embed "how to fill in this
section" guidance that the author sees when they open the file
but the reviewer does not see in the PR body.

Total lines in template: {len(raw_template.splitlines())}
Lines after HTML-comment strip (what reviewers see): {len(rendered.splitlines())}

---

## Scenario 1 -- Bug fix PR

40 checkboxes total. Most checked, some N/A, very few unchecked.

{SCENARIO_1}

---

## Scenario 2 -- New paper PR

40 checkboxes total. Most checked, some N/A, very few unchecked.

{SCENARIO_2}

---

## Scenario 3 -- Refactor PR

40 checkboxes total. Most checked, some N/A, very few unchecked.

{SCENARIO_3}
'''

OUTPUT.write_text(demo_content, encoding='utf-8')
print()
print(f'Wrote {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)')

# Clean up the broken backup
backup = ROOT / '_demo_pr_workflow_backup.py'
if backup.exists():
    backup.unlink()
    print(f'Removed {backup.name}')

print()
print('Done.')