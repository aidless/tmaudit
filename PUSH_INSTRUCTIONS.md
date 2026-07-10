# Push Instructions for tmaudit v0.1.1

**Status as of 2026-07-10**: The repository is **ready to push**
locally. Two commits + two tags exist. The `origin` remote is
configured to point at `https://github.com/liumingrui/tmaudit.git`,
but **that repository does not yet exist on GitHub**. You need
to create it before pushing.

## What is already done locally

```
$ git log --oneline --decorate
80dc9a1 (HEAD -> main, tag: v0.1.1, tag: v0.1.0) feat: initial release of tmaudit v0.1.1
7f29b30 chore: add .gitignore for tmaudit

$ git tag -l
v0.1.0
v0.1.1

$ git status
On branch main
nothing to commit, working tree clean
```

- 49 files committed (48 in the feat commit + 1 .gitignore)
- 10,049 lines of code, tests, and documentation
- 2 tags: `v0.1.0` and `v0.1.1` (both point at commit `80dc9a1`)
- `origin` remote is `https://github.com/liumingrui/tmaudit.git`

## Step 1: Create the GitHub repository

Open <https://github.com/new> and create a new repository:

- **Owner**: `liumingrui` (or your own GitHub username if different)
- **Repository name**: `tmaudit`
- **Description**: "Local-only LaTeX paper audit tool (C1..C6 categories) for TMLR-style submissions"
- **Visibility**: Public (or Private if you prefer)
- **Initialize**: **Do NOT** add README, .gitignore, or license —
  the local repo already has these.

Click "Create repository".

## Step 2: Push to GitHub

If you used the same name (`liumingrui/tmaudit`), the existing
remote will work as-is:

```bash
cd F:\Research\TEMPLATE
git push -u origin main
git push origin v0.1.0
git push origin v0.1.1
```

If you used a different name, update the remote first:

```bash
cd F:\Research\TEMPLATE
git remote set-url origin https://github.com/YOUR_USERNAME/tmaudit.git
git push -u origin main
git push origin v0.1.0
git push origin v0.1.1
```

You will be prompted for your GitHub username and password
(or, if you have 2FA enabled, a personal access token). To
create a token: <https://github.com/settings/tokens>.

## Step 3: Create the v0.1.1 GitHub Release

### Option A: Using `gh` CLI (recommended)

```bash
# Install: https://cli.github.com/
gh release create v0.1.1 \
    --title "v0.1.1 — Bug 7 fix: C6 blacklist false-positive" \
    --notes-file RELEASE_NOTES_v0.1.1.md \
    --target main \
    tmaudit.pyz
```

The `--notes-file` flag uses our `RELEASE_NOTES_v0.1.1.md` as
the release body. The `tmaudit.pyz` argument attaches the
46 KB single-file distribution to the release so users can
download it directly.

### Option B: Using the GitHub web UI

1. Go to <https://github.com/liumingrui/tmaudit/releases/new>
2. **Tag version**: `v0.1.1`
3. **Release title**: `v0.1.1 — Bug 7 fix: C6 blacklist false-positive`
4. **Description**: paste the contents of
   [`RELEASE_NOTES_v0.1.1.md`](./RELEASE_NOTES_v0.1.1.md)
5. **Attach binaries**: drag-drop or upload `tmaudit.pyz`
6. Click "Publish release"

## Step 4: Verify

After pushing, verify everything works:

```bash
# Check the repository is public and main branch is visible
gh repo view liumingrui/tmaudit

# Check the v0.1.1 release exists
gh release view v0.1.1

# Or, in a browser:
#   https://github.com/liumingrui/tmaudit
#   https://github.com/liumingrui/tmaudit/releases/tag/v0.1.1
#   https://github.com/liumingrui/tmaudit/blob/v0.1.1/README.md
```

## Step 5: Trigger the CI

The CI workflow at `.github/workflows/ci.yml` will run
automatically on the first push to `main`. You can also
trigger it manually:

1. Go to the "Actions" tab on GitHub.
2. Click "CI" in the left sidebar.
3. Click "Run workflow" → select `main` → "Run".

The CI runs 3 jobs (pytest matrix, meta-test, lint) on
Python 3.9, 3.10, 3.11, 3.12. All 14 sub-jobs should pass.

## What if the push fails?

If `git push` returns an authentication error, you need
to set up credentials:

### HTTPS (recommended for first-time setup)

1. Create a personal access token at
   <https://github.com/settings/tokens> (scopes: `repo`,
   `workflow`).
2. Use the token as the password when prompted.

### SSH (recommended for daily use)

1. Generate an SSH key: `ssh-keygen -t ed25539 -C "your@email"`.
2. Add the public key to <https://github.com/settings/keys>.
3. Switch the remote to SSH:
   `git remote set-url origin git@github.com:liumingrui/tmaudit.git`.
4. Push: `git push -u origin main`.

## What the GitHub UI will look like

After pushing, the repository will show:

- 49 files on `main`
- 2 tags (`v0.1.0`, `v0.1.1`)
- 1 release (`v0.1.1` with `tmaudit.pyz` attached)
- 4 badges in the README (CI, Python, Tests, Meta-tests,
  PR checks, Issues, Security, Version, License)
- 9 community-health files in `.github/`
- A green CI checkmark on the latest commit

## FAQ

**Q: Do I need to create `liumingrui/tmaudit` or can I use my own name?**
A: Use your own name if `liumingrui` is not your GitHub
username. Just update the remote URL and the badges in
`README.md` (the badge URLs are `liumingrui/tmaudit` placeholders).

**Q: Can I push to a different branch first?**
A: Yes. `git checkout -b release/v0.1.1`, then `git push -u origin release/v0.1.1`.
After verifying the CI is green on that branch, open a PR
to merge into `main`.

**Q: I want to make the repo public but the README has my local paths in it.**
A: The README references `F:/Research/PAPER*_CONSOLIDATED`
which is a Windows path on your machine. If you don't want
to expose your local file structure, replace those paths
with relative paths like `./paper1` or with placeholder
names before pushing.

**Q: The .github/CODEOWNERS lists @liumingrui. Will that cause issues?**
A: If you use a different GitHub username, update the
`@liumingrui` references in `CODEOWNERS` and
`dependabot.yml` to your username.

**Q: Will the release page have `tmaudit.pyz` as a download?**
A: Yes — `tmaudit.pyz` is in the repository (53,827 bytes) and
will be attached to the release as a download link.

---

**When you've finished pushing, the project is officially
live.** Welcome to v0.1.1! 🎉
