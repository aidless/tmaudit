# Security policy

## Supported versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

`tmaudit` is a **local-only audit tool** that reads your LaTeX
source files and reports findings. It does not:

- Make network requests.
- Read files outside the directories you specify.
- Execute the audited LaTeX (compile is a separate opt-in step
  that requires explicit user confirmation).

Because of this limited attack surface, the security risk
profile is lower than for a typical CLI tool. However, the
audit logic itself is security-sensitive: a bug that causes
`tmaudit` to silently miss a finding is effectively a way to
hide a real paper bug from the author. We treat such bugs
as security issues and follow the disclosure process below.

## Reporting a vulnerability

**Please do NOT file a public issue for security
vulnerabilities.**

Use one of these private channels:

1. **GitHub Security Advisories** (preferred):
   [github.com/liumingrui/tmaudit/security/advisories/new](https://github.com/liumingrui/tmaudit/security/advisories/new)
2. **Email**: security@liumingrui-tmaudit.example (PGP key in
   `.gpg/` if you need it; this is a placeholder address for
   the template repo).

Please include:

- A description of the vulnerability and its impact.
- A minimal reproduction (paper directory + command).
- The `tmaudit` version, Python version, and OS.
- Whether you are willing to be credited in the advisory.

## Response timeline

| Stage | Time |
|---|---|
| Acknowledgement | within 3 business days |
| Triage & impact assessment | within 7 business days |
| Patch & advisory draft | within 30 days for high-severity, 90 days for low |
| Public disclosure | coordinated with the reporter |

## What we consider a security issue

- **Audit bypass**: a way to make `tmaudit` report 0 findings
  on a paper that actually has a C1..C6 violation. (This is
  why the meta-test in `_check_all_regressions.py` exists.)
- **Path traversal**: a way to make `tmaudit` read files
  outside the paper directory.
- **Code execution**: a way to make `tmaudit` execute
  arbitrary code via a malicious `.tex` or `.bib` file.
- **Information disclosure**: a way to leak the user's file
  system layout (e.g., `/home/user` path) in the audit output.
- **Dependency vulnerability**: a known CVE in a runtime
  dependency (e.g., `pyyaml`, `regex`).

## What is NOT a security issue

- A false positive in the audit (the audit reports a finding
  where there is no real bug). File a regular bug report.
- A paper that fails the audit. Edit your paper; do not
  open a security advisory.
- A feature request for a new audit category. Use the
  feature request template.

## Security-related configuration

The following items have security implications; please
review them before deployment:

| File | What to check |
|---|---|
| `src/tmaudit/forge.py` | The substitution engine must not allow arbitrary code injection via LaTeX content. |
| `src/tmaudit/cli.py` | Path arguments must be validated to prevent traversal (`..` segments). |
| `pyproject.toml` | Pin dependency versions; do not use floating specifiers like `>= 2.0`. |
| `tmaudit.pyz` | Rebuild from source after any change to `src/tmaudit/`; do not distribute a stale `.pyz`. |

## Acknowledgements

We thank the following reporters (alphabetical by GitHub
username; updated after each disclosure):

<!--
- @reporter-1 for the audit-bypass report fixed in v0.1.1
-->
