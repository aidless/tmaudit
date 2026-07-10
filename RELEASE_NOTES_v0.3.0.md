# Release Notes — v0.3.0

> **TLDR**: Two new audit categories close the 8-category vision: **C8 (statistical-power audit)** ships now, **C10 (reproducibility audit)** shipped earlier in the v0.3.0 dev cycle and is included here. **160 unit tests pass, 11/11 historical bugs caught, 44/44 community-files checks pass.**

## At a Glance

| | v0.2.0 (previous) | **v0.3.0 (this)** | Delta |
|---|---|---|---|
| Audit categories | 7 (C1..C7) | **9 (C1..C8, C10)** | +2 |
| Unit tests | 122 | **160** | +38 (+18 C8, +20 C10) |
| Meta-test bugs caught | 9/9 | **11/11** | +2 (Bug 10, Bug 11) |
| Community-files checks | 44/44 | **44/44** | unchanged |
| Per-paper opt-in configs | c7_max_ceremonial | + **c8_claimed_effects**, **c10_reproducibility_claims** | +2 |
| Total commits | 15 (since v0.1.1) | **22 (since v0.1.1)** | +7 |
| Lines added | — | **+~5,500 (since v0.2.0)** | — |

## Highlights

1. **C8 — Statistical-power audit** (NEW). The 8th audit
   category. For each `c8_claimed_effects` entry in the
   per-paper config, the auditor:
   - **Re-derives Cohen's d** from the (mean, sd, n) triple
     in the matching `\begin{tabular}` row. A mismatch
     `|d_actual - d_claimed| > 0.10` emits a **HIGH** finding.
   - **Computes post-hoc power** via the standard
     `Phi(|d| * sqrt(n_per_group/2) - z_alpha/2)` formula.
     Below 0.50 is **underpowered** (MED, recommend n × 4).
     Above 0.99 with a small claimed d and n ≥ 1000 is
     **suspiciously overpowered** (MED, a p-hacking tell).
   - **Scans the body for "significantly different" claims**.
     Independent of opt-in config. Missing p-value within 200
     chars (MED), or an internally-inconsistent pair
     (d < 0.10 with p < 0.001) (MED).

   Sample finding:
   ```
   HIGH: claimed d=0.50 for 'main_effect' is inconsistent with
         reported table numbers (computed d=1.00, diff=0.50).
         Reviewer §5 #8.
   ```

2. **C10 — Reproducibility audit** (shipped earlier in v0.3.0
   dev cycle; documented here). The 10th audit category.
   Catches:
   - **No availability statement** (HIGH): the paper has no
     code/data release URL or section.
   - **Future-tense release promise** (HIGH): "we will release"
     without a concrete deadline.
   - **SOTA-without-release** (HIGH): "state-of-the-art"
     claim coupled with "no release planned".
   - **Missing hyperparameters** (LOW): no learning-rate,
     batch-size, or optimizer mention.
   - **Missing random seed** (LOW).
   - **Missing hardware spec** (LOW).
   - **Missing library versions** (LOW).
   For each `c10_reproducibility_claims` entry in the per-paper
   config, the auditor verifies the claim is backed by a release.

   Sample finding:
   ```
   HIGH: paper has no code/data availability statement
         (no \\section{...Availability...} and no URL).
         Reviewer §5 #10.
   ```

3. **11/11 meta-test bugs caught**. v0.3.0 keeps the
   regression-injection meta-test discipline: every
   historical bug has a `inject_bugN()` function in
   `_check_all_regressions.py` that mutates the source and
   asserts the targeted regression test FAILS (catches the
   regression). All 11 are confirmed caught.

4. **Heuristic constants mirrored in tests**. The C8
   thresholds (0.10 d-mismatch, 0.50/0.99 power) appear as
   module-level constants and as comments at the top of
   `tests/test_c8_statistical_power.py`. Any future tuning
   is a single-file change.

5. **C8 + C10 are opt-in**. Like C7 (`c7_max_ceremonial`),
   both new categories are off when their per-paper config
   list is empty. The C8 *significance-claim scan* (sub-check
   3) is independent of opt-in because it catches a different
   class of error (textual claim without p-value).

## Breaking Changes

None. All v0.2.0 findings, configs, and CI workflows remain
valid. New per-paper fields (`c8_claimed_effects`,
`c10_reproducibility_claims`) are read with `or []` semantics
so older per-paper verify scripts without them still work.

## Upgrade from v0.2.0

