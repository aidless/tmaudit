<!--
This file is a draft GitHub issue. To open it as a real issue on
GitHub, copy the body (between the --- markers below) and use
`gh issue create --body-file .github/issues/16-c7-citation-context.md`
OR use the GitHub web UI and paste the body.

Title:    [Feature]: C7 audit category — citation context validation
Labels:   enhancement, area:c7, milestone:v0.1.2
Assignees: (none — open to community)
-->

---

## Summary

Add a new audit category, **C7 (citation context)**, that
validates whether the paper actually **engages with** the
works it cites, or whether the citation is **ceremonial**
(cited but never discussed).

## Why

A common weakness in ML papers (especially in the TMLR
ecosystem) is the "ceremonial cite": a paper is cited in the
related-work section but the citing paper never actually uses
or critiques the cited work. Reviewers notice this and dock
the paper for it, but it's hard to enforce systematically
because it requires **reading the citing sentence** in
context.

A C7 check would catch this automatically:

- **Engaged citation**: the citing sentence includes a verb
  like "show", "demonstrate", "argue", "extend", "improve
  upon", "follows from", "builds on", etc.
- **Ceremonial citation**: the citing sentence is just
  "Smith et al. [12] studied X." with no further context.

## Use case

I want to know which of the 30+ citations in my paper are
"ceremonial" so I can decide whether to keep them (e.g., for
completeness) or remove them. Right now I have to read every
citation manually, which is time-consuming.

A C7 check would:

1. Parse each `\cite{...}` and find the surrounding sentence.
2. Classify the sentence as "engaged" or "ceremonial" using
   a small set of heuristics (verb presence, sentence length,
   keyword match).
3. Report any "ceremonial" citation with a HIGH severity
   (reviewer concern) and an explanation.

## Proposed solution

Add a 7th check function `check_c7_citation_context` to
`src/tmaudit/templates/verify_TEMPLATE.py`. The check:

1. Walks every `\cite{...}` in `main.tex`.
2. For each cite, finds the **citing sentence** (the sentence
   containing the `\cite`).
3. Classifies the sentence as engaged or ceremonial:
   - **Engaged signals**: contains a verb like "show",
     "demonstrate", "argue", "extend", "build on", "follow",
     "use", "apply", "compare", "improve", "outperform",
     "validate", "verify".
   - **Engaged signals (alt)**: contains a comparison word
     like "however", "in contrast", "unlike", "while",
     "although", "whereas".
   - **Length signal**: citing sentence is >= 30 words
     (shorter = likely ceremonial).
   - **Pattern signal**: citing sentence starts with
     "X et al. [N] ..." (this is the canonical ceremonial
     template).
4. If **none** of the engaged signals match, mark the
   citation as ceremonial and report it as a finding.

### Example

```latex
% Ceremonial (will be flagged):
Recent work has studied this problem \cite{smith2020}.
  -> citing sentence = "Recent work has studied this problem."
  -> no engaged signal, length < 30 words, matches ceremonial pattern
  -> C7 finding: "Citation [smith2020] is ceremonial (sentence
     does not engage with the cited work)."

% Engaged (will pass):
We extend the framework of Smith et al. \cite{smith2020} by
introducing a new loss function that reduces the bias from
30% to 5%.
  -> citing sentence contains "extend" and "reduces"
  -> length > 30 words
  -> C7 finding: none
```

### CLI / output

```text
$ tmaudit verify --paper 1
  C1  [OK]     0 finding(s)
  C2  [OK]     0 finding(s)
  C3  [OK]     0 finding(s)
  C4  [OK]     0 finding(s)
  C5  [OK]     0 finding(s)
  C6  [OK]     0 finding(s)
  C7  [MED]    2 finding(s)   <-- NEW

[HIGH] C7  (line 234)
    Citation [smith2020] is ceremonial (sentence does not
    engage with the cited work). Consider removing or
    elaborating on the citation.
```

## Acceptance criteria

- [ ] `check_c7_citation_context` is implemented in
      `verify_TEMPLATE.py`.
- [ ] `paper_configs.py` has a new `c7_settings` block
      per paper (e.g., `c7_max_ceremonial: 2` to allow
      2 ceremonial cites before flagging as MED).
- [ ] `tests/test_c7_citation_context.py` has at least
      6 unit tests covering:
      - 1 engaged cite (verifies no finding)
      - 1 ceremonial cite (verifies finding)
      - 1 cite with comparison word (engaged)
      - 1 cite with short sentence (ceremonial)
      - 1 cite with long sentence + verb (engaged)
      - per-paper threshold respected
- [ ] Meta-test now reports **8/8 caught** (add `inject_bug8`).
- [ ] Paper 1 and Paper 5 audits both pass with C7 enabled
      (or are pre-validated to have < threshold ceremonial
      citations).
- [ ] `engineering_notes_verify_template.md` gets a new §11
      documenting the C7 design.
- [ ] `CHANGELOG.md` v0.1.2 section added.

## Alternatives considered

- **Use a LLM (e.g., GPT-4) to classify sentences**: more
  accurate but requires API key + cost. Defer to v0.2.0+.
- **Skip C7 entirely**: simpler but leaves a real reviewer
  concern unaddressed. The heuristic approach is good enough
  for a v0.1.2 release.
- **Only flag cites with < 5-word citing sentence**: too
  aggressive — would flag many legitimate cites.

## Affected components

- [ ] `src/tmaudit/forge.py`
- [ ] `src/tmaudit/templates/verify_TEMPLATE.py`
- [x] `src/tmaudit/configs/paper_configs.py`
- [x] `tests/`
- [ ] `hooks/`
- [ ] `.github/workflows/ci.yml`
- [x] Documentation (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`)
- [ ] Other:

## Scope

- [x] Purely additive (no existing functionality changes)
- [ ] Internal refactor (no public API change)
- [ ] Public API change (breaking — list in the section below)

## Effort estimate

- [ ] Small (< 1 day)
- [x] Medium (1-3 days)
- [ ] Large (1-2 weeks)
- [ ] X-Large (> 2 weeks)

## Are you willing to implement it?

- [x] Yes, I plan to submit a PR
- [ ] Yes, but I need help / mentorship
- [ ] No, but I'd be happy to review
- [ ] No, asking for someone else to implement

## Related issues / PRs

- Tracks the v0.1.2 milestone
- See also: v0.1.1 release notes ("What's next" section)

## Reviewer notes

I'm not sure if the heuristic approach is accurate enough —
manual validation on Paper 1 and Paper 5 would be needed to
calibrate the threshold. The biggest risk is **false
positives**: flagging a legitimate citation as ceremonial
because the heuristic missed an "engage" signal.

To mitigate: the `c7_max_ceremonial` threshold defaults to
**2** (per paper) — so 1-2 ceremonial cites are OK, 3+
are flagged. This makes the check lenient rather than
aggressive.