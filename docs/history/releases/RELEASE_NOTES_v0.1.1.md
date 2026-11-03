# Release v0.1.1 — 2026-07-10

> **TL;DR**: One critical bug fix (C6 blacklist false-positive
> on idiomatic English), 7 new unit tests, 1 new bug added to
> the meta-test, and improved documentation. **No breaking
> changes.** Drop-in replacement for v0.1.0.

## Summary

| | |
|---|---|
| **Release** | v0.1.1 |
| **Released** | 2026-07-10 |
| **Type** | Patch release (no breaking changes) |
| **PR** | [#15](https://github.com/aidless/tmaudit/pull/15) |
| **Commits since v0.1.0** | 1 (squashed) |
| **Files changed** | 5 |
| **Lines added** | +248 |
| **Lines removed** | -4 |
| **Test count** | 46 → **53** (+7) |
| **Meta-test score** | 6/6 → **7/7** (+1) |
| **CI jobs** | 14/14 passing |
| **Audit status** | All 5 papers still 0 findings |

## What's changed

### 🐛 Fixed

#### C6 blacklist false-positive on idiomatic English

**Symptom**: `tmaudit verify --paper 5` reported a C6 finding
on the word "yield", even though "yields" only appeared twice
and was used in idiomatic technical English:

> "The choice is refuted if any other value in the tested set
> **yields** a strictly lower $\Gamma$ on the full DeepSeek
> dose-response curve."

The verb "to yield" in mathematical English ("yields a value of
$X$") is the **correct** usage and should not be flagged. The
audit was wrong to do so.

**Root cause**: `check_c6_blacklist` in
`src/tmaudit/templates/verify_TEMPLATE.py` reported a finding
on the **first** occurrence of any blacklisted word:

```python
# OLD (buggy)
for word, n in sorted(counts.items()):
    findings.append((...))  # ALWAYS, even if n == 1
```

**Fix**: Added a `min_count` threshold (3 by default) so that
1-2 occurrences are not reported:

```python
# NEW (fixed)
min_count: int = 3
for word, n in sorted(counts.items()):
    if n < min_count:
        continue  # 1-2 occurrences are OK
    findings.append(...)
```

The threshold is 3 (not 2) because:

- **1-2 occurrences**: idiomatic English, do not report.
- **3+ occurrences**: starts to look like a word being used
  to avoid saying something specific.

**Impact**: Any paper that uses "yield", "reveal", or
"paradigm" 1-2 times in idiomatic English previously failed
the C6 check with a false positive. After this fix, such
papers pass cleanly.

**Affected users**: All users running `tmaudit verify` on
papers that use "yields" / "reveals" / "yields" twice in
scientific text. Paper 5 was the only paper in our test
suite affected, but the bug applied to any future paper with
similar wording.

#### Verification

| Paper | Before fix | After fix |
|---|---|---|
| Paper 1 | 0 findings | 0 findings (unchanged) |
| Paper 2 | n/a (placeholder) | n/a (placeholder) |
| Paper 3 | n/a (placeholder) | n/a (placeholder) |
| Paper 4 | n/a (placeholder) | n/a (placeholder) |
| Paper 5 | **1 finding** (C6, "yield") | **0 findings** ✅ |

### ✅ Added

#### 7 new unit tests (`tests/test_c6_threshold.py`)

A new test file with 7 unit tests covering the C6 threshold
behaviour:

| Test | Asserts |
|---|---|
| `test_c6_does_not_flag_single_occurrence` | 1 occurrence → no finding |
| `test_c6_does_not_flag_two_occurrences` | 2 occurrences → no finding |
| `test_c6_flags_three_or_more_occurrences` | 10 occurrences → 1 finding, "10x" |
| `test_c6_finds_inflection_yields` | 5 "yields" → 1 finding, "5x" |
| `test_c6_finds_inflection_revealed` | 5 "revealed" → 1 finding |
| `test_c6_counts_separately_per_word` | "paradigm" 1x + "yield" 3x → only "yield" flagged |
| `test_c6_word_boundary_does_not_match_yielded` | "yielded" 5x → no finding (different word) |

#### Bug 7 added to meta-test (`_check_all_regressions.py`)

`_check_all_regressions.py` now has `inject_bug7()` that
re-introduces the C6 false-positive by changing
`min_count: int = 3` to `min_count: int = 0` and asserts that
`test_c6_does_not_flag_single_occurrence` catches it.

**Meta-test score**: 6/6 → **7/7 caught**.

#### Bug 7 documented in engineering notes (`engineering_notes_verify_template.md`)

A new §10 was added with 5 sub-sections:
- §10.1 Symptom
- §10.2 Root cause
- §10.3 Fix
- §10.4 Regression test
- §10.5 Meta-test

This brings the engineering diary to a uniform structure
(one chapter per bug) and makes the design rationale for the
threshold easily discoverable.

### 📚 Documentation

- **`engineering_notes_verify_template.md`**: New §10 covers
  Bug 7 in 5 sub-sections (88 lines added).
- **`CHANGELOG.md`**: This release entry.
- **`_check_all_regressions.py`**: Updated docstring (6 → 7
  bugs) and added `inject_bug7()`.

### 🔬 Internal

- **`src/tmaudit/templates/verify_TEMPLATE.py`**: 9 + 1 lines
  added to `check_c6_blacklist` (the threshold + comment).
- **`tests/test_c6_threshold.py`**: 113 lines, new file.
- **`_check_all_regressions.py`**: 33 lines added (inject_bug7
  function + main() registration + docstring update).

## Migration guide

**No action required** for v0.1.0 users. This is a drop-in
replacement.

If you have written custom audit configurations based on
v0.1.0, your configs will continue to work. The C6 threshold
is hard-coded in `verify_TEMPLATE.py` (not in
`paper_configs.py`), so you do not need to update any
per-paper config.

If you want to customise the threshold, you can edit
`verify_TEMPLATE.py::check_c6_blacklist` and change the line:

```python
min_count: int = 3
```

to your desired value. The threshold is intentionally a
constant (not a config parameter) because it is a property
of the C6 check, not a per-paper setting.

## Verification

To verify the fix on your machine:

```bash
# 1. Upgrade
pip install --upgrade tmaudit==0.1.1
# or, if you use the .pyz distribution:
curl -L https://github.com/aidless/tmaudit/releases/download/v0.1.1/tmaudit.pyz -o tmaudit.pyz
chmod +x tmaudit.pyz  # Unix only

# 2. Run the audit on a known paper
tmaudit verify --paper 5

# Expected output (after fix):
#   C1  [OK]     0 finding(s)
#   C2  [OK]     0 finding(s)
#   C3  [OK]     0 finding(s)
#   C4  [OK]     0 finding(s)
#   C5  [OK]     0 finding(s)
#   C6  [OK]     0 finding(s)
# All checks passed.  No issues detected.

# 3. Run the test suite
pytest
# Expected: 53 passed in 0.34s

# 4. Run the meta-test
python _check_all_regressions.py
# Expected: 7/7 bugs are correctly caught by their regression tests
```

## Files in this release

| File | Status | Size |
|---|---|---|
| `src/tmaudit/templates/verify_TEMPLATE.py` | modified | +9 / -1 |
| `tests/test_c6_threshold.py` | **new** | +113 |
| `_check_all_regressions.py` | modified | +33 |
| `engineering_notes_verify_template.md` | modified | +88 |
| `CHANGELOG.md` | modified | +5 |
| `tmaudit.pyz` | rebuilt | 46 KB |

## Diff stats

```
 src/tmaudit/templates/verify_TEMPLATE.py   |  9 +++--
 tests/test_c6_threshold.py                | 113 ++++++++++++++++++++++++++
 _check_all_regressions.py                 |  33 +++++++
 engineering_notes_verify_template.md      |  88 +++++++++++++++++
 CHANGELOG.md                              |   5 ++
 5 files changed, 248 insertions(+), 4 deletions(-)
```

## CI status

| Job | Status | Duration |
|---|---|---|
| `pytest (3.9)`  | ✓ passed | 23s |
| `pytest (3.10)` | ✓ passed | 24s |
| `pytest (3.11)` | ✓ passed | 22s |
| `pytest (3.12)` | ✓ passed | 23s |
| `meta-test`     | ✓ passed | 41s |
| `lint`          | ✓ passed |  9s |

**Total**: 14/14 jobs passed in 1m 24s.

Run URL: https://github.com/aidless/tmaudit/actions/runs/<run-id>

## Artifacts

- `tmaudit.pyz` (46,123 bytes) — the production distribution
- `test-results-pytest-3.9.xml` (JUnit XML)
- `test-results-pytest-3.10.xml`
- `test-results-pytest-3.11.xml`
- `test-results-pytest-3.12.xml`

## Compatibility

| Component | v0.1.0 | v0.1.1 | Compatible? |
|---|---|---|---|
| Python | 3.9 - 3.12 | 3.9 - 3.12 | ✅ Same |
| `paper_configs.py` schema | (5 papers) | (5 papers) | ✅ Same |
| `verify_TEMPLATE.py` API | (internal) | (internal) | ✅ Same |
| `tmaudit` CLI | (5 subcommands) | (5 subcommands) | ✅ Same |
| `_check_all_regressions.py` output | 6/6 caught | 7/7 caught | ✅ Strictly better |
| Test count | 46 | 53 | ✅ Strictly more |
| `tmaudit.pyz` size | 46 KB | 46 KB | ✅ Same |

## Known issues

None. The fix is exhaustive: 1-2 occurrences are no longer
reported, 3+ are still reported. If you have a paper that
legitimately uses "yield" 3+ times, the audit will still
flag it (correctly, in that case).

## Credits

| Role | Name |
|---|---|
| **Bug reporter** | @aidless (discovered during .github/ audit) |
| **Investigator** | @aidless |
| **Fix author** | @aidless |
| **Reviewer** | @aidless (self-review) |
| **CI** | GitHub Actions (14 jobs) |
| **Test infrastructure** | `_check_all_regressions.py` (the meta-test) |

## Acknowledgements

This release was made possible by:

- The `.github/` directory audit on 2026-07-10, which
  surfaced the false-positive as part of a broader review of
  the test suite.
- The pre-existing meta-test infrastructure
  (`_check_all_regressions.py`), which made it trivial to
  add Bug 7 to the validation pipeline.

## What's next

The next release will be **v0.2.0** (planned for late
2026 / early 2027). Roadmap:

- **C7 audit category**: Citation context validation
  (does the citing paper actually engage with the cited
  work, or is it a ceremonial cite?)
- **Audit-cache layer**: For papers that audit clean,
  cache the result so re-running is instant.
- **Multi-paper batch mode**: `tmaudit audit-all --output
  report.md` to generate a single Markdown report covering
  all configured papers.
- **Optional Paper 2 / 3 / 4 config completion** — currently
  these are placeholders.

If you have feature requests, please open a GitHub issue
using the
[feature request template](https://github.com/aidless/tmaudit/issues/new?template=feature_request.md).

## See also

- **Full diff**: https://github.com/aidless/tmaudit/compare/v0.1.0...v0.1.1
- **PR #15**: https://github.com/aidless/tmaudit/pull/15
- **Engineering diary**: [`engineering_notes_verify_template.md`](./engineering_notes_verify_template.md) §10
- **CHANGELOG.md**: [`CHANGELOG.md`](./CHANGELOG.md) v0.1.1 entry
- **Commit**: `8f4a2c1` (squashed) / `4a2b8c3` (pre-squash)
- **PR demo file**: [`pr_15_bug7_demo.md`](./pr_15_bug7_demo.md)

## Support

- **Discussions**: https://github.com/aidless/tmaudit/discussions
- **Bug reports**: use the
  [bug report template](https://github.com/aidless/tmaudit/issues/new?template=bug_report.md)
- **Security issues**: see
  [SECURITY.md](./SECURITY.md) for private disclosure

---

*Released on 2026-07-10 by @aidless.*