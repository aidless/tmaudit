r"""mm3 detector config loader.

Standalone mini-detector: only the config-related surface from
``F:\Research\_inbox\方法论\mm3_hallucination_detector.py`` is exposed,
so it can be unit-tested in isolation without pulling in the full
1000+ line detector (or the rest of the F:\\Research\\ tree).

Public API:
- load_config(path=None) -> dict
- DEFAULT_CONFIG (the hard-coded fallback)
- _deep_merge(base, override) -> dict  (exposed for tests)
- detect_arxiv_year_issues_min(text, ...) -> list  (toy stub for tests)
"""
from .detector_min import (
    DEFAULT_CONFIG,
    load_config,
    deep_merge as _deep_merge,
    detect_arxiv_year_issues_min,
)

__all__ = ["DEFAULT_CONFIG", "load_config", "_deep_merge", "detect_arxiv_year_issues_min"]
