# Release Notes — v0.4.0

> **TLDR.** First release with the **plugin API**: third-party
> packages can register audit checks via `[tool.tmaudit.plugins]`
> in `pyproject.toml`, and `tmaudit` discovers and runs them via
> `audit-all` per paper.
>
> **218 unit tests pass, 14/14 meta-test bugs caught, 44/44
> community-files checks pass.**

## At a Glance

| | v0.3.0 (previous) | **v0.4.0 (this)** | Delta |
|---|---|---|---|
| Audit categories | 10 (C1..C10) | **10 + plugins** | +plugin API |
| Unit tests | 176 | **218** | +42 (+29 plugin_api + 11 example_plugin + 2 meta) |
| Meta-test bugs caught | 12/12 | **14/14** | +2 (Bug 13 + Bug 14) |
| Community-files checks | 44/44 | **44/44** | unchanged |
| Total commits | 22 (since v0.1.1) | **27 (since v0.1.1)** | +5 |
| Per-paper opt-in configs | c8 / c9 / c10 | + **c11_plugins_disabled** | +1 |
| Plugin API | none | **Finding, @check, entry-points, audit_plugins** | new |

## Highlights

1. **Plugin API** (the headline feature of v0.4.0). Plugins are
   Python callables registered via the standard PEP 621
   `[tool.tmaudit.plugins]` entry-points table. The loader
   uses `importlib.metadata`; plugins need only be installed
   in the same environment as `tmaudit`. Three primitives:
   - `Finding` — frozen dataclass (the standard return type).
   - `@check(name=…, severity=…, help_text=…, version=…)`
     decorator wrapping a `def check(tex, config) -> List[Finding]`.
   - `audit_plugins(paper_n, paper_dir, …)` — bulk runner
     invoked by `audit-all`.

2. **`tmaudit plugins list / info / run`**. Three new
   subcommands under the `plugins` namespace:
   - `list` — table of every discovered plugin.
   - `info NAME` — details for one plugin.
   - `run NAME --paper N` — execute one plugin against one
     paper (no caching).

3. **Per-paper `c11_plugins_disabled`**. Per-paper config
   can list plugin names that should NOT run on that paper
   (mirrors the `c7_max_ceremonial` precedent). Future v1.0
   will add `c11_plugins_enabled` (whitelist).

4. **Plugin-fingerprint cache keys**. Each plugin's cached
   findings are keyed on `(paper_n, plugin_name,
   plugin_version, tex_hash)`. Plugin updates and paper
   edits both invalidate stale entries; a clean paper with
   the same plugin version hits the cache.

5. **Example plugin ships in-tree**. `tmaudit_example_plugin/`
   is a sibling directory in this repo, installable as
   `pip install -e ./tmaudit_example_plugin`. It registers
   three demo checks (`flag-todo-markers`,
   `flag-xxx-markers`, `flag-long-abstract`). Use it as a
   starting point for your own plugin.

6. **Bug 13 + Bug 14 in `_check_all_regressions.py`**.
   - **Bug 13**: Loader raises on a malformed entry-point
     (replaces try/except with bare `raise`).
   - **Bug 14**: Per-paper `c11_plugins_disabled` is ignored
     (drops the `filter_active` step).

7. **§14 engineering notes** document the design rationale
   (~415 lines, 14 sub-sections): motivation, protocol,
   pyproject schema, discovery, lifecycle, CLI,
   per-paper override, cache integration, test plan,
   limitations, roadmap to v1.0, alternative designs, and
   implementation milestones.

8. **Paper 5 `Bug 6` fix**. `paper_configs.py` Paper 5
   `c2_section_pattern` now correctly accepts both `\section{
   Power analysis}` and `\subsection{Statistical Protocol}`,
   so Bug 6's regression test passes.

## Author-side example

```python
# my_plugin/checks.py
from tmaudit import Finding, check

@check(name='no-todo', severity='LOW',
       help_text='Flag TODO markers', version='0.1.0')
def flag_todos(tex, config=None):
    return [
        Finding(category='TODO', severity='LOW',
                message=f'TODO at line {i+1}', line=i+1)
        for i, line in enumerate(tex.splitlines())
        if 'TODO' in line
    ]
```

```toml
# my_plugin/pyproject.toml
[project]
name = "my-tmaudit-plugin"
dependencies = ["tmaudit>=0.4"]

[project.entry-points."tmaudit.plugins"]
no-todo = "my_plugin.checks:flag_todos"
```

```bash
pip install -e ./my_plugin
tmaudit plugins list     # shows "no-todo"
tmaudit plugins info no-todo
tmaudit plugins run no-todo --paper 5
```

## Upgrade from v0.3.0

```powershell
git pull
pip install -e .[dev]
python _check_all_regressions.py   # expect 14/14 caught
```

Plugins already installed keep working unchanged. New fields
(`c11_plugins_disabled`) in `CHECKS_CONFIG` are read with `or []`
semantics, so older per-paper verify scripts continue to run.

See [`RELEASE_NOTES_v0.3.0.md`](./RELEASE_NOTES_v0.3.0.md) for
the prior release (10 audit categories, 176 tests).

## Breaking Changes

None. All v0.3.0 findings, configs, and CI workflows remain
valid. The plugin API itself is **new**; C1–C10 are unchanged.
The legacy tuple return type `(category, message, line)` is
deprecated in favour of `Finding` for plugins but remains the
canonical shape for the C1–C10 core categories.

## Known Limitations

- **No plugin sandbox.** Plugins run with full user
  permissions. A malicious plugin could read arbitrary
  files. Documented; v2.0+ may add `RestrictedPython`.
- **Plugins cannot import other plugins.** Composition is
  via the public `Finding` list only. Future v2.0 may add a
  typed inter-plugin API.
- **No plugin-level configuration schema validation.**
  Plugins can ask for free-form `config` dict but cannot
  declare what keys they expect. JSON-Schema-based validator
  planned for v2.0.
- **Plugin-fingerprint cache: per-process invalidation**.
  The cache works within one `tmaudit` invocation. Plugin
  updates across invocations are picked up via the
  `version=` argument.

## Acknowledgements

The plugin API design follows the standard Python packaging
ecosystem (entry-points, `importlib.metadata`) and is
intentionally minimal so the user only learns `@check` +
`Finding`; everything else is Python.

## Next Steps (planned for v0.5.0)

- `c11_plugins_enabled` (whitelist) — opt-in subset per paper.
- Plugin configuration schema validator (JSON Schema).
- Performance: < 1 second per paper including plugin runtime.
- Migrate C1–C10 to return `Finding` (deprecate tuples).
- Document the tutorial videos planned for v1.0.

---

*Released 2026-07-10. See [`CHANGELOG.md`](./CHANGELOG.md) for
commit-by-commit detail and
[`engineering_notes_verify_template.md`](./engineering_notes_verify_template.md) §14
for the design rationale.*
