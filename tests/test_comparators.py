"""Tests for comparators.py."""

from pathlib import Path

from media_backup.comparators import (
    Confidence,
    coverage_check,
    find_duplicates,
    safe_to_clear,
    sync_check,
)


class TestSyncCheck:
    def test_identical_dirs(self, tmp_path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        for d in (a, b):
            (d / "photos").mkdir(parents=True)
            (d / "photos" / "img.jpg").write_bytes(b"\x00" * 100)

        result = sync_check(a, b)
        assert result.in_sync
        assert result.only_in_a == []
        assert result.only_in_b == []
        assert result.diverged == []

    def test_detects_only_in_a_and_b(self, twin_dirs):
        a, b = twin_dirs
        result = sync_check(a, b)

        names_a = {f.name for f in result.only_in_a}
        names_b = {f.name for f in result.only_in_b}

        assert "only_a.jpg" in names_a
        assert "only_b.png" in names_b

    def test_detects_diverged(self, twin_dirs):
        a, b = twin_dirs
        result = sync_check(a, b)

        assert len(result.diverged) == 1
        file_a, file_b = result.diverged[0]
        assert file_a.name == "img002.jpg"
        assert file_a.size != file_b.size

    def test_empty_dirs(self, tmp_path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()

        result = sync_check(a, b)
        assert result.in_sync


class TestCoverageCheck:
    def test_full_coverage(self, tmp_path):
        src = tmp_path / "src"
        tgt = tmp_path / "tgt"
        (src).mkdir()
        (tgt / "nested").mkdir(parents=True)

        (src / "pic.jpg").write_bytes(b"\x00" * 100)
        (tgt / "nested" / "pic.jpg").write_bytes(b"\x00" * 100)

        result = coverage_check(src, tgt)
        assert result.coverage_pct == 100.0
        assert len(result.missing) == 0

    def test_partial_coverage(self, coverage_dirs):
        src, tgt = coverage_dirs
        result = coverage_check(src, tgt)

        assert len(result.matched) == 2
        assert len(result.missing) == 1
        assert result.missing[0].source_file.name == "photo_c.heic"

    def test_ignores_directory_structure(self, tmp_path):
        src = tmp_path / "src"
        tgt = tmp_path / "tgt"

        (src / "flat").mkdir(parents=True)
        (tgt / "deep" / "nested" / "dir").mkdir(parents=True)

        (src / "flat" / "photo.jpg").write_bytes(b"\x00" * 256)
        (tgt / "deep" / "nested" / "dir" / "photo.jpg").write_bytes(b"\x00" * 256)

        result = coverage_check(src, tgt)
        assert result.coverage_pct == 100.0


class TestSafeToClear:
    def test_safe_when_on_both_drives(self, tmp_path):
        laptop = tmp_path / "laptop"
        ssd = tmp_path / "ssd"
        hdd = tmp_path / "hdd"

        for d in (laptop, ssd / "sub", hdd / "other"):
            d.mkdir(parents=True)

        (laptop / "pic.jpg").write_bytes(b"\x00" * 100)
        (ssd / "sub" / "pic.jpg").write_bytes(b"\x00" * 100)
        (hdd / "other" / "pic.jpg").write_bytes(b"\x00" * 100)

        result = safe_to_clear(laptop, ssd, hdd)
        assert result.safe

    def test_not_safe_when_missing_from_one(self, tmp_path):
        laptop = tmp_path / "laptop"
        ssd = tmp_path / "ssd"
        hdd = tmp_path / "hdd"

        for d in (laptop, ssd, hdd):
            d.mkdir(parents=True)

        (laptop / "pic.jpg").write_bytes(b"\x00" * 100)
        (ssd / "pic.jpg").write_bytes(b"\x00" * 100)
        # missing from hdd

        result = safe_to_clear(laptop, ssd, hdd)
        assert not result.safe


class TestFindDuplicates:
    def test_finds_cross_dir_duplicates(self, dup_dir):
        groups = find_duplicates(dup_dir)
        assert len(groups) == 1
        assert groups[0].name == "pic.jpg"
        assert len(groups[0].paths) == 2

    def test_no_duplicates_when_unique(self, tmp_path):
        root = tmp_path / "root"
        (root / "a").mkdir(parents=True)
        (root / "b").mkdir(parents=True)
        (root / "a" / "one.jpg").write_bytes(b"\x00" * 100)
        (root / "b" / "two.jpg").write_bytes(b"\x00" * 200)

        groups = find_duplicates(root)
        assert groups == []

    def test_same_dir_not_counted(self, tmp_path):
        root = tmp_path / "root" / "same"
        root.mkdir(parents=True)
        (root / "pic.jpg").write_bytes(b"\x00" * 100)
        # Can't have two files with same name in same dir,
        # so this just confirms no false positives.
        groups = find_duplicates(tmp_path / "root")
        assert groups == []
