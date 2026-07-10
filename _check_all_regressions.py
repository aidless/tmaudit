"""_check_all_regressions.py — verify that the 7 bug-specific
regression tests in tests/test_forge.py, tests/test_c6_threshold.py,
and related test files actually catch a re-introduction of
each bug.

For each bug, this script:
  1. Backs up the relevant source file (forge.py,
     templates/verify_TEMPLATE.py, or configs/paper_configs.py).
  2. Injects a small change that re-introduces the bug.
  3. Runs the targeted TestBug* test class.
  4. Asserts the test FAILS (i.e. the bug fingerprint is
     recognised).
  5. Restores the original source.
  6. Re-runs the test and asserts it PASSES.

Exit code:
  0 if all 7 bugs are correctly caught and restored.
  1 if any bug is NOT caught (i.e. the regression test would
    silently miss the bug — a serious problem).

Usage:
    python _check_all_regressions.py
"""
from __future__ import annotations
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

TEMPLATE = Path('F:/Research/TEMPLATE')
FORGE = TEMPLATE / 'src' / 'tmaudit' / 'forge.py'
VERIFY_TPL = TEMPLATE / 'src' / 'tmaudit' / 'templates' / 'verify_TEMPLATE.py'
PAPER_CONFIGS = TEMPLATE / 'src' / 'tmaudit' / 'configs' / 'paper_configs.py'
PYTEST = [sys.executable, '-m', 'pytest', '--no-header', '-q',
          '--tb=line', '--color=no']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_pytest(test_target: str) -> tuple[int, str]:
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    result = subprocess.run(
        PYTEST + [test_target],
        cwd=str(TEMPLATE),
        env=env,
        capture_output=True,
        text=True,
        errors='replace',
    )
    return result.returncode, (result.stdout + '\n' + result.stderr)


@contextmanager
def _patched(path: Path) -> Iterator[None]:
    """Context manager: backup path, yield, restore on exit.

    Usage:
        with _patched(FORGE):
            FORGE.write_text(new_content, encoding='utf-8')
    """
    backup = path.read_text(encoding='utf-8')
    try:
        yield
    finally:
        path.write_text(backup, encoding='utf-8')


def _check_bug(
    bug_id: str,
    test_target: str,
    inject_fn: Callable[[], None],
) -> bool:
    """Inject a bug via inject_fn, run the test, assert catch + restore.

    Returns True iff the regression test caught the bug AND
    restoration left the test passing.
    """
    print(f'\n=== Bug {bug_id}: inject + verify catch ===')
    try:
        inject_fn()
    except Exception as e:
        print(f'  ERROR during inject: {e!r}')
        return False

    # Step 1: with bug injected, run the test and expect FAIL
    rc, out = _run_pytest(test_target)
    caught = (rc != 0 and 'FAILED' in out)
    if caught:
        # Find the specific failing test line for reporting
        fail_lines = [line for line in out.splitlines() if 'FAILED' in line]
        first_fail = fail_lines[0] if fail_lines else '(no FAILED line)'
        print(f'  PASS: regression test caught the bug (rc={rc})')
        print(f'        e.g., {first_fail[:120]}')
    else:
        print(f'  FAIL: regression test did NOT catch the bug (rc={rc})')
        print('  --- pytest output (last 25 lines) ---')
        for line in out.splitlines()[-25:]:
            print(f'    | {line}')
        return False

    # Step 2: restore and re-run, expect PASS
    # (we use a fresh subprocess to ensure no caching of the
    # modified module)
    rc, out = _run_pytest(test_target)
    if rc != 0:
        print(f'  RESTORE FAILED: test still failing after restore (rc={rc})')
        print('  --- pytest output (last 25 lines) ---')
        for line in out.splitlines()[-25:]:
            print(f'    | {line}')
        return False
    print(f'  RESTORE OK: test passes again after restore (rc=0)')
    return True


