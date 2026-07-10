---
name: Feature request
description: Propose a new feature, audit category, or improvement to tmaudit.
title: "[Feature]: Plugin API — enable user-written audit checks (v0.4.0)"
labels: ["enhancement", "needs-triage", "v0.4.0-milestone"]
assignees: []
---

<!--
Status: ACCEPTED for v0.4.0 (per ROADMAP.md line 105).
Initial implementation shipped in this PR series:
  - §14 engineering notes (commit ed9d8f4)
  - src/tmaudit/plugins.py + tests (commit 3ad2825)
This issue documents the open follow-ups.
-->

## What do you want?

Add a **plugin API** that lets users write their own audit
checks (above and beyond C1–C10) and register them via
`pyproject.toml`, without forking the auditor.

The three primitives are:

1. **`Finding` dataclass** — the standard return type for
   every check (replaces the loose `tuple[str, str, int]`
   currently used by C1–C10).
2. **`@check` decorator** — turns a Python function into a
   registerable plugin, attaching metadata (name, severity,
   requires_config) without forcing boilerplate.
3. **`[tool.tmaudit.plugins]` entry-points table** — the
   discovery mechanism. Installed Python packages can
   declare plugin functions via the standard `entry_points`
   mechanism.

## Why does it matter?

`tmaudit` ships 10 core audit categories. But researchers
have concerns that don't fit those 10:

- A **specific venue** (NeurIPS 2026) requires page-length vs
  reference-count ratio.
- A **specific lab** (Smith Lab) wants every paper to follow
  the lab's nomenclature.
- A **specific workflow** (Hugging Face Spaces reproducer)
  requires a third-party service URL.

Without a plugin API, every such concern has to be added to
core, slowing releases and bloating the auditor. The plugin
API lets users extend `tmaudit` without forking it.

## Use case

A NeurIPS 2026 author installs a community plugin:

```bash
pip install tmaudit-nips2026-pagecheck
```

That package declares:

```toml
[project.entry-points."tmaudit.plugins"]
nips_pagecheck = "tmaudit_nips2026_pagecheck:check_page_length"
```

When the author runs `tmaudit verify --paper 1`, the plugin
runs alongside C1–C10 and emits findings using the same
`Finding` shape. The author can disable it per-paper:

```python
'c11_plugins_disabled': ['nips_pagecheck'],
```

## Proposed solution

**Author side** (in `tmaudit_nips2026_pagecheck/__init__.py`):

```python
from tmaudit import Finding, check

@check(name='nips-pagecheck', severity='MED', help_text='NeurIPS page count')
def check_page_length(tex, config=None):
    findings = []
    word_count = len(tex.split())
    if word_count > 9000:
        findings.append(Finding(
            category='NIPS-PC',
            severity='MED',
            message=f'Paper has {word_count} words; NeurIPS limit is 9000.',
        ))
    return findings
```

**Caller side** (built into tmaudit):

- `tmaudit plugins list` — table of every loaded plugin.
- `tmaudit plugins info nips-pagecheck` — details for one.
- `tmaudit plugins run nips-pagecheck --paper 1` — execute one
  plugin against one paper (no caching).

The full design rationale is in
[`engineering_notes_verify_template.md` §14](file:///F:/Research/TEMPLATE/engineering_notes_verify_template.md#L1705-L2120) (~415 lines).

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| **YAML-based plugin definition** | Requires learning both Python and YAML. Entry-points are PEP 621-standard. |
| **Plugins as directories with `__init__.py` shim** | Implicit, hard to discover, conflicts with `pip install -e .`. |
| **Built-in plugin DSL** | Users already know Python; another language is dead weight. |
| **`setup.cfg` entry-points** | `pyproject.toml` is the canonical modern place. |

See §14.13 in engineering notes for full comparison.

## Scope

- [x] Purely additive (no existing functionality changes) — the
  C1–C10 check functions still use the legacy tuple return type.
- [ ] Internal refactor (no public API change)
- [ ] Public API change (breaking — list below)

### Breaking changes

None in v0.4.0. The plugin API itself is **new**; C1–C10 are
unchanged. Migration to the `Finding` dataclass for C1–C10
will happen in v0.5.0+ if requested; **not in v0.4.0**.

## Affected components

- [x] `src/tmaudit/plugins.py` — NEW (Finding, @check, loader)
- [x] `src/tmaudit/__init__.py` — re-exports
- [x] `src/tmaudit/cli.py` — `tmaudit plugins list/info/run`
- [x] `src/tmaudit/configs/paper_configs.py` — `c11_plugins_disabled` (optional)
- [x] `tests/test_plugin_api.py` — NEW (29 unit tests)
- [x] `engineering_notes_verify_template.md` — §14 (NEW)
- [ ] `src/tmaudit/forge.py` — would need to wire audit-all to call plugins
- [ ] `src/tmaudit/cache.py` — would need plugin-fingerprint cache keys
- [ ] Example plugin package (`tmaudit_example_plugin/`) — separate follow-up
- [ ] Public PyPI release of `tmaudit` v0.4.0

## Effort estimate

- [x] Medium (1-3 days) — core API + tests + CLI
- [ ] Small follow-ups:
  - [ ] Wire `tmaudit audit-all` to invoke active plugins (forge integration)
  - [ ] Add `make_cache_key()` to `cache.py` (1 day)
  - [ ] Author `tmaudit_example_plugin/` (1 day)
  - [ ] Meta-test (Bug 13 + 14) in `_check_all_regressions.py`

## Are you willing to implement it?

- [ ] Yes, I plan to submit a PR
- [x] Yes, but I need help / mentorship — initial commit `3ad2825`
      ships the core API; reviewer input wanted on
      `Finding.to_tuple()` shim and the `MED`/`MEDIUM` alias.
- [ ] No, but I'd happy to review
- [ ] No, asking for someone else to implement

## Related issues / PRs

- Initial PR series:
  - `ed9d8f4 docs(§14): plugin API design rationale`
  - `3ad2825 feat(plugins): v0.4.0 plugin API (Finding + @check + loader + CLI + tests)`
- ROADMAP.md line 105 — the original "Plugin API" idea.
- Duplicates: —
- Cross-cutting: §13 (C9 design) and §14 (this API) both ship
  in v0.4.0.

## Open follow-ups (these need decisions before v0.4.0 release)

1. **`Finding.to_tuple()` shim** — keep as a backward-compat
   helper, or remove and force C1–C10 to migrate now?
   *Recommendation*: keep, surface minimal.

2. **`MED` vs `MEDIUM` severity alias** — the dataclass
   currently accepts both. Keep accepting both forever, or
   normalise to `MEDIUM` only at v1.0?
   *Recommendation*: accept both, document the rationale.

3. **Sandboxing** — plugins run with full user permissions.
   Add `RestrictedPython` at v2.0, or rely on package
   trust model?
   *Recommendation*: rely on trust model; document it.

4. **Plugin-fingerprint cache keys** — each plugin emit
   depends on (paper_n, plugin_name, plugin_version, tex_hash).
   Add to `cache.py` now, or defer to a cache rewrite in v0.5?
   *Recommendation*: defer; the loader integration is the bigger
   lift.

5. **Example plugin** — author a `tmaudit_example_plugin/`
   package that ships in-tree (alongside `tmaudit`) for new
   users to read and adapt. Add now or wait for community
   feedback?
   *Recommendation*: add now, small standalone package.

## Checklist

- [x] I have searched existing issues and this is not a duplicate
- [x] I have described a concrete use case (not "would be nice")
- [x] I have considered alternatives
- [x] I have described how this fits the project scope
- [x] I have indicated whether I am willing to submit a PR
