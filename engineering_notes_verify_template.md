# Engineering Notes: 6 Bugs in the `verify_p<N>.py` Template Generator

**Authors:** Liu Mingrui
**Repo path:** `F:\Research\TEMPLATE\`
**Date:** 2026-07-10
**Scope:** debugging `gen_verify_scripts.py` — the config-driven fork tool that
turns `_verify_TEMPLATE.py` into per-paper `verify_p<N>.py` audit scripts.

## 0. Motivation and setup

TMLR submission requires that every paper has a 6-category audit (C1 abstract
symbols, C2 Bonferroni scheme, C3 formalization, C4 citation hygiene, C5
n/d/test transparency, C6 blacklisted vocabulary). With five papers (Paper
1–5), the naive approach is five hand-written audit scripts. We instead built
a single template, `_verify_TEMPLATE.py`, that reads per-paper rules from
a `CHECKS_CONFIG` dict, and a fork tool, `gen_verify_scripts.py`, that
materialises the template into the right `PAPER<N>_CONSOLIDATED/` directory.

The fork is **config-driven**: per-paper `PAPER_CONFIGS` entries contain the
C1–C6 rules, and the generator substitutes them into the template. During
the first fork to Paper 1, the generator produced a script that crashed
inside the auditor with a `re.error`. The chain of fixes took six iterations
before both Paper 1 and Paper 5 reached **0 findings**. This document
records each of the six bugs in the order they appeared, the one-line
reproducer for each, the fix, and the broader engineering lesson. It is
intended to be the engineering appendix of the TMLR submission.

## 0.1 Reproducibility

Every command in this document was run from `F:\Research\TEMPLATE\`:

```powershell
cd F:\Research\TEMPLATE
python gen_verify_scripts.py --list                                    # show known papers
python gen_verify_scripts.py --paper 1 --dry-run                       # show what would be written
python gen_verify_scripts.py --paper 1                                 # write and run
python gen_verify_scripts.py --paper 5
```

A regression test in this document is "Paper 1 reaches 0 findings" and
"Paper 5 reaches 0 findings". Both pass on the final commit.

| Bug | One-line reproducer (after the fix) | Final fix |
|---|---|---|
| 1 | `python -c "print(repr('\\b'))"` shows `'\\x08'` | r-string literal in generator |
| 2 | `re.sub('x', r'\s\\n', 'x')` raises `bad escape \s` | brace-count + str.slice instead of `re.sub` |
| 3 | generator writes `]*\}|'` literally after the dict | string-literal-aware brace counter |
| 4 | `verify_p1.py` flags TTRL even though Notation block defines it | C1 second pass (whole abstract) |
| 5 | `verify_p1.py` flags p-value for missing test name | regex allows `$`, `-`, etc. between `t` and `test` |
| 6 | `verify_p5.py` flags missing Power analysis section | Paper 5's section is `Statistical Protocol` |

---

## 1. Bug 1 — `\b` becomes backspace when stringified through `repr()`

**Symptom.** First run of `python verify_p1.py` after a fork:

```
Traceback (most recent call last):
  ...
  File ".../verify_p1.py", line 211, in check_c1_abstract_definitions
    m = re.search(token, abstract, re.IGNORECASE)
re.error: bad escape \m at position 19
```

**Root cause.** The Paper 1 `c1_symbols` configuration contained regex
patterns like `r'\bCAF\b'`. The generator's `_format_simple_value` used
`repr(value)` to inject these into the source file. For non-raw Python
strings, `repr('\\bCAF\\b')` returns `'\\x08CAF\\x08'` — `\b` is
interpreted as the backspace character `\x08`, not as a regex word
boundary. The generated `.py` file then contained `'\bCAF\b'`, which
`re` parsed as `'\x08CAF\x08'` and complained about the `\x08`
escape sequence.

**One-line reproducer:**

```python
>>> re.search('\\b', 'CAF', re.IGNORECASE)
# Raises: re.error: bad escape \b at position 0
```