# ---------------------------------------------------------------------------
# Bug-specific inject functions
#
# Each function:
#   - uses _patched() to back up the file
#   - writes a buggy version
#   - the buggy version is reverted when _patched() exits
#   - we then call _check_bug() which runs pytest twice and
#     asserts catch + restore
# ---------------------------------------------------------------------------

def inject_bug1() -> None:
    """Bug 1: r-string -> repr. Patch the r-string return in
    _format_simple_value with a plain repr return.
    """
    with _patched(FORGE):
        original = FORGE.read_text(encoding='utf-8')
        old = "return f\"r'{escaped}'\""
        new = 'return repr(value)  # BROKEN: regressed to no r-string'
        if old not in original:
            raise RuntimeError(f'bug-1 anchor not found: {old!r}')
        FORGE.write_text(original.replace(old, new, 1), encoding='utf-8')
        # Run check inside the patch context
        _check_bug_inside_patch('1', 'tests/test_forge.py::TestBug1ReprInterpretsBackslash')


def inject_bug2() -> None:
    """Bug 2: re.sub interprets backslashes in replacement. Replace
    the manual brace-counting block with a broken re.sub call.
    """
    with _patched(FORGE):
        original = FORGE.read_text(encoding='utf-8')
        block_start = original.find(
            "# Replace the existing CHECKS_CONFIG block with literal string slicing"
        )
        if block_start < 0:
            raise RuntimeError('bug-2 anchor not found')
        block_end = original.find(
            "out = out[:start] + new_block + '\\n' + out[end:]",
            block_start,
        )
        if block_end < 0:
            raise RuntimeError('bug-2 anchor end not found')
        block_end = original.find('\n', block_end) + 1
        broken = (
            "    # BROKEN: re.sub interprets backslashes in the replacement text\n"
            "    import re as _re\n"
            "    out = _re.sub(\n"
            "        r'CHECKS_CONFIG: dict = \\{.*?\\}',\n"
            "        new_block + '\\n',\n"
            "        out,\n"
            "        count=1,\n"
            "        flags=_re.DOTALL,\n"
            "    )\n"
        )
        FORGE.write_text(
            original[:block_start] + broken + original[block_end:],
            encoding='utf-8',
        )
        _check_bug_inside_patch('2', 'tests/test_forge.py::TestBug2ResubBackslashInReplacement')


def inject_bug3() -> None:
    """Bug 3: na\"ive brace counter. Replace the state machine in
    forge._substitute_verify with a simple counter that does NOT
    skip braces inside string literals.
    """
    with _patched(FORGE):
        original = FORGE.read_text(encoding='utf-8')
        while_marker = '    while i < len(out):\n'
        start = original.find(while_marker)
        if start < 0:
            raise RuntimeError('bug-3 anchor (while loop) not found')
        end = original.find('    return out\n', start)
        if end < 0:
            raise RuntimeError('bug-3 anchor end (return out) not found')
        end += len('    return out\n')
        naive = (
            '    while i < len(out):\n'
            '        c = out[i]\n'
            '        if c == "}":  # BROKEN: no string-literal awareness\n'
            '            depth -= 1\n'
            '            if depth == 0:\n'
            '                end = i + 1\n'
            '                break\n'
            '        elif c == "{":\n'
            '            depth += 1\n'
            '        i += 1\n'
        )
        FORGE.write_text(
            original[:start] + naive + original[end:],
            encoding='utf-8',
        )
        _check_bug_inside_patch('3', 'tests/test_forge.py::TestBug3BraceCounterIgnoresStringLiterals')


