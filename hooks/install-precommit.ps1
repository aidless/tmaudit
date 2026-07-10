# install-precommit.ps1 - install the pre-commit hook for tmaudit.
#
# Usage:  powershell -ExecutionPolicy Bypass -File hooks\install-precommit.ps1
#
# This copies hooks/pre-commit to .git/hooks/pre-commit. After
# this, every `git commit` will run the four CI steps (yaml
# check, pytest, meta-test, build pyz).
#
# To uninstall:  powershell -ExecutionPolicy Bypass -File hooks\install-precommit.ps1 -Uninstall
[CmdletBinding()]
param(
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'

# Resolve the repo root (the parent of the hooks/ directory).
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$HookSrc = Join-Path $RepoRoot 'hooks' 'pre-commit'
$HookDst = Join-Path $RepoRoot '.git' 'hooks' 'pre-commit'

if ($Uninstall) {
    if (Test-Path $HookDst) {
        $content = Get-Content $HookDst -Raw -ErrorAction SilentlyContinue
        if ($content -and $content -match 'tmaudit pre-commit hook') {
            Remove-Item $HookDst -Force
            Write-Host "Uninstalled: removed $HookDst"
        } else {
            Write-Host "No tmaudit pre-commit hook found at $HookDst"
        }
    } else {
        Write-Host "No hook file at $HookDst"
    }
    exit 0
}

if (-not (Test-Path $HookSrc)) {
    Write-Error "ERROR: $HookSrc not found. Are you running this from the repo root?"
    exit 1
}

# Backup any existing pre-commit hook
if (Test-Path $HookDst) {
    $timestamp = Get-Date -Format 'yyyyMMddHHmmss'
    $bak = "$HookDst.bak.$timestamp"
    Copy-Item $HookDst $bak -Force
    Write-Host "Backed up existing hook to: $bak"
}

Copy-Item $HookSrc $HookDst -Force
Write-Host "Installed: $HookDst"
Write-Host ""
Write-Host "Test it with:  git commit --allow-empty -m 'test pre-commit'"
Write-Host "Skip it with:  git commit --no-verify"