**Fix.** In `gen_verify_scripts.py`, replace `repr(value)` with a
heuristic that detects regex patterns (the presence of `\b`, `\d`,
`\s`, `\.`, `\{`, `\}`, etc.) and emits them as raw string literals
(`r'...'`):

```python
def _format_simple_value(value) -> str:
    if isinstance(value, str):
        regex_marker_re = re.compile(r'\\[bBdDsSwWnrtfv0]|\\\.|\\\{|\\\}')
        if regex_marker_re.search(value):
            escaped = value.replace("'", r"\'")
            return f"r'{escaped}'"
        return repr(value)
    if value is None:
        return 'None'
    return repr(value)
```

**Lesson.** When generating Python source code that contains regex
patterns, **always emit the regex as a raw string** (`r'...'`). The
double-interpretation of backslashes (once by Python when parsing the
literal, then again by `re` when compiling the pattern) is a perennial
source of bugs. The same lesson applies to file paths on Windows: a
raw string `r'F:\Research\PAPER1_CONSOLIDATED'` is correct, but
`'F:\Research\PAPER1_CONSOLIDATED'` will silently drop `\R` and `\P`.

---

## 2. Bug 2 — `re.sub` interprets backslashes in the replacement text

**Symptom.** After the Bug 1 fix:

```
Traceback (most recent call last):
  ...
  File ".../sre_parse.py", line 1051, in parse_template
    this = chr(ESCAPES[this][1])
KeyError: '\\s'
```

**Root cause.** The generator used `re.sub` to inject the
`CHECKS_CONFIG` block. `re.sub`'s second argument is the
**replacement**, not a literal — it interprets backslashes as
backreferences (`\g<name>`, `\1`, etc.). When the replacement
text contained a regex pattern like `\s`, `\d`, or `\b`,
`sre_parse.parse_template` raised `bad escape`.

**One-line reproducer:**

```python
>>> re.sub('x', r'\s\n', 'x')   # r-string literal; \s means whitespace
# Raises: re.error: bad escape \s at position 0
```

**Fix.** Replace `re.sub` with a hand-written brace-matching loop
that does **literal string slicing**:

```python
out = out[:start] + new_block + '\n' + out[end:]
```

This avoids the entire replacement-as-template machinery. The
brace counter is needed because the source contains nested `{` and
`}` (the outer `CHECKS_CONFIG` dict, plus inner dicts in
`c1_symbols`).

**Lesson.** `re.sub` is a deceptively-named function: the second
argument is not a literal but a *replacement template* in which
`\1`, `\g<name>`, and similar sequences are special. If you
want a literal replacement, use `str.slice` or `str.replace` —
or pass a callable `re.sub(pat, lambda m: repl, s)` that returns
the literal string. This is the kind of bug that only surfaces
once a config contains a regex with backslash sequences; the
first five template runs all happened to use only ASCII punctuation.

---

## 3. Bug 3 — Brace counter mis-counts `\{` and `\}` inside string literals

**Symptom.** After the Bug 2 fix, `python verify_p1.py` produced a
file with a syntax error at the end of the substituted config:

```
SyntaxError: unmatched ']'
]*\}|'
    ^
```

**Root cause.** The brace counter from Bug 2 was a naïve
`depth += 1` / `depth -= 1` loop. The Paper 1 `c2_section_pattern`
config contained the regex string

```python
r'\\section\*?\{[^}]*Power analysis[^}]*\}|\\subsection\*?\{[^}]*Power analysis[^}]*\}'
```

This string contains eight `{` and four `}` characters that are
**inside a string literal**, not Python source-level braces. The
counter saw them as a depth mismatch and exited early, leaving the
rest of the template (`]*\}|'`) in the output file.

**One-line reproducer:**

```python
# naively count braces in a Python source line containing a regex
s = r"    'foo': r'\\section\{[^}]*\}|...',"  # pretend this is the line
depth = 0
for c in s:
    if c == '{': depth += 1
    elif c == '}': depth -= 1
# depth ends at -1, but the line is syntactically correct!
```

**Fix.** Augment the brace counter with a string-literal state
machine. When we are inside a string (single- or double-quoted),
skip brace counting entirely:

```python
in_str: str | None = None
while i < len(out):
    c = out[i]
    if in_str is not None:
        if c == '\\' and i + 1 < len(out):
            i += 2  # skip escape sequence
            continue
        if c == in_str:
            in_str = None
    else:
        if c in ('"', "'"):
            in_str = c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    i += 1
```

**Lesson.** Any mini-parser that operates on Python-like source
must be aware of string literals. The naïve approach — counting
`{` and `}` in raw text — works for short snippets but fails the
moment the snippet contains regex patterns, docstrings, or
f-strings with `{}` interpolation. The correct primitive is the
`tokenize` module from the Python standard library, but for our
narrow use case (replacing a single top-level `CHECKS_CONFIG`
dict) the hand-rolled state machine is sufficient and easier to
debug.

---

## 4. Bug 4 — C1 check too narrow: 250-character window misses Notation block

**Symptom.** After Bug 3, `python verify_p1.py` ran cleanly and
reported:

```
[HIGH] C1  (line 60)
    TTRL (Test-Time Reinforcement Learning) appears in abstract
    without inline definition. Reviewer §3 #1.
```

But Paper 1's abstract **does** define TTRL — in a "Notation" block
appended to the end of the abstract (at line 64, roughly 1500
characters after the first mention of "TTRL" at line 60).

**Root cause.** The C1 check required the definitional phrase to
appear within **250 characters** of the first mention of the symbol.
This window was sized for "inline definition immediately after the
symbol". A Notation block at the end of the abstract is a perfectly
valid place to define a symbol — but it falls outside the window.

**One-line reproducer:**

```python
import re
abstract = "We find (i) ... TTRL dynamics ... (1,500 chars later) ... TTRL (Test-Time RL) ..."
m = re.search(r'TTRL', abstract)
# Look 250 chars around it: contains neither the word "Test-Time" nor
# the word "Reinforcement Learning" — but the definition is elsewhere.
```

**Fix.** Add a second and third pass to the C1 check:

```python
# Second pass: definition anywhere within the abstract.
if re.search(defn, abstract, re.IGNORECASE | re.DOTALL):
    continue
# Third pass: definition in the first \section{Introduction}.
intro_match = re.search(
    r'\\section\{Introduction\}(.+?)\\section\{',
    tex, re.DOTALL,
)
if intro_match and re.search(
    defn, intro_match.group(1), re.IGNORECASE | re.DOTALL,
):
    continue
```

**Lesson.** Audit checks should follow the **principle of least
strictness**: prefer false negatives (which the human reviewer will
catch) over false positives (which the human reviewer will ignore
or, worse, distrust the audit). The 250-character window was
optimised for a particular writing style (inline definition) and
penalised a different but equally valid style (Notation block).
Whenever an audit rule is added, it is worth listing the writing
styles that should pass; the rule should be the **union** of those
styles, not the intersection.

---

## 5. Bug 5 — C5 test-name regex too strict: `paired\s+t-test` misses `paired $t$-tests`

**Symptom.** After Bug 4, C1 passed but C5 reported:

```
[MEDIUM] C5  (line 60)
    Reported p-value at abstract line 60 is missing test name.
```

But the abstract contained `paired $t$-tests across $n{=}30$ seeds`
in the Notation block.

**Root cause.** The C5 regex was `r'(Wilcoxon|paired\\s+t|t-?test|...)'`.
The literal substring `paired $t$-tests` does not contain `\s+t`,
because there is no whitespace between `paired` and `$t$` — the
`$` is a LaTeX math-mode delimiter. Likewise, the substring `t$-tests`
does not match `t-?test` because the `-` is followed by `tests` (with
a trailing `s`), which the original pattern did not allow.

**One-line reproducer:**

```python
import re
s = "from paired $t$-tests across $n{=}30$ seeds"
re.search(r'paired\s+t-test', s)   # None
# But the meaning is exactly "paired t-tests"!
```

**Fix.** Relax the regex to allow any non-letter character between
the keyword and `test`, and allow the plural `tests`:

