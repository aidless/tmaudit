#!/usr/bin/env bash
# 60-second demo: audit the deliberately flawed sample paper without touching it.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp -R "$ROOT/examples/sample-paper/." "$TMP/"
cd "$ROOT"
python3 tmaudit.pyz verify --paper-dir "$TMP"
