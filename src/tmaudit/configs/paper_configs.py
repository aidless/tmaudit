#!/usr/bin/env python3
"""gen_verify_scripts.py — fork the verify_p<N>.py audit script from TEMPLATE.

This tool:
  1. Reads F:/Research/TEMPLATE/_verify_TEMPLATE.py
  2. Reads PAPER_CONFIGS (below) for the per-paper check configuration
  3. Substitutes the ROOT and CHECKS_CONFIG blocks
  4. Writes the result to F:/Research/PAPER<N>_CONSOLIDATED/verify_p<N>.py
  5. Backs up any existing target file to .bak_before_template

Usage:
    python gen_verify_scripts.py --list
    python gen_verify_scripts.py --paper 1
    python gen_verify_scripts.py --paper 1 --dry-run

Per-paper configuration is read from PAPER_CONFIGS below. To add a new
paper, append a new entry.

Note: this tool writes the *audit* (verify) script. For the *compile*
script (the 4-pass pdflatex+bibtex+pdflatex+pdflatex pipeline), use
`gen_compile_scripts.py` instead.
"""
from __future__ import annotations
import argparse
import re
import shutil
import sys
from pathlib import Path

TEMPLATE_DIR = Path('F:/Research/TEMPLATE')
RESEARCH_DIR = Path('F:/Research')

