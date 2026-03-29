"""Smoke tests for reporter.py — verify render functions don't crash."""

from datetime import datetime

from media_backup.comparators import (
    Confidence,
    CoverageResult,
    DuplicateGroup,
    MatchResult,
    SafeToClearResult,
    SyncResult,
    TimelineGap,
)
from media_backup.reporter import (
    render_coverage,
    render_duplicates,
    render_safe_to_clear,
    render_sync,
    render_timeline_gaps,
)
from media_backup.scanner import MediaFile

from pathlib import Path


def _fake_mf(name: str = "pic.jpg", size: int = 100) -> MediaFile:
    return MediaFile(
        path=Path(f"/fake/{name}"),
        rel_path=name,
        name=name,
        size=size,
        mtime=0.0,
        ext=Path(name).suffix.lower(),
    )


class TestRenderSync:
    def test_in_sync(self):
        result = SyncResult()
        parts = render_sync(result)
        assert isinstance(parts, list)
        assert len(parts) > 0

    def test_with_differences(self):
        result = SyncResult(
            only_in_a=[_fake_mf("a.jpg")],
            only_in_b=[_fake_mf("b.jpg")],
            diverged=[(_fake_mf("c.jpg", 100), _fake_mf("c.jpg", 200))],
        )
        parts = render_sync(result)
        assert isinstance(parts, list)
        assert len(parts) >= 3


class TestRenderCoverage:
    def test_full_coverage(self):
        result = CoverageResult(
            matched=[MatchResult(_fake_mf(), _fake_mf(), Confidence.EXACT)],
        )
        parts = render_coverage(result, "src", "tgt")
        assert isinstance(parts, list)

    def test_with_missing(self):
        result = CoverageResult(
            missing=[MatchResult(_fake_mf("missing.jpg"))],
        )
        parts = render_coverage(result, "src", "tgt")
        assert isinstance(parts, list)
        assert len(parts) >= 1

    def test_with_ambiguous(self):
        result = CoverageResult(
            ambiguous=[MatchResult(
                _fake_mf("ambig.jpg", 100),
                _fake_mf("ambig.jpg", 200),
                Confidence.AMBIGUOUS,
            )],
        )
        parts = render_coverage(result, "src", "tgt")
        assert isinstance(parts, list)


class TestRenderSafeToClear:
    def test_safe(self):
        cov = CoverageResult(
            matched=[MatchResult(_fake_mf(), _fake_mf(), Confidence.EXACT)],
        )
        result = SafeToClearResult(ssd_coverage=cov, hdd_coverage=cov)
        parts = render_safe_to_clear(result, "laptop1")
        assert isinstance(parts, list)
        assert any("SAFE" in str(p) for p in parts)

    def test_not_safe(self):
        cov_ok = CoverageResult(
            matched=[MatchResult(_fake_mf(), _fake_mf(), Confidence.EXACT)],
        )
        cov_bad = CoverageResult(
            missing=[MatchResult(_fake_mf("gone.jpg"))],
        )
        result = SafeToClearResult(ssd_coverage=cov_ok, hdd_coverage=cov_bad)
        parts = render_safe_to_clear(result, "laptop1")
        assert any("NOT SAFE" in str(p) for p in parts)


class TestRenderDuplicates:
    def test_no_duplicates(self):
        parts = render_duplicates([])
        assert isinstance(parts, list)

    def test_with_groups(self):
        groups = [DuplicateGroup("pic.jpg", 100, ["a/pic.jpg", "b/pic.jpg"])]
        parts = render_duplicates(groups)
        assert isinstance(parts, list)
        assert len(parts) >= 2


class TestRenderTimelineGaps:
    def test_no_dates(self):
        parts = render_timeline_gaps([], None, None, 7)
        assert isinstance(parts, list)

    def test_no_gaps(self):
        d1 = datetime(2024, 1, 1)
        d2 = datetime(2024, 1, 5)
        parts = render_timeline_gaps([], d1, d2, 7)
        assert isinstance(parts, list)

    def test_with_gaps(self):
        d1 = datetime(2024, 1, 1)
        d2 = datetime(2024, 3, 1)
        gaps = [TimelineGap(start=datetime(2024, 1, 10), end=datetime(2024, 2, 15))]
        parts = render_timeline_gaps(gaps, d1, d2, 7)
        assert isinstance(parts, list)
