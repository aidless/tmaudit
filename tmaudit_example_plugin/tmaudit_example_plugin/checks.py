"""Demo checks for tmaudit_example_plugin.

These three functions are registered with tmaudit via the
``tmaudit.plugins`` entry-point group (declared in
``pyproject.toml``). They are intentionally simple so that
plugin authors can copy-paste this file as a starting point.

Each check returns a list of ``Finding`` objects. The
``@tmaudit.check`` decorator carries the metadata that
``tmaudit plugins info`` and ``plugins list`` display.
"""
from __future__ import annotations
import re
from typing import List, Optional

from tmaudit import Finding, check


# ---------------------------------------------------------------------------
# Check 1: flag TODO markers
# ---------------------------------------------------------------------------

@check(
    name="flag-todo-markers",
    severity="MEDIUM",
    help_text="Flag any 'TODO' or 'FIXME' marker in main.tex",
    version="0.1.0",
)
def flag_todo_markers(
    tex: str,
    config: Optional[dict] = None,
) -> List[Finding]:
    """Find every TODO / FIXME marker in the body text.

    Patterns matched (case-sensitive):
      - ``TODO:`` / ``TODO `` (followed by space)
      - ``FIXME:`` / ``FIXME ``

    A simple line-by-line scan — sufficient for most papers.
    For multi-line markers, use a regex with DOTALL.
    """
    findings: List[Finding] = []
    for i, line in enumerate(tex.splitlines()):
        if re.search(r"\b(TODO|FIXME)\b", line):
            findings.append(Finding(
                category="TODO",
                severity="MEDIUM",
                message=(
                    f"{line.strip()[:80]} marker at line {i+1}; "
                    f"resolve before submission."
                ),
                line=i + 1,
            ))
    return findings


# ---------------------------------------------------------------------------
# Check 2: flag XXX debug markers
# ---------------------------------------------------------------------------

@check(
    name="flag-xxx-markers",
    severity="LOW",
    help_text=(
        "Flag any 'XXX' debug marker left in main.tex; "
        "common in draft papers but never in camera-ready."
    ),
    version="0.1.0",
)
def flag_xxx_markers(
    tex: str,
    config: Optional[dict] = None,
) -> List[Finding]:
    """Find any standalone ``XXX`` debug marker.

    XXX markers in a LaTeX source typically mean "fill
    this in later" or "TODO check this". They should
    never reach a camera-ready submission.
    """
    findings: List[Finding] = []
    for i, line in enumerate(tex.splitlines()):
        # Match XXX surrounded by non-letter characters (word
        # boundaries) so we don't flag words containing xxx.
        if re.search(r"\bXXX\b", line):
            findings.append(Finding(
                category="XXX",
                severity="LOW",
                message=(
                    f"Debug marker 'XXX' at line {i+1}; "
                    f"remove before submission."
                ),
                line=i + 1,
            ))
    return findings


# ---------------------------------------------------------------------------
# Check 3: flag long abstracts
# ---------------------------------------------------------------------------

@check(
    name="flag-long-abstract",
    severity="MEDIUM",
    help_text=(
        "Flag abstracts longer than 300 words; most venues "
        "(TMLR, NeurIPS, ICLR) cap at 250 words."
    ),
    version="0.1.0",
)
def flag_long_abstract(
    tex: str,
    config: Optional[dict] = None,
) -> List[Finding]:
    """Find the abstract environment and count its words.

    A simple heuristic: locate ``\\begin{abstract}`` and
    ``\\end{abstract}``, count words in the body. If the
    count exceeds the configurable threshold (default 300),
    emit a single MEDIUM finding.

    The threshold is configurable per-paper via:

        CHECKS_CONFIG['c11_long_abstract_threshold'] = 250

    Not all papers carry this key; we default to 300 to be
    lenient (the strictest venue limit is 250).
    """
    findings: List[Finding] = []

    # Find the abstract span.
    begin = tex.find(r"\begin{abstract}")
    if begin < 0:
        return findings  # No abstract; nothing to check.
    end = tex.find(r"\end{abstract}", begin)
    if end < 0:
        return findings  # Malformed LaTeX; skip.

    body = tex[begin:end]
    # Strip simple LaTeX commands (\\command{...}) so we
    # don't count commands as words. Not perfect but
    # sufficient for a heuristic.
    body = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", "", body)
    # Strip braces and dollar math.
    body = re.sub(r"[{}]", "", body)
    word_count = len(body.split())

    threshold = 300
    if config and isinstance(config, dict):
        threshold = int(config.get("c11_long_abstract_threshold", threshold))

    if word_count > threshold:
        # Convert byte offset to 1-based line number.
        line_no = tex[:begin].count("\n") + 1
        findings.append(Finding(
            category="ABSTRACT",
            severity="MEDIUM",
            message=(
                f"Abstract is {word_count} words; "
                f"limit is {threshold}. Consider trimming."
            ),
            line=line_no,
        ))
    return findings
