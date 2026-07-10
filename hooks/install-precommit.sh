#!/usr/bin/env bash
# install-precommit.sh — install the pre-commit hook for tmaudit.
#
# Usage:  ./hooks/install-precommit.sh
#
# This copies hooks/pre-commit to .git/hooks/pre-commit and makes
# it executable. After this, every `git commit` will run the
# four CI steps (yaml check, pytest, meta-test, build pyz).
#
# To uninstall:  ./hooks/install-precommit.sh --uninstall
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="$REPO_ROOT/hooks/pre-commit"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"

if [[ "${1:-}" == "--uninstall" ]]; then
    if [[ -f "$HOOK_DST" ]] && grep -q 'tmaudit pre-commit hook' "$HOOK_DST"; then
        rm -f "$HOOK_DST"
        echo "Uninstalled: removed $HOOK_DST"
    else
        echo "No tmaudit pre-commit hook found at $HOOK_DST"
    fi
    exit 0
fi

if [[ ! -f "$HOOK_SRC" ]]; then
    echo "ERROR: $HOOK_SRC not found." >&2
    echo "Are you running this from the repository root?" >&2
    exit 1
fi

# Backup any existing pre-commit hook
if [[ -f "$HOOK_DST" ]]; then
    bak="$HOOK_DST.bak.$(date +%Y%m%d%H%M%S)"
    cp "$HOOK_DST" "$bak"
    echo "Backed up existing hook to: $bak"
fi

cp "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_DST"
echo "Installed: $HOOK_DST"
echo
echo "Test it with:  git commit --allow-empty -m 'test pre-commit'"
echo "Skip it with:   git commit --no-verify"