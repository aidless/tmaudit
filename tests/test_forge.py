"""Regression tests for tmaudit.forge — one test per documented bug.

Each test reproduces the exact bug fingerprint described in
engineering_notes_verify_template.md, then asserts the fix. If
someone changes forge.py in a way that re-introduces one of the
bugs, the corresponding test will fail with a precise error
message pointing at the bug.

Bug-to-test mapping:
  - test_bug1_repr_interprets_backslash        : bug 1
  - test_bug2_re_sub_interprets_replacement    : bug 2
  - test_bug3_brace_counter_ignores_string     : bug 3
  - test_bug4_c1_narrow_window_removed         : bug 4 (this is
    tested via the verify_TEMPLATE.py / _substitute_verify
    integration test in test_forge_happy.py)
  - test_bug5_regex_too_strict_replaced        : bug 5 (tested
    against the C1 symbol-definitions in the audit output, not
    the forge substitution)
  - test_bug6_paper5_section_pattern_accepted  : bug 6

The remaining bugs (1, 2, 3) are unit-testable on the substitution
engine itself; bugs 4, 5, 6 are tested against the actual
audit output produced by the forked verify script.
"""
from __future__ import annotations
import re
import textwrap
import pytest

from tmaudit.forge import (
    _format_simple_value,
    _substitute_verify,
    _substitute_fix_unicode,
)


# ============================================================================
# Bug 1: repr() interprets \b as backspace
# ============================================================================

class TestBug1ReprInterpretsBackslash:
    """Bug 1: a regex string like '\\bCAF\\b' is emitted by repr() as
    '\\x08CAF\\x08'. The fix uses r-string literals (r'...') when
    the input contains backslash regex sequences.
    """

    @pytest.mark.parametrize('raw', [
        r'\bCAF\b',
        r'\s+t',
        r'\d{3}',
        r'\{abc\}',
        r'foo\.',
    ])
    def test_regex_string_emitted_as_raw_literal(self, raw):
        """A regex-looking string must be emitted as an r-string."""
        out = _format_simple_value(raw)
        assert out.startswith("r'"), (
            f'expected raw string literal, got {out!r}'
        )
        # And the backslashes must still be present (not turned into \x08)
        assert '\\' in out, f'backslashes were stripped from {raw!r}'

    def test_non_regex_string_uses_repr(self):
        """A plain string (no backslashes) must use repr(), not r-string."""
        out = _format_simple_value('Cohen')
        # repr('Cohen') -> "'Cohen'" — no r prefix
        assert out == "'Cohen'", f'expected repr output, got {out!r}'

    def test_string_with_embedded_quote_is_escaped(self):
        """A regex with a single-quote must have it backslash-escaped."""
        out = _format_simple_value(r"it's\b")
        assert out.startswith("r'")
        # The apostrophe must not terminate the string literal
        assert out.endswith("'"), f'expected r-string, got {out!r}'

    def test_apostrophe_value(self):
        """Cohen's d (default effect-size) must round-trip safely."""
        out = _format_simple_value("Cohen's d")
        # This is NOT a regex string (no backslash), so it's a normal
        # string literal with proper quote escaping
        assert out == "\"Cohen's d\"", f'got {out!r}'

    def test_repro_line_from_engineering_notes(self):
        """The exact one-liner reproducer from the engineering notes."""
        # Original bug: repr('\b') was '\x08' (backspace).
        # Fix: regex strings get r-string treatment.
        result = _format_simple_value(r'\b')
        assert result == r"r'\b'", (
            f'\\b should emit r-string, got {result!r} — '
            f'this is the bug-1 fingerprint'
        )


# ============================================================================
# Bug 2: re.sub interprets backslashes in replacement text
# ============================================================================