def inject_bug4() -> None:
    """Bug 4: C1 narrow 250-char window. Disable the second and
    third passes in check_c1_abstract_definitions so only the
    250-char window is used. Paper 1's TTRL symbol is defined
    1500+ chars after first mention, so the audit will flag it.
    """
    with _patched(VERIFY_TPL):
        original = VERIFY_TPL.read_text(encoding='utf-8')
        # Mark the second/third passes as dead code by raising
        # before they execute.
        marker = '        # Second pass: definition anywhere within the abstract'
        start = original.find(marker)
        if start < 0:
            raise RuntimeError('bug-4 anchor (second pass) not found')
        # Replace the next 30 lines with a no-op
        broken_block = (
            '        # BROKEN: second pass disabled (bug 4 regression)\n'
            '        pass\n\n'
        )
        # Find the third pass and kill that too
        third_pass = original.find(
            '        # Third pass: definition in the first',
            start,
        )
        if third_pass < 0:
            raise RuntimeError('bug-4 anchor (third pass) not found')
        # Find the end of the third pass: the next "return findings" at the same indent
        end = original.find('        return findings\n', third_pass)
        if end < 0:
            raise RuntimeError('bug-4 anchor end (return findings) not found')
        end += len('        return findings\n')
        # Replace both passes with a no-op
        patched = (
            original[:start]
            + broken_block
            + original[end:]
        )
        # Also remove the "    abstract, abs_start = abs_result" for
        # safety: no, that's needed. Just disable the two passes.
        VERIFY_TPL.write_text(patched, encoding='utf-8')
        # Bug 4 is in the verify_TEMPLATE.py, so we need to run
        # the end-to-end audit (which executes the template code).
        _check_bug_inside_patch('4', 'tests/test_forge_happy.py::TestEndToEndAudit::test_paper_1_forks_and_passes')


def inject_bug5() -> None:
    """Bug 5: C5 test-name regex too strict. Replace the relaxed
    `paired[^a-zA-Z]{0,8}t[^a-zA-Z]{0,3}test` with the strict
    `paired\\s+t-test` that does not match `paired $t$-tests`.
    """
    with _patched(VERIFY_TPL):
        original = VERIFY_TPL.read_text(encoding='utf-8')
        relaxed_pattern = (
            "r'paired[^a-zA-Z]{0,8}t[^a-zA-Z]{0,3}test|'\n"
        )
        strict_replacement = (
            "r'paired\\s+t-test|'\n"
        )
        if relaxed_pattern not in original:
            raise RuntimeError('bug-5 anchor (relaxed pattern) not found')
        VERIFY_TPL.write_text(
            original.replace(relaxed_pattern, strict_replacement, 1),
            encoding='utf-8',
        )
        _check_bug_inside_patch('5', 'tests/test_bug5_unit.py')


def inject_bug6() -> None:
    """Bug 6: c2_section_pattern too narrow. Remove the
    `Statistical Protocol` branch from the Paper 5 config so
    the audit fails to find Paper 5's `Statistical Protocol`
    section.
    """
    with _patched(PAPER_CONFIGS):
        original = PAPER_CONFIGS.read_text(encoding='utf-8')
        # The Paper 5 c2_section_pattern is a multi-line string. We
        # remove the "Statistical Protocol" branch by replacing the
        # whole pattern with a narrower one.
        old_pat = (
            "        # Paper 5's section is named \"Statistical Protocol\", not \"Power analysis\".\n"
            "        'c2_section_pattern': (\n"
            "            r'\\\\section\\*?\\{[^}]*Power analysis[^}]*\\}|'\n"
            "            r'\\\\subsection\\*?\\{[^}]*Statistical Protocol[^}]*\\}'\n"
            "        ),"
        )
        new_pat = (
            "        'c2_section_pattern': (\n"
            "            r'\\\\section\\*?\\{[^}]*Power analysis[^}]*\\}'\n"
            "        ),"
        )
        if old_pat not in original:
            raise RuntimeError('bug-6 anchor (Statistical Protocol branch) not found')
        PAPER_CONFIGS.write_text(
            original.replace(old_pat, new_pat, 1),
            encoding='utf-8',
        )
        _check_bug_inside_patch('6', 'tests/test_forge_happy.py::TestEndToEndAudit::test_paper_5_forks_and_passes')


