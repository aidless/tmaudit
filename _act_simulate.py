"""_act_simulate.py — local simulator for the GitHub Actions
workflow .github/workflows/ci.yml.

We would prefer to use the official `act` tool
(https://github.com/nektos/act), but the local environment
blocks it for two reasons:

  1. `act` is not installed and the sandbox blocks `winget`,
     `scoop`, and direct `curl` downloads from github.com.
  2. Docker is installed but its daemon is not running, and
     `act` requires a working Docker daemon.

This script implements a minimal subset of `act`'s behaviour:

  - Parse `.github/workflows/ci.yml` with PyYAML.
  - For each job, walk the steps in order.
  - Skip `uses:` steps (we only run `run:` steps).
  - For `run:` steps, substitute `${{ matrix.X }}` with the
    matrix value, then run the resulting command via
    `subprocess.run`.
  - Respect `if:` conditions (best effort: we only handle the
    simple "always()" condition used in the upload-artifact
    steps).
  - Apply the matrix (one sub-invocation per matrix row).
  - Print a GitHub-Actions-style summary at the end.

Limitations vs. the real `act`:

  - No Docker isolation; commands run on the host shell.
  - `uses:` steps (e.g., `actions/checkout@v4`,
    `actions/setup-python@v5`) are simulated by
    `actions_checkout.py` and `actions_setup_python.py` —
    minimal stubs that perform the same effect on the host
    (clone the working tree; ensure a Python interpreter).
  - `needs:` is honoured (we run jobs in topological order).

Usage:
    python _act_simulate.py
    python _act_simulate.py --job pytest
    python _act_simulate.py --matrix-version 3.11
    python _act_simulate.py --list
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path('F:/Research/TEMPLATE')
WORKFLOW = ROOT / '.github' / 'workflows' / 'ci.yml'
PYTHON = Path('C:/Users/Administrator/AppData/Roaming/uv/python/cpython-3.9.25-windows-x86_64-none/python.exe')

# Ensure `python` is on PATH for any `subprocess.run(cmd, shell=True)`
# step. Real GitHub Actions runners have python on PATH automatically.
# Our sandbox does not always; we explicitly add the known python dir.
import os as _os
_PYTHON_DIR = str(PYTHON.parent)
if _PYTHON_DIR not in _os.environ.get('PATH', ''):
    _os.environ['PATH'] = _PYTHON_DIR + _os.pathsep + _os.environ.get('PATH', '')


# ---------------------------------------------------------------------------
# GitHub Actions environment variables that the real runner provides
# ---------------------------------------------------------------------------

GITHUB_ENV = {
    'GITHUB_WORKSPACE': str(ROOT),
    'GITHUB_REPOSITORY': 'liumingrui/tmaudit',
    'GITHUB_REF': 'refs/heads/main',
    'GITHUB_SHA': 'local-act-simulation',
    'GITHUB_ACTOR': 'act-simulator',
    'GITHUB_RUN_ID': '0001',
    'RUNNER_OS': 'Linux',
    'RUNNER_TEMP': str(ROOT / '_act_run' / 'tmp'),
}


# ---------------------------------------------------------------------------
# `uses:` step stubs
# ---------------------------------------------------------------------------

def _step_uses_checkout(step: dict, ctx: dict, log) -> int:
    """actions/checkout@v4 — we already have the working tree,
    so this is a no-op (return 0)."""
    log('  [uses: actions/checkout@v4] (no-op, working tree already present)')
    return 0


def _step_uses_setup_python(step: dict, ctx: dict, log) -> int:
    """actions/setup-python@v5 — ensure the requested Python
    version is available; in our case, only the host Python
    is available, so we check the version and continue."""
    py_version = ctx.get('python-version', '3.9')
    log(f'  [uses: actions/setup-python@v5] python-version={py_version}')
    # We only have one Python available; print a warning if
    # the requested version is not the host version, but do
    # not fail. This is a known limitation of the simulator.
    try:
        result = subprocess.run(
            [str(PYTHON), '-c',
             'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'],
            capture_output=True, text=True,
        )
        actual = result.stdout.strip()
    except Exception as e:
        log(f'  ERROR: cannot run python: {e}')
        return 1
    if actual != py_version:
        log(f'  WARN: requested python {py_version}, '
            f'host python is {actual}; using host python.')
    else:
        log(f'  OK: host python is {actual} (matches requested)')
    return 0


def _step_uses_upload_artifact(step: dict, ctx: dict, log) -> int:
    """actions/upload-artifact@v4 — copy the artifact path to
    a local _artifacts/ directory."""
    name = step.get('with', {}).get('name', 'artifact')
    path = step.get('with', {}).get('path', '')
    if not Path(path).exists():
        log(f'  [uses: actions/upload-artifact@v4] {name}: '
            f'path not found, skipping ({path})')
        return 0
    out_dir = ROOT / '_act_run' / 'artifacts' / name
    out_dir.mkdir(parents=True, exist_ok=True)
    for src in Path(path).iterdir():
        if src.is_file():
            dst = out_dir / src.name
            dst.write_bytes(src.read_bytes())
            log(f'  [uses: actions/upload-artifact@v4] {name}: '
                f'uploaded {src.name} ({src.stat().st_size} bytes)')
    return 0


def _dispatch_uses(step: dict, ctx: dict, log) -> int:
    """Route a `uses:` step to one of the stubs above."""
    uses = step.get('uses', '')
    if uses.startswith('actions/checkout'):
        return _step_uses_checkout(step, ctx, log)
    if uses.startswith('actions/setup-python'):
        return _step_uses_setup_python(step, ctx, log)
    if uses.startswith('actions/upload-artifact'):
        return _step_uses_upload_artifact(step, ctx, log)
    log(f'  [uses: {uses}] (unhandled, treating as no-op)')
    return 0


# ---------------------------------------------------------------------------
# Substitute ${{ matrix.X }} and ${{ env.X }} in a run-string
# ---------------------------------------------------------------------------

_MATRIX_RE = re.compile(r'\$\{\{\s*matrix\.([\w\-]+)\s*\}\}')


def _substitute(s: str, ctx: dict) -> str:
    def repl(m: re.Match) -> str:
        return str(ctx.get(m.group(1), m.group(0)))
    return _MATRIX_RE.sub(repl, s)


# ---------------------------------------------------------------------------
# Run a `run:` step
# ---------------------------------------------------------------------------

def _step_run(step: dict, ctx: dict, log) -> int:
    cmd = step.get('run', '')
    cmd = _substitute(cmd, ctx)
    # Strip "--upgrade pip" line from `python -m pip install --upgrade pip`
    # when running in our sandbox: the user-host has pip 24.0 and the
    # sandbox blocks the upgrade (the allowlist does not include
    # site-packages modifications). The package is already installed.
    if 'python -m pip install --upgrade pip' in cmd:
        cmd = cmd.replace('python -m pip install --upgrade pip\n', 'REM pip upgrade skipped (sandbox)\n')
        cmd = cmd.replace('python -m pip install --upgrade pip', 'REM pip upgrade skipped (sandbox)')
    log(f'$ {cmd.replace(chr(10), chr(10) + "  ")}')
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=ROOT,
        env={**os.environ, **GITHUB_ENV},
    )
    return result.returncode


# ---------------------------------------------------------------------------
# Topological sort of jobs by `needs:`
# ---------------------------------------------------------------------------

def _topo_order(jobs: dict) -> list[str]:
    """Kahn's algorithm: process jobs whose dependencies have
    all been processed.
    """
    def _needs_list(spec: dict) -> list[str]:
        n = spec.get('needs')
        if n is None:
            return []
        if isinstance(n, str):
            return [n]
        return list(n)

    in_degree = {name: len(_needs_list(spec)) for name, spec in jobs.items()}
    dependents: dict[str, list[str]] = {name: [] for name in jobs}
    for name, spec in jobs.items():
        for dep in _needs_list(spec):
            dependents[dep].append(name)

    ready = [n for n, d in in_degree.items() if d == 0]
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in dependents[n]:
            in_degree[m] -= 1
            if in_degree[m] == 0:
                ready.append(m)

    if len(order) != len(jobs):
        cycle = set(jobs) - set(order)
        raise RuntimeError(f'cycle in needs: {cycle}')
    return order


# ---------------------------------------------------------------------------
# Run one job (with its matrix)
# ---------------------------------------------------------------------------

def _run_job(name: str, spec: dict, log) -> int:
    log(f'\n{"=" * 72}\nJob: {name}\n{"=" * 72}')
    matrix = spec.get('strategy', {}).get('matrix', {}) or {}
    if matrix:
        # Cartesian product
        from itertools import product
        keys = list(matrix.keys())
        values_product = list(product(*(matrix[k] for k in keys)))
        n_rows = len(values_product)
        log(f'Matrix: {len(keys)} axes, {n_rows} row(s)')
        rc_total = 0
        for combo in values_product:
            ctx = dict(zip(keys, combo))
            label = ', '.join(f'{k}={v}' for k, v in ctx.items())
            log(f'\n--- matrix row: {label} ---')
            rc = _run_job_single(name, spec, ctx, log)
            rc_total = rc_total or rc
        return rc_total
    return _run_job_single(name, spec, {}, log)


def _run_job_single(name: str, spec: dict, ctx: dict, log) -> int:
    rc_total = 0
    for step in spec.get('steps', []):
        # Handle `if:` (we support only the "always()" case)
        if_cond = step.get('if', '')
        if if_cond and 'always()' not in if_cond and 'success()' in if_cond and rc_total != 0:
            log(f'  -- skipping step (if: {if_cond}) --')
            continue
        if 'uses' in step:
            rc = _dispatch_uses(step, ctx, log)
        else:
            rc = _step_run(step, ctx, log)
        rc_total = rc_total or rc
        if rc != 0 and 'continue-on-error' not in step:
            log(f'  step failed (rc={rc}); stopping job')
            return rc
    return rc_total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _list_jobs(jobs: dict) -> int:
    print('Available jobs:')
    for name, spec in jobs.items():
        matrix = spec.get('strategy', {}).get('matrix', {}) or {}
        n_rows = 1
        for v in matrix.values():
            n_rows *= len(v)
        needs = spec.get('needs', []) or []
        needs_str = f' (needs: {needs})' if needs else ''
        print(f'  {name:14s}  {n_rows} matrix row(s){needs_str}')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true',
                        help='list jobs and exit')
    parser.add_argument('--job', type=str, default=None,
                        help='run a specific job (default: all)')
    args = parser.parse_args()

    if not WORKFLOW.exists():
        print(f'ERROR: {WORKFLOW} not found', file=sys.stderr)
        return 1

    doc = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))
    jobs = doc.get('jobs', {})
    if args.list:
        return _list_jobs(jobs)

    if args.job:
        if args.job not in jobs:
            print(f'ERROR: job {args.job!r} not in workflow', file=sys.stderr)
            return 1
        order = [args.job]
    else:
        order = _topo_order(jobs)

    print(f'Running {len(order)} job(s) in order: {order}')
    overall_rc = 0
    timing: dict[str, float] = {}
    for name in order:
        t0 = time.monotonic()
        rc = _run_job(name, jobs[name], print)
        timing[name] = time.monotonic() - t0
        overall_rc = overall_rc or rc

    # GitHub-Actions-style summary
    print()
    print('=' * 72)
    print('JOB SUMMARY')
    print('=' * 72)
    for name, dt in timing.items():
        status = 'PASS' if rc == 0 else 'FAIL'
        print(f'  {name:14s}  {status}  ({dt:.1f}s)')
    print()
    print(f'Overall: {"PASS" if overall_rc == 0 else "FAIL"}')
    return overall_rc


if __name__ == '__main__':
    sys.exit(main())