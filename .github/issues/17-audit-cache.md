<!--
This file is a draft GitHub issue. To open it as a real issue on
GitHub, copy the body (between the --- markers below) and use
`gh issue create --body-file .github/issues/17-audit-cache.md`
OR use the GitHub web UI and paste the body.

Title:    [Feature]: Audit-cache layer for instant re-runs
Labels:   enhancement, area:performance, milestone:v0.1.2
Assignees: (none — open to community)
-->

---

## Summary

Add a **content-addressed cache** for audit results: if
`tmaudit verify --paper N` is run twice on the same `main.tex`
and `refs.bib` (no changes), the second run is **instant**
(returns the cached result).

## Why

Right now, `tmaudit verify --paper N` does the following
on every run:

1. Read `main.tex` (60-70 KB)
2. Read `refs.bib` (1-5 KB)
3. Run 6 checks (C1..C6) on the text
4. Format the output

Steps 1-3 take **~150 ms** on a typical paper. For most
papers, the audit **passes cleanly** — so we are redoing
work whose result we already know.

A cache would help in three scenarios:

1. **Re-running after a non-content change**: e.g.,
   `tmaudit verify --paper 1` → result is "all good" →
   user runs again 5 minutes later → should be instant.
2. **CI on a known-good commit**: the CI workflow runs
   the audit on every push, but the paper content
   usually hasn't changed → cache hit saves ~150 ms per
   job × 5 jobs = ~750 ms per CI run.
3. **Iterating on the audit logic itself**: when changing
   `verify_TEMPLATE.py`, the cache is invalidated, so
   the next run is fresh.

## Use case

I run `tmaudit verify --paper 1` 5-10 times a day while
editing. Each run takes 150 ms. With a cache, the 9/10
runs that are no-ops (no content change) would be **< 5 ms**
(just a cache lookup). This is a **30× speedup** for the
common case.

## Proposed solution

Add a content-addressed cache in `~/.cache/tmaudit/`:

```
~/.cache/tmaudit/
├── cache.db         # SQLite database
└── lock             # lockfile to prevent concurrent writes
```

### Cache key

The cache key is the SHA-256 of the **content** being
audited:

```
key = sha256( main.tex + ":" + refs.bib )
```

If the content changes by a single byte, the key changes
and the cache is invalidated for that paper.

### Cache value

The cache value is the **structured audit result** as JSON:

```json
{
  "paper_id": 1,
  "content_hash": "abc123...",
  "timestamp": "2026-07-10T15:00:00Z",
  "version": "0.1.2",
  "findings": [
    {"category": "C1", "severity": "OK", "count": 0},
    {"category": "C2", "severity": "OK", "count": 0},
    ...
  ],
  "exit_code": 0,
  "summary": "All checks passed. 0 finding(s)."
}
```

### CLI

```bash
# Default: use cache, write new results to cache
$ tmaudit verify --paper 1
[cache] HIT: paper 1, content hash abc123
All checks passed. 0 finding(s).
[exit 0]

# --no-cache: bypass cache (force fresh run)
$ tmaudit verify --paper 1 --no-cache
[cache] MISS: paper 1, computing fresh result
All checks passed. 0 finding(s).
[exit 0]

# --clear-cache: clear the cache (e.g., after a tmaudit upgrade)
$ tmaudit --clear-cache
[cache] Cleared 47 entries (3.2 MB freed)

# --cache-info: show cache statistics
$ tmaudit --cache-info
[cache] 47 entries, 3.2 MB total
[cache] Oldest entry: 2026-06-15T10:00:00Z
[cache] Hit rate: 92% (lifetime)
```

### Implementation

1. New module `src/tmaudit/cache.py` with:
   - `class CacheDB` — SQLite wrapper
   - `def get(key) -> Optional[dict]` — fetch cached result
   - `def put(key, value)` — store result
   - `def clear()` — drop all entries
   - `def stats() -> dict` — cache statistics
2. `cli.py` integrates cache lookup at the start of
   `verify` and writes the result at the end.
3. `paper_configs.py` adds a per-paper `c_cache_enabled: bool`
   flag (default `True`) so users can opt out per paper.

## Acceptance criteria

- [ ] `src/tmaudit/cache.py` implements `CacheDB` with
      SQLite backing.
- [ ] `tmaudit verify --paper N` does a cache lookup on
      entry and reuses the result on hit.
- [ ] `tmaudit verify --paper N --no-cache` bypasses the
      cache and computes a fresh result.
- [ ] `tmaudit --clear-cache` drops all cached entries.
- [ ] `tmaudit --cache-info` shows hit rate and size.
- [ ] A `.cache-hash-mismatch` (paper content changed) is
      detected: cache is invalidated, fresh result is
      computed, and the new result is stored.
- [ ] `tests/test_cache.py` has at least 5 unit tests:
      - cache hit returns the same result
      - cache miss (new content) computes fresh
      - --no-cache bypasses
      - --clear-cache drops entries
      - corrupt cache file is handled gracefully
- [ ] All existing tests still pass (53/53 minimum).
- [ ] `engineering_notes_verify_template.md` gets a new
      §12 documenting the cache design.
- [ ] `CHANGELOG.md` v0.1.2 section added.
- [ ] Cache hit is **< 5 ms** (measured) on a typical paper.

## Alternatives considered

- **Hash by file mtime instead of content**: faster but
  less correct (mtime can change without content change).
- **No cache, just a "fast" pre-check that skips if
  nothing changed**: less flexible, no historical record.
- **Use a third-party library (e.g., `cachetools`)**: adds
  a dependency for ~50 lines of code. Defer to v0.2.0 if
  we need LRU/LFU semantics.

## Affected components

- [ ] `src/tmaudit/forge.py`
- [x] `src/tmaudit/cli.py`
- [ ] `src/tmaudit/templates/verify_TEMPLATE.py`
- [ ] `src/tmaudit/templates/compile_check_TEMPLATE.py`
- [ ] `src/tmaudit/templates/fix_abstract_unicode_TEMPLATE.py`
- [x] `src/tmaudit/configs/paper_configs.py`
- [ ] `src/tmaudit/configs/compile_configs.py`
- [x] `tests/`
- [ ] `hooks/`
- [ ] `.github/workflows/ci.yml`
- [x] Documentation (`README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `engineering_notes_verify_template.md`)
- [x] New file: `src/tmaudit/cache.py`

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

The cache should be **opt-in** for v0.1.2 (controlled by
`c_cache_enabled` per paper), and **opt-out** for v0.2.0
(defaults to `True`). This gradual rollout reduces the
risk of cache-related bugs in production.

The cache should be **invalidate-on-version-change**:
when `tmaudit` is upgraded, the cache is automatically
cleared (the `version` field in the cache value is used
to detect this).