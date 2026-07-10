"""tmaudit.cache — content-addressed SQLite cache for audit results.

When `tmaudit verify --paper N` is run twice on the same
main.tex + refs.bib content, the second run is **instant**
(returns the cached result). The cache is invalidated
automatically when:

  1. The content of main.tex or refs.bib changes (sha256
     mismatch).
  2. The tmaudit version changes (so a bug fix in the
     audit logic invalidates old results).
  3. The user explicitly clears the cache (--clear-cache).

The cache is stored at:
  Linux/Mac: ~/.cache/tmaudit/cache.db
  Windows:   %LOCALAPPDATA%\\tmaudit\\cache.db

Public API:
  - CacheDB: SQLite wrapper, persistent cache.
  - cache_key(main_tex, refs_bib, version): compute the
    cache key from inputs.
  - CacheEntry: the cached value type (a dict with keys
    'findings', 'exit_code', 'summary', 'timestamp').
  - DEFAULT_CACHE_DIR: where the cache lives (overridable
    via TMAUDIT_CACHE_DIR env var).

Usage:
    db = CacheDB()
    key = cache_key(tex, bib, tmaudit.__version__)
    entry = db.get(key)
    if entry is None:
        # cache miss: run the audit
        findings = run_audit(tex, bib)
        entry = {'findings': findings, 'exit_code': 0,
                 'summary': '...', 'timestamp': now()}
        db.put(key, entry)
    # else: cache hit, use entry['findings'] directly
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sqlite3
import time
from pathlib import Path
from typing import Optional


# Default cache directory: ~/.cache/tmaudit on Linux/Mac,
# %LOCALAPPDATA%\\tmaudit on Windows. Override with
# TMAUDIT_CACHE_DIR env var.
def _default_cache_dir() -> Path:
    env = os.environ.get('TMAUDIT_CACHE_DIR')
    if env:
        return Path(env)
    if platform.system() == 'Windows':
        appdata = os.environ.get('LOCALAPPDATA', 'C:\\Users\\Public\\AppData\\Local')
        return Path(appdata) / 'tmaudit'
    return Path.home() / '.cache' / 'tmaudit'


DEFAULT_CACHE_DIR: Path = _default_cache_dir()
DEFAULT_CACHE_FILE: Path = DEFAULT_CACHE_DIR / 'cache.db'
DEFAULT_CACHE_VERSION: str = '1'


def cache_key(
    main_tex: str,
    refs_bib: str,
    tmaudit_version: str = DEFAULT_CACHE_VERSION,
) -> str:
    """Compute the cache key from input content + version.

    The key is the SHA-256 of the concatenation of the
    input content and the tmaudit version. Any change in
    input or version produces a new key, invalidating the
    old cache entry.
    """
    h = hashlib.sha256()
    h.update(main_tex.encode('utf-8', errors='replace'))
    h.update(b'\x00')  # separator
    h.update(refs_bib.encode('utf-8', errors='replace'))
    h.update(b'\x00')  # separator
    h.update(tmaudit_version.encode('utf-8', errors='replace'))
    return h.hexdigest()


def plugin_cache_key(
    paper_n: int,
    plugin_name: str,
    plugin_version: str,
    main_tex: str,
) -> str:
    """Compute the cache key for a single plugin's findings.

    Added in v0.4.0 for the plugin API. The key is a
    SHA-256 of:

    - paper_n (which paper the plugin was run on),
    - plugin_name + plugin_version (so an updated plugin
      invalidates stale cached findings),
    - main_tex content (so editing the paper invalidates
      the cached findings).

    The leading ``plugin:`` prefix separates these entries
    from the legacy ``cache_key()`` entries.
    """
    tex_hash = hashlib.sha256(
        main_tex.encode('utf-8', errors='replace')
    ).hexdigest()
    raw = f"plugin:{paper_n}:{plugin_name}:{plugin_version}:{tex_hash}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class CacheDB:
    """SQLite-backed cache for audit results.

    Schema:
        CREATE TABLE IF NOT EXISTS entries (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,    -- JSON-serialized CacheEntry
            created_at REAL NOT NULL,
            size_bytes INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_created_at
            ON entries(created_at);
    """

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS entries (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL,
            size_bytes INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_created_at
            ON entries(created_at);
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        """Open (or create) the cache at the given path.

        Default: DEFAULT_CACHE_FILE (~/.cache/tmaudit/cache.db
        on Linux/Mac).
        """
        self.path = Path(path) if path is not None else DEFAULT_CACHE_FILE
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path))
            self._conn.executescript(self.SCHEMA)
        return self._conn

    def get(self, key: str) -> Optional[dict]:
        """Fetch the entry for `key`, or None if not present.

        Returns the deserialized dict on hit, None on miss.
        """
        conn = self._get_conn()
        row = conn.execute(
            'SELECT value FROM entries WHERE key = ?', (key,)
        ).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            # Corrupt entry; treat as miss and remove it.
            conn.execute('DELETE FROM entries WHERE key = ?', (key,))
            conn.commit()
            return None

    def put(self, key: str, value: dict) -> None:
        """Store `value` (a dict) under `key`.

        The dict is JSON-serialized. The entry's size in
        bytes is also stored for statistics.
        """
        serialized = json.dumps(value, ensure_ascii=False)
        size_bytes = len(serialized.encode('utf-8'))
        conn = self._get_conn()
        conn.execute(
            'INSERT OR REPLACE INTO entries (key, value, created_at, size_bytes) '
            'VALUES (?, ?, ?, ?)',
            (key, serialized, time.time(), size_bytes),
        )
        conn.commit()

    def clear(self) -> int:
        """Remove all entries. Returns the number removed."""
        conn = self._get_conn()
        cur = conn.execute('DELETE FROM entries')
        conn.commit()
        return cur.rowcount

    def stats(self) -> dict:
        """Return cache statistics as a dict.

        Keys:
          - n_entries: number of entries
          - total_bytes: total size of all values (uncompressed)
          - oldest: timestamp of oldest entry (or None)
          - newest: timestamp of newest entry (or None)
          - path: cache file path
        """
        conn = self._get_conn()
        row = conn.execute(
            'SELECT COUNT(*), COALESCE(SUM(size_bytes), 0), '
            'MIN(created_at), MAX(created_at) FROM entries'
        ).fetchone()
        return {
            'n_entries': int(row[0]),
            'total_bytes': int(row[1]),
            'oldest': float(row[2]) if row[2] is not None else None,
            'newest': float(row[3]) if row[3] is not None else None,
            'path': str(self.path),
        }

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


# Default version is a module-level constant, but tests may
# override it. The cache_key function takes version as an
# argument to make this easy.
def tmaudit_version() -> str:
    """Get the current tmaudit version.

    Default: 'dev'. Tests may monkey-patch this.
    """
    try:
        from . import __version__
        return __version__
    except ImportError:
        return 'dev'


def make_entry(
    findings: list,
    exit_code: int,
    summary: str = '',
) -> dict:
    """Build a CacheEntry dict from raw audit results.

    Helper for the call site. The dict has keys: findings,
    exit_code, summary, timestamp.
    """
    return {
        'findings': findings,
        'exit_code': int(exit_code),
        'summary': str(summary),
        'timestamp': time.time(),
    }