# ---------------------------------------------------------------------------
# Per-paper CHECKS_CONFIG (6 categories of audit)
# ---------------------------------------------------------------------------
# Each entry has:
#   'dir':           output directory,
#   'c1_symbols':    list of {name, token, definition, window} dicts,
#   'c2_families':   {family_name: k_value},
#   'c2_section_pattern': regex (r-string) for the \\section / \\subsection
#                        that declares the statistical protocol.
#   'c2_abstract_k_allowed': list[int] of k values acceptable in the abstract.
#   'c3_concept':           human-readable label of the concept
#                           (e.g., "crossover", "Two Faces").
#   'c3_concept_token':     regex matching the concept in main.tex
#                           (e.g., r'\\textbf\{crossover\}|\bcrossover\b').
#   'c3_formal':            regex that must match a formal definition
#                           of the concept.
#   'c3_formal_secondary':  optional, second formal definition (used when
#                           the concept has two halves, e.g. Face 1 / Face 2).
#   'c4_self_cite_threshold': float (default 0.30).
#   'c4_self_cite_prefix':   str (default 'liu2026').
#   'c4_max_self_cite_keys': int (default 3).
#   'c5_d_type':             str (default "Cohen's d").
#   'c6_blacklist':          list[str] (default ['paradigm','yield','reveal']).
# ---------------------------------------------------------------------------
PAPER_CONFIGS: dict[int, dict] = {
    1: {
        'dir': RESEARCH_DIR / 'PAPER1_CONSOLIDATED',
        'c1_symbols': [
            {
                'name': r'$\Delta$CAF (consensus-against-field coefficient)',
                'token': r'\bCAF\b',
                'definition': r'\bCAF\b.{0,80}=|consensus.{0,30}agreement|strateg.{0,30}convergence',
            },
            {
                'name': r'$E_T$ (temporal-accumulation effect on calibration)',
                'token': r'\bE_T\b',
                'definition': r'E_T.{0,80}=|temporal.{0,30}accumulation|peer.anchored.{0,30}confidence',
            },
            {
                'name': r'$\Delta$ECE (calibration delta)',
                'token': r'\\Delta\s*ECE|\\Delta\\mathrm\{ECE\}',
                'definition': r'\\Delta\s*ECE.{0,80}=|calibration.{0,30}loss|calibration.{0,30}degrad',
            },
            {
                'name': 'TTRL (Test-Time Reinforcement Learning)',
                'token': r'\bTTRL\b',
                'definition': r'TTRL.{0,80}=|Test.Time.{0,40}Reinforcement.{0,40}Learning',
            },
        ],
        'c2_families': {'main': 3},
        'c2_section_pattern': (
            r'\\section\*?\{[^}]*Power analysis[^}]*\}|'
            r'\\subsection\*?\{[^}]*Power analysis[^}]*\}'
        ),
        'c2_abstract_k_allowed': [3],
        'c3_concept': 'Two Faces (Face 1 / Face 2)',
        'c3_concept_token': r'\\textbf\{Face 1\}|\\textbf\{Face 2\}|\bFace\s+1\b|\bFace\s+2\b',
        'c3_formal': r'\\section\{Face 1:',
        'c3_formal_secondary': r'\\section\{Face 2:',
        'c4_self_cite_threshold': 0.30,
        'c4_self_cite_prefix': 'liu2026',
        'c4_max_self_cite_keys': 3,
        'c5_d_type': "Cohen's d",
        'c6_blacklist': ['paradigm', 'yield', 'reveal'],
    },
    2: {
        # Placeholder — Paper 2 is the impossibility triangle paper.
        # TODO: replace with the actual Paper 2 symbols.
        'dir': RESEARCH_DIR / 'PAPER2_CONSOLIDATED',
        'c1_symbols': [],   # No specific symbols expected to require inline defs
        'c2_families': {},
        'c2_section_pattern': r'\\section\*?\{[^}]*(Power analysis|Statistical Protocol)[^}]*\}',
        'c2_abstract_k_allowed': [],
        'c3_concept': 'Impossibility Triangle',
        'c3_concept_token': r'\\textbf\{Impossibility Triangle\}|\bimpossibility triangle\b',
        'c3_formal': r'\\subsection\{The Impossibility Triangle\}',
        'c3_formal_secondary': None,
        'c4_self_cite_threshold': 0.30,
        'c4_self_cite_prefix': 'liu2026',
        'c4_max_self_cite_keys': 3,
        'c5_d_type': "Cohen's d",
        'c6_blacklist': ['paradigm', 'yield', 'reveal'],
    },
    3: {
        # Placeholder — Paper 3 (Calibration Fatigue / Self-Eval Fragility / Coupling-Noise).
        'dir': RESEARCH_DIR / 'PAPER3_CONSOLIDATED',
        'c1_symbols': [],
        'c2_families': {},
        'c2_section_pattern': r'\\section\*?\{[^}]*(Power analysis|Statistical Protocol)[^}]*\}',
        'c2_abstract_k_allowed': [],
        'c3_concept': 'Coupling-Noise Decomposition (Theorem 2)',
        'c3_concept_token': r'\\textbf\{Coupling.Noise\}|Coupling.Noise Decomposition',
        'c3_formal': r'CNR.{0,80}=|Coupling.Noise.{0,80}\$',
        'c3_formal_secondary': None,
        'c4_self_cite_threshold': 0.30,
        'c4_self_cite_prefix': 'liu2026',
        'c4_max_self_cite_keys': 3,
        'c5_d_type': "Cohen's d",
        'c6_blacklist': ['paradigm', 'yield', 'reveal'],
    },
    4: {
        # Placeholder — Paper 4 (N-Sensitivity).
        'dir': RESEARCH_DIR / 'PAPER4_CONSOLIDATED',
        'c1_symbols': [],
        'c2_families': {},
        'c2_section_pattern': r'\\section\*?\{[^}]*(Power analysis|Statistical Protocol)[^}]*\}',
        'c2_abstract_k_allowed': [],
        'c3_concept': 'N-Sensitivity',
        'c3_concept_token': r'\\textbf\{N.Sensitivity\}|N.Sensitivity\b',
        'c3_formal': r'N.Sensitivity.{0,80}=|S_N.{0,80}=|N_0',
        'c3_formal_secondary': None,
        'c4_self_cite_threshold': 0.30,
        'c4_self_cite_prefix': 'liu2026',
        'c4_max_self_cite_keys': 3,
        'c5_d_type': "Cohen's d",
        'c6_blacklist': ['paradigm', 'yield', 'reveal'],
    },
    5: {
        'dir': RESEARCH_DIR / 'PAPER5_CONSOLIDATED',
        'c1_symbols': [
            {
                'name': r'$\Gamma_{\mathrm{temporal}}$ (Wasserstein-1 bias-propagation metric)',
                'token': r'\\Gamma',
                'definition': r'\\Gamma_\{\\text\{temporal\}\}\s*=|Wasserstein',
            },
            {
                'name': 'contamination rate (fraction of stored outputs modified)',
                'token': r'contamination rate',
                'definition': r'fraction of stored outputs|proportion of stored|modified at the start',
            },
            {
                'name': 'length bias',
                'token': r'length bias',
                'definition': r'expansion by a factor|expansion factor|output expansion|alpha=1\.5',
            },
            {
                'name': 'authority bias',
                'token': r'authority bias',
                'definition': r'explicit source|source.attribution|"according to',
            },
        ],
        'c2_families': {
            'dose-response': 9,
            'cross-model': 6,
            'authority-bias': 3,
        },
        # Paper 5's section is named "Statistical Protocol", not "Power analysis".
        'c2_section_pattern': (
            r'\\section\*?\{[^}]*Power analysis[^}]*\}|'
            r'\\subsection\*?\{[^}]*Statistical Protocol[^}]*\}'
        ),
        'c2_abstract_k_allowed': [9],
        'c3_concept': 'crossover',
        'c3_concept_token': r'\\textbf\{crossover\}|\bcrossover\b',
        'c3_formal': r'crossover.{0,80}\\arg\\?min',
        'c3_formal_secondary': None,
        'c4_self_cite_threshold': 0.30,
        'c4_self_cite_prefix': 'liu2026',
        'c4_max_self_cite_keys': 1,  # Paper 5 retains only memorycontagion
        'c5_d_type': "Cohen's d",
        'c6_blacklist': ['paradigm', 'yield', 'reveal'],
    },
}


