"""tmaudit.configs.target_config — external (non-author) paper configs.

``PAPER_CONFIGS`` is a dict keyed by ``int`` 1..5: it is the author's own
research tree, and that keying is the reason a stranger cannot use this
tool. ``tmaudit verify --paper 1`` is meaningless to anyone who does not
own a directory called ``PAPER1_CONSOLIDATED``.

This module removes that constraint without touching ``PAPER_CONFIGS``.
A config file on disk is loaded into the same dict shape the forger
already consumes, so *the same verify path* runs — same checks, same
report format, same exit codes. Nothing is reimplemented.

Accepted formats:

* ``.toml`` — needs ``tomllib`` (Python 3.11+) or the ``tomli`` backport
  (``pip install 'tmaudit[toml]'``).
* ``.json`` — stdlib only, always available. Use it on 3.9/3.10 when
  you cannot install extras.

Layout::

    schema = "tmaudit-target/1"

    [paper]
    name = "my-paper"        # optional: drives verify_<name>.py
    dir = "."                # optional: default = this file's directory
    tex_basename = "main"    # optional
    bib = "refs.bib"         # optional: many projects use references.bib

    [checks]
    c4_self_cite_prefix = "smith2025"
    c6_blacklist = ["paradigm", "yield"]

    [[checks.c1_symbols]]
    name = "$\\Delta$CAF"
    token = "\\bCAF\\b"
    definition = "CAF.{0,80}="

    [checks.c2_families]
    main = 3

Every key is validated: an unknown key is an error with a suggestion, not
a silent no-op. That is deliberate — a config typo that silently disables
a check produces exactly the kind of unverifiable audit this tool exists
to prevent.
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Content probes for bibliography detection. Kept here rather than
# imported from the template: this module must stay importable without
# exec'ing a 70 KB generated script.
_BIB_ENTRY_RE = re.compile(r"@\w+\s*\{\s*[^,\s]+\s*,")
_BIBITEM_RE = re.compile(r"\\bibitem\s*(?:\[[^\]]*\])?\s*\{")

__all__ = [
    "SCHEMA_ID",
    "TargetConfigError",
    "TargetSpec",
    "load_target_config",
]

SCHEMA_ID = "tmaudit-target/1"

_PAPER_KEYS = frozenset({"name", "dir", "tex_basename", "bib"})

# Bibliography filenames probed first when [paper].bib is not given, in
# priority order. Only a fast path: a real arXiv batch turned up bib.bib,
# custom.bib and main.bbl, so name matching alone is not sufficient and
# _detect_bib() falls through to sniffing file contents.
_BIB_CANDIDATES = (
    "refs.bib",
    "references.bib",
    "bibliography.bib",
    "main.bib",
    "main.bbl",
    "refs.bbl",
)


def _sniff_bib(path: Path) -> Optional[str]:
    """Return 'bib' / 'bbl' / None by looking at the first few KB.

    Extensions lie in the wild (a .bib starting with a comment, a .bbl
    behind a custom extension), and a paper project may hold several
    .bib files with only one actually used. Content is the only reliable
    signal, and this probe is cheap enough to run on every candidate.
    """
    try:
        with path.open("rb") as fh:
            head = fh.read(4096).decode("utf-8", errors="replace")
    except OSError:
        return None
    if _BIB_ENTRY_RE.search(head):
        return "bib"
    if _BIBITEM_RE.search(head):
        return "bbl"
    return None


def _detect_bib(paper_dir: Path) -> str:
    """Pick the bibliography file for a paper directory.

    1. Conventional names, in order.
    2. Any other top-level file whose content parses as BibTeX or a .bbl.
    3. Give up and return 'refs.bib' so the warning names something real.
    """
    for name in _BIB_CANDIDATES:
        if (paper_dir / name).is_file():
            return name

    try:
        entries = sorted(
            p for p in paper_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".bib", ".bbl", "")
        )
    except OSError:
        return "refs.bib"

    # Prefer a real BibTeX file over a compiled .bbl: the .bib lists every
    # entry, the .bbl only the keys that were cited in the compiled run.
    found: Dict[str, str] = {}
    for candidate in entries:
        kind = _sniff_bib(candidate)
        if kind and kind not in found:
            found[kind] = candidate.name
    return found.get("bib") or found.get("bbl") or "refs.bib"

# Keys accepted under [checks]. Mirrors PAPER_CONFIGS' entry shape, so a
# config file can express every check C1..C11 can consume.
_CHECK_KEYS = (
    "c1_symbols",
    "c2_families",
    "c2_section_pattern",
    "c2_abstract_k_allowed",
    "c3_concept",
    "c3_concept_token",
    "c3_formal",
    "c3_formal_secondary",
    "c4_self_cite_threshold",
    "c4_self_cite_prefix",
    "c4_max_self_cite_keys",
    "c5_d_type",
    "c6_blacklist",
    "c7_max_ceremonial",
    "c8_claimed_effects",
    "c9_figure_keywords",
    "c10_reproducibility_claims",
    "c11_plugins_enabled",
    "c11_plugins_disabled",
)
_CHECK_KEY_SET = frozenset(_CHECK_KEYS)

# Neutral defaults. Deliberately different from PAPER_CONFIGS in one
# place: c4_self_cite_prefix defaults to '' (no opinion about whose work
# you are citing), never to the author's own prefix.
_DEFAULTS: Dict[str, Any] = {
    "c1_symbols": [],
    "c2_families": {},
    "c2_section_pattern": None,
    "c2_abstract_k_allowed": None,
    "c3_concept": None,
    "c3_concept_token": None,
    "c3_formal": None,
    "c3_formal_secondary": None,
    "c4_self_cite_threshold": 0.30,
    "c4_self_cite_prefix": "",
    "c4_max_self_cite_keys": 3,
    "c5_d_type": "Cohen's d",
    "c6_blacklist": ["paradigm", "yield", "reveal"],
    "c7_max_ceremonial": 2,
    "c8_claimed_effects": [],
    "c9_figure_keywords": [],
    "c10_reproducibility_claims": [],
    "c11_plugins_enabled": [],
    "c11_plugins_disabled": [],
}


class TargetConfigError(ValueError):
    """Raised when a target config file is missing, malformed, or wrong."""


@dataclass(frozen=True)
class TargetSpec:
    """A validated external paper config."""

    source: Path
    name: str
    dir: Path
    tex_basename: str
    config: Dict[str, Any]
    bib: str = "refs.bib"

    def to_cfg(self) -> Dict[str, Any]:
        """The dict shape ``forge._substitute_verify`` consumes."""
        cfg = dict(self.config)
        cfg["dir"] = self.dir
        cfg["tex_basename"] = self.tex_basename
        cfg["bib"] = self.bib
        return cfg

    def script_name(self) -> str:
        slug = _slugify(self.name) or "external"
        return "verify_%s.py" % slug

    def warnings(self) -> List[str]:
        """Non-fatal problems: missing tex, missing bib, empty checks."""
        out: List[str] = []
        tex = self.dir / (self.tex_basename + ".tex")
        if not tex.exists():
            out.append(
                "tex file not found: %s (set [paper].dir or --paper-dir)" % tex
            )
        if not (self.dir / self.bib).exists():
            out.append(
                "no bibliography found in %s (looked for %s) — C4 citation "
                "hygiene cannot resolve any cite key and will report every "
                "one as missing. Add a .bib, or a compiled .bbl (both are "
                "parsed as of v0.6.0)."
                % (self.dir, ", ".join(_BIB_CANDIDATES))
            )
        empty = [k for k in _CHECK_KEYS if self.config.get(k) in ([], {}, None, "")]
        if len(empty) >= len(_CHECK_KEYS) - 3:
            out.append(
                "almost no checks are configured; the audit will only run "
                "the generic categories (C4/C6/C9/C10)"
            )
        return out


def _slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-").lower()
    return re.sub(r"-{2,}", "-", slug)


def _toml_loader():
    try:
        import tomllib as _toml  # Python 3.11+
        return _toml, "rb"
    except ModuleNotFoundError:
        pass
    try:
        import tomli as _toml  # backport
        return _toml, "rb"
    except ModuleNotFoundError:
        return None, ""


def _read_raw(path: Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise TargetConfigError(
                "%s: invalid JSON at line %d column %d — %s"
                % (path, e.lineno, e.colno, e.msg)
            ) from e
    if suffix != ".toml":
        raise TargetConfigError(
            "%s: unsupported config format %r; expected .toml or .json"
            % (path, path.suffix)
        )
    loader, mode = _toml_loader()
    if loader is None:
        raise TargetConfigError(
            "%s: reading .toml needs tomllib (Python 3.11+) or tomli.\n"
            "  fix: pip install 'tmaudit[toml]'\n"
            "  or:  write this config as .json instead (stdlib, no extras)"
            % path
        )
    with path.open(mode) as fh:
        try:
            return loader.load(fh)
        except Exception as e:  # tomllib.TOMLDecodeError / tomli.TOMLDecodeError
            raise TargetConfigError("%s: invalid TOML — %s" % (path, e)) from e


def _unknown_keys(got: Any, allowed: frozenset, where: str, path: Path) -> None:
    if not isinstance(got, dict):
        raise TargetConfigError(
            "%s: %s must be a table, got %s" % (path, where, type(got).__name__)
        )
    unknown = sorted(set(got) - allowed)
    if not unknown:
        return
    lines = ["%s: unknown key(s) in %s: %s" % (path, where, ", ".join(unknown))]
    for key in unknown:
        close = difflib.get_close_matches(key, sorted(allowed), n=1)
        if close:
            lines.append("  did you mean %r?" % close[0])
    lines.append("  allowed: %s" % ", ".join(sorted(allowed)))
    raise TargetConfigError("\n".join(lines))


def _as_str(raw: Dict[str, Any], key: str, default: Optional[str], path: Path) -> Optional[str]:
    value = raw.get(key, default)
    if value is None or isinstance(value, str):
        return value
    raise TargetConfigError(
        "%s: checks.%s must be a string, got %s"
        % (path, key, type(value).__name__)
    )


def _as_float(raw: Dict[str, Any], key: str, default: float, path: Path) -> float:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TargetConfigError(
            "%s: checks.%s must be a number, got %r" % (path, key, value)
        )
    return float(value)


def _as_int(raw: Dict[str, Any], key: str, default: int, path: Path) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TargetConfigError(
            "%s: checks.%s must be an integer, got %r" % (path, key, value)
        )
    return value


def _as_str_list(raw: Dict[str, Any], key: str, default: List[str], path: Path) -> List[str]:
    value = raw.get(key, default)
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise TargetConfigError(
            "%s: checks.%s must be a list of strings, got %r"
            % (path, key, value)
        )
    return list(value)


def _as_dict(raw: Dict[str, Any], key: str, default: Dict[str, Any], path: Path) -> Dict[str, Any]:
    value = raw.get(key, default)
    if not isinstance(value, dict):
        raise TargetConfigError(
            "%s: checks.%s must be a table, got %s"
            % (path, key, type(value).__name__)
        )
    return dict(value)


def _as_table_list(
    raw: Dict[str, Any],
    key: str,
    required: tuple,
    path: Path,
) -> List[Dict[str, Any]]:
    value = raw.get(key, [])
    if not isinstance(value, list):
        raise TargetConfigError(
            "%s: checks.%s must be an array of tables, got %s"
            % (path, key, type(value).__name__)
        )
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            raise TargetConfigError(
                "%s: checks.%s[%d] must be a table, got %s"
                % (path, key, i, type(item).__name__)
            )
        missing = [r for r in required if r not in item]
        if missing:
            raise TargetConfigError(
                "%s: checks.%s[%d] is missing required key(s): %s"
                % (path, key, i, ", ".join(missing))
            )
        out.append(dict(item))
    return out


def load_target_config(path: Path) -> TargetSpec:
    """Load and validate an external paper config.

    Raises:
        TargetConfigError: on missing file, unparseable input, unknown
            keys, or wrong value types. Every message names the file and
            the offending key.
    """
    path = Path(path)
    if not path.exists():
        raise TargetConfigError("config file not found: %s" % path)
    if path.is_dir():
        raise TargetConfigError("%s is a directory, not a config file" % path)

    raw = _read_raw(path)
    if not isinstance(raw, dict):
        raise TargetConfigError(
            "%s: top level must be a table/object" % path
        )

    _unknown_keys(raw, frozenset({"schema", "paper", "checks"}), "top level", path)

    schema = raw.get("schema", SCHEMA_ID)
    if schema != SCHEMA_ID:
        raise TargetConfigError(
            "%s: unsupported schema %r (this build understands %r)"
            % (path, schema, SCHEMA_ID)
        )

    paper = raw.get("paper", {})
    _unknown_keys(paper, _PAPER_KEYS, "[paper]", path)

    name = paper.get("name") or path.stem
    if not isinstance(name, str):
        raise TargetConfigError("%s: paper.name must be a string" % path)

    base = path.parent.resolve()
    dir_value = paper.get("dir", ".")
    if not isinstance(dir_value, str):
        raise TargetConfigError(
            "%s: paper.dir must be a string path, got %s"
            % (path, type(dir_value).__name__)
        )
    paper_dir = Path(dir_value)
    if not paper_dir.is_absolute():
        paper_dir = (base / paper_dir).resolve()

    tex_basename = paper.get("tex_basename", "main")
    if not isinstance(tex_basename, str) or not tex_basename:
        raise TargetConfigError(
            "%s: paper.tex_basename must be a non-empty string" % path
        )

    bib = paper.get("bib", "refs.bib")
    if not isinstance(bib, str) or not bib:
        raise TargetConfigError(
            "%s: paper.bib must be a non-empty string filename" % path
        )

    # An explicit [paper].bib wins. Otherwise detect the bibliography, so
    # an arXiv source tarball (main.bbl, no .bib) and a project using
    # bib.bib / custom.bib / references.bib all work with no config edit.
    # C4 understands both formats as of v0.6.0.
    if "bib" not in paper:
        bib = _detect_bib(paper_dir)

    checks_raw = raw.get("checks", {})
    _unknown_keys(checks_raw, _CHECK_KEY_SET, "[checks]", path)

    cfg: Dict[str, Any] = {}
    cfg["c1_symbols"] = _as_table_list(
        checks_raw, "c1_symbols", ("name", "token", "definition"), path
    )
    cfg["c2_families"] = _as_dict(checks_raw, "c2_families", {}, path)
    for key in (
        "c2_section_pattern",
        "c3_concept",
        "c3_concept_token",
        "c3_formal",
        "c3_formal_secondary",
        "c4_self_cite_prefix",
        "c5_d_type",
    ):
        cfg[key] = _as_str(checks_raw, key, _DEFAULTS[key], path)

    cfg["c2_abstract_k_allowed"] = checks_raw.get(
        "c2_abstract_k_allowed", _DEFAULTS["c2_abstract_k_allowed"]
    )
    if cfg["c2_abstract_k_allowed"] is not None:
        allowed = cfg["c2_abstract_k_allowed"]
        if not isinstance(allowed, list) or any(
            isinstance(v, bool) or not isinstance(v, int) for v in allowed
        ):
            raise TargetConfigError(
                "%s: checks.c2_abstract_k_allowed must be a list of integers"
                % path
            )

    cfg["c4_self_cite_threshold"] = _as_float(
        checks_raw, "c4_self_cite_threshold",
        _DEFAULTS["c4_self_cite_threshold"], path,
    )
    cfg["c4_max_self_cite_keys"] = _as_int(
        checks_raw, "c4_max_self_cite_keys",
        _DEFAULTS["c4_max_self_cite_keys"], path,
    )
    cfg["c7_max_ceremonial"] = _as_int(
        checks_raw, "c7_max_ceremonial", _DEFAULTS["c7_max_ceremonial"], path
    )
    cfg["c6_blacklist"] = _as_str_list(
        checks_raw, "c6_blacklist", list(_DEFAULTS["c6_blacklist"]), path
    )
    cfg["c11_plugins_enabled"] = _as_str_list(
        checks_raw, "c11_plugins_enabled", [], path
    )
    cfg["c11_plugins_disabled"] = _as_str_list(
        checks_raw, "c11_plugins_disabled", [], path
    )
    cfg["c8_claimed_effects"] = _as_table_list(
        checks_raw, "c8_claimed_effects", ("name",), path
    )
    cfg["c9_figure_keywords"] = _as_table_list(
        checks_raw, "c9_figure_keywords", ("fig_id",), path
    )
    cfg["c10_reproducibility_claims"] = _as_table_list(
        checks_raw, "c10_reproducibility_claims", ("type",), path
    )

    return TargetSpec(
        source=path.resolve(),
        name=name,
        dir=paper_dir,
        tex_basename=tex_basename,
        config=cfg,
        bib=bib,
    )
