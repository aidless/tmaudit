"""Corpus-level regression: the audit runs unattended on real arXiv sources.

These tests exist because a single hand-chosen paper is not evidence. The
v0.6.0 fixes — .bbl parsing, bibliography detection, and C1 degrading
instead of crashing — were each found by running the tool on a real
tarball, and each was found on a *different* paper. This file replays all
of them at once so the next change cannot quietly reintroduce a paper
shape that aborts the audit.

Marked ``slow`` (spawns a subprocess per paper): run with ``-m slow``.
Skips entirely if the corpus is absent, which is the case on a fresh
clone that has not fetched ``case-studies/arxiv-corpus/_corpus``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CORPUS = (
    Path(__file__).resolve().parent.parent
    / "case-studies" / "arxiv-corpus" / "_corpus" / "extracted"
)
SRC = Path(__file__).resolve().parent.parent / "src"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not CORPUS.is_dir(),
        reason="arXiv corpus not present (case-studies/arxiv-corpus/_corpus)",
    ),
]


def _papers() -> list[Path]:
    if not CORPUS.is_dir():
        return []
    return sorted(
        p for p in CORPUS.iterdir() if p.is_dir() and (p / "main.tex").is_file()
    )


def _run_verify(paper: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    work = tmp_path / "paper"
    shutil.copytree(paper, work)
    (work / "paper.toml").write_text(
        'schema = "tmaudit-target/1"\n[paper]\nname = "corpus"\n',
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC)
    return subprocess.run(
        [sys.executable, "-m", "tmaudit.cli", "verify", "--target", "paper.toml"],
        cwd=work, capture_output=True, text=True, env=env,
    )


def test_corpus_is_present():
    assert _papers(), "corpus directory exists but holds no main.tex papers"


@pytest.mark.parametrize("paper", _papers(), ids=lambda p: p.name)
def test_no_paper_aborts_the_audit(paper: Path, tmp_path):
    """Every paper in the corpus must produce a report.

    Exit codes: 0 clean, 1 findings, 3 unobserved category. Exit 2 means
    the run did not complete — a missing input or a crashed check — and
    that is the failure this test guards against.
    """
    proc = _run_verify(paper, tmp_path)
    combined = proc.stdout + proc.stderr
    assert proc.returncode in (0, 1, 3), (
        "exit %d for %s\n%s" % (proc.returncode, paper.name, combined[-1500:])
    )
    assert "ERROR: missing" not in proc.stderr, proc.stderr
    assert "crashed" not in proc.stdout, combined[-1500:]
    assert "PAPER AUDIT" in proc.stdout


@pytest.mark.parametrize("paper", _papers(), ids=lambda p: p.name)
def test_bibliography_resolves_for_every_paper(paper: Path, tmp_path):
    """"Refs: 0 entries" means C4 had nothing to check against.

    For a paper that cites anything, a zero key count is a detection
    failure, not a clean result. Papers with no bibliography at all are
    exempt — but there are none in this corpus.
    """
    proc = _run_verify(paper, tmp_path)
    refs = [
        line for line in proc.stdout.splitlines() if line.startswith("Refs:")
    ]
    assert refs, proc.stdout[:800]
    count = int(refs[0].split()[1])
    cites = "\\cite" in (paper / "main.tex").read_text(
        encoding="utf-8", errors="replace")
    if cites:
        assert count > 0, "%s cites but resolved 0 keys: %s" % (
            paper.name, refs[0])
