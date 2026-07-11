# Release Notes — v0.5.0

> **TLDR.** v0.5.0 adds the **whitelist half** of the per-paper
> plugin filter. v0.4.0 shipped `c11_plugins_disabled` (blacklist).
> v0.5.0 ships `c11_plugins_enabled` (whitelist). The two work
> together under a clear precedence rule.
>
> **225 unit tests pass, 16/16 meta-test bugs caught, 44/44
> community-files checks pass.**

## At a Glance

| | v0.4.0 (previous) | **v0.5.0 (this)** | Delta |
|---|---|---|---|
| Audit categories | 10 + plugins | unchanged | — |
| Unit tests | 218 | **225** | +7 (whitelist tests) |
| Meta-test bugs caught | 14/14 | **16/16** | +2 (Bug 15 + Bug 16) |
| Community-files checks | 44/44 | **44/44** | unchanged |
| Total commits | 27 (since v0.1.1) | **31 (since v0.1.1)** | +4 |
| Per-paper plugin filter | `c11_plugins_disabled` only | + **`c11_plugins_enabled`** | +whitelist |
| Precedence rule | n/a | **enabled wins, disabled ignored (with warning)** | new |

## Highlights

1. **`c11_plugins_enabled` whitelist** (the headline feature).
   Per-paper, you can now lock down the audit to a known
   short list of plugins. Use this when:
   - The author wants the audit to only run their custom
     project-specific checks.
   - A new paper version is being audited and you want to
     disable everything else (focus mode).
   - You want to encode "this paper only ever ran plugin X"
     as a reproducible contract.

2. **Precedence rule (the second headline feature)**.
   If both `c11_plugins_enabled` and `c11_plugins_disabled`
   are set on the same paper, **enabled wins, disabled is
   ignored**, with a warning logged. This avoids the
   ambiguity of "what does intersection mean here?" and gives
   the author a clear semantic.

3. **Backward-compatible**. Existing v0.4.0 callers that
   pass only `disabled` continue to work. The new `enabled`
   parameter defaults to `None`, which means "no whitelist".

## Behaviour

```python
filter_active(plugins, disabled=[], enabled=[])

# All four cases:
# 1. both empty      -> all plugins run
# 2. only disabled   -> blacklist (v0.4.0 behavior)
# 3. only enabled    -> whitelist (v0.5.0)
# 4. both set        -> enabled wins, warning logged
```

## API Changes

### `filter_active(plugins, disabled, enabled=None)`

New third parameter `enabled`:
- `None` or `[]` → no whitelist applied.
- non-empty iterable → only plugins whose name is in the
  list are kept.

### `audit_plugins(..., enabled=None)`

New `enabled` kwarg threaded through to `filter_active`.
If not explicitly passed, `audit_plugins` reads
`config.get('c11_plugins_enabled', [])` from the paper
config.

### `paper_configs.PAPER5_CONSOLIDATED`

Adds `'c11_plugins_enabled': ['flag-todo-markers']` as a
usage example. **Note:** PAPER5 currently locks itself down
to a single example plugin. To re-run a broader audit on
PAPER5, set `c11_plugins_enabled=[]` or remove the field.

## Tests

| Test | What it locks |
|---|---|
| `test_filter_active_empty_lists_run_all` | neither filter set → run all |
| `test_filter_active_blacklist_only` | disabled-only → existing behavior |
| `test_filter_active_whitelist_only` | enabled-only → whitelist applied |
| `test_filter_active_whitelist_overrides_blacklist` | both set → enabled wins |
| `test_filter_active_whitelist_with_unknown_plugin` | unknown name in enabled is dropped silently |
| `test_audit_plugins_respects_c11_plugins_enabled` | end-to-end through `audit_plugins` |
| `test_paper_configs_can_carry_c11_plugins_enabled` | per-paper config field is honored |

**Total: 225 tests pass (+7 vs v0.4.0).**

## Meta-test

| Bug | What it injects | Test |
|---|---|---|
| Bug 15 | removes the whitelist branch entirely | `test_audit_plugins_respects_c11_plugins_enabled` |
| Bug 16 | swaps the order of `enabled` and `disabled` branches | `test_filter_active_whitelist_overrides_blacklist` |

**Total: 16/16 caught (was 14/14 in v0.4.0).**

## TDD Provenance

The v0.5.0 work followed the project's documented TDD
pattern (§15.12):

| Step | Commit | Summary |
|---|---|---|
| 1. Red | `0d538a1` | 7 new failing tests added to `test_plugin_api.py` |
| 2. Green | `424c806` | minimal changes to `filter_active` + `audit_plugins` + `paper_configs` |
| 3. Driver wiring | (in `424c806`) | `cmd_audit_all` annotated; reads from config |
| 4. Meta-test | `5129e5d` + this release | Bug 14 anchor updated; Bug 15 + 16 added |
| 5. Docs | this release | CHANGELOG + RELEASE_NOTES_v0.5.0 + ROADMAP |

## Compatibility Notes

- **CLI**: no new flags in v0.5.0. The `c11_plugins_enabled`
  field is set via the per-paper config dict, not via a CLI
  flag. (Adding `--enabled-plugins` to `cmd_audit_all` is
  on the v0.6.0 roadmap.)
- **Plugin authors**: no API change required. The
  `filter_active` and `audit_plugins` signatures are
  backward-compatible — the new `enabled` parameter has a
  default of `None`, so existing callers work unchanged.
- **Config schema**: `c11_plugins_enabled` is an optional
  field. If absent, v0.4.0 behavior (no whitelist) is
  preserved.

## Upgrade Path

For projects upgrading from v0.4.0:

1. Pull the v0.5.0 release.
2. Run `tmaudit audit-all` on each paper — the audit
   output is unchanged unless you add `c11_plugins_enabled`
   to a paper config.
3. To lock down a specific paper, add
   ```python
   'c11_plugins_enabled': ['your-plugin-1', 'your-plugin-2'],
   ```
   to its entry in `paper_configs.py`.

No migration script is needed.

## Known Limitations

- **No CLI flag for `enabled` yet.** v0.6.0 will add
  `--enabled-plugins` to `cmd_audit_all` (and a
  corresponding `--disabled-plugins` for symmetry).
- **No warning to user if whitelist excludes a plugin that
  was previously running.** v0.6.0 will add an
  `--warn-on-whitelist-exclusion` flag.
- **Whitelist is name-based, not capability-based.** v0.6.0
  will add `c12_plugin_capabilities` for capability-based
  filtering.

## Acknowledgements

The v0.5.0 design was driven by the requirement to encode
"this paper only ever ran plugin X" as a reproducible
contract — a need that surfaced during the paper-review-toolkit
work. The whitelist-or-blacklist design and precedence rule
are documented in `V050_PLAN.md` (§16.4).

---

**Full diff**: see `CHANGELOG.md` for the v0.5.0 entry.
**Regressions protected**: 16 (was 14 in v0.4.0).