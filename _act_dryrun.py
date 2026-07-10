"""_act_dryrun.py — dry-run the GitHub Actions workflow
.github/workflows/ci.yml.

This script:
  1. Parses the workflow with PyYAML.
  2. Resolves the `needs:` graph into a topological order.
  3. For each job, expands the matrix into rows.
  4. For each step in each job, prints what would be run
     (the `run:` command, the substituted matrix vars, the
     uses: action name).
  5. Does NOT execute any commands — this is purely a
     preview/sanity check.

This is the closest equivalent to `act -n` (dry-run) that
runs without Docker, without network, and without `act`
itself.
"""
from __future__ import annotations
import argparse
import re
import sys
from itertools import product
from pathlib import Path
from typing import Any

import yaml

ROOT = Path('F:/Research/TEMPLATE')
WORKFLOW = ROOT / '.github' / 'workflows' / 'ci.yml'

_MATRIX_RE = re.compile(r'\$\{\{\s*matrix\.([\w\-]+)\s*\}\}')


def _substitute(s: str, ctx: dict) -> str:
    def repl(m: re.Match) -> str:
        return str(ctx.get(m.group(1), m.group(0)))
    return _MATRIX_RE.sub(repl, s)


def _print_step(step: dict, ctx: dict, indent: str) -> None:
    if 'uses' in step:
        print(f'{indent}  [uses] {step["uses"]}', end='')
        with_dict = step.get('with', {})
        if with_dict:
            print(f'   with: {with_dict}', end='')
        print()
        if_cond = step.get('if', '')
        if if_cond:
            print(f'{indent}        if: {if_cond}')
    elif 'run' in step:
        cmd = _substitute(step['run'], ctx)
        for line in cmd.splitlines():
            print(f'{indent}  $ {line}')
        if_cond = step.get('if', '')
        if if_cond:
            print(f'{indent}    if: {if_cond}')


def _expand_matrix(matrix: dict) -> list[dict]:
    if not matrix:
        return [{}]
    keys = list(matrix.keys())
    return [dict(zip(keys, combo))
            for combo in product(*(matrix[k] for k in keys))]


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=str, default=None,
                        help='only show this job')
    args = parser.parse_args()

    if not WORKFLOW.exists():
        print(f'ERROR: {WORKFLOW} not found')
        return 1
    doc = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))
    jobs = doc.get('jobs', {})

    triggers = doc.get(True) or doc.get('on') or {}
    print(f'Workflow: {doc.get("name", "(unnamed)")}')
    print(f'Triggers: {list(triggers.keys())}')
    print()
    print('Job graph:')
    for name, spec in jobs.items():
        needs = spec.get('needs', []) or []
        runs_on = spec.get('runs-on', '(none)')
        arrow = f' <- {needs}' if needs else ''
        print(f'  {name:14s}  ({runs_on}){arrow}')
    print()

    if args.job:
        if args.job not in jobs:
            print(f'ERROR: job {args.job!r} not in workflow')
            return 1
        order = [args.job]
    else:
        order = _topo_order(jobs)

    for job_name in order:
        spec = jobs[job_name]
        matrix = spec.get('strategy', {}).get('matrix', {}) or {}
        rows = _expand_matrix(matrix)
        print('=' * 72)
        print(f'Job: {job_name}    ({len(rows)} matrix row(s))')
        print('=' * 72)
        for i, ctx in enumerate(rows, start=1):
            label = ', '.join(f'{k}={v}' for k, v in ctx.items()) or '(no matrix)'
            print(f'\n[matrix row {i}/{len(rows)}]  {label}')
            for j, step in enumerate(spec.get('steps', []), start=1):
                name = step.get('name', f'step-{j}')
                print(f'  Step {j}: {name}')
                _print_step(step, ctx, indent='    ')
    return 0


if __name__ == '__main__':
    sys.exit(main())