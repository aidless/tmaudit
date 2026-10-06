# tmaudit — Deploy & Quick Start

[![CI](https://github.com/aidless/tmaudit/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/tmaudit/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)
![Tests](https://img.shields.io/badge/tests-176%20passing-brightgreen)
![Meta--tests](https://img.shields.io/badge/meta--tests-12%2F12%20caught-success)
![Categories](https://img.shields.io/badge/audit%20categories-C1..C10-blue)
![PR%20Checks](https://img.shields.io/badge/PR%20checks-40%20checkboxes-blueviolet)
![Issues](https://img.shields.io/badge/issues-4%20templates-blueviolet)
![Security](https://img.shields.io/badge/security-policy%20in%20place-green)
![Version](https://img.shields.io/badge/version-0.5.0-blue)
![Roadmap](https://img.shields.io/badge/roadmap-through%20v0.5.0-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

This directory is a **deployable Python package** named `tmaudit`. It
ships three things in one place:

1. The **templates** for the three operational scripts that every
   `PAPER<N>_CONSOLIDATED/` directory needs
   (`verify_p<N>.py`, `_compile_check.py`,
   `_fix_abstract_unicode.py`).
2. The **per-paper configurations** (C1..C10 audit rules: C1–C7
   in v0.1.0–v0.2.0, plus C8 statistical power, C9 figure-caption,
   and C10 reproducibility in v0.3.0; abstract Unicode
   replacements) for Paper 1, 2, 3, 4, 5.
3. A **CLI** (`tmaudit`) that forks the templates into any paper
   directory and (optionally) runs them.

## Three ways to use it

### (A) Run the single-file `tmaudit.pyz` (zero install)

```bash
# on any machine with Python 3.9+
python tmaudit.pyz list
python tmaudit.pyz verify --paper 1
python tmaudit.pyz compile --paper 5
python tmaudit.pyz fix-unicode --paper 1
python tmaudit.pyz audit-all
```

The `.pyz` is a self-extracting Python zip archive; the user does not
need to `pip install` anything. The file is `~46 KB` and contains all
five `PAPER_CONFIGS` and all three templates.

This is the **recommended distribution form** for handing the tool
to a co-author or to the TMLR reviewers.

### (B) `pip install --editable .` (development)

```powershell
cd F:\Research\TEMPLATE
python -m pip install --editable . --break-system-packages
tmaudit list
tmaudit verify --paper 1
```

Edits to `src/tmaudit/templates/*.py` or
`src/tmaudit/configs/*.py` are picked up immediately on the next
`tmaudit` invocation. This is the **recommended form for ongoing
development** of the templates themselves.

### (C) `pip install .` (deployment to a venv)

```bash
python -m venv .venv
source .venv/bin/activate           # or .venv\Scripts\activate on Windows
pip install F:\Research\TEMPLATE
tmaudit list
```

This produces a `tmaudit` console-script entry in the venv. The
template and config files are inside the wheel.

## v0.3.0 highlights

**Released: 2026-07-10.** This release adds 3 new audit categories
(C8, C9, C10) and brings the project to **10 categories, 176 unit
tests, 12/12 meta-test bugs caught, 5/5 papers auditable**.

| Category | What it checks | Severity | Always runs? |
|---|---|---|---|
| **C1** (v0.1.0) | Symbol inline definition | HIGH | Yes |
| **C2** (v0.1.0) | Bonferroni consistency | HIGH | Yes |
| **C3** (v0.1.0) | Formalization of key concept | MEDIUM | Yes |
| **C4** (v0.1.0) | Self-citation threshold | MEDIUM | Yes |
| **C5** (v0.1.0) | Test-name d | MEDIUM | Yes |
| **C6** (v0.1.1) | Blacklist word frequency | LOW | Yes |
| **C7** (v0.1.2) | Ceremonial citation detection | MEDIUM | Yes |
| **C8** (v0.3.0) | **Statistical power** (d-mismatch, post-hoc power) | HIGH/MED | No (opt-in) |
| **C9** (v0.3.0) | **Figure-caption consistency** (4 sub-checks) | HIGH/MED | Yes (sub-check 3 opt-in) |
| **C10** (v0.3.0) | **Reproducibility** (availability, metadata, consistency) | HIGH/MED/LOW | Yes (sub-check 2 opt-in) |
| **C7-LLM** (v0.2.0) | LLM fallback for C7 borderline cases (opt-in via `TMAUDIT_LLM_*` env) | MEDIUM | No |

**v0.2.0 added** (still shipping): `audit-all --output report.md`
generates a single Markdown report covering all papers; the report
is uploaded as a CI artefact.

**v0.2.0 added** (still shipping): per-paper config for Paper 2,
Paper 3, Paper 4 (was placeholder in v0.1.1). All 5 papers
(P1..P5) are now auditable.

**Per-paper config** for v0.3.0: `c8_claimed_effects` (statistical),
`c9_figure_keywords` (figure-caption), `c10_reproducibility_claims`
(reproducibility). Empty list = opt-out (with graceful degradation
in C9 and C10).

See [`RELEASE_NOTES_v0.3.0.md`](./RELEASE_NOTES_v0.3.0.md) for the
full release notes and [`engineering_notes_verify_template.md`](./engineering_notes_verify_template.md)
§12 (C8+C10) and §13 (C9) for the design rationale.

## CLI reference

```text
tmaudit list                              # show all known paper configs
tmaudit verify --paper N [--dry-run]      # fork verify_pN.py + run audit
tmaudit compile --paper N [--dry-run]     # fork _compile_check.py + 4-pass build
tmaudit fix-unicode --paper N [--dry-run] # fork _fix_abstract_unicode.py
tmaudit audit-all [--start 1] [--end 5]   # verify all papers in a range
```

Every subcommand also accepts `--paper-dir PATH` to override the
default paper directory.

## The standard 3-step protocol for any new paper

```powershell
cd F:\Research\PAPER<N>_CONSOLIDATED

# 1. audit
tmaudit verify --paper N

# 2. fix abstract Unicode (if any finding)
tmaudit fix-unicode --paper N
tmaudit verify --paper N

# 3. compile
tmaudit compile --paper N
```

## Package layout

```
TEMPLATE/
├── pyproject.toml                            # build config
├── tmaudit.pyz                               # single-file distribution (46 KB)
├── README.md                                 # this file
├── engineering_notes_verify_template.md      # 6-bug engineering diary
├── _setup_pkg.py                             # one-time: copy templates into src/
├── _build_pyz.py                             # one-time: build tmaudit.pyz
├── _compile_appendix.py                      # LaTeX compile for the appendix
├── _regen_appendix.py                        # regenerate appendix_engineering.tex
├── _status.py                                # TEMPLATE/ state summary
└── src/
    └── tmaudit/                              # the actual package
        ├── __init__.py
        ├── __main__.py                       # `python -m tmaudit`
        ├── cli.py                            # argparse CLI
        ├── forge.py                          # template-substitution engine
        ├── templates/
        │   ├── __init__.py
        │   ├── verify_TEMPLATE.py            # ≈ 22 KB, ~400 lines
        │   ├── compile_check_TEMPLATE.py     # ≈ 4.5 KB
        │   └── fix_abstract_unicode_TEMPLATE.py  # ≈ 5 KB
        └── configs/
            ├── __init__.py                   # re-exports
            ├── paper_configs.py              # VERIFY_CONFIGS for paper 1..5
            └── compile_configs.py            # COMPILE_CONFIGS for paper 1..5
```

## Adding a new paper (e.g., Paper 6)

Edit **two** files:

1. `src/tmaudit/configs/paper_configs.py` — add a new entry to
   `PAPER_CONFIGS` (or `VERIFY_CONFIGS` after re-export). The fields
   are documented in the docstring at the top of that file.
2. `src/tmaudit/configs/compile_configs.py` — add a matching entry
   to `COMPILE_CONFIGS`. The fields are documented in the docstring
   there.

Then:

```powershell
python -m pip install --editable . --break-system-packages
python _build_pyz.py
tmaudit list               # confirm Paper 6 shows up
tmaudit verify --paper 6   # fork + run; will report any HIGH-severity
                           # issues caused by your config choices
```

## Verifying the .pyz is portable

```bash
# On the source machine:
python _build_pyz.py
# -> tmaudit.pyz (46 KB)

# Copy tmaudit.pyz to a fresh machine with no Python packages installed
# (only a base Python 3.9+ interpreter):
scp tmaudit.pyz other-host:/tmp/
ssh other-host 'python /tmp/tmaudit.pyz list'
# -> should print the same 5-paper table
```

The `.pyz` has **no external dependencies** (only the Python standard
library). It works on Linux, macOS, and Windows alike.

## Bug history

The **twelve historical bugs** encountered while building this
package are documented in
[`engineering_notes_verify_template.md`](./engineering_notes_verify_template.md).
Each bug has a dedicated regression test in
`tests/test_forge_happy.py`, `tests/test_bug5_unit.py`,
`tests/test_c6_threshold.py`, `tests/test_c7_citation_context.py`,
`tests/test_cache.py`, `tests/test_c10_reproducibility.py`,
`tests/test_c8_statistical_power.py`, and
`tests/test_c9_figure_caption.py`. The meta-test
(`_check_all_regressions.py`) injects each bug in turn, asserts the
regression test catches it, and restores the source. **12/12 bugs
are caught.**

The fix patterns (raw-string regex literals, brace-counting state
machines, non-letter-class regex, second/third-pass audit logic,
sentinel-character sub-string extraction, etc.) are all implemented
in `src/tmaudit/forge.py` and
`src/tmaudit/templates/verify_TEMPLATE.py`.

## Continuous integration

### Workflow

`.github/workflows/ci.yml` runs on every push and pull request.
It consists of **five** jobs:

1. **pytest** (matrix: Python 3.9, 3.10, 3.11, 3.12 on `ubuntu-latest`)
   — runs the **176-test** suite and uploads JUnit XML artifacts.
2. **meta-test** (Python 3.11) — runs `_check_all_regressions.py`
   to verify that each of the **12 regression tests** actually catches
   its target bug. Builds `tmaudit.pyz` and runs it as a smoke
   test.
3. **validate-community-files** (Python 3.11) — runs
   `_check_github_templates.py` to verify the `.github/`
   directory structure (4 issue templates, PR template, CODEOWNERS,
   dependabot.yml, CODE_OF_CONDUCT, SUPPORT, workflows).
4. **audit-all** (Python 3.11) — runs
   `tmaudit audit-all --start 1 --end 5 --output audit-report.md
   --no-cache` and uploads the Markdown report as a CI artefact.
5. **lint** (Python 3.11) — runs `pyflakes` on `src/tmaudit/`
   and `tests/`.

### Local validation (before pushing)

To run the same checks locally before pushing:

```bash
pip install -e . pytest pyflakes
pytest
python _check_all_regressions.py
python _build_pyz.py
python tmaudit.pyz list
python -m pyflakes src/tmaudit/ tests/
```

### Local CI simulation (`act` / `_act_*`)

The preferred tool for local CI simulation is
[nektos/act](https://github.com/nektos/act):

```bash
act -l                    # list jobs
act -j pytest             # run the pytest job
act -j meta-test          # run the meta-test job (after pytest)
act -j lint               # run the lint job
```

`act` requires `act` installed **and** a working Docker daemon.
If either is unavailable (e.g., on a restricted sandbox machine),
this repo ships two **fallback** simulators:

| Script | `act` equivalent | What it does |
|---|---|---|
| `_act_dryrun.py` | `act -n` (dry-run) | Parses `ci.yml`, expands the matrix, prints what each step would do. **No commands are executed.** |
| `_act_simulate.py` | `act` (real run) | Same as dryrun, but actually runs the `run:` steps via `subprocess`. Implements stubs for `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`. |

```bash
python _act_dryrun.py            # show what would be executed
python _act_dryrun.py --list     # show jobs only
python _act_simulate.py --list   # list jobs (act -l equivalent)
python _act_simulate.py --job pytest    # run pytest job
```

### CI simulation results

`_act_dryrun.py` was used to validate the workflow before
pushing. Results:

- ✅ `ci.yml` is valid YAML (parsed by PyYAML)
- ✅ **5 jobs**, 4 + 1 + 1 + 1 + 1 matrix rows, ~25 steps
- ✅ `meta-test` correctly depends on `pytest` (Kahn's algorithm topo sort)
- ✅ `matrix.python-version` substituted correctly into `${{ ... }}` expressions
- ✅ `if: always()` preserved on the upload-artifact step
- ✅ `with:` arguments (e.g., `cache: pip`, `cache-dependency-path: pyproject.toml`) preserved

The CI workflow's `run:` blocks are identical to commands
we have already executed successfully on the host:

| CI step | Local result |
|---|---|
| `python -m pip install -e .` | tmaudit installed ✅ |
| `python -m pip install pytest scipy` | deps installed ✅ |
| `python -m pytest` | **176 passed in ~7s** ✅ |
| `python _check_all_regressions.py` | **12/12 bugs caught** ✅ |
| `python _check_github_templates.py` | **44/44 OK** ✅ |
| `python -m src.tmaudit audit-all ...` | audit-report.md generated ✅ |
| `python -m src.tmaudit audit-all ...` | report uploaded as artefact ✅ |
| `python _build_pyz.py` | tmaudit.pyz built ✅ |
| `python tmaudit.pyz list` | 5 papers listed ✅ |
| `python -m pyflakes src/tmaudit/ tests/` | 0 errors ✅ |

### What `_act_*` cannot simulate

- `actions/setup-python@v5` cannot actually install a different
  Python version (the host has only one Python; the matrix
  includes 3.9/3.10/3.11/3.12). The simulator prints a
  warning but does not fail.
- `actions/upload-artifact@v4` is simulated by copying files
  to `_act_run/artifacts/<name>/`.
- The Docker isolation that real `act` provides is not present;
  steps run on the host shell.

### Pre-push hook recommendation

To enforce CI validation before every push:

```bash
# .git/hooks/pre-push
python _check_yaml.py && python _act_dryrun.py
```

The `_check_yaml.py` script validates `ci.yml` is parseable
and has the expected structure (catches YAML syntax errors
before pushing).

### Full evidence

For the full simulation transcript (including the 5 sandbox
issues encountered and how they were worked around), see
[`act_summary.md`](./act_summary.md).
