# PUSH_v0.3.0 — Manual Steps to Publish v0.3.0

> **Status**: Local repo ready to push. Remote `liumingrui/tmaudit.git` does
> not yet exist on GitHub. v0.3.0 tag is created locally. Bundle file is
> ready as a fallback. This document lists the manual steps to publish.

## What's already done

- 27 commits on `main` since v0.1.1, all 176 tests pass, 12/12 meta-test.
- `v0.3.0` annotated tag created locally:
  ```
  v0.3.0 - 10 audit categories (C1-C10), 176 tests, 12/12 meta-test
  ```
- Bundle file: `F:\temp\tmaudit-v0.3.0.bundle` (353 KB, contains
  `main`, `v0.1.0`, `v0.1.1`, `v0.3.0`, `HEAD`).

## Manual Push Steps

### Step 1: Create the GitHub repository (one-time)

1. Open <https://github.com/new>.
2. Fill in:
   - **Owner**: `liumingrui`
   - **Repository name**: `tmaudit`
   - **Description**: `Config-driven TMLR paper audit + LaTeX compile pipeline`
   - **Visibility**: Public (recommended for a TMLR reproducer)
   - **DO NOT** tick `Initialize with README`,
     `Add .gitignore`, or `Choose a license` — we have these locally.
3. Click **Create repository**.

### Step 2A: Push via HTTPS with a Personal Access Token

1. Generate a fine-grained PAT (Settings → Developer settings → Personal
   access tokens → Tokens (classic) → Generate new token):
   - Scope: **`repo`** (includes `public_repo`, `repo:status`)
   - Expiration: 30 days
2. Copy the token (looks like `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`).
3. Push (use the token as the password):
   ```powershell
   cd F:\Research\TEMPLATE
   git push -u origin main
   # When prompted: Username = liumingrui, Password = <paste token>
   git push origin v0.3.0
   git push origin --tags   # if you want all tags
   ```

### Step 2B (alternative): Use the local bundle

If you'd rather avoid typing a token in PowerShell:

1. Copy the bundle to a machine that has GitHub push access:
   ```bash
   scp F:/temp/tmaudit-v0.3.0.bundle user@remote:/tmp/
   ```
2. On the remote, in a fresh clone of your future repo (after Step 1):
   ```bash
   git clone https://github.com/liumingrui/tmaudit.git
   cd tmaudit
   git fetch /tmp/tmaudit-v0.3.0.bundle 'refs/heads/*:refs/heads/*'
   git fetch /tmp/tmaudit-v0.3.0.bundle 'refs/tags/*:refs/tags/*'
   git push origin main --tags --force-with-lease  # careful with --force-with-lease
   ```

### Step 3: Verify the release on GitHub

1. Visit <https://github.com/liumingrui/tmaudit/releases>.
2. Click **Draft a new release**:
   - Choose tag: `v0.3.0`
   - Title: `v0.3.0 — 10 audit categories, statistical rigor`
   - Description: paste the Highlights from `RELEASE_NOTES_v0.3.0.md`.
3. Click **Publish release**.

## What if it still fails?

| Symptom | Likely cause | Fix |
|---|---|---|
| `Repository not found` | Repo not yet created on GitHub | Step 1 |
| `Authentication failed` | Token missing or wrong scope | Re-generate with `repo` scope |
| `Permission denied (publickey)` | SSH key not configured | Use HTTPS + PAT (this guide) |
| `non-fast-forward` (rejected) | Remote has commits we don't have | Verify with `git log origin/main..HEAD` (should be 27+); if remote is empty it's fine |
| `commits author email rejected` | `liumingrui@example.com` not in your verified emails | Either verify it on GitHub, or rewrite authors: `git commit --amend --reset-author --no-edit` on each commit |

## Fallback: if you want to push under a different identity

The local git config has user `liumingrui <liumingrui@example.com>` but the
global gitconfig has `aidless <101927025+aidless@users.noreply.github.com>`.
If you'd rather push as `aidless`:

```powershell
cd F:\Research\TEMPLATE
git remote set-url origin https://github.com/aidless/<repo>.git   # if the repo exists under aidless
# Also rewrite authors if you want clean attribution:
git filter-branch -f --env-filter "GIT_AUTHOR_NAME='aidless'; GIT_AUTHOR_EMAIL='101927025+aidless@users.noreply.github.com'; GIT_COMMITTER_NAME='aidless'; GIT_COMMITTER_EMAIL='101927025+aidless@users.noreply.github.com'" HEAD
```

---

Once the push succeeds, run:

```powershell
python _check_all_regressions.py   # expect 12/12 caught
```

To confirm the public repo matches v0.3.0 exactly.
