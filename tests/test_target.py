"""Tests for tmaudit.target and the plugin signature adaptation.

Two contracts are under test:

1. ``TexTarget`` parses structure (headings, citations) correctly,
   including titles with nested braces and multi-key ``\\cite``.
2. The plugin API stays total: a legacy ``def check(tex, config)``
   receives a ``str``, a ``def check(target, config)`` receives a
   ``Target``, and both the positional and the ``tex=`` keyword call
   styles keep working.
"""
from __future__ import annotations

import hashlib

import pytest

from tmaudit import plugins as P
from tmaudit.target import (
    TexTarget,
    TextTarget,
    as_target,
    as_text,
    is_target,
)

SAMPLE = r"""\documentclass{article}
\begin{document}
\section{Introduction}
We study calibration \citep{smith2020, doe2021}.

\subsection{Related \emph{Work}}
Prior work \cite[p.~3]{smith2020}.

\subsubsection{Deep}
Nested.
\end{document}
"""


# ============================================================================
# TexTarget structure
# ============================================================================

class TestSections:
    def test_levels_and_titles(self):
        t = TexTarget(SAMPLE)
        got = [(s.level, s.title) for s in t.sections()]
        assert got == [
            (1, "Introduction"),
            (2, r"Related \emph{Work}"),
            (3, "Deep"),
        ]

    def test_line_numbers_are_one_based(self):
        t = TexTarget(SAMPLE)
        first = t.sections()[0]
        assert first.line == 3
        assert SAMPLE.splitlines()[first.line - 1].startswith(r"\section")

    def test_nested_braces_do_not_truncate_title(self):
        t = TexTarget(r"\section{On \textbf{bold} things}text")
        assert t.sections()[0].title == r"On \textbf{bold} things"

    def test_starred_and_spaced_forms(self):
        t = TexTarget("\\section*{Star}\n\\subsection {Spaced}\n")
        assert [s.title for s in t.sections()] == ["Star", "Spaced"]

    def test_body_range_stops_at_next_heading(self):
        t = TexTarget(SAMPLE)
        a, b = t.sections()[0], t.sections()[1]
        # body_end is the index where the next heading *starts*, and
        # body_start is the index just past that heading's own title, so
        # the slice between them is the next heading command itself.
        assert a.body_end < b.body_start
        assert SAMPLE[a.body_end:b.body_start].startswith("\\subsection")
        assert "calibration" in a.body_of(t)
        assert "calibration" not in b.body_of(t)
        assert "Prior work" in b.body_of(t)

    def test_section_titles_helper(self):
        assert TexTarget(SAMPLE).section_titles()[0] == "Introduction"


class TestCitations:
    def test_multi_key_cite_is_split(self):
        refs = TexTarget(SAMPLE).citations()
        keys = [r.key for r in refs]
        assert keys == ["smith2020", "doe2021", "smith2020"]

    def test_optional_arg_is_skipped(self):
        t = TexTarget(r"text \cite[p.~3]{smith2020}")
        ref = t.citations()[0]
        assert ref.key == "smith2020"
        assert ref.command == "cite"
        assert ref.line == 1

    def test_parencite_variant(self):
        t = TexTarget(r"x \parencite{a,b}")
        assert [r.key for r in t.citations()] == ["a", "b"]
        assert t.citations()[0].command == "parencite"

    def test_citation_keys_are_deduplicated_in_order(self):
        assert TexTarget(SAMPLE).citation_keys() == ["smith2020", "doe2021"]

    def test_no_citations(self):
        assert TexTarget("nothing here").citations() == []


