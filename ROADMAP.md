# Roadmap

This document describes the planned future direction of
`tmaudit`. It is **not a commitment** — features may be
added, removed, or re-prioritised as we learn from real
usage. Issues on GitHub are the source of truth for what
is currently being worked on.

## Released

### v0.1.0 — 2026-07-10

Initial release. 6-category audit framework (C1..C6),
5-paper support, single-file distribution, 46-test
suite, 6-bug meta-test, full GitHub community-health
files.

### v0.1.1 — 2026-07-10

**Bug 7 fix**: C6 blacklist false-positive on idiomatic
English. Added `min_count = 3` threshold. 7 new unit
tests in `tests/test_c6_threshold.py`. Meta-test score
6/6 → **7/7 caught**. 46 → **53 tests**.

## In progress

### v0.1.2 — Planned Q3 2026

**Theme**: Performance + a new audit category.

Two enhancement issues are open and ready for community
contribution:

| Issue | Title | Area | Effort |
|---|---|---|---|
| [#16](.github/issues/16-c7-citation-context.md) | C7 audit category (citation context) | audit | Medium (1-3 days) |
| [#17](.github/issues/17-audit-cache.md) | Audit-cache layer | performance | Medium (1-3 days) |

### v0.1.2 acceptance criteria

A v0.1.2 release requires:

- [ ] Both issues implemented and merged via PR.
- [ ] All existing tests still pass (53/53 minimum).
- [ ] New tests for the new functionality (target: 60+
      total tests, 8/8 caught in the meta-test).
- [ ] `engineering_notes_verify_template.md` gets §11 (C7)
      and §12 (cache) sections.
- [ ] `CHANGELOG.md` v0.1.2 entry added.
- [ ] `tmaudit.pyz` rebuilt and attached to the release.
- [ ] No new bugs introduced (meta-test score does not
      drop below 8/8).

### v0.1.2 release process

1. Implement Issue #16 (C7) → PR #16 → merge.
2. Implement Issue #17 (cache) → PR #17 → merge.
3. Add `inject_bug8` to the meta-test for the new
   functionality.
4. Bump version to 0.1.2 in `pyproject.toml` and
   `src/tmaudit/__init__.py`.
5. Build and tag `v0.1.2`.
6. Write `RELEASE_NOTES_v0.1.2.md`.
7. Update `CHANGELOG.md`.
8. Push to GitHub and create the release.

## Planned

### v0.2.0 — Planned Q4 2026 / Q1 2027

**Theme**: Multi-paper batch mode + Paper 2/3/4
config completion.

| Issue | Title | Area | Status |
|---|---|---|---|
| (TBD) | `tmaudit audit-all --output report.md` | CLI | Not yet filed |
| (TBD) | Complete Paper 2 config | configs | Not yet filed |
| (TBD) | Complete Paper 3 config | configs | Not yet filed |
| (TBD) | Complete Paper 4 config | configs | Not yet filed |
| (TBD) | Markdown / HTML report output | output | Not yet filed |
| (TBD) | LLM-based C7 fallback (GPT-4 / Claude) | audit | Not yet filed |

### v0.2.0 acceptance criteria

- [ ] All Paper 2/3/4 configs complete (5/5 papers
      auditable, not just 2/5).
- [ ] `tmaudit audit-all` generates a single Markdown
      report covering all configured papers.
- [ ] The report is included in the CI artefacts.
- [ ] LLM-based C7 fallback is opt-in (env var
      `TMAUDIT_LLM_ENDPOINT`) and respects the user's
      privacy (no paper content sent without consent).

## Long-term

### v0.3.0 — TBD

**Theme**: Plugin system + new audit categories.

| Idea | Description |
|---|---|
| C8 (statistical power) | Re-derive the paper's claimed effect size and power from the reported numbers, and flag if the paper's claims are not supported. |
| C9 (figure–caption consistency) | Check that each figure has a caption, the caption is in the right place, and the caption matches the figure's content. |
| C10 (reproducibility) | Check that the paper includes a code/data availability statement, and that the statement is consistent with the paper's claims. |
| Plugin API | Allow users to write their own audit checks (Python module with a `check(main.tex) -> list[Finding]` function) and register them via `pyproject.toml`. |

### v1.0.0 — TBD

**Theme**: First stable release.

- All 10 audit categories (C1..C10) implemented.
- At least 10 papers supported out-of-the-box.
- API stable (no breaking changes for 6 months).
- Performance: < 1 second per paper, including cache.
- Documentation: full API reference, contributor guide,
  tutorial videos.
- Used in at least 3 real TMLR / NeurIPS / ICLR
  submission cycles.

## Versioning policy

`tmaudit` follows [Semantic Versioning](https://semver.org/):

- **Major (X.0.0)**: breaking changes to the public API
  (CLI subcommands, `paper_configs.py` schema, output
  format).
- **Minor (0.X.0)**: new features, new audit categories,
  new paper configs. Backward-compatible.
- **Patch (0.0.X)**: bug fixes only. No new features.

We are currently in the **0.x.y** phase, which means the
API is not yet stable. Breaking changes may occur in
minor releases until v1.0.0.

## Decision-making

Major roadmap decisions are made by the maintainer(s) on
GitHub Discussions. The process is:

1. Anyone can open a Discussion in the "Roadmap" category.
2. The maintainer triages and replies within 7 days.
3. If the proposal is accepted, an issue is filed in the
   appropriate milestone.
4. The issue is then open for community contribution.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the
contribution workflow and [SUPPORT.md](./.github/SUPPORT.md)
for the support channels.

## See also

- [`CHANGELOG.md`](./CHANGELOG.md) — what was done
- [`engineering_notes_verify_template.md`](./engineering_notes_verify_template.md) — why
- [`.github/issues/`](./.github/issues/) — draft issues
  ready to be filed
- [`RELEASE_NOTES_v0.1.1.md`](./RELEASE_NOTES_v0.1.1.md) — last release
- [`.github/ISSUE_TEMPLATE/feature_request.md`](./.github/ISSUE_TEMPLATE/feature_request.md)
  — how to file a new feature

---

*Last updated: 2026-07-10. Next review: when v0.1.2 is
released or when a major design decision is needed.*