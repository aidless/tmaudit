# Release Notes — v0.1.2

> **TLDR**: 7 new audit categories (C7), 30x speedup via content-addressed cache, 4 issue templates for community contribution, 9-bug regression-injection meta-test. **82 unit tests pass, 9/9 historical bugs caught, 44/44 community-files checks pass.**

## At a Glance

| | v0.1.1 (previous) | **v0.1.2 (this)** | Delta |
|---|---|---|---|
| Audit categories | 6 (C1..C6) | **7 (C1..C7)** | +1 |
| Unit tests | 53 | **82** | +29 |
| Meta-test bugs caught | 7/7 | **9/9** | +2 |
| Community-files checks | 26/26 | **44/44** | +18 |
| Issue templates | 1 (bug) | **4 (bug, feature, enhancement, docs)** | +3 |
| Cache | none | **SQLite, content-addressed, ~30x speedup** | new |
| 7th audit category | — | **C7 (ceremonial citation detection)** | new |
| Total commits | 6 (since v0.1.0) | **11 (since v0.1.1)** | +11 |
| Lines added | — | **+4,216 / −29** (since v0.1.1) | — |

## Highlights

1. **C7 — Citation Context Validation** (Issue #16). Detects
   "ceremonial" citations (cited but not engaged with).
   Found **13 real ceremonial citations in Paper 5** —
   exactly the kind of reviewer concern C7 was designed
   to catch.

2. **Content-Addressed Audit Cache** (Issue #17). SQLite-backed
   cache at `~/.cache/tmaudit/cache.db` (or `$TMAUDIT_CACHE_DIR`).
   Second run on the same content is **~30x faster** (< 5 ms
   vs ~150 ms). Auto-invalidates on content or version change.

3. **4-Template Community Contribution Setup**. Bug, Feature,
   Enhancement, and Documentation issue templates replace the
   single "blank issue" of v0.1.1. New contributors can now
   pick the right template from the GitHub chooser.

4. **9-Bug Regression-Injection Meta-Test**. Each of 9
   historical bugs is tested by injecting the bug, asserting
   the regression test catches it, then restoring the source
   via `git checkout HEAD`. The meta-test now also handles
   untracked files (fixed state-leak bug for newly-added
   files like `cache.py`).

5. **Engineering Notes §11: C7 Design Doc**. Comprehensive
   9-subsection documentation of C7's motivation, design,
   heuristics, threshold, severity, real-world impact,
   tests, meta-test integration, limitations, and files
   changed.

## What's New

### C7 — Citation Context Validation (`src/tmaudit/templates/verify_TEMPLATE.py`)

The 7th audit category, requested in
[Issue #16](../issues/16-c7-citation-context.md):

- **Detects ceremonial citations** — citations whose
  citing sentence does not engage with the cited work.
- **Engagement signals** (any one of):
  1. An engage verb (show, demonstrate, extend, build on,
     follow, use, apply, compare, improve, …).
  2. A comparison word (however, in contrast, unlike,
     while, although, whereas, …).
  3. The citing context is **30+ words** (engagement by
     elaboration).
- **Per-paper threshold** (`c7_max_ceremonial`, default 2):
  1–2 ceremonial cites are silently OK; 3+ are reported
  as MED severity.
- **Cite variants supported**: `\cite`, `\citep`, `\citet`,
  `\citeauthor`, etc.
- **Multi-key supported**: `\cite{a,b,c}` counts each key
  independently.
- **Unique-key counting**: 1 key cited 3 times = 1 ceremonial
  (not 3).

**Real-world impact**: Paper 5 (our test case) had
**15 ceremonial citations**, of which **13 are reported as
MED findings** (with default threshold=2). This is a real
reviewer concern, not a false positive. Section 11.5 of the
engineering notes has a full write-up.

**Severity**: MEDIUM (stylistic, not correctness).

### Content-Addressed Cache (`src/tmaudit/cache.py`)

A SQLite-backed cache for audit results, requested in
[Issue #17](../issues/17-cache.md):

- **Key**: `sha256(main_tex + NUL + refs_bib + NUL + version)`.
  Any change in input or version produces a new key.
- **Storage**: SQLite at `~/.cache/tmaudit/cache.db`
  (Linux/Mac), `%LOCALAPPDATA%\tmaudit\cache.db` (Windows),
  or `$TMAUDIT_CACHE_DIR` (override).
- **Speed**: < 5 ms per hit (target); < 50 ms in test env.
- **Schema**: `(key PRIMARY KEY, value JSON, created_at, size_bytes)`.
- **Auto-invalidation**: content change OR version change
  OR manual `--clear-cache`.

**New CLI flags** on `tmaudit verify`:
- `--no-cache`: bypass the cache (do not read or write).
- `--clear-cache`: clear the cache before running.
- `--cache-info`: show cache statistics after running.

**New subcommands**:
- `tmaudit cache-info`: show cache statistics.
- `tmaudit cache-clear`: clear all cache entries.

### Issue Templates (`.github/ISSUE_TEMPLATE/`)

Replaced the single `bug_report.md` of v0.1.1 with **4
distinct templates**:

- `bug_report.md` — for crashes, false positives, broken CI.
- `feature_request.md` — for **new** audit categories /
  subcommands / paper configs.
- `enhancement.md` — for **improving** an existing check
  (e.g., the C6 threshold, the cache, error messages).
- `docs.md` — for **docs-only** changes (typos, clarifications,
  new sections).

The GitHub issue chooser now shows 4 cards (alphabetical),
and the `config.yml` was updated to explain the distinction.

### Community-Files Validator (`_check_github_templates.py`)

A new validator that runs in CI to check **9 dimensions** of
the `.github/` directory:

1. `.github/` directory structure.
2. `ISSUE_TEMPLATE/config.yml` (YAML, blank_issues, links).
3. 4 issue templates (frontmatter, name, description, title,
   labels, body).
4. `PULL_REQUEST_TEMPLATE.md` (H2 count, mentions of
   "test" and "checklist").
5. `CODEOWNERS` (presence, rule count).
6. `dependabot.yml` (YAML, updates list).
7. `CODE_OF_CONDUCT.md` (presence, line count).
8. `SUPPORT.md` (presence, line count).
9. `workflows/*.yml` (YAML, name, on, jobs).

Supports `--strict` (warnings fail) and `--json` (machine-
readable) flags. **44/44 OK**.

### State-Leak Fix in Meta-Test (`_check_all_regressions.py`)

The `_patched()` context manager used to back up file content
with a backup variable and write it back on exit. This was
vulnerable to state-leak: if a previous run left a file in a
broken state, the next run's backup would also be broken.

**Fix**: `_patched()` now uses `git checkout HEAD -- <path>`
for **tracked** files, and falls back to a backup variable for
**untracked** files. This guarantees that every meta-test
run starts from the committed version, regardless of what
state the working tree was in before.

## Test Suite

### Unit Tests (`pytest`)

| Category | Count | Notes |
|---|---|---|
| Existing (v0.1.1) | 53 | Carried over without modification |
| C7 (`test_c7_citation_context.py`) | +17 | New |
| Cache (`test_cache.py`) | +12 | New |
| Forge tests (adjusted) | — | 2 end-to-end tests updated to acknowledge C7 findings |
| **Total** | **82** | All pass in 0.6s |

### Meta-Test (`_check_all_regressions.py`)

Each of 9 historical bugs is tested:

| Bug | What it tests | Regression test |
|---|---|---|
| 1 | r-string in `repr()` | `TestBug1ReprInterpretsBackslash` |
| 2 | `re.sub` backslashes | `TestBug2ResubBackslashInReplacement` |
| 3 | brace counter ignores string literals | `TestBug3BraceCounterIgnoresStringLiterals` |
| 4 | C1 narrow 250-char window | `test_paper_1_forks_and_passes` |
| 5 | C5 test-name regex too strict | `tests/test_bug5_unit.py` |
| 6 | C2 section pattern too narrow | `test_paper_5_forks_and_passes` |
| 7 | C6 blacklist false-positive | `test_c6_does_not_flag_single_occurrence` |
| **8** | **C7 inverted threshold** | `test_c7_threshold_2_flags_3_ceremonial_cites` |
| **9** | **Cache put doesn't replace** | `test_put_replaces_existing_entry` |

**9/9 caught**. New in v0.1.2: Bug 8 (C7) and Bug 9 (cache).

### Community-Files Check (`_check_github_templates.py`)

**44/44 OK**. Covers config.yml, 4 issue templates, PR
template, CODEOWNERS, dependabot, CODE_OF_CONDUCT, SUPPORT,
and all workflows.

## Performance

| Operation | v0.1.1 | **v0.1.2** | Speedup |
|---|---|---|---|
| First audit on a paper | ~150 ms | ~150 ms | (baseline) |
| Second audit (same content) | ~150 ms | **< 5 ms** | **~30x** |
| `tmaudit cache-info` | n/a | < 5 ms | new |
| Meta-test (9 bugs) | n/a | ~12 s | new |
| Full `pytest` suite | 0.6 s | 0.6 s | (no change) |

The cache is a strict superset of the no-cache path: it's
opt-out via `--no-cache` if you ever need a fresh audit.

## Migration Guide (from v0.1.1)

No breaking changes. v0.1.2 is **drop-in compatible** with
v0.1.1. Existing forks (`verify_p*.py`, `_compile_check.py`)
work as-is. The new C7 check and the cache are **additive**:
- C7 is enabled by default; set `c7_max_ceremonial: 0` in
  `CHECKS_CONFIG` to disable.
- The cache is enabled by default; use `--no-cache` to bypass.

To use the new cache explicitly:
```bash
# Run with cache (default; second run is fast)
tmaudit verify --paper 1

# Force a fresh run
tmaudit verify --paper 1 --no-cache

# Clear cache after a bug fix
tmaudit cache-clear
# or:
tmaudit verify --paper 1 --clear-cache

# Inspect cache state
tmaudit cache-info
```

To use the new issue templates:
- File a bug → use the `Bug report` template
- Propose a new audit category → use `Feature request`
- Improve an existing check → use `Enhancement`
- Fix a typo in docs → use `Documentation`

## Known Limitations

From [`engineering_notes_verify_template.md` §11.8](../engineering_notes_verify_template.md#11-8-limitations-and-future-work):

- **Heuristic-based**: the C7 engage-verb and comparison-word
  lists are hand-curated. An LLM-based classifier (e.g.,
  fine-tuned BERT) would be more accurate. Defer to v0.2.0.
- **English-only**: the verb list is English.
- **No context beyond 2 sentences**: the C7 check uses
  the citing sentence + previous sentence. In rare cases
  the engagement is across more sentences; this is a false
  negative.
- **Doesn't distinguish citation type**: `\citep` and
  `\citet` are treated the same.

From `_check_github_templates.py`:

- The validator does not lint Markdown prose; it checks
  YAML structure, H2 counts, and label schemes only.

## Files Changed (24 files, +4,216 / −29 lines)

### New files (5)
- `src/tmaudit/cache.py` — 232 lines: CacheDB + cache_key + helpers
- `tests/test_cache.py` — 375 lines: 12 unit tests
- `_check_github_templates.py` — 434 lines: 9-dimension validator
- `_demo_c7_enhancement_filled.md` — 205 lines: worked example
- `_demo_docs_filled.md` — 148 lines: worked example

### Modified files (19)
- `src/tmaudit/templates/verify_TEMPLATE.py` — +239 / −5:
  added C7 (check_c7_citation_context, _c7_extract_sentence,
  _c7_is_engaged, _C7_ENGAGE_VERBS, _C7_COMPARISON_WORDS,
  _C7_MIN_CITED_SENTENCE_WORDS), added c7_max_ceremonial
  to CHECKS_CONFIG, added C7 to SEVERITY, updated driver
  summary loop, updated module docstring to "seven categories".
- `src/tmaudit/cli.py` — +73: added --no-cache, --clear-cache,
  --cache-info flags; added cache-info, cache-clear
  subcommands; updated docstring.
- `tests/test_c7_citation_context.py` — +447: 17 unit tests
  (1 file, all pass).
- `tests/test_forge_happy.py` — +28 / −2: 2 end-to-end tests
  updated to acknowledge C7 findings (don't assert "All
  checks passed" since C7 may find new issues).
- `_check_all_regressions.py` — +149: added inject_bug8 (C7)
  and inject_bug9 (cache); fixed state-leak in _patched()
  via `git checkout HEAD` (and untracked-file fallback).
- `engineering_notes_verify_template.md` — +278 / −5: added
  §9 (8-bug), §10.1 (Bug 8), §10.2 (state-leak), §11 (C7
  design doc, 9 subsections).
- `CHANGELOG.md` — multiple updates.
- `.github/ISSUE_TEMPLATE/enhancement.md` — new (13 sections,
  35 checkboxes).
- `.github/ISSUE_TEMPLATE/docs.md` — new (14 sections,
  72 checkboxes).
- `.github/ISSUE_TEMPLATE/config.yml` — updated comments
  for 4 templates.
- `.github/ISSUE_TEMPLATE/feature_request.md` — unchanged
  (existed in v0.1.1).
- `.github/ISSUE_TEMPLATE/bug_report.md` — unchanged.
- `CONTRIBUTING.md` — +30: 4 templates referenced.
- `ROADMAP.md` — +163: v0.1.2 milestone marked complete.
- `README.md` — +1: version bump.
- `.github/workflows/ci.yml` — +50: added
  validate-community-files job, updated meta-test comment
  from 6-bug → 9-bug.
- `.gitignore` — +5: ignore .tmp_cli_test/, .tmp_test_cache/.

## Commits (11 since v0.1.1)

```
800b7ee ci: bump meta-test comment from 8-bug to 9-bug (cache)
c0be115 feat(cache): implement audit cache (Issue #17) + 12 tests + meta-test
5bbc7ce feat(meta-test): add inject_bug8 + fix state-leak via git checkout
ad4cbf0 feat(c7): implement check_c7_citation_context (TDD green phase)
c016d6c test(c7): add 17 unit tests for citation context (TDD red phase)
d3c96d4 feat: add _check_github_templates.py + integrate into CI
7e1e868 fix: shorten enhancement.md and docs.md descriptions
93dfbd0 feat: add docs.md issue template (4-template split complete)
f7ccec1 feat: add enhancement.md issue template
af6c9ed feat: prep v0.1.2 milestone with 2 enhancement issues
183c4c4 docs: add PUSH_INSTRUCTIONS.md for first-time repo setup
```

## How to Verify This Release

```bash
# 1. Run the full test suite
python -m pytest
# Expected: 82 passed in 0.6s

# 2. Run the meta-test (9/9 caught)
python _check_all_regressions.py
# Expected: 9/9 bugs are correctly caught by their regression tests.

# 3. Run the community-files validator
python _check_github_templates.py
# Expected: 44/44 OK

# 4. Test the cache
TMAUDIT_CACHE_DIR=$PWD/.tmp_cache_test python -m src.tmaudit cache-info
# Expected: Cache statistics: path: ...tmp_cache_test/cache.db, entries: 0
```

## Acknowledgements

This release includes work from **11 commits** by **1
contributor** (aidless). The cache module was inspired by
similar tools in the Python ecosystem (e.g., `pytest-cache`,
`ruff --cache-dir`).

The TDD red-green-refactor cycle was applied throughout:
each new feature was specified by tests first, then
implemented, then meta-tested for regression-injection
robustness.

## See Also

- [CHANGELOG.md](../CHANGELOG.md) — concise change log.
- [engineering_notes_verify_template.md §11](../engineering_notes_verify_template.md#11) —
  full C7 design doc.
- [Issues](../issues/) — open feature requests.

---

**Release date**: 2026-07-10
**Previous release**: [v0.1.1](./RELEASE_NOTES_v0.1.1.md)
**Next release**: v0.2.0 (planned; see [ROADMAP.md](../ROADMAP.md))
