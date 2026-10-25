# Release checklist — v0.7.0

> **Status**: artifacts built and verified locally; **not uploaded**.
> **Prepared**: 2026-10-24
> **Supersedes**: `PYPI_PREP_v0.4.1_archive.md` (kept for the name check only).

Uploading to PyPI is irreversible — a version number cannot be reused or
withdrawn. Everything below §6 has been executed. §6 needs a human decision
and a credential, so it is deliberately left unticked.

## 1. Version agreement

Three places carry the version. All three said `0.7.0` at build time, and a
test now fails if any two disagree.

| Location | Value | Checked by |
|---|---|---|
| `pyproject.toml` `version` | 0.7.0 | `test_version_matches_pyproject` |
| `src/tmaudit/__init__.py` `__version__` | 0.7.0 | `test_version_prints_package_version` |
| `README.md` badge | 0.7.0 | manual |

This section exists because 0.5.1 shipped while `__version__` said `0.5.0`,
which put a wrong version string on every generated report.

## 2. Test and lint gates

| Gate | Command | Result |
|---|---|---|
| Full suite | `PYTHONPATH=src pytest` | **394 passed, 3 skipped** |
| Slow corpus regression | `PYTHONPATH=src pytest -m slow` | included above |
| Static check | `pyflakes src/tmaudit tests` | clean |
| Metadata | `twine check dist/*` | **PASSED** (both files) |

The 3 skips are platform/optional-dependency skips, not disabled tests.

## 3. Artifacts

```
dist/tmaudit-0.7.0-py3-none-any.whl    95,640 bytes
dist/tmaudit-0.7.0.tar.gz             156,039 bytes
```

Contents verified:

- sdist ships `src/tmaudit/{target,admission}.py`,
  `src/tmaudit/configs/target_config.py`, and the new tests.
- wheel ships `tmaudit/templates/verify_TEMPLATE.py` (73 KB) and the rest of
  the package data. Without this the forked script cannot be generated, and
  the failure would only appear after install.

## 4. Clean-room install

Installed the wheel into a fresh venv with no other packages:

```
python -m venv /tmp/clean-venv2
/tmp/clean-venv2/bin/pip install dist/tmaudit-0.7.0-py3-none-any.whl
/tmp/clean-venv2/bin/pip list      -> tmaudit 0.7.0   (nothing else)
```

`dependencies = []` is a real property of this package, not an aspiration:
the environment contained no third-party packages and `admission` still ran.

## 5. Functional smoke test (from the installed wheel, not the source tree)

| Check | Command | Result |
|---|---|---|
| Version flag | `tmaudit --version` | `tmaudit 0.7.0` |
| Admission, uncertified | `tmaudit admission --gain 7.3 --tasks 89` | NOT CERTIFIED, `upper=+32.10pp`, exit 1 |
| Admission, inversion | `tmaudit admission --required-tasks 7.3` | `tasks m >= 2,593` |
| External target | `tmaudit verify --target paper.toml` | exit 0, 5 LOW findings |

The external-target run used a paper directory created from scratch in
`/tmp` — a LaTeX file, a `.bib`, and a six-line TOML — with no reference to
`PAPER_CONFIGS`. This is the change that makes the tool usable by someone
who does not own paper 1 through 5.

## 6. Upload (NOT DONE — needs explicit approval)

```bash
# 1. Confirm the credential exists and points at the real PyPI.
#    A typo here uploads to TestPyPI, which is harmless but wastes a version.
twine upload --repository testpypi dist/*
# 2. Verify install from TestPyPI in a clean venv, then:
twine upload dist/*
```

Before running either command:

- [ ] Confirm `tmaudit` is still unclaimed or already owned by this account.
      The archive note records it FREE as of 2026-07-10, which is over three
      months stale.
- [ ] Confirm the `tmaudit` API token, not a password.
- [ ] Decide whether to tag `v0.7.0` and push the tag **before** uploading.
      The commit exists (`3d78dc7`) but is not pushed.

## 7. Known gaps after release

These do not block 0.7.0 and are recorded so they are not mistaken for done:

1. `tmaudit-audit/` (`ids.txt`, `list.xml`, `papers/`) is fetched corpus with
   no consuming tool.
2. The user's dev venv previously held a 0.5.1 install that shadowed the
   source tree; resolved locally with `pip install -e .`, but anyone with an
   old wheel installed will hit the same shadowing after this release.

The README "Self-audit" gap is now closed: a second round was added recording
the 25/25 external-path run (see §8).

## 8. Corpus evidence (external path, clean install)

The v0.5.0 self-audit ran through `PAPER_CONFIGS` — configs the author wrote.
That is not evidence for anyone else. This round ran the `--target` path,
which is what a stranger uses, over all 25 arXiv `cs.CL` sources, generating
a six-line config per paper:

| Metric | v0.5.1 | v0.7.0 |
|---|---|---|
| Completed the audit | 21 / 25 | **25 / 25** |
| Aborted (exit 2) | 4 | **0** |
| A category `[not observed]` | — | **0** |
| Bibliography resolved | 21 / 25 | **25 / 25** |

Bibliography filenames encountered and handled without any config edit:
`main.bbl` (62 keys), `bib.bib` (11), `references.bib` (46).

Caveat, stated plainly: exit 0 means "the audit ran and found no HIGH
finding", not "the paper is sound". The categories are heuristics and the
corpus is 25 papers from one arXiv listing.