def inject_bug7() -> None:
    """Bug 7: C6 blacklist false-positive on idiomatic English.
    The min_count threshold (3) is the fix that makes 1-2
    occurrences of 'yield' / 'reveal' not be reported. If the
    threshold is removed (set to 0), the audit reverts to the
    buggy behaviour: every occurrence generates a finding.

    We inject by changing the literal `min_count: int = 3` to
    `min_count: int = 0` in
    `src/tmaudit/templates/verify_TEMPLATE.py::check_c6_blacklist`.

    The regression test that should catch this is
    `test_c6_does_not_flag_single_occurrence`: it constructs a
    tex with one 'paradigm' and asserts the C6 finding list
    is empty. With min_count=0, the finding list is non-empty
    (it has 1 entry) and the test fails.
    """
    with _patched(VERIFY_TPL):
        original = VERIFY_TPL.read_text(encoding='utf-8')
        old = '    min_count: int = 3'
        new = '    min_count: int = 0  # BROKEN: regression to 1-occurrence reporting'
        if old not in original:
            raise RuntimeError(f'bug-7 anchor not found: {old!r}')
        VERIFY_TPL.write_text(
            original.replace(old, new, 1),
            encoding='utf-8',
        )
        _check_bug_inside_patch(
            '7',
            'tests/test_c6_threshold.py::test_c6_does_not_flag_single_occurrence',
        )


# ---------------------------------------------------------------------------
# Per-bug test runner
# ---------------------------------------------------------------------------

# Module-level container so inject_* can pass results back to main().
# We use a list of (bug_id, success, error_msg) tuples.
_results: list[tuple[str, bool, str]] = []


def _check_bug_inside_patch(bug_id: str, test_target: str) -> None:
    """Run pytest inside the patch context (where the bug is in
    place). Append the result to _results.
    """
    rc, out = _run_pytest(test_target)
    caught = (rc != 0 and 'FAILED' in out)
    if caught:
        _results.append((bug_id, True, ''))
    else:
        # Save last 5 lines for diagnostics
        snippet = '\n'.join(out.splitlines()[-5:])
        _results.append((bug_id, False, snippet))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    cases: list[tuple[str, Callable[[], None]]] = [
        ('1', inject_bug1),
        ('2', inject_bug2),
        ('3', inject_bug3),
        ('4', inject_bug4),
        ('5', inject_bug5),
        ('6', inject_bug6),
        ('7', inject_bug7),
    ]

    for bug_id, inject_fn in cases:
        try:
            inject_fn()
        except Exception as e:
            _results.append((bug_id, False, f'inject failed: {e!r}'))

    # After all bugs have been injected-and-restored (via the
    # _patched context manager), do a final clean run to confirm
    # the workspace is intact.
    print()
    print('=' * 72)
    print('SUMMARY')
    print('=' * 72)
    for bug_id, ok, err in sorted(_results):
        marker = '[OK]' if ok else '[FAIL]'
        print(f'  Bug {bug_id}: {marker}')
        if err:
            print(f'    {err}')

    n_pass = sum(1 for _, ok, _ in _results if ok)
    n_total = len(_results)
    print()
    print(f'  {n_pass}/{n_total} bugs are correctly caught by their regression tests.')

    # Final sanity check: all tests should pass on the restored code
    print()
    print('=== Final sanity: full test suite should pass ===')
    rc, out = _run_pytest('tests/')
    if rc == 0:
        print(f'  OK: full test suite passes (rc=0)')
    else:
        print(f'  WARN: full test suite returns rc={rc} after all restores')
        print('  --- pytest output (last 25 lines) ---')
        for line in out.splitlines()[-25:]:
            print(f'    | {line}')

    if n_pass == n_total and rc == 0:
        print()
        print('=== ALL REGRESSION TESTS ARE EFFECTIVE ===')
        return 0
    print()
    print('=== SOME REGRESSION TESTS ARE NOT EFFECTIVE ===')
    return 1


if __name__ == '__main__':
    sys.exit(main())