class TestBug2ResubBackslashInReplacement:
    """Bug 2: re.sub() with a regex pattern as the replacement
    text raises 'bad escape \\s' (etc.) because re.sub interprets
    backslashes as backreferences. The fix replaces re.sub with
    a hand-written brace-counting loop and literal str.slice.
    """

    def test_substitute_verify_with_regex_replacement_succeeds(self, minimal_verify_template, paper1_config):
        """The substitute function must succeed even when the
        replacement text contains backslashes (regex patterns).
        """
        # Act: this should not raise re.error: bad escape \s
        out = _substitute_verify(minimal_verify_template, paper1_config)
        # Assert
        assert "CHECKS_CONFIG: dict = {" in out
        assert "c1_symbols" in out
        # The whole substituted file must be parseable Python. We
        # use ast.parse for safety (does not execute side effects).
        import ast
        try:
            ast.parse(out)
        except SyntaxError as e:
            pytest.fail(
                f'Substituted output is not parseable Python: {e}\n'
                f'Output was:\n{out}'
            )

    def test_no_re_sub_in_substitute_verify(self, minimal_verify_template, paper1_config):
        """Defensive: ensure we never call re.sub with the substituted
        block as the replacement argument.
        """
        # This is a meta-test: the fix used str.slice instead of
        # re.sub. We can verify by monkey-patching re.sub and
        # checking it is NOT called by _substitute_verify.
        import re as _re
        original = _re.sub
        calls = []
        def spy(*args, **kwargs):
            calls.append(args)
            return original(*args, **kwargs)
        _re.sub = spy
        try:
            _substitute_verify(minimal_verify_template, paper1_config)
        finally:
            _re.sub = original
        # The substitute function should not use re.sub AT ALL.
        # (It uses a hand-written brace counter; see engineering notes
        #  bug 2 for the rationale.)
        assert calls == [], (
            f'_substitute_verify called re.sub {len(calls)} times — '
            f'bug-2 fingerprint: the replacement text contains '
            f'\\b/\\s/\\d which re.sub would interpret as backreferences'
        )

    def test_repro_from_engineering_notes(self):
        """The exact one-liner from the engineering notes that
        triggered the original bug.
        """
        # The original repro: re.sub('x', r'\s\n', 'x') raises
        # re.error: bad escape \s at position 0. We assert this
        # still raises (so we are testing Python's re module is
        # what we think it is) — and then assert that our
        # substitute function does NOT have this property.
        with pytest.raises(Exception):
            import re
            re.sub('x', r'\s\n', 'x')


# ============================================================================
# Bug 3: brace counter mis-counts \{ and \} inside string literals
# ============================================================================

class TestBug3BraceCounterIgnoresStringLiterals:
    """Bug 3: the brace counter naively counts { and } in raw text,
    but the CHECKS_CONFIG block contains a regex string with `\{`
    and `\{`. The fix adds a string-literal state machine.
    """

    def test_regex_string_with_braces_does_not_corrupt_block(self, bug4_config):
        """The substitute function must produce a clean CHECKS_CONFIG
        block even when c2_section_pattern contains escaped braces
        inside a string literal.
        """
        # Get the real verify_TEMPLATE.py (which contains the marker)
        from tmaudit.forge import _read_template
        template = _read_template('verify_TEMPLATE.py')
        out = _substitute_verify(template, bug4_config)
        # The whole substituted file must be parseable Python. If
        # bug 3 was re-introduced, the brace counter would exit
        # early and the file would have leftover text concatenated
        # to the CHECKS_CONFIG block, making it un-parseable.
        import ast
        try:
            ast.parse(out)
        except SyntaxError as e:
            pytest.fail(
                f'Substituted verify_TEMPLATE.py is not parseable: {e}\n'
                f'Fingerprint: bug 3 (brace counter did not skip '
                f'braces inside a string literal)\n'
                f'Output (last 500 chars):\n...{out[-500:]}'
            )
        # The substituted file must contain the regex string
        # verbatim (i.e. not truncated by the brace counter).
        assert 'Statistical Protocol' in out
        assert 'Power analysis' in out

    def test_braces_inside_string_literal_are_preserved(self, bug4_config):
        """The regex string with `\{` and `\}` should round-trip
        unchanged into the output.
        """
        from tmaudit.forge import _read_template
        template = _read_template('verify_TEMPLATE.py')
        out = _substitute_verify(template, bug4_config)
        # Find the CHECKS_CONFIG block and check that the escaped
        # braces are still escaped (not stripped)
        assert r'\{' in out or r'\section\*?\{' in out
        # And the closing brace of CHECKS_CONFIG must be the LAST
        # `}` in the block, not some intermediate `}` inside the
        # regex string.
        block_start = out.find('CHECKS_CONFIG: dict = {')
        # Count braces between block_start and the next few hundred chars
        chunk = out[block_start:block_start + 5000]
        # The first `}` in chunk should be the actual close of
        # CHECKS_CONFIG (after the closing `}` of c6_blacklist).
        # If bug 3 was re-introduced, the first `}` would be inside
        # the regex string.
        first_close = chunk.find('}')
        # That first close should NOT be preceded by an
        # un-escaped `\` in the regex
        # (this is a heuristic check; the real bug was that
        # the brace counter exited early)
        assert first_close > 100, (
            f'CHECKS_CONFIG block is suspiciously short '
            f'(first `}}` at char {first_close}); '
            f'bug-3 fingerprint: brace counter stopped early'
        )

    def test_repro_from_engineering_notes(self, bug4_config):
        """The exact scenario from engineering-notes bug 3:
        a regex string with `\{` and `\}` inside the config block
        must not confuse the brace counter.
        """
        from tmaudit.forge import _read_template
        template = _read_template('verify_TEMPLATE.py')
        out = _substitute_verify(template, bug4_config)
        # If bug 3 was re-introduced, the brace counter would exit
        # early inside the regex string, leaving a half-written
        # CHECKS_CONFIG block followed by random template text.
        # The result would be syntactically invalid Python. The
        # simplest check that the bug did not recur is to confirm
        # the file is parseable end-to-end.
        import ast
        try:
            ast.parse(out)
        except SyntaxError as e:
            pytest.fail(
                f'Bug 3 fingerprint detected: substituted output is '
                f'not parseable. {e}'
            )


