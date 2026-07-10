"""Bug 5 unit test — direct test of the C5 test-name regex.

This is a unit test (not an integration test) that loads the
installed verify_TEMPLATE module and verifies that the
test-name pattern correctly matches "paired $t$-test[s]".

If someone re-introduces the strict `paired\\s+t-test` pattern
(this is bug 5), this test will fail.
"""
from __future__ import annotations
import re
import pytest

from tmaudit.forge import _read_template


# The string patterns that bug 5's fix must accept
STRINGS_THAT_MUST_BE_DETECTED = [
    "we used paired $t$-test, with n=30",
    "we used paired $t$-tests, with n=30",
    "Wilcoxon signed-rank test, n=30",
    "we used paired t-test, n=30",
    "we used paired t-tests, n=30",
]


def _extract_test_name_pattern() -> str:
    """Extract the test-name pattern from verify_TEMPLATE.py.

    The pattern is split across multiple adjacent raw strings
    (so the source stays under 80 columns). We concatenate them
    into a single regex pattern.
    """
    src = _read_template('verify_TEMPLATE.py')
    lines = src.splitlines()

    # Find the line with "has_test = bool(re.search("
    for i, line in enumerate(lines):
        if 'has_test' in line and 'bool' in line and 're.search' in line:
            # The pattern extends from i+1 to the line containing
            # ", window, re.IGNORECASE,"
            pattern_lines = []
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if 're.IGNORECASE' in next_line or 'window,' in next_line:
                    break
                # Each pattern line is "r'...'" (raw string)
                m = re.match(r"\s*r'(.*)'", next_line)
                if m:
                    pattern_lines.append(m.group(1))
            return ''.join(pattern_lines)
    raise RuntimeError('Could not find test-name pattern in verify_TEMPLATE.py')


# Module-level cache for the pattern
_PATTERN_CACHE: dict = {}


@pytest.fixture(scope='module')
def test_name_pattern() -> str:
    if 'pat' not in _PATTERN_CACHE:
        _PATTERN_CACHE['pat'] = _extract_test_name_pattern()
    return _PATTERN_CACHE['pat']


class TestBug5TestNameRegexUnit:
    """Direct test of the C5 test-name regex on a few representative
    strings. If the pattern is regressed to the strict
    `paired\\s+t-test` form, the $t$-test cases will fail to match.
    """

    @pytest.mark.parametrize('text', STRINGS_THAT_MUST_BE_DETECTED)
    def test_text_recognized_as_test_name(self, test_name_pattern, text):
        match = re.search(test_name_pattern, text, re.IGNORECASE)
        assert match, (
            f'Test-name pattern did not match {text!r}.\n'
            f'Pattern is: {test_name_pattern!r}\n'
            f'Bug 5 fingerprint: pattern is regressed to a strict form '
            f'that does not allow `$t$` or `-` characters between '
            f'`paired` and `test`.'
        )

    def test_pattern_does_not_use_strict_paired_backslash_s(self, test_name_pattern):
        """The pattern must NOT contain the strict `paired\\s+t-test`."""
        assert 'paired\\s+t-test' not in test_name_pattern, (
            f'Pattern still contains the strict `paired\\s+t-test` form: '
            f'{test_name_pattern!r}\n'
            f'Bug 5 fingerprint: pattern is regressed to a strict form.'
        )

    def test_pattern_uses_paired_relaxed(self, test_name_pattern):
        """The pattern must contain the relaxed `paired[^a-zA-Z]{0,8}...`
        form (this is the bug 5 fix).
        """
        assert 'paired[^a-zA-Z]' in test_name_pattern, (
            f'Pattern does not contain the relaxed `paired[^a-zA-Z]` form: '
            f'{test_name_pattern!r}\n'
            f'Bug 5 fix fingerprint: pattern allows non-letter characters '
            f'between `paired` and `t`, and between `t` and `test`.'
        )