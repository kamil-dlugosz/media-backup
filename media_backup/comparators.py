"""Comparison logic for all verification commands."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from media_backup.scanner import (
    MediaFile,
    ScanCache,
    build_flat_index,
    scan_directory,
)


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

class Confidence(Enum):
    EXACT = "exact"
    LIKELY = "likely"
    AMBIGUOUS = "ambiguous"
    MISMATCH = "mismatch"   # same name candidate exists, but metadata disagrees
    MISSING = "missing"     # no candidate with this name at all


@dataclass
class MatchResult:
    source_file: MediaFile
    target_file: Optional[MediaFile] = None
    confidence: Confidence = Confidence.MISSING


@dataclass
class SyncResult:
    only_in_a: List[MediaFile] = field(default_factory=list)
    only_in_b: List[MediaFile] = field(default_factory=list)
    diverged: List[Tuple[MediaFile, MediaFile]] = field(default_factory=list)

    @property
    def in_sync(self) -> bool:
        return not self.only_in_a and not self.only_in_b and not self.diverged


@dataclass
class CoverageResult:
    matched: List[MatchResult] = field(default_factory=list)
    ambiguous: List[MatchResult] = field(default_factory=list)
    missing: List[MatchResult] = field(default_factory=list)

    @property
    def total_source(self) -> int:
        return len(self.matched) + len(self.ambiguous) + len(self.missing)

    @property
    def coverage_pct(self) -> float:
        """Only exact and likely matches count as covered."""
        if self.total_source == 0:
            return 100.0
        return len(self.matched) / self.total_source * 100


@dataclass
class SafeToClearResult:
    ssd_coverage: CoverageResult
    hdd_coverage: CoverageResult

    @property
    def safe(self) -> bool:
        """True when nothing is missing (matched + ambiguous cover everything)."""
        return not self.ssd_coverage.missing and not self.hdd_coverage.missing

    @property
    def has_ambiguous(self) -> bool:
        return bool(self.ssd_coverage.ambiguous or self.hdd_coverage.ambiguous)


@dataclass
class DuplicateGroup:
    name: str
    size: int
    paths: List[str]


@dataclass
class TimelineGap:
    start: datetime
    end: datetime

    @property
    def days(self) -> int:
        return (self.end - self.start).days


# ---------------------------------------------------------------------------
# sync-check
# ---------------------------------------------------------------------------

def sync_check(
    path_a: Path,
    path_b: Path,
    label_a: str = "SSD",
    label_b: str = "HDD",
    cache: Optional[ScanCache] = None,
) -> SyncResult:
    """Compare two directories by relative path structure."""
    _scan = cache.get if cache else scan_directory
    files_a = _scan(path_a, label=label_a)
    files_b = _scan(path_b, label=label_b)

    index_a: Dict[str, MediaFile] = {mf.rel_path: mf for mf in files_a}
    index_b: Dict[str, MediaFile] = {mf.rel_path: mf for mf in files_b}

    keys_a = set(index_a.keys())
    keys_b = set(index_b.keys())

    result = SyncResult()
    result.only_in_a = [index_a[k] for k in sorted(keys_a - keys_b)]
    result.only_in_b = [index_b[k] for k in sorted(keys_b - keys_a)]

    for k in sorted(keys_a & keys_b):
        a, b = index_a[k], index_b[k]
        if a.size != b.size:
            result.diverged.append((a, b))

    return result


# ---------------------------------------------------------------------------
# coverage-check
# ---------------------------------------------------------------------------

def _metadata_match(src: MediaFile, tgt: MediaFile) -> Confidence:
    """Compare metadata beyond name+size to determine confidence."""
    if src.size == tgt.size:
        return Confidence.EXACT

    matches = 0
    checks = 0

    if src.exif_date and tgt.exif_date:
        checks += 1
        if src.exif_date == tgt.exif_date:
            matches += 1

    if src.width and tgt.width and src.height and tgt.height:
        checks += 1
        if src.width == tgt.width and src.height == tgt.height:
            matches += 1

    if src.framerate and tgt.framerate:
        checks += 1
        if abs(src.framerate - tgt.framerate) < 0.1:
            matches += 1

    if checks == 0:
        return Confidence.AMBIGUOUS
    if matches == checks:
        return Confidence.LIKELY
    if matches > 0:
        return Confidence.AMBIGUOUS
    return Confidence.MISMATCH


def _match_files_against_index(
    source_files: List[MediaFile],
    target_index: Dict[str, List[MediaFile]],
) -> CoverageResult:
    """Match each source file against a flat target index by name, size, and metadata."""
    result = CoverageResult()

    for src in source_files:
        key = src.name.lower()
        candidates = target_index.get(key, [])

        exact = [c for c in candidates if c.size == src.size]
        if exact:
            result.matched.append(
                MatchResult(src, exact[0], Confidence.EXACT)
            )
            continue

        if candidates:
            best = candidates[0]
            conf = _metadata_match(src, best)
            if conf == Confidence.LIKELY:
                result.matched.append(MatchResult(src, best, conf))
                continue
            if conf == Confidence.AMBIGUOUS:
                result.ambiguous.append(MatchResult(src, best, conf))
                continue
            result.missing.append(MatchResult(src, best, Confidence.MISMATCH))
            continue

        result.missing.append(MatchResult(src))

    return result


def coverage_check(
    source_path: Path,
    target_path: Path,
    source_label: str = "source",
    target_label: str = "target",
    cache: Optional[ScanCache] = None,
) -> CoverageResult:
    """Check whether every file in *source_path* exists somewhere in *target_path*."""
    _scan = cache.get if cache else scan_directory
    source_files = _scan(source_path, label=source_label)
    target_files = _scan(target_path, label=target_label)
    target_index = build_flat_index(target_files)

    return _match_files_against_index(source_files, target_index)


# ---------------------------------------------------------------------------
# safe-to-clear
# ---------------------------------------------------------------------------

def safe_to_clear(
    laptop_path: Path,
    ssd_path: Path,
    hdd_path: Path,
    laptop_label: str = "laptop",
    cache: Optional[ScanCache] = None,
) -> SafeToClearResult:
    """Check if all files in *laptop_path* exist on both SSD and HDD."""
    _scan = cache.get if cache else scan_directory
    laptop_files = _scan(laptop_path, label=laptop_label)

    ssd_index = build_flat_index(_scan(ssd_path, label="SSD"))
    hdd_index = build_flat_index(_scan(hdd_path, label="HDD"))

    return SafeToClearResult(
        ssd_coverage=_match_files_against_index(laptop_files, ssd_index),
        hdd_coverage=_match_files_against_index(laptop_files, hdd_index),
    )


# ---------------------------------------------------------------------------
# duplicates
# ---------------------------------------------------------------------------

def find_duplicates(
    path: Path,
    label: str = "dir",
    cache: Optional[ScanCache] = None,
) -> List[DuplicateGroup]:
    """Find files with identical name+size in different subdirectories."""
    _scan = cache.get if cache else scan_directory
    files = _scan(path, label=label)

    buckets: Dict[Tuple[str, int], List[MediaFile]] = defaultdict(list)
    for mf in files:
        buckets[(mf.name.lower(), mf.size)].append(mf)

    groups: List[DuplicateGroup] = []
    for (name, size), members in sorted(buckets.items()):
        if len(members) < 2:
            continue
        dirs = {str(mf.path.parent.relative_to(path)) for mf in members}
        if len(dirs) < 2:
            continue
        groups.append(DuplicateGroup(
            name=members[0].name,
            size=size,
            paths=[mf.rel_path for mf in members],
        ))

    return groups


# ---------------------------------------------------------------------------
# timeline-gaps
# ---------------------------------------------------------------------------

def timeline_gaps(
    path: Path,
    label: str = "dir",
    min_gap_days: int = 7,
    cache: Optional[ScanCache] = None,
) -> Tuple[List[TimelineGap], Optional[datetime], Optional[datetime]]:
    """Find date gaps across all media in *path* (flattened, all subdirs).

    Returns (gaps, earliest_date, latest_date).
    """
    _scan = cache.get if cache else scan_directory
    files = _scan(path, read_metadata=True, label=label)

    dates: List[datetime] = []
    for mf in files:
        if mf.exif_date:
            dates.append(mf.exif_date)

    if not dates:
        return [], None, None

    dates.sort()
    earliest = dates[0]
    latest = dates[-1]
    threshold = timedelta(days=min_gap_days)

    gaps: List[TimelineGap] = []
    prev = dates[0]
    for d in dates[1:]:
        if d - prev > threshold:
            gaps.append(TimelineGap(start=prev, end=d))
        prev = d

    return gaps, earliest, latest
