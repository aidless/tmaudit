#!/usr/bin/env python3
"""Turn the 25-paper corpus results into a figure and a table.

The data already exists in ``case-studies/arxiv-corpus/results.json`` (produced
by that directory's ``audit_corpus.py`` against v0.5.0 as shipped). This script
does not re-run the audit and does not touch the network: it reads the recorded
per-category totals and renders them.

Run: ``python3 scripts/make_corpus_figure.py``

Outputs:
  figures/corpus_fire_rates.png
  figures/CORPUS.md
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "case-studies" / "arxiv-corpus" / "results.json"
OUT = ROOT / "figures"


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    totals = data["per_category_totals"]
    n_papers = int(data["corpus"]["n_ids"])
    cats = sorted(totals)
    rows = []
    for c in cats:
        t = totals[c]
        fired = int(t.get("fired", 0))
        clean = int(t.get("clean", 0))
        rows.append({"category": c, "fired": fired, "clean": clean,
                     "fire_rate": fired / n_papers})

    OUT.mkdir(exist_ok=True)
    lines = ["| category | papers where it fired | papers clean | fire rate |",
             "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['category']} | {r['fired']}/{n_papers} | {r['clean']}/{n_papers} | "
                     f"{r['fire_rate']:.0%} |")
    (OUT / "CORPUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib unavailable; wrote figures/CORPUS.md only")
        return

    fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=160)
    ys = list(range(len(rows)))
    rates = [r["fire_rate"] for r in rows]
    ax.barh(ys, rates, color="#1f6f5f", height=0.62)
    for y, r in zip(ys, rows):
        ax.text(min(r["fire_rate"] + 0.015, 0.99), y, f"{r['fired']}/{n_papers}",
                va="center", fontsize=8, color="#33413d")
    ax.set_yticks(ys)
    ax.set_yticklabels([r["category"] for r in rows], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("share of the 25 real cs.CL papers where the category fired")
    ax.set_title("tmaudit rulepack as shipped in v0.5.0 on 25 real arXiv papers\n"
                 "(the four defects this run exposed are fixed in v0.5.1)",
                 fontsize=9)
    ax.grid(axis="x", color="#e6e9e8", linewidth=0.7)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "corpus_fire_rates.png")
    print("wrote figures/corpus_fire_rates.png")


if __name__ == "__main__":
    main()