class TestMetadataAndCoercion:
    def test_metadata_sha256_matches_text(self):
        t = TexTarget("abc")
        meta = t.metadata()
        assert meta["sha256"] == hashlib.sha256(b"abc").hexdigest()
        assert meta["kind"] == "tex"
        assert meta["n_chars"] == 3

    def test_reads_from_path(self, tmp_path):
        p = tmp_path / "paper.tex"
        p.write_text(SAMPLE, encoding="utf-8")
        t = TexTarget(p)
        assert t.metadata()["path"] == str(p)
        assert t.metadata()["name"] == "paper"
        assert len(t.sections()) == 3

    def test_string_ending_in_tex_is_treated_as_path_when_it_exists(self, tmp_path):
        p = tmp_path / "x.tex"
        p.write_text("\\section{A}", encoding="utf-8")
        assert TexTarget(str(p)).section_titles() == ["A"]

    def test_is_target_and_as_target(self):
        t = TexTarget("x")
        assert is_target(t)
        assert not is_target("x")
        assert isinstance(as_target("x"), TextTarget)
        assert as_target(t) is t

    def test_as_text_unwraps(self):
        assert as_text(TexTarget("hello")) == "hello"
        assert as_text("hello") == "hello"

    def test_as_target_rejects_other_types(self):
        with pytest.raises(TypeError):
            as_target(17)

    def test_str_and_len_sugar(self):
        t = TexTarget("abcd")
        assert str(t) == "abcd"
        assert len(t) == 4


# ============================================================================
# Plugin signature adaptation
# ============================================================================

def _legacy_plugin():
    @P.check(name="legacy-todo", severity="LOW")
    def find_todos(tex, config=None):
        return [
            P.Finding("TODO", "LOW", "todo at %d" % (i + 1), i + 1)
            for i, line in enumerate(tex.splitlines())
            if "TODO" in line
        ]

    return find_todos


def _target_plugin():
    @P.check(name="target-sections", severity="LOW")
    def count_sections(target, config=None):
        return [
            P.Finding("STRUCT", "LOW", "section %r" % s.title, s.line)
            for s in target.sections()
        ]

    return count_sections


class TestAdaptation:
    def test_legacy_plugin_still_receives_str(self):
        plugin = _legacy_plugin()
        assert P.wants_target(plugin) is False
        findings = plugin(tex="a\nTODO\n")
        assert len(findings) == 1

    def test_target_plugin_receives_target(self):
        plugin = _target_plugin()
        assert P.wants_target(plugin) is True
        findings = plugin(TexTarget("\\section{A}\n\\section{B}\n"))
        assert [f.message for f in findings] == ["section 'A'", "section 'B'"]

    def test_run_plugin_adapts_for_each_convention(self):
        target = TexTarget("\\section{A}\nTODO\n")
        legacy = P.run_plugin(_legacy_plugin(), target)
        structured = P.run_plugin(_target_plugin(), target)
        assert len(legacy) == 1
        assert len(structured) == 1

    def test_run_plugin_accepts_plain_string_for_target_plugin(self):
        findings = P.run_plugin(_target_plugin(), "\\section{A}\n")
        assert len(findings) == 1

    def test_run_plugin_legacy_tex_keyword_still_works(self):
        findings = P.run_plugin(_legacy_plugin(), tex="TODO\n", paper_id="7")
        assert findings[0].paper_id == "7"

    def test_run_plugin_rejects_both_arguments(self):
        with pytest.raises(TypeError):
            P.run_plugin(_legacy_plugin(), TexTarget("x"), tex="x")

    def test_run_plugin_requires_an_object(self):
        with pytest.raises(TypeError):
            P.run_plugin(_legacy_plugin())

    def test_run_all_plugins_mixes_conventions(self):
        plugins = {"legacy": _legacy_plugin(), "struct": _target_plugin()}
        findings = P.run_all_plugins(plugins, TexTarget("\\section{A}\nTODO\n"))
        cats = sorted(f.category for f in findings)
        assert cats == ["STRUCT", "TODO"]

    def test_run_all_plugins_legacy_tex_keyword(self):
        findings = P.run_all_plugins({"legacy": _legacy_plugin()}, tex="TODO\n")
        assert len(findings) == 1

    def test_example_plugin_style_direct_call_with_tex_keyword(self):
        # Mirrors tests/test_example_plugin.py, which calls the decorated
        # object directly with tex= rather than going through run_plugin.
        plugin = _legacy_plugin()
        assert plugin(tex="TODO\n")[0].message == "todo at 1"

    def test_decorated_call_is_idempotent_under_double_adaptation(self):
        plugin = _target_plugin()
        target = TexTarget("\\section{A}\n")
        once = P.run_plugin(plugin, target)
        twice = plugin(P.adapt(plugin, target), None)
        assert once == twice