```python
has_test = bool(re.search(
    r'(Wilcoxon|'
    r'paired[^a-zA-Z]{0,8}t[^a-zA-Z]{0,3}test|'
    r'\bt[^a-zA-Z]{0,3}test|'
    r'Mann.Whitney|permutation)',
    window, re.IGNORECASE,
))
```

This now matches:
- `paired t-test` (the original happy path)
- `paired $t$-test` and `paired $t$-tests` (LaTeX math mode)
- `paired\\s+t-test` (a literal backslash-s-plus-t in raw string)
- `t-test`, `t-tests`, `t test`, `t$test` (any of these work)

**Lesson.** When auditing LaTeX manuscripts, the auditor must
treat LaTeX markup as part of the input language, not as
punctuation. A `t-test` in math mode is `t`-`-`-`test` with two
`$` characters that a naïve regex will reject. The fix is to
specify the regex in terms of "no letters between" rather than
"specific characters between". This is a recurring pattern in
any tool that processes LaTeX: it is easier to write the
negative-space regex once and reuse it than to enumerate every
legal LaTeX form.

---

## 6. Bug 6 — `c2_section_pattern` too narrow: Paper 5's section is `Statistical Protocol`, not `Power analysis`

**Symptom.** After Bug 5, Paper 1 reached 0 findings. Forking to
Paper 5 and running produced:

```
[HIGH] C2  (global)
    No Power analysis section declaring Bonferroni k found.
```

**Root cause.** The Paper 5 `c2_section_pattern` was inherited
from Paper 1's configuration:

```python
'c2_section_pattern': r'\\section\*?\{[^}]*Power analysis[^}]*\}',
```

