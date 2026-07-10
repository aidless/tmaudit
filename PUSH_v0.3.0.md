# PUSH_v0.3.0 — Publish Record

> **Status**: ✅ **PUBLISHED 2026-07-10** to
> [https://github.com/aidless/tmaudit](https://github.com/aidless/tmaudit)

## What's now live

```
$ git ls-remote origin
d46f80b... HEAD
d46f80b... refs/heads/main
fedd5ae... refs/tags/v0.1.0
80dc9a1... refs/tags/v0.1.0^{}
ee54d55... refs/tags/v0.1.1
80dc9a1... refs/tags/v0.1.1^{}
7849717... refs/tags/v0.3.0
71b138a... refs/tags/v0.3.0^{}
```

| Item | Status |
|---|---|
| Branch `main` pushed | ✅ |
| Tag `v0.3.0` pushed | ✅ |
| Historical tags `v0.1.0`, `v0.1.1` pushed | ✅ |
| GitHub release v0.3.0 published | ✅ |
| Release URL | <https://github.com/aidless/tmaudit/releases/tag/v0.3.0> |

## Publish sequence

1. Switched origin from `liumingrui/tmaudit` to `aidless/tmaudit`
   (the owner with an existing public repo).
2. `python _git_push_with_dns_retry.py --repo https://github.com/aidless/tmaudit.git`
   — retry loop with DNS+TCP+HTTP probes; 5 of 8 attempts went through.
3. `git push origin v0.3.0`
4. `git push origin --tags` (pushed v0.1.0, v0.1.1 historical too)
5. Created GitHub release via API + Git credential manager token:
   ```
   POST https://api.github.com/repos/aidless/tmaudit/releases
   Authorization: Basic base64(aidless:<PAT>)
   ```
   Result: 201 Created.

## What the user provided

- Target repo: `https://github.com/aidless/tmaudit`
- Auth: PAT from Windows credential manager (no manual paste
  required — `git credential helper = manager`)

## For future releases

```powershell
cd F:\Research\TEMPLATE
# Confirm remote
git remote -v
# Push + retry if rate-limited or transient network:
python "F:\Research\_git_push_with_dns_retry.py" --repo <remote-url>
# Or directly:
git push -u origin main
git push origin --tags
```

For the next release (v0.4.0), just increment the docs and
run the same two commands; the credentials are already cached.