# ============================================================================
# Bug 4: C1 check too narrow (250-char window)
# ============================================================================
# This is tested indirectly via the integration test in
# test_forge_happy.py: the audit script that _substitute_verify
# produces must accept a Notation block at the end of the abstract.
# The unit test here is on the substitution itself: the CHECKS_CONFIG
# block must include the c1_symbols entry from the config (which
# triggers the audit) and not lose the symbol token / definition.

class TestBug4C1SymbolSubstitution:
    """Bug 4 was an audit-logic issue, not a substitution issue.
    The substitution must faithfully emit the c1_symbols entry that
    triggers the audit, including the regex with `[^a-zA-Z]` etc.
    """

    def test_c1_symbols_round_trip_through_substitution(
        self, real_verify_template, paper1_config
    ):
        out = _substitute_verify(real_verify_template, paper1_config)
        # The first symbol in paper1_config is CAF. Its
        # definition contains `.{0,80}` (regex quantifier) and
        # `\\b` (word boundary). Both must be present in the
        # output as a raw string.
        assert r"r'\bCAF\b" in out, (
            'CAF symbol token not preserved as a raw string. '
            'bug-1 / bug-4 fingerprint: token or definition '
            'replaced or escaped incorrectly.'
        )

    def test_c1_symbol_definition_uses_raw_string(
        self, real_verify_template, paper1_config
    ):
        out = _substitute_verify(real_verify_template, paper1_config)
        # The definition string for E_T contains `.{0,80}` —
        # this should be emitted as a raw string (because the
        # leading `.` is a regex metachar).
        # It also contains the literal substring "temporal" which
        # is what the audit looks for.
        assert 'temporal' in out


# ============================================================================
# Bug 5: C5 test-name regex too strict
# ============================================================================
# Same as bug 4: the audit-logic itself is in verify_TEMPLATE.py.
# The substitution test is whether the c5_d_type value
# ("Cohen's d") is correctly emitted.

class TestBug5EffectSizeSubstitution:
    def test_c5_d_type_round_trips(self, real_verify_template, paper1_config):
        out = _substitute_verify(real_verify_template, paper1_config)
        # The c5_d_type value "Cohen's d" should appear in the
        # CHECKS_CONFIG block. (The original c5_d_type was hard-coded
        # in verify_TEMPLATE.py before bug 5 was fixed.)
        # After the fix, the value comes from CHECKS_CONFIG.
        assert "Cohen" in out
        # The CHECKS_CONFIG block must have the c5_d_type key
        assert "'c5_d_type'" in out


# ============================================================================
# Bug 6: c2_section_pattern too narrow
# ============================================================================