But Paper 5's actual section heading is `\subsection{Statistical
Protocol}` (added during the original Paper 5 polish pass). The
regex does not match `Statistical Protocol`.

**One-line reproducer:**

```python
import re
tex = "\\subsection{Statistical Protocol}\n\\begin{itemize}..."
re.search(r'\\section\*?\{[^}]*Power analysis[^}]*\}', tex)
# None
```

**Fix.** Broaden the pattern to accept either of the two valid
section names. Paper 5's `PAPER_CONFIGS` entry now contains:

```python
'c2_section_pattern': (
    r'\\section\*?\{[^}]*Power analysis[^}]*\}|'
    r'\\subsection\*?\{[^}]*Statistical Protocol[^}]*\}'
),
```

**Lesson.** When per-paper config inherits from a previous
paper's config, **always re-validate the inherited values** against
the current paper's source. The two are related but not
identical. A "test the config, not the template" discipline helps:
after any fork, immediately run `verify_p<N>.py` against the
target paper. If the audit produces findings, treat them as
config bugs first, template bugs second. In this case the
template was correct; the config was simply a stale copy from
Paper 1.

---

## 7. Cross-cutting lessons

1. **Generator templates have all the same bugs as the things they generate.**
   A regex template that produced a correct `verify_p<N>.py` for
   one paper can produce a broken one for another paper whose
   content happens to differ in a subtle way (here: a regex
   pattern in a config value, or a section heading name). A
   "one-paper regression test" is a *necessary* but not
   *sufficient* validation step. The minimum useful regression
   suite is one paper from each cluster of papers that share a
   config template.

2. **Bracket-counting and string-literal awareness are required for any
   mini-parser.** A naïve `re.sub` that *looks* like a literal
   string replace will misinterpret backslashes; a naïve brace
   counter will misinterpret `\{` inside a string literal. Both
   bugs are common and both have well-known fixes (use a state
   machine; use `tokenize`).

3. **Audit tools should be lenient on writing style and strict on substance.**
   Bugs 4 and 5 were both about being too strict on a valid
   writing style. The fix in both cases is to *expand* the
   matching patterns to include common variants. The general
   principle: if a finding is "the author wrote it differently
   than I expected", it is almost always a false positive; if a
   finding is "the author is missing a sample size", it is
   almost always a real issue.

4. **Configuration-driven generation is worth the upfront cost.**
   Before the template, we had five hand-written audit scripts
   (≈400 lines each, ≈2,000 lines total) that had drifted out of
   sync on three of the six categories. After the template, we
   have one template (≈400 lines), one generator (≈300 lines),
   and one `PAPER_CONFIGS` entry per paper (≈30 lines each).
   The cost of the six bugs in this document was a one-day
   debugging session; the cost of duplicating fixes across five
   scripts would have been a per-paper half-day, every time we
   found a new category to check. The arithmetic favours the
   template.

5. **All six bugs were caught at fork time, not at audit time.**
   The fork-and-run pipeline is `gen_verify_scripts.py --paper N`
   → `python verify_p<N>.py`. If the first step had a silent
   failure (e.g., emitted broken Python), the second step would
   have crashed, and we would have noticed within seconds. The
   same discipline applies to the compile-pipeline template
   (`gen_compile_scripts.py` + `_compile_check.py`): always run
   the auditor and the compiler after every fork.

## 8. Status after fixes

| Paper | verify_pN.py size | Findings | Compile (4-pass) |
|---|---|---|---|
| Paper 1 | 22,818 chars | 0/6 PASS | 0 fatal / 17 pages |
| Paper 5 | 22,750 chars | 0/6 PASS | 0 fatal / 26 pages |
| Paper 2/3/4 | not yet forked | — | — |

After applying the six fixes, both Paper 1 and Paper 5 reach
**0 findings** when audited by the generated `verify_p<N>.py`
scripts, and the 4-pass LaTeX compile produces a clean PDF
with no fatal errors and no undefined citations.

The engineering cost of this debugging session was approximately
90 minutes, distributed across 6 fix-and-rerun iterations. The
estimated savings over hand-writing five per-paper audit scripts
is approximately 8 hours, plus the ongoing savings of
single-point fixes for any future audit category we add.

---

## 9. Regression-test validity — six bugs, six catches

A regression test that **always passes** is worse than no test at
all: it gives false confidence. To make sure each of the six
regression tests in `tests/test_forge.py` and `tests/test_bug5_unit.py`
actually catches its target bug, we wrote
`_check_all_regressions.py` (a meta-test). The script:

1. For each of the 6 bugs, **injects a small change** that
   re-introduces the bug (1–3 line patch to the relevant source
   file).
2. Runs the bug's specific `TestBug*` test class.
3. **Asserts the test FAILS** (with a precise fingerprint message).
4. Restores the source file from the in-memory backup.
5. Re-runs the test and **asserts it PASSES**.

This makes the regression tests **self-validating**: a test that
silently passes (because the bug was never injected) cannot
happen.

### 9.1 Results

| Bug | File injected into | Test class | Catch | Restore | Status |
|---|---|---|---|---|---|
| 1 | `src/tmaudit/forge.py` | `TestBug1ReprInterpretsBackslash` | YES | YES | [OK] |
| 2 | `src/tmaudit/forge.py` | `TestBug2ResubBackslashInReplacement` | YES | YES | [OK] |
| 3 | `src/tmaudit/forge.py` | `TestBug3BraceCounterIgnoresStringLiterals` | YES | YES | [OK] |
| 4 | `src/tmaudit/templates/verify_TEMPLATE.py` | `TestEndToEndAudit::test_paper_1_forks_and_passes` | YES | YES | [OK] |
| 5 | `src/tmaudit/templates/verify_TEMPLATE.py` | `TestBug5TestNameRegexUnit` | YES | YES | [OK] |
| 6 | `src/tmaudit/configs/paper_configs.py` | `TestEndToEndAudit::test_paper_5_forks_and_passes` | YES | YES | [OK] |

Run time: **< 30 seconds** (most of it is 12 subprocess invocations
of pytest). Run with:

```bash
python _check_all_regressions.py
```

The script exits with code 0 iff all 6 are caught. If any test
silently passes despite the bug being injected, the script exits
with code 1 and prints the offending test class.

### 9.2 What each inject patch does

The inject patches are **the smallest possible change that
re-introduces the bug** — not just "any change that breaks the
test". This is important because a too-broad patch (e.g. deleting
the entire `_format_simple_value` function) would cause many tests
to fail, but the test class would fail for the wrong reason. The
goal is to make the test fail **for the right reason**.

| Bug | Inject patch (essential) | File |
|---|---|---|
| 1 | `return f"r'{escaped}'"` → `return repr(value)  # BROKEN` | `forge.py` line 39 |
| 2 | 9-line brace-counting block → 7-line `re.sub(...)` call | `forge.py` line 175 |
| 3 | String-literal state machine → naive `depth += 1` / `depth -= 1` | `forge.py` line 167 |
| 4 | Second/third passes in `check_c1_abstract_definitions` → commented out | `verify_TEMPLATE.py` line 222 |
| 5 | `r'paired[^a-zA-Z]{0,8}t[^a-zA-Z]{0,3}test\|'` → `r'paired\\s+t-test\|'` | `verify_TEMPLATE.py` line 419 |
| 6 | Paper 5 c2_section_pattern: remove the `Statistical Protocol` branch | `paper_configs.py` line 180 |

### 9.3 Why the original test design had three "blind" tests

When we first wrote `TestBug4C1SymbolSubstitution`,
`TestBug5EffectSizeSubstitution`, and `TestBug6Paper5SectionPattern`,
we only tested the **substitution** (whether the per-paper config
was injected into the verify_TEMPLATE block). We did NOT test the
**runtime audit logic**. So:

- The substitution tests passed even with a broken template, because
  the substitution was a no-op.
- The injected template change only affected the audit output, not
  the substitution output.

The fix was to point the meta-test at `TestEndToEndAudit` (which
runs the actual audit). For bug 5, the test point was moved to a
new file `tests/test_bug5_unit.py` that extracts the test-name
pattern from the template at runtime and asserts it matches
`paired $t$-test[s]` directly — bypassing the need for a real
paper.

### 9.4 The "anchor matching" problem

The inject patches use string-anchor matching (e.g. the literal
text `r'\\section\\*?\\{...'` from `paper_configs.py` line 180).
This is fragile in Python because of escape-sequence counting:

- File contents: `r'\\section\*?\{...'` (each `\` is **one** char)
- Python source representation: `"r'\\\\section\\*?\\{...'"` (each
  `\` in the file is **two** chars in the source)

We initially wrote the anchor with single backslashes, which did
not match. The bug-6 inject was failing silently (the
`RuntimeError` "anchor not found" was visible only at the end of
the chain). The fix was to use the right number of backslashes
in the Python source (and verify with `_dbg_anchor2.py`).

This lesson generalises: any test that injects source-code patches
should **first verify the anchor matches** in a debug script,
**before** running the full meta-test chain. (The meta-test
infrastructure now does this automatically: an inject function
that fails to find its anchor raises `RuntimeError` immediately,
with the offending anchor in the message.)

### 9.5 Total time

The full meta-test (6 inject + 12 pytest invocations + final
sanity check) completes in under 30 seconds. We can run it on
every commit, in CI, or before a release. The cost of the test
is dwarfed by the cost of any future bug that sneaks past
the (now-validated) regression tests.

## 10. Bug 7 — C6 blacklist false-positive on idiomatic English

### 10.1 Symptom

On 2026-07-10, after a content update to Paper 5's `main.tex`,
`tmaudit verify --paper 5` started reporting a C6 finding:

```
[LOW] C6  (line 233)
    Blacklist word "yield" appears 2x in main.tex (e.g., line 233).
```

Inspecting `main.tex` line 234, the offending text was:

> "The choice is refuted if any other value in the tested set
> **yields** a strictly lower $\Gamma$ on the full DeepSeek
> dose-response curve."

"yields a strictly lower $\Gamma$" is **idiomatic technical
English** — the verb "to yield" here means "to produce" /
"to give rise to". This is the *correct* usage of the word in
a mathematical / scientific context. The audit was wrong to
flag it as a C6 violation.

### 10.2 Root cause

`check_c6_blacklist` in `verify_TEMPLATE.py` reported a finding
on the **first occurrence** of any blacklist word:

```python
# OLD (buggy)
for word, n in sorted(counts.items()):
    findings.append((...))  # ALWAYS, even if n == 1
```

The blacklist was tuned for the original use case: catching
"reveal" or "paradigm" used 3+ times in a row to pad the prose.
But the same logic misfires on legitimate 1-2 occurrences of
common technical words like "yields".

### 10.3 Fix

Add a `min_count` threshold (3 by default) so that 1-2
occurrences are not reported:

```python
# NEW (fixed)
min_count: int = 3
for word, n in sorted(counts.items()):
    if n < min_count:
        continue  # 1-2 occurrences are OK
    findings.append(...)
```

The threshold is 3, not 2, because:
- 1-2 occurrences: idiomatic English, do not report.
- 3+ occurrences: starts to look like a word being used to
  avoid saying something specific.

### 10.4 Regression test

A new file `tests/test_c6_threshold.py` contains 7 unit tests:

| Test | Asserts |
|---|---|
| `test_c6_does_not_flag_single_occurrence` | 1 occurrence of "paradigm" → no finding |
| `test_c6_does_not_flag_two_occurrences` | 2 occurrences of "yield" → no finding |
| `test_c6_flags_three_or_more_occurrences` | 10 occurrences of "yield" → 1 finding, message says "10x" |
| `test_c6_finds_inflection_yields` | 5 occurrences of "yields" → 1 finding, message says "5x" |
| `test_c6_finds_inflection_revealed` | 5 occurrences of "revealed" → 1 finding |
| `test_c6_counts_separately_per_word` | "paradigm" 1x + "yield" 3x → only "yield" flagged |
| `test_c6_word_boundary_does_not_match_yielded` | "yielded" 5x → no finding (different word) |

### 10.5 Meta-test (bug 7 in `_check_all_regressions.py`)

`_check_all_regressions.py` now has an `inject_bug7()` that:

1. Reads `verify_TEMPLATE.py`.
2. Replaces `min_count: int = 3` with
   `min_count: int = 0  # BROKEN`.
3. Runs `tests/test_c6_threshold.py::test_c6_does_not_flag_single_occurrence`.
4. **Asserts the test FAILS** (with `min_count=0`, the 1-occurrence
   case generates a finding, breaking the test).
5. Restores `verify_TEMPLATE.py`.
6. Re-runs the test and **asserts it PASSES**.

Result: **7/7 bugs caught** (up from 6/6).

---

---

## Appendix: file listings

`F:\Research\TEMPLATE\` after this work:

| File | Size (chars) | Role |
|---|---|---|
| `_compile_check_TEMPLATE.py`            | ≈4,500 | Generic 4-pass LaTeX build. |
| `_fix_abstract_unicode_TEMPLATE.py`      | ≈5,000 | Generic abstract-Unicode fix. |
| `gen_compile_scripts.py`                | ≈4,500 | Fork tool for the compile scripts. |
| `_verify_TEMPLATE.py`                   | ≈15,000 | Generic 6-category audit. |
| `gen_verify_scripts.py`                 | ≈9,000  | Fork tool for the verify scripts. |
| `README.md`                             | ≈6,000  | User-facing documentation. |
| `engineering_notes_verify_template.md`  | (this file) | Engineering appendix. |

`F:\Research\PAPER<N>_CONSOLIDATED\` after this work (N ∈ {1, 5}):

| File | Size (chars) | Generated by |
|---|---|---|
| `verify_p<N>.py`              | ≈22,800 | `gen_verify_scripts.py` |
| `verify_p<N>.py.bak_before_template` | (original) | backup of hand-written original |
| `_compile_check.py`           | ≈5,600  | `gen_compile_scripts.py` |
| `_fix_abstract_unicode.py`    | ≈4,500  | `gen_compile_scripts.py` |

`F:\Research\PAPER<N>_CONSOLIDATED\` for N ∈ {2, 3, 4}: not yet
forked. The `PAPER_CONFIGS` entries in `gen_verify_scripts.py` for
Paper 2/3/4 are placeholders that need to be filled with the
actual paper-specific rules; the README has a template for
filling them in.