# ---------------------------------------------------------------------------
# Substitution logic
# ---------------------------------------------------------------------------

def _format_c1_symbols(symbols: list[dict]) -> str:
    """Format the c1_symbols list as Python source."""
    if not symbols:
        return '    # (no symbols configured for this paper)\n    [],'
    lines = ['    [']
    for i, sym in enumerate(symbols):
        sep = ',' if i < len(symbols) - 1 else ','
        lines.append('        {')
        for k, v in sym.items():
            if isinstance(v, str):
                # Use repr() so the result is a Python string literal.
                # For raw r-strings the user is expected to have escaped
                # backslashes already.
                lines.append(f"            {k!r}: {v!r},")
            else:
                lines.append(f"            {k!r}: {v!r},")
        lines.append(f'        }}{sep}')
    lines.append('    ],')
    return '\n'.join(lines)


def _format_simple_value(value) -> str:
    """Format a value as a Python source literal.

    For strings that look like regex patterns (contain backslash escape
    sequences such as \\b, \\d, \\s, \\w, \\., \\{, \\}, etc.), emit them
    as raw string literals (r'...') so Python does not interpret the
    backslashes. For other strings, use repr() (which produces a normal
    string literal with appropriate escaping).
    """
    if isinstance(value, str):
        # Heuristic: any of these regex-only escape sequences implies
        # the user intended a raw regex string.
        regex_marker_re = re.compile(r'\\[bBdDsSwWnrtfv0]|\\\.|\\\{|\\\}')
        if regex_marker_re.search(value):
            # Use r-string literal. We must still escape any embedded
            # single-quote (rare in our configs).
            escaped = value.replace("'", r"\'")
            return f"r'{escaped}'"
        return repr(value)
    if value is None:
        return 'None'
    return repr(value)


def _format_c2_families(families: dict) -> str:
    if not families:
        return '    {},'
    items = ', '.join(f'{k!r}: {v!r}' for k, v in families.items())
    return f'    {{{items}}},'


def _format_c6_blacklist(words: list[str]) -> str:
    if not words:
        return '    [],'
    return '    ' + repr(words) + ','


def substitute_verify(template: str, cfg: dict) -> str:
    """Substitute ROOT and CHECKS_CONFIG in the verify template."""
    out = template
    out = re.sub(
        r"ROOT\s*=\s*Path\('[^']*'\)",
        f"ROOT = Path('{cfg['dir'].as_posix()}')",
        out, count=1,
    )

    # Build a replacement for the entire CHECKS_CONFIG block
    parts = []
    parts.append('CHECKS_CONFIG: dict = {')
    parts.append("    'c1_symbols':")
    parts.append(_format_c1_symbols(cfg['c1_symbols']))
    parts.append('')
    parts.append("    'c2_families':")
    parts.append(_format_c2_families(cfg['c2_families']))
    parts.append("    'c2_section_pattern': " + _format_simple_value(cfg['c2_section_pattern']) + ',')
    parts.append("    'c2_abstract_k_allowed': " + _format_simple_value(cfg['c2_abstract_k_allowed']) + ',')
    parts.append('')
    parts.append("    'c3_concept': " + _format_simple_value(cfg['c3_concept']) + ',')
    parts.append("    'c3_concept_token': " + _format_simple_value(cfg['c3_concept_token']) + ',')
    parts.append("    'c3_formal': " + _format_simple_value(cfg['c3_formal']) + ',')
    parts.append("    'c3_formal_secondary': " + _format_simple_value(cfg.get('c3_formal_secondary')) + ',')
    parts.append('')
    parts.append("    'c4_self_cite_threshold': " + repr(cfg.get('c4_self_cite_threshold', 0.30)) + ',')
    parts.append("    'c4_self_cite_prefix': " + _format_simple_value(cfg.get('c4_self_cite_prefix', 'liu2026')) + ',')
    parts.append("    'c4_max_self_cite_keys': " + repr(cfg.get('c4_max_self_cite_keys', 3)) + ',')
    parts.append('')
    parts.append("    'c5_d_type': " + _format_simple_value(cfg.get('c5_d_type', "Cohen's d")) + ',')
    parts.append('')
    parts.append("    'c6_blacklist':")
    parts.append(_format_c6_blacklist(cfg.get('c6_blacklist', ['paradigm', 'yield', 'reveal'])))
    parts.append('}')

    new_block = '\n'.join(parts)

    # Replace the entire CHECKS_CONFIG block. We use a small brace-matching
    # loop that ignores braces inside string literals (single- and
    # double-quoted) so that c2_section_pattern strings like
    # r'\\section\*?\{...Power analysis[^}]*\}|...' do not throw off
    # the count. We also use literal string replacement (str.slice) so
    # that backslashes in the replacement text are not interpreted as
    # regex backreferences (which would raise "bad escape" errors).
    marker = 'CHECKS_CONFIG: dict = {'
    start = out.find(marker)
    if start < 0:
        raise RuntimeError('CHECKS_CONFIG marker not found in template')

    # Walk forward, tracking depth. Skip characters inside string literals.
    depth = 0
    i = start
    in_str: str | None = None  # quote char if inside a string
    while i < len(out):
        c = out[i]
        if in_str is not None:
            if c == '\\' and i + 1 < len(out):
                # Skip escaped character (handles \\, \', \", \n, etc.)
                i += 2
                continue
            if c == in_str:
                in_str = None
        else:
            if c in ('"', "'"):
                in_str = c
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        i += 1
    else:
        raise RuntimeError('CHECKS_CONFIG closing brace not found')
    if end < len(out) and out[end] == '\n':
        end += 1
    out = out[:start] + new_block + '\n' + out[end:]
    return out


