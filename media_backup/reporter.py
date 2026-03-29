"""Rich-based output formatting for command results."""

from __future__ import annotations

from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from media_backup.comparators import (
    Confidence,
    CoverageResult,
    DuplicateGroup,
    SafeToClearResult,
    SyncResult,
    TimelineGap,
)

console = Console()

MAX_MISSING_LISTED = 15


def _size_fmt(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024  # type: ignore[assignment]
    return f"{size:.1f} TB"


# ---------------------------------------------------------------------------
# sync-check
# ---------------------------------------------------------------------------

def render_sync(result: SyncResult, label_a: str = "SSD", label_b: str = "HDD") -> str:
    """Return a Rich-renderable string for sync-check results."""
    parts: List[str] = []

    if result.in_sync:
        parts.append(f"[bold green]✓ {label_a} and {label_b} are fully in sync.[/]")
        return "\n".join(parts)

    if result.only_in_a:
        table = Table(title=f"Only in {label_a} ({len(result.only_in_a)} files)", expand=True)
        table.add_column("Relative Path")
        table.add_column("Size", justify="right")
        for mf in result.only_in_a[:50]:
            table.add_row(mf.rel_path, _size_fmt(mf.size))
        if len(result.only_in_a) > 50:
            table.add_row(f"… and {len(result.only_in_a) - 50} more", "")
        parts.append(table)

    if result.only_in_b:
        table = Table(title=f"Only in {label_b} ({len(result.only_in_b)} files)", expand=True)
        table.add_column("Relative Path")
        table.add_column("Size", justify="right")
        for mf in result.only_in_b[:50]:
            table.add_row(mf.rel_path, _size_fmt(mf.size))
        if len(result.only_in_b) > 50:
            table.add_row(f"… and {len(result.only_in_b) - 50} more", "")
        parts.append(table)

    if result.diverged:
        table = Table(title=f"Diverged — same path, different size ({len(result.diverged)} files)", expand=True)
        table.add_column("Relative Path")
        table.add_column(f"{label_a} Size", justify="right")
        table.add_column(f"{label_b} Size", justify="right")
        for a, b in result.diverged[:50]:
            table.add_row(a.rel_path, _size_fmt(a.size), _size_fmt(b.size))
        if len(result.diverged) > 50:
            table.add_row(f"… and {len(result.diverged) - 50} more", "", "")
        parts.append(table)

    summary = (
        f"[bold]{label_a}[/] only: {len(result.only_in_a)}  |  "
        f"[bold]{label_b}[/] only: {len(result.only_in_b)}  |  "
        f"Diverged: {len(result.diverged)}"
    )
    parts.append(summary)

    return parts


def render_sync_to_console(result: SyncResult, label_a: str = "SSD", label_b: str = "HDD") -> List:
    """Return list of Rich renderables for the split layout."""
    return render_sync(result, label_a, label_b)


# ---------------------------------------------------------------------------
# coverage-check
# ---------------------------------------------------------------------------

def render_coverage(result: CoverageResult, source_label: str, target_label: str) -> List:
    parts: List = []

    parts.append(
        f"Matched: [bold green]{len(result.matched)}[/] / {result.total_source} files "
        f"([bold]{result.coverage_pct:.1f}%[/] coverage)"
    )

    confidence_counts = {}
    for m in result.matched:
        confidence_counts[m.confidence.value] = confidence_counts.get(m.confidence.value, 0) + 1
    if confidence_counts:
        breakdown = "  ".join(f"{k}: {v}" for k, v in sorted(confidence_counts.items()))
        parts.append(f"  Match confidence: {breakdown}")

    if result.missing:
        n = len(result.missing)
        if n > MAX_MISSING_LISTED:
            parts.append(f"\n[bold red]Missing from {target_label}: {n} files[/]")
        else:
            table = Table(title=f"Missing from {target_label} ({n} files)", expand=True)
            table.add_column("File")
            table.add_column("Size", justify="right")
            for m in result.missing:
                table.add_row(m.source_file.name, _size_fmt(m.source_file.size))
            parts.append(table)
    else:
        parts.append(f"[bold green]✓ Every file in {source_label} exists in {target_label}.[/]")

    return parts


# ---------------------------------------------------------------------------
# safe-to-clear
# ---------------------------------------------------------------------------

def render_safe_to_clear(result: SafeToClearResult, label: str) -> List:
    parts: List = []

    ssd_pct = result.ssd_coverage.coverage_pct
    hdd_pct = result.hdd_coverage.coverage_pct

    parts.append(f"  {label} → SSD: [bold]{ssd_pct:.1f}%[/] covered")
    parts.append(f"  {label} → HDD: [bold]{hdd_pct:.1f}%[/] covered")

    if result.safe:
        total = result.ssd_coverage.total_source
        parts.append(
            f"\n[bold green]✓ SAFE TO DELETE[/] — all {total} files exist on both drives"
        )
    else:
        parts.append("\n[bold red]✗ NOT SAFE[/] — some files are missing from at least one drive")
        for drive, cov in [("SSD", result.ssd_coverage), ("HDD", result.hdd_coverage)]:
            if cov.missing:
                n = len(cov.missing)
                if n <= MAX_MISSING_LISTED:
                    for m in cov.missing:
                        parts.append(f"    Missing on {drive}: {m.source_file.name}")
                else:
                    parts.append(f"    Missing on {drive}: {n} files")

    return parts


# ---------------------------------------------------------------------------
# duplicates
# ---------------------------------------------------------------------------

def render_duplicates(groups: List[DuplicateGroup]) -> List:
    parts: List = []

    if not groups:
        parts.append("[bold green]✓ No duplicates found.[/]")
        return parts

    parts.append(f"[bold]{len(groups)} duplicate group(s) found:[/]")

    table = Table(expand=True)
    table.add_column("File")
    table.add_column("Size", justify="right")
    table.add_column("Locations")

    for g in groups[:30]:
        table.add_row(g.name, _size_fmt(g.size), "\n".join(g.paths))

    if len(groups) > 30:
        table.add_row(f"… and {len(groups) - 30} more groups", "", "")

    parts.append(table)
    return parts


# ---------------------------------------------------------------------------
# timeline-gaps
# ---------------------------------------------------------------------------

def render_timeline_gaps(gaps, earliest, latest, min_gap_days: int) -> List:
    parts: List = []

    if earliest is None:
        parts.append("[yellow]No EXIF dates found in any files.[/]")
        return parts

    parts.append(
        f"Date range: [bold]{earliest.strftime('%Y-%m-%d')}[/] → "
        f"[bold]{latest.strftime('%Y-%m-%d')}[/]"
    )

    if not gaps:
        parts.append(
            f"[bold green]✓ No gaps larger than {min_gap_days} days.[/]"
        )
        return parts

    table = Table(title=f"Gaps > {min_gap_days} days", expand=True)
    table.add_column("From")
    table.add_column("To")
    table.add_column("Days", justify="right")

    for g in gaps:
        table.add_row(
            g.start.strftime("%Y-%m-%d"),
            g.end.strftime("%Y-%m-%d"),
            str(g.days),
        )

    parts.append(table)
    return parts
