# Support

This document lists the channels where you can get help
with `tmaudit`. Pick the channel that best matches your
question; using the right channel gets you a faster answer
and keeps the maintainers' attention focused.

## Before you ask

1. **Read the README**: [README.md](../blob/main/README.md)
   covers installation, CLI usage, and a 5-minute quick
   start.
2. **Read the contributing guide**:
   [CONTRIBUTING.md](../blob/main/CONTRIBUTING.md) covers
   development setup, the test suite, and the pre-commit
   hook.
3. **Search existing issues and discussions**:
   [issues](https://github.com/aidless/tmaudit/issues)
   and
   [discussions](https://github.com/aidless/tmaudit/discussions).
   The answer to your question may already be there.
4. **Run the diagnostics**:
   ```bash
   pytest
   python _check_all_regressions.py
   python tmaudit.pyz list
   ```
   and paste the full output. This is the most helpful
   thing you can include.

## How to get help

### Q&A and how-to questions

**Use GitHub Discussions**:
[github.com/aidless/tmaudit/discussions](https://github.com/aidless/tmaudit/discussions)

Use this for:
- "How do I configure X for paper Y?"
- "What does the C3 finding mean?"
- "How do I add a new paper to the audit?"
- Best practices and design questions

Discussions are indexed by search engines, so a question
you ask today will help someone else tomorrow.

### Bug reports

**Open a GitHub issue** using the
[bug report template](../issues/new?template=bug_report.md).

Use this for:
- Crashes and stack traces
- Incorrect audit results (false positives / false negatives)
- Broken CI / pre-commit hook

Do **not** use issues for general questions; use
discussions instead.

### Feature requests

**Open a GitHub issue** using the
[feature request template](../issues/new?template=feature_request.md).

Use this for:
- New audit categories (C7, C8, ...)
- New CLI subcommands
- Improvements to the templates

### Security vulnerabilities

**File a private security advisory**:
[github.com/aidless/tmaudit/security/advisories/new](https://github.com/aidless/tmaudit/security/advisories/new)

Do **not** open a public issue for security problems.
See [SECURITY.md](../blob/main/SECURITY.md) for the
full disclosure policy.

## Response time

| Channel | Expected response time | Best for |
|---|---|---|
| Discussions | 1-7 days | general questions |
| Bug report | 3-7 days | confirmed bugs |
| Feature request | 7-30 days | new features |
| Security advisory | 3 days | security issues |

The maintainer works on this project part-time; please be
patient. If your question is urgent (e.g., you have a
paper submission deadline tomorrow), say so explicitly
and a maintainer will prioritise.

## Maintainers

- @liumingrui (primary)

If you would like to become a maintainer, see the
"Adding maintainers" section of CONTRIBUTING.md.

## Languages

The maintainer's working language is English. Questions in
other languages are welcome but may take longer to
answer; please consider asking in English first.