def write_output(target: Path, content: str, dry_run: bool) -> None:
    print(f'\n--- {target} ---')
    print(f'  size: {len(content):,} chars')
    print(f'  first 80: {content.splitlines()[0][:80]!r}')

    if dry_run:
        print('  DRY-RUN: not writing')
        return

    if target.exists():
        bak = target.with_suffix(target.suffix + '.bak_before_template')
        if not bak.exists():
            shutil.copy2(target, bak)
            print(f'  [BACKUP] -> {bak.name}')
        else:
            print(f'  [BACKUP] {bak.name} already exists; not overwriting')

    target.write_text(content, encoding='utf-8')
    print(f'  [WRITE] {target} ({len(content):,} chars)')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=int,
                        help='Paper number to generate the verify script for')
    parser.add_argument('--list', action='store_true',
                        help='List all known paper configurations and exit')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be written, but make no changes')
    args = parser.parse_args()

    if args.list:
        print('Known verify configurations:')
        for n, cfg in sorted(PAPER_CONFIGS.items()):
            n_c1 = len(cfg['c1_symbols'])
            n_fam = len(cfg['c2_families'])
            print(f'  Paper {n}: c1_symbols={n_c1}, c2_families={n_fam}, '
                  f'c3="{cfg.get("c3_concept", "")}", '
                  f'c4_max_keys={cfg.get("c4_max_self_cite_keys", 3)}')
        return 0

    if args.paper is None:
        print('ERROR: must specify --paper N or --list', file=sys.stderr)
        return 2

    if args.paper not in PAPER_CONFIGS:
        print(f'ERROR: no config for paper {args.paper}', file=sys.stderr)
        print(f'       known papers: {sorted(PAPER_CONFIGS)}', file=sys.stderr)
        print('       add an entry to PAPER_CONFIGS in gen_verify_scripts.py', file=sys.stderr)
        return 2

    cfg = PAPER_CONFIGS[args.paper]
    print('=' * 72)
    print(f'Generating verify script for Paper {args.paper}')
    print('=' * 72)
    print(f'  Target dir:  {cfg["dir"]}')
    print(f'  c1_symbols:  {len(cfg["c1_symbols"])} rule(s)')
    print(f'  c2_families: {cfg["c2_families"]}')
    print(f'  c3_concept:  {cfg["c3_concept"]!r}')
    print(f'  c5_d_type:   {cfg.get("c5_d_type")!r}')
    print(f'  c6_blacklist: {cfg.get("c6_blacklist")}')
    print(f'  Mode: {"DRY-RUN" if args.dry_run else "APPLY"}')
    print()

    if not cfg['dir'].exists():
        print(f'ERROR: target dir does not exist: {cfg["dir"]}', file=sys.stderr)
        return 2

    tpl = TEMPLATE_DIR / '_verify_TEMPLATE.py'
    if not tpl.exists():
        print(f'ERROR: missing template {tpl}', file=sys.stderr)
        return 2

    out = substitute_verify(tpl.read_text(encoding='utf-8'), cfg)

    # Output file name: verify_p<N>.py
    target = cfg['dir'] / f'verify_p{args.paper}.py'
    write_output(target, out, args.dry_run)

    print()
    print('=' * 72)
    if args.dry_run:
        print('DRY-RUN: no files written.  Re-run without --dry-run to commit.')
    else:
        print(f'Done.  Next: cd {cfg["dir"]} && python verify_p{args.paper}.py')
    print('=' * 72)
    return 0


if __name__ == '__main__':
    sys.exit(main())