"""_check_yaml.py — validate .github/workflows/ci.yml is parseable
YAML with the expected top-level keys.

This catches syntax errors before pushing to GitHub, where
they would only show up in the workflow UI.
"""
from pathlib import Path
import sys

import yaml  # pyyaml

WORKFLOW = Path('F:/Research/TEMPLATE/.github/workflows/ci.yml')

text = WORKFLOW.read_text(encoding='utf-8')
try:
    doc = yaml.safe_load(text)
except yaml.YAMLError as e:
    print(f'YAML parse error: {e}')
    sys.exit(1)

# Sanity checks
required_keys = ['name', 'jobs']
for k in required_keys:
    if k not in doc:
        print(f'Missing top-level key: {k!r}')
        sys.exit(1)

# 'on' is a YAML 1.1 boolean key; in PyYAML it may parse as True.
# Accept either.
triggers = doc.get(True) or doc.get('on')
if not triggers:
    print("Missing 'on' (or True) top-level key")
    sys.exit(1)

print(f'workflow name: {doc["name"]}')
print(f'triggers: {list(triggers.keys())}')
print(f'jobs: {list(doc["jobs"].keys())}')

# Check each job has runs-on and steps
for job_name, job in doc['jobs'].items():
    if 'runs-on' not in job:
        print(f'Job {job_name!r} missing runs-on')
        sys.exit(1)
    if 'steps' not in job:
        print(f'Job {job_name!r} missing steps')
        sys.exit(1)
    n_steps = len(job['steps'])
    print(f'  job {job_name!r}: runs-on={job["runs-on"]!r}, steps={n_steps}')

# Check matrix
matrix = doc['jobs'].get('pytest', {}).get('strategy', {}).get('matrix', {})
if 'python-version' in matrix:
    print(f'pytest matrix python-version: {matrix["python-version"]}')

print('\n[OK] ci.yml is valid YAML with expected structure.')