1. Pull v0.3.0.
2. Re-fork per-paper verify scripts:
   ```bash
   python gen_verify_scripts.py --paper 1   # Paper 1
   python gen_verify_scripts.py --paper 2   # Paper 2
   python gen_verify_scripts.py --paper 3   # Paper 3
   python gen_verify_scripts.py --paper 4   # Paper 4
   python gen_verify_scripts.py --paper 5   # Paper 5
   ```
   The writer now adds `c8_claimed_effects` and
   `c10_reproducibility_claims` fields (empty by default for
   the new ones; **Papers 1, 3, 5 carry C8 example entries**).
3. Optionally populate `c10_reproducibility_claims` for each
   paper (e.g., `[{'name': 'model weights', 'description':
   'Pretrained transformer'}])`.
4. Re-run audits:
   ```bash
   tmaudit audit-all
   ```
5. Verify meta-test:
   ```bash
   python _check_all_regressions.py
   ```
   Expect **11/11 bugs caught** + **final sanity OK**.

## Detailed Change List

### Templates — `src/tmaudit/templates/verify_TEMPLATE.py`

- **C8 section added** (lines ~1093-1437):
  - `check_c8_statistical_power(tex, c8_claimed_effects)` —
    main entry point.
  - `_c8_compute_d`, `_c8_compute_power`,
    `_c8_parse_table_row`, `_c8_find_table_for_effect` —
    supporting helpers (LaTeX-row parser, d-formula, power
    formula with `min(n1, n2)` per-group n).
  - `_C8_TABLE_RE`, `_C8_ROW_SEP_RE`, `_C8_COL_SEP_RE`,
    `_C8_SIG_DIFF_RE`, `_C8_P_VALUE_RE`, `_C8_CLAIMED_D_RE`,
    `_C8_NUMBER_RE`, `_C8_LABEL_RE`, `_C8_N_DECL_RE` —
    regex constants.
  - SEVERITY['C8'] = 'MEDIUM'.
- Driver `main()` updated to call `check_c8_statistical_power`
  and `check_c10_reproducibility`, and the findings table
  now prints a C8 and C10 row.

### Configs — `src/tmaudit/configs/paper_configs.py`

- Papers 1, 3, 5 carry C8 example entries (Paper 1: `main_effect`,
  d=1.00, n=50/50; Paper 3: `coupling`, d=0.80, n=30/30; Paper 5:
  `accuracy`, d=0.50, n=20/20).
- Papers 1, 3, 5 also carry C10 example entries (model weights,
  code, training data).
- Papers 2 and 4 carry empty lists for both — opt-in.
- `_format_c8_claimed_effects()` and
  `_format_c10_reproducibility_claims()` added.

### Tests — `tests/`

- **`test_c8_statistical_power.py`** (NEW, 18 tests) — TDD red
  then green. Covers d-mismatch, power regimes,
  significance scan, multiple effects, opt-in no-op, table
  parsing fallback, malformed LaTeX, extra fields, tolerance.
- **`test_c10_reproducibility.py`** (already added, 20 tests) —
  TDD. Covers availability statement, future-tense,
  SOTA-no-release, hyperparameter / seed / hardware / library
  mention detection.
- Existing 122 tests still pass (no regressions).

### Meta-test — `_check_all_regressions.py`

- `inject_bug10()` (added earlier, C10 inverted severity).
- `inject_bug11()` (NEW, C8 inverted d-mismatch threshold).
- Total bugs checked: **11**.

## Known Limitations

- C8's LaTeX-row parser is best-effort: it falls back to the
  first two data rows when no label match is found. Tables
  with `> 2` groups (3-way ANOVA, multi-factor designs) are
  not yet supported (planned for v0.4.0+).
- C8's significance scan only flags English `significantly
  different` (case-insensitive). Other languages and
  paraphrases (`p < 0.05 between A and B`) are not yet
  recognised.
- The `_c8_compute_power` formula is a normal-approximation
  closed form (Cohen 1988). For very small n (< 10) the
  approximation underestimates power by ~5%.

## Acknowledgements

C8 design follows Cohen, J. (1988). *Statistical Power
Analysis for the Behavioral Sciences*. 2nd ed. Lawrence
Erlbaum. The test pattern was inspired by the C7
ceremonial-cite detection in v0.1.2.

## Next Steps (planned for v0.4.0)

- C9 (figure-caption audit) — detect ungrammatical /
  uninformative captions.
- §12 engineering notes (C10 reproducibility design).
- Public release on GitHub (push 21+ local commits, then
  tag v0.3.0).
- Beginner-friendly tutorial videos (paper-config
  walkthrough).

---
*Released 2026-07-10. See [`CHANGELOG.md`](./CHANGELOG.md) for
commit-by-commit detail.*
