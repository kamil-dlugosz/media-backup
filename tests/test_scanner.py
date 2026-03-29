"""Tests for scanner.py."""

from pathlib import Path

from media_backup.scanner import build_flat_index, scan_directory


def _make(tmp_path: Path, name: str, size: int = 100) -> Path:
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x00" * size)
    return p


class TestScanDirectory:
    def test_finds_media_files(self, tmp_path):
        _make(tmp_path, "a.jpg", 100)
        _make(tmp_path, "b.mp4", 200)
        _make(tmp_path, "c.txt", 50)  # not media

        files = scan_directory(tmp_path)
        names = {f.name for f in files}

        assert "a.jpg" in names
        assert "b.mp4" in names
        assert "c.txt" not in names

    def test_recursive_discovery(self, tmp_path):
        _make(tmp_path, "sub/deep/photo.heic", 300)
        files = scan_directory(tmp_path)

        assert len(files) == 1
        assert files[0].name == "photo.heic"
        assert files[0].rel_path == "sub/deep/photo.heic"

    def test_size_and_metadata(self, tmp_path):
        _make(tmp_path, "pic.jpg", 1234)
        files = scan_directory(tmp_path)

        assert files[0].size == 1234
        assert files[0].ext == ".jpg"
        assert files[0].is_image
        assert not files[0].is_video

    def test_empty_directory(self, tmp_path):
        files = scan_directory(tmp_path)
        assert files == []

    def test_ignores_non_media(self, tmp_path):
        _make(tmp_path, "doc.pdf", 100)
        _make(tmp_path, "data.csv", 100)
        _make(tmp_path, "README.md", 100)
        assert scan_directory(tmp_path) == []


class TestBuildFlatIndex:
    def test_groups_by_lowercase_name(self, tmp_path):
        _make(tmp_path, "a/Photo.JPG", 100)
        _make(tmp_path, "b/photo.jpg", 200)

        files = scan_directory(tmp_path)
        index = build_flat_index(files)

        assert "photo.jpg" in index
        assert len(index["photo.jpg"]) == 2

    def test_different_names_separate_keys(self, tmp_path):
        _make(tmp_path, "alpha.jpg", 100)
        _make(tmp_path, "beta.png", 200)

        files = scan_directory(tmp_path)
        index = build_flat_index(files)

        assert "alpha.jpg" in index
        assert "beta.png" in index
        assert len(index["alpha.jpg"]) == 1
