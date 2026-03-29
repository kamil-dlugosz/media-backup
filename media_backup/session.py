"""In-memory named-path store for a single REPL session."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from media_backup.scanner import ScanCache

REQUIRED_PATHS = ("SSD", "HDD")


class Session:
    """Holds named paths for the lifetime of one REPL session."""

    def __init__(self) -> None:
        self._paths: Dict[str, Path] = {}
        self.cache: ScanCache = ScanCache()

    def set(self, name: str, path: str) -> Tuple[Path, bool]:
        """Register *name* → *path*.  Returns (resolved Path, exists)."""
        p = Path(path)
        self._paths[name] = p
        return p, p.exists()

    def unset(self, name: str) -> bool:
        """Remove a named path.  Returns True if it existed."""
        return self._paths.pop(name, None) is not None

    def get(self, name_or_path: str) -> Optional[Path]:
        """Look up a session name; fall back to treating the arg as a literal path."""
        if name_or_path in self._paths:
            return self._paths[name_or_path]
        p = Path(name_or_path)
        if p.exists():
            return p
        return None

    def resolve(self, name_or_path: str) -> Tuple[str, Optional[Path]]:
        """Return (display_label, Path | None).

        The display label is the session name if one matched, otherwise the
        raw string the user typed.
        """
        if name_or_path in self._paths:
            return name_or_path, self._paths[name_or_path]
        p = Path(name_or_path)
        if p.exists():
            return name_or_path, p
        return name_or_path, None

    def list_paths(self) -> List[Tuple[str, Path]]:
        """All (name, path) pairs, required paths first."""
        required = [(n, self._paths[n]) for n in REQUIRED_PATHS if n in self._paths]
        custom = [
            (n, p) for n, p in self._paths.items() if n not in REQUIRED_PATHS
        ]
        return required + sorted(custom, key=lambda t: t[0])

    def has_drives(self) -> bool:
        return "SSD" in self._paths and "HDD" in self._paths

    def missing_drives(self) -> List[str]:
        return [n for n in REQUIRED_PATHS if n not in self._paths]

    @property
    def names(self) -> List[str]:
        """All currently registered names (for tab-completion)."""
        return list(self._paths.keys())