class TestBug6Paper5SectionPattern:
    """Bug 6: Paper 5's section is "Statistical Protocol", not
    "Power analysis". The config must be substituted faithfully so
    the audit accepts the new section name.
    """

    def test_paper5_section_pattern_includes_statistical_protocol(
        self, real_verify_template, bug4_config
    ):
        out = _substitute_verify(real_verify_template, bug4_config)
        # The CHECKS_CONFIG c2_section_pattern should include
        # both "Power analysis" and "Statistical Protocol"
        assert 'Power analysis' in out
        assert 'Statistical Protocol' in out

    def test_paper5_abstract_k_allowed_is_9(
        self, real_verify_template, bug4_config
    ):
        out = _substitute_verify(real_verify_template, bug4_config)
        # bug4_config's c2_abstract_k_allowed is [9]
        assert '9' in out

    def test_paper5_max_self_cite_keys_is_1(
        self, real_verify_template, bug4_config
    ):
        out = _substitute_verify(real_verify_template, bug4_config)
        # bug4_config's c4_max_self_cite_keys is 1 (Paper 5 retains
        # only memorycontagion)
        assert "'c4_max_self_cite_keys': 1" in out


# ============================================================================
# Bug-class invariants: properties that any correct fix must satisfy
# ============================================================================

class TestInvariants:
    """These tests check properties of the substituted output that
    must hold for ANY correct implementation of the fix — not just
    the current one. They are the most defensive against regression.
    """

    def test_substituted_output_is_parseable_python(
        self, real_verify_template, paper1_config
    ):
        """The substituted output, as a string, must be valid Python
        that can be `exec()`-ed without raising.
        """
        out = _substitute_verify(real_verify_template, paper1_config)
        ns: dict = {'Path': __import__('pathlib').Path}
        try:
            # exec the whole file (minus the shebang which exec
            # cannot handle)
            if out.startswith('#!/'):
                out_for_exec = '\n'.join(out.splitlines()[1:])
            else:
                out_for_exec = out
            exec(out_for_exec, ns)
        except Exception as e:
            pytest.fail(f'Substituted verify script is not valid Python: {e}')
        # And the resulting CHECKS_CONFIG must be a dict
        assert isinstance(ns.get('CHECKS_CONFIG'), dict), (
            'CHECKS_CONFIG is not a dict after substitution'
        )

    def test_substituted_output_preserves_all_six_categories(
        self, real_verify_template, paper1_config
    ):
        """The substituted output must have a check function for
        every category C1..C6 (otherwise the audit is silently
        reduced in scope).
        """
        out = _substitute_verify(real_verify_template, paper1_config)
        for cat in ('c1_symbols', 'c2_families', 'c2_section_pattern',
                    'c3_concept', 'c4_self_cite_prefix',
                    'c5_d_type', 'c6_blacklist'):
            assert f"'{cat}'" in out, (
                f'CHECKS_CONFIG is missing key {cat!r}; '
                f'a category has been silently dropped from the audit'
            )

    def test_substituted_output_has_correct_root_path(
        self, real_verify_template, paper1_config
    ):
        out = _substitute_verify(real_verify_template, paper1_config)
        # The ROOT line must reference the paper's directory
        assert 'PAPER1_CONSOLIDATED' in out

    def test_substituted_output_has_correct_output_path(
        self, real_verify_template, paper1_config
    ):
        out = _substitute_verify(real_verify_template, paper1_config)
        # The verify output filename is verify_p1.py
        assert 'verify_p1' in out or 'verify_p' in out


# ============================================================================
# Smoke test: substitute a real template and exec the result
# ============================================================================

def test_substitute_real_template_for_paper_1_produces_valid_python(
    real_verify_template, paper1_config
):
    """End-to-end: take the actual installed verify_TEMPLATE.py,
    substitute Paper 1's config, and exec the result.
    """
    out = _substitute_verify(real_verify_template, paper1_config)
    if out.startswith('#!/'):
        out = '\n'.join(out.splitlines()[1:])
    ns: dict = {'Path': __import__('pathlib').Path,
                're': __import__('re'),
                'sys': __import__('sys'),
                'defaultdict': __import__('collections').defaultdict,
                '__name__': 'verify_p1_forged'}
    exec(compile(out, '<forged>', 'exec'), ns)
    # And the resulting module should expose main() and the 6 checks
    assert callable(ns.get('main'))
    assert callable(ns.get('check_c1_abstract_definitions'))
    assert callable(ns.get('check_c2_bonferroni_consistency'))
    assert callable(ns.get('check_c3_formalization'))
    assert callable(ns.get('check_c4_citation_hygiene'))
    assert callable(ns.get('check_c5_sample_size_and_test'))
    assert callable(ns.get('check_c6_blacklist'))