"""_check_github_templates.py — validate all GitHub community
files (issue templates, PR template, workflows, CODEOWNERS,
dependabot, conduct, support).

Exit codes:
  0 = all critical checks pass (warnings allowed)
  1 = at least one critical check failed
  2 = internal error (e.g., file not found)

Usage:
  python _check_github_templates.py
  python _check_github_templates.py --strict   # warnings also fail
  python _check_github_templates.py --json     # JSON output for CI

The script is designed to be run from the repository root.

This script is part of the project's own CI: it runs as a
"validate community files" job in .github/workflows/ci.yml.
A failure here means the PR will be blocked.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent
GITHUB_DIR = ROOT / '.github'
ISSUE_DIR = GITHUB_DIR / 'ISSUE_TEMPLATE'
WORKFLOWS_DIR = GITHUB_DIR / 'workflows'

# The 4 issue templates we expect
EXPECTED_ISSUE_TEMPLATES = [
    'bug_report.md',
    'feature_request.md',
    'enhancement.md',
    'docs.md',
]


class Result:
    """One check result."""
    def __init__(self, dim, status, detail):
        self.dim = dim
        self.status = status  # 'OK' | 'WARN' | 'FAIL'
        self.detail = detail

    def __str__(self):
        return f'[{self.status:4s}] {self.dim}: {self.detail}'


def _print(json_mode, msg):
    """Print only when not in JSON mode."""
    if not json_mode:
        print(msg)


# ============================================================================
# Section 1: .github/ directory structure
# ============================================================================
def check_github_dir(results, json_mode):
    _print(json_mode, '\n[1] .github/ directory structure')
    if not GITHUB_DIR.exists():
        results.append(Result('1. .github/ exists', 'FAIL', 'directory missing'))
        return
    _print(json_mode, '    OK: .github/ exists')
    results.append(Result('1. .github/ exists', 'OK', str(GITHUB_DIR)))

    for sub in ['ISSUE_TEMPLATE', 'workflows', 'PULL_REQUEST_TEMPLATE.md']:
        p = GITHUB_DIR / sub
        if p.exists():
            _print(json_mode, f'    OK: {sub} exists')
            results.append(Result(f'1. {sub}', 'OK', 'present'))
        else:
            _print(json_mode, f'    FAIL: {sub} missing')
            results.append(Result(f'1. {sub}', 'FAIL', 'missing'))


# ============================================================================
# Section 2: ISSUE_TEMPLATE/config.yml
# ============================================================================
def check_config_yml(results, json_mode):
    _print(json_mode, '\n[2] .github/ISSUE_TEMPLATE/config.yml')
    p = ISSUE_DIR / 'config.yml'
    if not p.exists():
        results.append(Result('2. config.yml exists', 'FAIL', 'missing'))
        return

    text = p.read_text(encoding='utf-8')
    try:
        cfg = yaml.safe_load(text)
        results.append(Result('2. config.yml valid YAML', 'OK', 'parsed'))
    except yaml.YAMLError as e:
        results.append(Result('2. config.yml valid YAML', 'FAIL', str(e)))
        return

    if cfg.get('blank_issues_enabled') is False:
        results.append(Result('2. blank_issues_enabled', 'OK', 'False'))
    else:
        results.append(Result('2. blank_issues_enabled', 'WARN',
                               f'expected False, got {cfg.get("blank_issues_enabled")}'))

    contact_links = cfg.get('contact_links', [])
    if not contact_links:
        results.append(Result('2. contact_links', 'WARN', 'empty (questions will become issues)'))
    else:
        for i, link in enumerate(contact_links, 1):
            for f in ('name', 'url', 'about'):
                if f not in link:
                    results.append(Result(f'2. contact_link[{i}].{f}', 'FAIL', 'missing'))
                else:
                    val = link[f]
                    if f == 'url':
                        parsed = urlparse(val)
                        if not all([parsed.scheme, parsed.netloc]):
                            results.append(Result(f'2. contact_link[{i}].url', 'FAIL', val))
                        elif parsed.scheme not in ('http', 'https'):
                            results.append(Result(f'2. contact_link[{i}].url', 'FAIL', val))
                        else:
                            results.append(Result(f'2. contact_link[{i}].url', 'OK', parsed.netloc))
                    elif f == 'name' and len(val) > 50:
                        results.append(Result(f'2. contact_link[{i}].name', 'WARN', f'{len(val)} chars'))
                    elif f == 'about' and len(val) > 200:
                        results.append(Result(f'2. contact_link[{i}].about', 'WARN', f'{len(val)} chars'))


# ============================================================================
# Section 3: 4 issue templates
# ============================================================================
def check_issue_templates(results, json_mode):
    _print(json_mode, '\n[3] 4 issue templates')
    template_names = []

    for name in EXPECTED_ISSUE_TEMPLATES:
        p = ISSUE_DIR / name
        if not p.exists():
            results.append(Result(f'3. {name}', 'FAIL', 'missing'))
            continue

        text = p.read_text(encoding='utf-8')
        m = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
        if not m:
            results.append(Result(f'3. {name}', 'FAIL', 'no YAML frontmatter'))
            continue

        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError as e:
            results.append(Result(f'3. {name}', 'FAIL', f'frontmatter: {e}'))
            continue

        # name
        tname = fm.get('name', '')
        if not tname:
            results.append(Result(f'3. {name} name', 'FAIL', 'missing'))
        else:
            template_names.append(tname)
            results.append(Result(f'3. {name} name', 'OK', tname))

        # description
        desc = fm.get('description', '')
        if not desc:
            results.append(Result(f'3. {name} description', 'FAIL', 'missing'))
        elif len(desc) > 200:
            results.append(Result(f'3. {name} description', 'FAIL', f'{len(desc)} chars'))
        elif len(desc) > 100:
            results.append(Result(f'3. {name} description', 'WARN', f'{len(desc)} chars (truncated in chooser)'))
        else:
            results.append(Result(f'3. {name} description', 'OK', f'{len(desc)} chars'))

        # title
        title = fm.get('title', '')
        if not title:
            results.append(Result(f'3. {name} title', 'FAIL', 'missing'))
        elif not (title.startswith('[') and title.endswith(': ')):
            results.append(Result(f'3. {name} title', 'WARN', f'expected "[Tag]: ", got {title!r}'))
        else:
            results.append(Result(f'3. {name} title', 'OK', title))

        # labels
        labels = fm.get('labels', [])
        if not labels:
            results.append(Result(f'3. {name} labels', 'WARN', 'empty'))
        elif len(labels) > 5:
            results.append(Result(f'3. {name} labels', 'FAIL', f'{len(labels)} labels (max 5)'))
        elif 'needs-triage' not in labels:
            results.append(Result(f'3. {name} labels', 'WARN', 'no "needs-triage"'))
        else:
            results.append(Result(f'3. {name} labels', 'OK', str(labels)))

        # assignees
        assignees = fm.get('assignees', None)
        if assignees is None:
            results.append(Result(f'3. {name} assignees', 'OK', 'not specified (default)'))
        elif not isinstance(assignees, list):
            results.append(Result(f'3. {name} assignees', 'FAIL', 'must be a list'))
        else:
            results.append(Result(f'3. {name} assignees', 'OK', str(assignees)))

        # body sanity
        body = text[m.end():]
        n_h2 = len(re.findall(r'^## ', body, re.MULTILINE))
        n_boxes = body.count('- [ ]')
        if n_h2 < 5:
            results.append(Result(f'3. {name} structure', 'WARN',
                                  f'only {n_h2} H2 sections'))
        else:
            results.append(Result(f'3. {name} structure', 'OK',
                                  f'{n_h2} H2 sections, {n_boxes} checkboxes'))

    # Check name uniqueness
    if len(template_names) == len(set(template_names)):
        results.append(Result('3. name uniqueness', 'OK', f'{len(template_names)} unique'))
    else:
        dups = [n for n in template_names if template_names.count(n) > 1]
        results.append(Result('3. name uniqueness', 'FAIL', f'duplicates: {set(dups)}'))


# ============================================================================
# Section 4: PULL_REQUEST_TEMPLATE.md
# ============================================================================
def check_pr_template(results, json_mode):
    _print(json_mode, '\n[4] .github/PULL_REQUEST_TEMPLATE.md')
    p = GITHUB_DIR / 'PULL_REQUEST_TEMPLATE.md'
    if not p.exists():
        results.append(Result('4. PR template exists', 'WARN', 'missing (PR body will be blank)'))
        return

    text = p.read_text(encoding='utf-8')
    n_h2 = len(re.findall(r'^## ', text, re.MULTILINE))
    n_boxes = text.count('- [ ]')

    if n_h2 < 5:
        results.append(Result('4. PR template H2 count', 'WARN', f'only {n_h2} sections'))
    else:
        results.append(Result('4. PR template H2 count', 'OK', f'{n_h2} sections'))

    if n_boxes < 10:
        results.append(Result('4. PR template checkboxes', 'WARN', f'only {n_boxes}'))
    else:
        results.append(Result('4. PR template checkboxes', 'OK', f'{n_boxes}'))

    # Must mention test / pre-merge / checklist
    lower = text.lower()
    for must_have in ['checklist', 'test']:
        if must_have not in lower:
            results.append(Result(f'4. PR template mentions {must_have!r}', 'WARN', 'not found'))
        else:
            results.append(Result(f'4. PR template mentions {must_have!r}', 'OK', 'present'))


# ============================================================================
# Section 5: CODEOWNERS
# ============================================================================
def check_codeowners(results, json_mode):
    _print(json_mode, '\n[5] .github/CODEOWNERS')
    for name in ['CODEOWNERS', 'codeowners']:
        p = GITHUB_DIR / name
        if p.exists():
            results.append(Result(f'5. {name} exists', 'OK', f'{p.stat().st_size} bytes'))
            # Basic syntax check
            text = p.read_text(encoding='utf-8')
            n_rules = sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith('#'))
            if n_rules < 1:
                results.append(Result('5. CODEOWNERS rules', 'WARN', 'no rules'))
            else:
                results.append(Result('5. CODEOWNERS rules', 'OK', f'{n_rules} rules'))
            return
    results.append(Result('5. CODEOWNERS exists', 'WARN', 'missing (no auto-assignment)'))


# ============================================================================
# Section 6: dependabot.yml
# ============================================================================
def check_dependabot(results, json_mode):
    _print(json_mode, '\n[6] .github/dependabot.yml')
    p = GITHUB_DIR / 'dependabot.yml'
    if not p.exists():
        results.append(Result('6. dependabot.yml exists', 'WARN', 'missing'))
        return
    try:
        cfg = yaml.safe_load(p.read_text(encoding='utf-8'))
        results.append(Result('6. dependabot.yml valid YAML', 'OK', 'parsed'))
        updates = cfg.get('updates', [])
        if not updates:
            results.append(Result('6. dependabot.yml updates', 'WARN', 'empty'))
        else:
            results.append(Result('6. dependabot.yml updates', 'OK', f'{len(updates)} update configs'))
    except yaml.YAMLError as e:
        results.append(Result('6. dependabot.yml valid YAML', 'FAIL', str(e)))


# ============================================================================
# Section 7: CODE_OF_CONDUCT.md
# ============================================================================
def check_conduct(results, json_mode):
    _print(json_mode, '\n[7] .github/CODE_OF_CONDUCT.md')
    p = GITHUB_DIR / 'CODE_OF_CONDUCT.md'
    if not p.exists():
        results.append(Result('7. CODE_OF_CONDUCT.md exists', 'WARN', 'missing'))
        return
    text = p.read_text(encoding='utf-8')
    n_lines = len(text.splitlines())
    if n_lines < 50:
        results.append(Result('7. CODE_OF_CONDUCT.md length', 'WARN', f'only {n_lines} lines'))
    else:
        results.append(Result('7. CODE_OF_CONDUCT.md length', 'OK', f'{n_lines} lines'))


# ============================================================================
# Section 8: SUPPORT.md
# ============================================================================
def check_support(results, json_mode):
    _print(json_mode, '\n[8] .github/SUPPORT.md')
    p = GITHUB_DIR / 'SUPPORT.md'
    if not p.exists():
        results.append(Result('8. SUPPORT.md exists', 'WARN', 'missing'))
        return
    text = p.read_text(encoding='utf-8')
    n_lines = len(text.splitlines())
    if n_lines < 20:
        results.append(Result('8. SUPPORT.md length', 'WARN', f'only {n_lines} lines'))
    else:
        results.append(Result('8. SUPPORT.md length', 'OK', f'{n_lines} lines'))


# ============================================================================
# Section 9: workflows/*.yml
# ============================================================================
def check_workflows(results, json_mode):
    _print(json_mode, '\n[9] .github/workflows/*.yml')
    if not WORKFLOWS_DIR.exists():
        results.append(Result('9. workflows/ exists', 'FAIL', 'missing'))
        return
    yml_files = sorted(WORKFLOWS_DIR.glob('*.yml')) + sorted(WORKFLOWS_DIR.glob('*.yaml'))
    if not yml_files:
        results.append(Result('9. workflow files', 'WARN', 'no .yml files'))
        return
    for p in yml_files:
        try:
            cfg = yaml.safe_load(p.read_text(encoding='utf-8'))
            if cfg is None:
                results.append(Result(f'9. {p.name}', 'FAIL', 'empty file'))
                continue
            if 'name' not in cfg:
                results.append(Result(f'9. {p.name} name', 'WARN', 'no workflow name'))
            if True not in cfg and 'on' not in cfg:
                results.append(Result(f'9. {p.name} on', 'WARN', 'no "on" trigger'))
            if 'jobs' not in cfg:
                results.append(Result(f'9. {p.name} jobs', 'FAIL', 'no jobs'))
            else:
                n_jobs = len(cfg['jobs'])
                results.append(Result(f'9. {p.name} jobs', 'OK', f'{n_jobs} job(s)'))
        except yaml.YAMLError as e:
            results.append(Result(f'9. {p.name} valid YAML', 'FAIL', str(e)))


# ============================================================================
# Main
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict', action='store_true',
                        help='Treat warnings as failures')
    parser.add_argument('--json', action='store_true',
                        help='Output JSON for CI parsing')
    args = parser.parse_args()

    if not args.json:
        print('=' * 80)
        print('GITHUB COMMUNITY FILES VALIDATION')
        print('=' * 80)
        print(f'Root: {ROOT}')

    results = []

    check_github_dir(results, args.json)
    check_config_yml(results, args.json)
    check_issue_templates(results, args.json)
    check_pr_template(results, args.json)
    check_codeowners(results, args.json)
    check_dependabot(results, args.json)
    check_conduct(results, args.json)
    check_support(results, args.json)
    check_workflows(results, args.json)

    if args.json:
        out = {
            'total': len(results),
            'ok': sum(1 for r in results if r.status == 'OK'),
            'warn': sum(1 for r in results if r.status == 'WARN'),
            'fail': sum(1 for r in results if r.status == 'FAIL'),
            'results': [
                {'dim': r.dim, 'status': r.status, 'detail': r.detail}
                for r in results
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        print('\n' + '=' * 80)
        print('SUMMARY')
        print('=' * 80)
        n_ok = sum(1 for r in results if r.status == 'OK')
        n_warn = sum(1 for r in results if r.status == 'WARN')
        n_fail = sum(1 for r in results if r.status == 'FAIL')
        total = len(results)
        print(f'OK    : {n_ok}/{total}')
        print(f'WARN  : {n_warn}/{total}')
        print(f'FAIL  : {n_fail}/{total}')

        if n_fail > 0:
            print('\nCritical failures (block CI):')
            for r in results:
                if r.status == 'FAIL':
                    print(f'  {r}')

        if n_warn > 0 and args.strict:
            print('\nWarnings (--strict): treated as failures:')
            for r in results:
                if r.status == 'WARN':
                    print(f'  {r}')

    if any(r.status == 'FAIL' for r in results):
        sys.exit(1)
    if args.strict and any(r.status == 'WARN' for r in results):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()