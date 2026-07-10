"""tmaudit.cli — command-line entry point for the tmaudit tool.

Usage:
    tmaudit list
    tmaudit verify --paper N [--paper-dir PATH] [--dry-run]
                     [--no-cache] [--clear-cache] [--cache-info]
    tmaudit compile --paper N [--paper-dir PATH]
    tmaudit fix-unicode --paper N [--paper-dir PATH] [--apply]
    tmaudit audit-all [--start 1] [--end 5]
    tmaudit cache-info
    tmaudit cache-clear

The CLI works equally well when the package is installed via
`pip install` or when it is run as a zipapp via `python tmaudit.pyz`.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

from .configs.compile_configs import PAPER_CONFIGS as COMPILE_CONFIGS
from .configs.paper_configs import PAPER_CONFIGS as VERIFY_CONFIGS
from . import forge
from . import cache as _cache


def _add_paper_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--paper', type=int, required=False,
        help='paper number to operate on (e.g., 1, 2, ..., 5)',
    )
    parser.add_argument(
        '--paper-dir', type=Path, default=None,
        help='override the paper directory (default: from config)',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='show what would be written, but make no changes',
    )


def cmd_list(args: argparse.Namespace) -> int:
    print('Known paper configurations:')
    print(f'  {"Paper":<6}  {"verify":<7}  {"compile":<8}  path')
    for n in sorted(VERIFY_CONFIGS):
        verify_ok = 'OK'
        compile_ok = 'OK' if n in COMPILE_CONFIGS else '—'
        path = VERIFY_CONFIGS[n]['dir']
        print(f'  {n:<6}  {verify_ok:<7}  {compile_ok:<8}  {path}')
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    if args.paper is None:
        print('ERROR: --paper N is required for verify', file=sys.stderr)
        return 2
    if args.paper not in VERIFY_CONFIGS:
        print(f'ERROR: no VERIFY_CONFIGS for paper {args.paper}', file=sys.stderr)
        return 2

    # Cache handling: --clear-cache clears the cache before running,
    # --no-cache disables reading from the cache (the verify script
    # is still run end-to-end; the cache integration is in
    # verify_TEMPLATE.py in v0.2.0+, here we just expose the flags).
    if getattr(args, 'clear_cache', False):
        cmd_cache_info(argparse.Namespace())  # not used, just placeholder
        db = _cache.CacheDB()
        n = db.clear()
        print(f'[CACHE] Cleared {n} entries before running')
        db.close()

    if args.dry_run:
        print(f'[DRY-RUN] would fork verify_p{args.paper}.py for paper {args.paper}')
        cfg = VERIFY_CONFIGS[args.paper]
        paper_dir = args.paper_dir or cfg['dir']
        print(f'  target: {paper_dir / f"verify_p{args.paper}.py"}')
        return 0
    target = forge.fork_verify(args.paper, args.paper_dir)
    print(f'[WRITE] {target} ({target.stat().st_size:,} chars)')
    # Run the freshly-forked verify script to give the user immediate feedback.
    rc = subprocess.run(
        [sys.executable, str(target)],
        cwd=target.parent,
    ).returncode

    if getattr(args, 'cache_info', False):
        cmd_cache_info(argparse.Namespace())

    return rc


def cmd_compile(args: argparse.Namespace) -> int:
    if args.paper is None:
        print('ERROR: --paper N is required for compile', file=sys.stderr)
        return 2
    if args.paper not in COMPILE_CONFIGS:
        print(f'ERROR: no COMPILE_CONFIGS for paper {args.paper}', file=sys.stderr)
        return 2
    if args.dry_run:
        print(f'[DRY-RUN] would fork _compile_check.py for paper {args.paper}')
        cfg = COMPILE_CONFIGS[args.paper]
        paper_dir = args.paper_dir or cfg['dir']
        print(f'  target: {paper_dir / "_compile_check.py"}')
        return 0
    target = forge.fork_compile(args.paper, args.paper_dir)
    print(f'[WRITE] {target} ({target.stat().st_size:,} chars)')
    rc = subprocess.run(
        [sys.executable, str(target)],
        cwd=target.parent,
    ).returncode
    return rc


def cmd_fix_unicode(args: argparse.Namespace) -> int:
    if args.paper is None:
        print('ERROR: --paper N is required for fix-unicode', file=sys.stderr)
        return 2
    if args.paper not in COMPILE_CONFIGS:
        print(f'ERROR: no COMPILE_CONFIGS for paper {args.paper}', file=sys.stderr)
        return 2
    if args.dry_run:
        print(f'[DRY-RUN] would fork _fix_abstract_unicode.py for paper {args.paper}')
        cfg = COMPILE_CONFIGS[args.paper]
        paper_dir = args.paper_dir or cfg['dir']
        print(f'  target: {paper_dir / "_fix_abstract_unicode.py"}')
        return 0
    target = forge.fork_fix_unicode(args.paper, args.paper_dir)
    print(f'[WRITE] {target} ({target.stat().st_size:,} chars)')
    return 0


def cmd_audit_all(args: argparse.Namespace) -> int:
    """Run verify for all papers in [start, end] and write a Markdown
    report if --output is set.

    Per v0.2.0 acceptance criteria:
      - Generate a single Markdown report covering all
        configured papers.
      - The report is included in CI artefacts (see
        .github/workflows/ci.yml).
      - LLM-based C7 fallback is opt-in (deferred to
        a future v0.2.x; this command does not use it).
    """
    import time as _time
    from . import report as _report

    start = args.start
    end = args.end
    output_path = getattr(args, 'output', None)
    no_cache = getattr(args, 'no_cache', False)
    started_at = _time.time()
    print(f'Auditing papers {start}..{end} ...')
    if output_path:
        print(f'Markdown report will be written to: {output_path}')
    if no_cache:
        print('Cache: disabled (--no-cache)')

    results: list = []
    fail = 0
    for n in range(start, end + 1):
        if n not in VERIFY_CONFIGS:
            print(f'  [SKIP] paper {n}: not in VERIFY_CONFIGS')
            continue
        cfg = VERIFY_CONFIGS[n]
        paper_dir = args.paper_dir or cfg['dir']
        target = forge.fork_verify(n, paper_dir)
        print(f'\n--- paper {n} ({paper_dir}) ---')
        paper_started = _time.time()
        proc = subprocess.run(
            [sys.executable, str(target)],
            cwd=target.parent,
            capture_output=True,
            text=True,
        )
        paper_ended = _time.time()
        # Print the first 30 lines of stdout for immediate feedback
        out_preview = proc.stdout.splitlines()[:30]
        for line in out_preview:
            print(f'    | {line}')
        if proc.returncode != 0:
            fail += 1
            print(f'  [FAIL] paper {n} returned {proc.returncode}')
        # Build the result
        result = _report.parse_verify_output(
            paper=n,
            paper_dir=paper_dir,
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
            started_at=paper_started,
            ended_at=paper_ended,
        )
        results.append(result)

    ended_at = _time.time()

    # Write the Markdown report if --output is set
    if output_path is not None:
        try:
            from . import __version__ as _ver
            tmaudit_version = _ver
        except ImportError:
            tmaudit_version = 'dev'
        _report.write_markdown_report(
            Path(output_path),
            results,
            started_at=started_at,
            ended_at=ended_at,
            tmaudit_version=tmaudit_version,
            cache_used=not no_cache,
        )
        print(f'\n[REPORT] Markdown report written to: {output_path}')

    return 0 if fail == 0 else 1


def cmd_cache_info(args: argparse.Namespace) -> int:
    """Show cache statistics: number of entries, total size, oldest/newest."""
    db = _cache.CacheDB()
    stats = db.stats()
    print('Cache statistics:')
    print(f'  path:    {stats["path"]}')
    print(f'  entries: {stats["n_entries"]}')
    print(f'  bytes:   {stats["total_bytes"]:,}')
    if stats['oldest'] is not None:
        import time as _time
        oldest = _time.strftime('%Y-%m-%d %H:%M:%S', _time.localtime(stats['oldest']))
        newest = _time.strftime('%Y-%m-%d %H:%M:%S', _time.localtime(stats['newest']))
        print(f'  oldest:  {oldest}')
        print(f'  newest:  {newest}')
    db.close()
    return 0


def cmd_cache_clear(args: argparse.Namespace) -> int:
    """Clear the cache (remove all entries)."""
    db = _cache.CacheDB()
    n = db.clear()
    print(f'Cleared {n} cache entries from {db.path}')
    db.close()
    return 0


# ============================================================================
# Plugin subcommands (added in v0.4.0)
# ============================================================================

def _format_plugin_table(plugins: dict) -> str:
    """Render the plugin list as a 4-column table."""
    if not plugins:
        return "(no plugins registered)\n"
    rows = [("NAME", "MODULE", "SEVERITY", "VERSION")]
    for name, plugin in sorted(plugins.items()):
        meta = plugin.__tmaudit_meta__
        rows.append((
            name,
            getattr(plugin.fn, "__module__", "<unknown>"),
            meta["severity"],
            meta["version"],
        ))
    widths = [max(len(row[i]) for row in rows) for i in range(4)]
    out = []
    for i, row in enumerate(rows):
        line = "  ".join(c.ljust(widths[j]) for j, c in enumerate(row))
        out.append(line)
        if i == 0:
            out.append("  ".join("-" * widths[j] for j in range(4)))
    return "\n".join(out) + "\n"


def cmd_plugins_list(args: argparse.Namespace) -> int:
    """List every discovered plugin (one per line)."""
    from . import plugins as _plugins
    _plugins.reset_loader_cache()
    loaded = _plugins.load_plugins()
    sys.stdout.write(_format_plugin_table(loaded))
    return 0


def cmd_plugins_info(args: argparse.Namespace) -> int:
    """Show details for one plugin, looked up by name."""
    from . import plugins as _plugins
    _plugins.reset_loader_cache()
    loaded = _plugins.load_plugins()
    name = args.name
    if name not in loaded:
        sys.stderr.write(
            f"Plugin {name!r} not registered. "
            f"Known: {', '.join(sorted(loaded)) or '(none)'}\n"
        )
        return 1
    plugin = loaded[name]
    meta = plugin.__tmaudit_meta__
    module = getattr(plugin.fn, "__module__", "<unknown>")
    qualname = getattr(plugin.fn, "__qualname__", repr(plugin.fn))
    sys.stdout.write(
        f"Name:        {name}\n"
        f"Module:      {module}\n"
        f"Function:    {qualname}\n"
        f"Severity:    {meta['severity']}\n"
        f"Version:     {meta['version']}\n"
        f"Help:        {meta['help_text']}\n"
        f"Config:      {'required' if meta['requires_config'] else 'ignored'}\n"
    )
    return 0


def cmd_plugins_run(args: argparse.Namespace) -> int:
    """Run a single plugin against one paper's main.tex (no caching)."""
    from . import plugins as _plugins
    _plugins.reset_loader_cache()
    loaded = _plugins.load_plugins()
    name = args.name
    if name not in loaded:
        sys.stderr.write(
            f"Plugin {name!r} not registered. "
            f"Known: {', '.join(sorted(loaded)) or '(none)'}\n"
        )
        return 1
    plugin = loaded[name]

    paper_n = args.paper
    if paper_n not in VERIFY_CONFIGS:
        sys.stderr.write(f"Unknown paper {paper_n!r}\n")
        return 1
    paper_dir = Path(args.paper_dir or VERIFY_CONFIGS[paper_n]['dir'])
    main_tex = paper_dir / 'main.tex'
    if not main_tex.exists():
        sys.stderr.write(f"main.tex not found at {main_tex}\n")
        return 1
    tex = main_tex.read_text(encoding='utf-8', errors='replace')

    findings = _plugins.run_plugin(
        plugin, tex=tex,
        config=VERIFY_CONFIGS[paper_n],
        paper_id=str(paper_n),
    )
    if not findings:
        print(f"Plugin {name!r} emitted 0 findings on paper {paper_n}.")
        return 0
    for f in findings:
        print(f"[{f.severity}] {f.category} L{f.line}: {f.message}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='tmaudit',
        description='Config-driven TMLR paper audit + LaTeX compile pipeline.',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    p_list = sub.add_parser('list', help='list known paper configurations')
    p_list.set_defaults(func=cmd_list)

    p_verify = sub.add_parser(
        'verify', help='fork verify_p<N>.py and run the audit on the paper',
    )
    _add_paper_arg(p_verify)
    p_verify.add_argument(
        '--no-cache', action='store_true',
        help='bypass the cache: do not read or write audit results',
    )
    p_verify.add_argument(
        '--clear-cache', action='store_true',
        help='clear the cache before running (useful after a bug fix)',
    )
    p_verify.add_argument(
        '--cache-info', action='store_true',
        help='show cache statistics after running',
    )
    p_verify.add_argument(
        '--llm-budget', type=int, default=0,
        help='max number of LLM calls for C7 fallback (0 = no LLM)',
    )
    p_verify.set_defaults(func=cmd_verify)

    p_compile = sub.add_parser(
        'compile', help='fork _compile_check.py and run a 4-pass LaTeX build',
    )
    _add_paper_arg(p_compile)
    p_compile.set_defaults(func=cmd_compile)

    p_fix = sub.add_parser(
        'fix-unicode', help='fork _fix_abstract_unicode.py and (optionally) apply',
    )
    _add_paper_arg(p_fix)
    p_fix.set_defaults(func=cmd_fix_unicode)

    p_audit = sub.add_parser(
        'audit-all', help='run verify for all papers in a range',
    )
    p_audit.add_argument('--start', type=int, default=1)
    p_audit.add_argument('--end', type=int, default=5)
    p_audit.add_argument('--paper-dir', type=Path, default=None)
    p_audit.add_argument(
        '--output', type=Path, default=None,
        help='write a Markdown report to this path (e.g. report.md)',
    )
    p_audit.add_argument(
        '--no-cache', action='store_true',
        help='bypass the cache (do not read or write audit results)',
    )
    p_audit.add_argument(
        '--llm-budget', type=int, default=0,
        help='max LLM calls per paper for C7 fallback (0 = no LLM)',
    )
    p_audit.set_defaults(func=cmd_audit_all)

    p_cache_info = sub.add_parser(
        'cache-info',
        help='show cache statistics (entries, size, oldest/newest)',
    )
    p_cache_info.set_defaults(func=cmd_cache_info)

    p_cache_clear = sub.add_parser(
        'cache-clear',
        help='clear all cache entries',
    )
    p_cache_clear.set_defaults(func=cmd_cache_clear)

    # Plugin subcommands (added in v0.4.0).
    p_plugins = sub.add_parser(
        'plugins',
        help='manage user-written audit plugins',
    )
    p_plugins_sub = p_plugins.add_subparsers(
        dest='plugins_command', required=True,
    )
    p_plugins_list = p_plugins_sub.add_parser(
        'list', help='list every discovered plugin',
    )
    p_plugins_list.set_defaults(func=cmd_plugins_list)
    p_plugins_info = p_plugins_sub.add_parser(
        'info', help='show details for one plugin',
    )
    p_plugins_info.add_argument('name', help='plugin name (e.g. nips-pagecheck)')
    p_plugins_info.set_defaults(func=cmd_plugins_info)
    p_plugins_run = p_plugins_sub.add_parser(
        'run', help='run a single plugin against one paper (no caching)',
    )
    p_plugins_run.add_argument('name', help='plugin name')
    _add_paper_arg(p_plugins_run)
    p_plugins_run.set_defaults(func=cmd_plugins_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())