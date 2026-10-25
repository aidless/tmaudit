"""tmaudit.target — the audited object, decoupled from LaTeX.

Before v0.6.0 every plugin received a bare ``str`` of LaTeX source and
had to re-parse it to answer questions like "which sections exist?" or
"which keys are cited?". That made the audited object an *implicit*
constant of the plugin API: a check written against ``tex`` could not
be pointed at anything that was not a ``.tex`` file, so an audit rule
could never outlive the format it was written for.

This module introduces ``Target``: a thin, read-only view over whatever
is being audited. ``TexTarget`` is the first — and currently only —
implementation. It exposes:

    read()        -> str                  full source text
    lines()       -> list[str]            source split on newlines
    sections()    -> list[Section]        heading tree with line numbers
    citations()   -> list[CitationRef]    every \\cite-like reference
    metadata()    -> dict                 path / kind / sha256 / counts

Design constraints, in priority order:

1. **Read-only.** A Target never writes. Plugins stay side-effect-free,
   which is what makes the audit cache sound.
2. **No new dependencies.** Brace matching and citation scanning are
   done with the stdlib only.
3. **Thin.** Parsing is structural (headings, citations), not semantic.
   C1..C10 keep their own regexes; this module does not try to replace
   them, only to give plugins a stable place to stand.

``TexTarget`` accepts a path or a raw string, so a plugin can be tested
without touching the filesystem.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

__all__ = [
    "CitationRef",
    "Section",
    "Target",
    "TexTarget",
    "TextTarget",
    "as_target",
    "as_text",
    "is_target",
]

# Heading commands we recognise, mapped to an integer level. `part` and
# `chapter` are included so the section tree stays well-formed for book-
# class documents; `paragraph` is deliberately excluded — it is used for
# inline run-in headings far more often than for real structure.
_HEADING_LEVELS = {
    "part": 0,
    "chapter": 1,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
}

_HEADING_RE = re.compile(
    r"\\(part|chapter|section|subsection|subsubsection)\*?\s*\{"
)

# \cite, \citep, \citet, \citealp, \citeauthor, \citeyear, \nocite,
# \parencite, \textcite, \autocite, \footcite, ...
_CITE_RE = re.compile(
    r"\\([A-Za-z]*cite[A-Za-z]*)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^{}]*)\}"
)


@dataclass(frozen=True)
class Section:
    """One heading in the document, with the body range that follows it."""

    level: int
    title: str
    line: int
    body_start: int
    body_end: int

    def length(self) -> int:
        """Characters between this heading and the next one (exclusive)."""
        return max(0, self.body_end - self.body_start)

    def body_of(self, target: "Target") -> str:
        """Body text, read back through the target it came from."""
        return target.read()[self.body_start:self.body_end]


@dataclass(frozen=True)
class CitationRef:
    """One \\cite-like occurrence."""

    key: str
    line: int
    command: str


class Target(Protocol):
    """Read-only view over an auditable object.

    Plugins that want structured access declare their first parameter as
    ``target`` (or ``target_or_tex``); tmaudit then passes a ``Target``
    instead of a raw string. Plugins that declare ``tex`` keep receiving
    a ``str``, so every pre-v0.6.0 plugin continues to work unchanged.
    """

    @property
    def kind(self) -> str:
        ...

    def read(self) -> str:
        ...

    def lines(self) -> List[str]:
        ...

    def sections(self) -> List[Section]:
        ...

    def citations(self) -> List[CitationRef]:
        ...

    def metadata(self) -> Dict[str, Any]:
        ...


def _match_brace(text: str, open_index: int) -> int:
    """Return the index just past the ``}`` matching ``text[open_index]``.

    Handles nesting and backslash escapes. Returns -1 if unbalanced.
    """
    if open_index >= len(text) or text[open_index] != "{":
        return -1
    depth = 0
    i = open_index
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _line_of(text: str, index: int) -> int:
    """1-based line number of ``index`` inside ``text``."""
    return text.count("\n", 0, index) + 1


class _BaseTarget:
    """Shared implementation. Subclasses supply ``_text`` and ``_name``."""

    _text: str
    _name: str
    _path: Optional[Path]
    _kind: str

    def read(self) -> str:
        return self._text

    def lines(self) -> List[str]:
        return self._text.splitlines()

    def metadata(self) -> Dict[str, Any]:
        return {
            "kind": self._kind,
            "name": self._name,
            "path": str(self._path) if self._path is not None else None,
            "sha256": hashlib.sha256(
                self._text.encode("utf-8", errors="replace")
            ).hexdigest(),
            "n_chars": len(self._text),
            "n_lines": self._text.count("\n") + 1,
            "n_sections": len(self.sections()),
            "n_citations": len(self.citations()),
        }

    def sections(self) -> List[Section]:
        raw: List[Tuple[str, str, int, int]] = []
        for m in _HEADING_RE.finditer(self._text):
            command = m.group(1)
            brace = m.end() - 1
            end = _match_brace(self._text, brace)
            if end < 0:
                continue
            title = self._text[brace + 1:end - 1].strip()
            raw.append(
                (command, title, m.start(), end)  # type: ignore[arg-type]
            )
        out: List[Section] = []
        for idx, (command, title, start, body_start) in enumerate(raw):
            body_end = raw[idx + 1][2] if idx + 1 < len(raw) else len(self._text)
            out.append(
                Section(
                    level=_HEADING_LEVELS[command],
                    title=title,
                    line=_line_of(self._text, start),
                    body_start=body_start,
                    body_end=body_end,
                )
            )
        return out

    def section_titles(self) -> List[str]:
        return [s.title for s in self.sections()]

    def citations(self) -> List[CitationRef]:
        out: List[CitationRef] = []
        for m in _CITE_RE.finditer(self._text):
            command = m.group(1)
            for key in m.group(2).split(","):
                key = key.strip()
                if key:
                    out.append(
                        CitationRef(
                            key=key,
                            line=_line_of(self._text, m.start()),
                            command=command,
                        )
                    )
        return out

    def citation_keys(self) -> List[str]:
        seen: Dict[str, None] = {}
        for ref in self.citations():
            seen.setdefault(ref.key, None)
        return list(seen)

    # -- dunder sugar so a Target can stand in for the old ``str`` API ---

    def __str__(self) -> str:
        return self._text

    def __len__(self) -> int:
        return len(self._text)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(name={self._name!r}, "
            f"chars={len(self._text)}, sections={len(self.sections())})"
        )


class TexTarget(_BaseTarget):
    """A LaTeX document.

    Args:
        source: path to a ``.tex`` file, or the document text itself.
        name: overrides the display name (defaults to the file stem).
    """

    _kind = "tex"

    def __init__(
        self,
        source: Union[str, Path],
        *,
        name: Optional[str] = None,
    ) -> None:
        if isinstance(source, Path):
            self._path: Optional[Path] = source
            self._text = source.read_text(encoding="utf-8", errors="replace")
            self._name = name or source.stem
            return
        looks_like_path = (
            "\n" not in source
            and len(source) < 4096
            and source.endswith(".tex")
        )
        if looks_like_path:
            p = Path(source)
            self._path = p
            self._text = p.read_text(encoding="utf-8", errors="replace")
            self._name = name or p.stem
            return
        self._path = None
        self._text = source
        self._name = name or "<memory>"

    @property
    def kind(self) -> str:
        return self._kind


class TextTarget(_BaseTarget):
    """A plain-text stand-in, used when a ``str`` reaches a Target-aware
    plugin. Keeps the plugin API total: a caller that only has a string
    can still drive a Target-aware check.
    """

    _kind = "text"

    def __init__(self, text: str, *, name: Optional[str] = None) -> None:
        self._text = text
        self._path = None
        self._name = name or "<string>"

    @property
    def kind(self) -> str:
        return self._kind


def is_target(obj: Any) -> bool:
    """Duck-typed check.

    ``Target`` is a ``Protocol`` with data members, so ``isinstance`` on a
    ``runtime_checkable`` version would only verify attribute presence;
    an explicit check says the same thing without the caveat.
    """
    return callable(getattr(obj, "read", None)) and callable(
        getattr(obj, "sections", None)
    )


def as_target(obj: Any) -> Target:
    """Coerce a path / string / Target into a Target."""
    if is_target(obj):
        return obj  # type: ignore[return-value]
    if isinstance(obj, Path):
        return TexTarget(obj)
    if isinstance(obj, str):
        return TextTarget(obj)
    raise TypeError(
        "cannot use %s as an audit target; expected a path, a string, "
        "or a Target" % type(obj).__name__
    )


def as_text(obj: Any) -> str:
    """Coerce a Target / string into the raw text a legacy plugin wants."""
    if is_target(obj):
        return obj.read()  # type: ignore[no-any-return]
    if isinstance(obj, Path):
        return obj.read_text(encoding="utf-8", errors="replace")
    return str(obj)
