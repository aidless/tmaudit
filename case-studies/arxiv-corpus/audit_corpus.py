"""Run tmaudit's audit core over a real arXiv corpus, as shipped.

Why this exists
---------------
`tmaudit` is published on PyPI and its README tells a reader to fork the
template into their own paper directory. The template ships with a
``CHECKS_CONFIG`` block that the reader is expected to edit. This script asks
the question that a "clone and run" reader will ask: **what does the audit
core do on real papers when the config has not been edited for them?**

It answers it on a corpus of real LaTeX sources pulled from arXiv, running the
ten categories exactly as ``verify_TEMPLATE.main()`` runs them -- same order,
same arguments, same default config -- with one addition: each check is
isolated in a ``try`` so that one failure does not hide the other nine. That
isolation lives in the harness, not in the tool, and the difference is itself
one of the results.

Version note
------------
The committed ``results.json`` was produced against the template **as shipped
in v0.5.0**. As of v0.5.1 the factory ``CHECKS_CONFIG`` is empty (defect D1)
and C1/C2/C4 read the config with ``get()`` defaults (D3/D6), so on a v0.5.1+
template this script injects ``V0_5_0_CHECKS_CONFIG`` to reproduce the
v0.5.0 behaviour for the config-driven categories. The bib-key regex fix
(D4) lives in the function body and cannot be restored by configuration: on
a v0.5.1+ template, C4 will no longer fabricate the "missing cite key"
findings recorded in the committed results.

The corpus is mechanical: the first 25 entries in arXiv's ``cs.CL`` recent
listing at the time of the run, taken in page order, no content screening. The
ID list is committed next to this script so the selection can be replayed.

What it measures
----------------
* per paper, per category: ``fired`` / ``clean`` / ``needs_config`` /
  ``error``
* the default config's provenance, read out of the template itself
* the findings that are genuinely portable, separated from the ones that are
  artefacts of running a foreign config
* whether an abstract could be located at all, since six categories need one

Usage
-----
    python3 audit_corpus.py --prepare       # extract the e-prints in _corpus/
    python3 audit_corpus.py                 # audit and write results.json
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import re
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TEMPLATE = REPO / "src" / "tmaudit" / "templates" / "verify_TEMPLATE.py"

MAX_INPUT_DEPTH = 8

# The factory CHECKS_CONFIG exactly as it shipped in v0.5.0. Injected when
# the template on disk no longer carries it (v0.5.1+ ships an empty dict),
# so the audit below measures the shipped-in-v0.5.0 surface it claims to.
V0_5_0_CHECKS_CONFIG = {
    "c1_symbols": [
        {
            "name": r"$\Delta$CAF (consensus-against-field coefficient)",
            "token": r"\bCAF\b",
            "definition": r"\bCAF\b.{0,80}=|consensus.{0,30}agreement|strateg.{0,30}convergence",
        },
        {
            "name": r"$E_T$ (temporal-accumulation effect on calibration)",
            "token": r"\bE_T\b",
            "definition": r"E_T.{0,80}=|temporal.{0,30}accumulation|peer.anchored.{0,30}confidence",
        },
        {
            "name": r"$\Delta$ECE (calibration delta)",
            "token": r"\\Delta\s*ECE|\\Delta\\mathrm\{ECE\}",
            "definition": r"\\Delta\s*ECE.{0,80}=|calibration.{0,30}loss|calibration.{0,30}degrad",
        },
        {
            "name": "TTRL (Test-Time Reinforcement Learning)",
            "token": r"\bTTRL\b",
            "definition": r"TTRL.{0,80}=|Test.Time.{0,40}Reinforcement.{0,40}Learning",
        },
    ],
    "c2_families": {"main": 3},
    "c2_section_pattern": (
        r"\\section\*?\{[^}]*Power analysis[^}]*\}|"
        r"\\subsection\*?\{[^}]*Power analysis[^}]*\}"
    ),
    "c2_abstract_k_allowed": [3, 9],
    "c3_concept": (
        "Two Faces (Face 1: Strategy Consensus; Face 2: Calibration Contagion)"
    ),
    "c3_concept_token": (
        r"\\textbf\{Face 1\}|\\textbf\{Face 2\}|\bFace\s+1\b|\bFace\s+2\b"
    ),
    "c3_formal": r"\\section\{Face 1:",
    "c3_formal_secondary": r"\\section\{Face 2:",
    "c4_self_cite_threshold": 0.30,
    "c4_self_cite_prefix": "liu2026",
    "c4_max_self_cite_keys": 3,
    "c5_d_type": "Cohen's d",
    "c6_blacklist": ["paradigm", "yield", "reveal"],
    "c7_max_ceremonial": 2,
}


def load_template(path: Path):
    """Import the template as a module, exactly as it ships."""
    spec = importlib.util.spec_from_file_location("verify_TEMPLATE_as_shipped", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def extract(eprint: Path, out: Path) -> str:
    """Unpack one e-print. Returns how it arrived, not whether it parsed."""
    out.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(eprint, "r:gz") as tf:
            tf.extractall(out, filter="data")
        return "tar"
    except (tarfile.ReadError, EOFError):
        pass
    try:
        with gzip.open(eprint, "rb") as fh:
            payload = fh.read()
    except OSError as exc:
        return f"gzip_error:{type(exc).__name__}"
    if payload[:4] == b"%PDF":
        (out / "main.pdf").write_bytes(payload)
        return "pdf"
    (out / "main.tex").write_bytes(payload)
    return "single_tex"


def find_main_tex(root: Path) -> Path | None:
    candidates = []
    for path in root.rglob("*.tex"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "\\begin{document}" in text:
            candidates.append((len(path.parts), len(text), path))
    if not candidates:
        return None
    # Shallowest path first, then the longest file: the root file is usually
    # the one that pulls the rest in.
    candidates.sort(key=lambda item: (item[0], -item[1]))
    return candidates[0][2]


def flatten(main: Path, root: Path, depth: int = 0) -> str:
    text = main.read_text(encoding="utf-8", errors="replace")
    if depth >= MAX_INPUT_DEPTH:
        return text

    def substitute(match: re.Match) -> str:
        name = match.group(1).strip()
        if not name.endswith(".tex"):
            name += ".tex"
        target = root / name
        if not target.exists():
            return match.group(0)
        return flatten(target, root, depth + 1)

    return re.sub(r"\\(?:input|include)\s*\{([^}]+)\}", substitute, text)


def find_bib(root: Path, tex: str) -> str:
    named = re.search(r"\\bibliography\{([^}]+)\}", tex)
    if named:
        for part in named.group(1).split(","):
            candidate = root / (part.strip() + ".bib")
            if candidate.exists():
                return candidate.read_text(encoding="utf-8", errors="replace")
    bibs = sorted(root.rglob("*.bib"), key=lambda p: -p.stat().st_size)
    if bibs:
        return bibs[0].read_text(encoding="utf-8", errors="replace")
    return ""


def build_checks(tmpl):
    """The ten categories, wired exactly as the template's main() wires them."""
    cfg = tmpl.CHECKS_CONFIG
    c7_threshold = int(cfg.get("c7_max_ceremonial", 2))
    c8_claims = cfg.get("c8_claimed_effects", []) or []
    c9_keywords = cfg.get("c9_figure_keywords", []) or []
    c10_claims = cfg.get("c10_reproducibility_claims", []) or []
    return [
        ("C1", lambda t, b: tmpl.check_c1_abstract_definitions(t)),
        ("C2", lambda t, b: tmpl.check_c2_bonferroni_consistency(t)),
        ("C3", lambda t, b: tmpl.check_c3_formalization(t)),
        ("C4", lambda t, b: tmpl.check_c4_citation_hygiene(t, b)),
        ("C5", lambda t, b: tmpl.check_c5_sample_size_and_test(t)),
        ("C6", lambda t, b: tmpl.check_c6_blacklist(t)),
        ("C7", lambda t, b: tmpl.check_c7_citation_context(t, c7_max_ceremonial=c7_threshold)),
        ("C8", lambda t, b: tmpl.check_c8_statistical_power(t, c8_claims)),
        ("C9", lambda t, b: tmpl.check_c9_figure_caption(t, c9_keywords)),
        ("C10", lambda t, b: tmpl.check_c10_reproducibility(t, c10_claims)),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, default=HERE / "_corpus")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--prepare", action="store_true",
                        help="extract the e-prints under _corpus/papers first")
    args = parser.parse_args(argv)

    ids = [line.strip() for line in (HERE / "ids.txt").read_text(encoding="utf-8").splitlines()
           if line.strip()]
    papers_dir = args.corpus / "papers"
    work_dir = args.corpus / "extracted"

    if args.prepare:
        for paper_id in ids:
            eprint = papers_dir / f"{paper_id}.e-print"
            if not eprint.exists():
                print(f"{paper_id}: no e-print on disk")
                continue
            print(f"{paper_id}: {extract(eprint, work_dir / paper_id)}")
        return 0

    tmpl = load_template(args.template)
    if not tmpl.CHECKS_CONFIG:
        # v0.5.1+ ships an empty factory config (D1 fix). Restore the
        # v0.5.0 values so the audit measures the surface it claims to.
        tmpl.CHECKS_CONFIG.update(V0_5_0_CHECKS_CONFIG)
    checks = build_checks(tmpl)
    default_config = {
        "c1_symbols": [s.get("name") for s in tmpl.CHECKS_CONFIG.get("c1_symbols", [])],
        "c2_families": tmpl.CHECKS_CONFIG.get("c2_families"),
        "c2_section_pattern": tmpl.CHECKS_CONFIG.get("c2_section_pattern"),
        "c3_concept_token": tmpl.CHECKS_CONFIG.get("c3_concept_token"),
        "c3_formal": tmpl.CHECKS_CONFIG.get("c3_formal"),
        "c4_self_cite_prefix": tmpl.CHECKS_CONFIG.get("c4_self_cite_prefix"),
        "c6_blacklist": tmpl.CHECKS_CONFIG.get("c6_blacklist"),
        "c8_claimed_effects": tmpl.CHECKS_CONFIG.get("c8_claimed_effects", []),
        "c9_figure_keywords": tmpl.CHECKS_CONFIG.get("c9_figure_keywords", []),
        "c10_reproducibility_claims": tmpl.CHECKS_CONFIG.get("c10_reproducibility_claims", []),
    }

    per_paper = []
    for paper_id in ids:
        root = work_dir / paper_id
        entry: dict = {"paper_id": paper_id, "categories": {}}
        main_tex = find_main_tex(root) if root.exists() else None
        if main_tex is None:
            entry["status"] = "no_latex_source"
            per_paper.append(entry)
            continue
        entry["status"] = "latex"
        entry["main_tex"] = str(main_tex.relative_to(root))
        tex = flatten(main_tex, root)
        bib = find_bib(root, tex)
        entry["tex_chars"] = len(tex)
        entry["bib_chars"] = len(bib)
        entry["has_abstract"] = tmpl.extract_abstract(tex) is not None

        for cat, fn in checks:
            try:
                findings = fn(tex, bib)
            except KeyError as exc:
                entry["categories"][cat] = {"outcome": "needs_config", "key": str(exc)}
                continue
            except Exception as exc:  # noqa: BLE001 - the point is to record it
                entry["categories"][cat] = {"outcome": "error",
                                            "detail": f"{type(exc).__name__}: {exc}"[:160]}
                continue
            if findings:
                entry["categories"][cat] = {
                    "outcome": "fired",
                    "n": len(findings),
                    "messages": [msg.splitlines()[0][:200] for _, msg, _ in findings],
                }
            else:
                entry["categories"][cat] = {"outcome": "clean"}
        per_paper.append(entry)

    totals: dict[str, dict[str, int]] = {}
    for cat, _ in checks:
        counts: dict[str, int] = {}
        for entry in per_paper:
            outcome = entry["categories"].get(cat, {}).get("outcome", "not_run")
            counts[outcome] = counts.get(outcome, 0) + 1
        totals[cat] = counts

    payload = {
        "generated_by": "case-studies/arxiv-corpus/audit_corpus.py",
        "template": str(args.template.relative_to(REPO)),
        "shipped_default_config": default_config,
        "corpus": {
            "source": "arXiv cs.CL recent listing, first 25 entries in page order",
            "n_ids": len(ids),
            "n_with_latex": sum(1 for e in per_paper if e["status"] == "latex"),
        },
        "per_category_totals": totals,
        "per_paper": per_paper,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"\ncorpus: {payload['corpus']['n_with_latex']}/{len(ids)} papers had LaTeX sources")
    print(f"{'cat':4s} " + "  ".join(f"{k:>13s}" for k in
                                     ("fired", "clean", "needs_config", "error", "not_run")))
    for cat, _ in checks:
        row = totals[cat]
        print(f"{cat:4s} " + "  ".join(f"{row.get(k, 0):>13d}" for k in
                                       ("fired", "clean", "needs_config", "error", "not_run")))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
