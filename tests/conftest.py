"""Shared fixtures: temporary directory trees with fake media files."""

from __future__ import annotations

from pathlib import Path

import pytest


def _make_file(path: Path, size: int = 1024) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)


@pytest.fixture
def twin_dirs(tmp_path: Path):
    """Two directories with mostly-matching media files.

    dir_a/
        photos/img001.jpg  (1024)
        photos/img002.jpg  (2048)
        videos/clip01.mp4  (4096)
        only_a.jpg         (512)
    dir_b/
        photos/img001.jpg  (1024)       ← same
        photos/img002.jpg  (999)        ← different size (diverged)
        videos/clip01.mp4  (4096)       ← same
        only_b.png         (768)
    """
    a = tmp_path / "dir_a"
    b = tmp_path / "dir_b"

    _make_file(a / "photos" / "img001.jpg", 1024)
    _make_file(a / "photos" / "img002.jpg", 2048)
    _make_file(a / "videos" / "clip01.mp4", 4096)
    _make_file(a / "only_a.jpg", 512)

    _make_file(b / "photos" / "img001.jpg", 1024)
    _make_file(b / "photos" / "img002.jpg", 999)
    _make_file(b / "videos" / "clip01.mp4", 4096)
    _make_file(b / "only_b.png", 768)

    return a, b


@pytest.fixture
def coverage_dirs(tmp_path: Path):
    """Source dir with files, target dir with some matches (any subdir).

    source/
        photo_a.jpg   (1024)
        photo_b.jpg   (2048)
        photo_c.heic  (3072)
    target/
        sub1/photo_a.jpg  (1024)   ← match
        sub2/photo_b.jpg  (2048)   ← match
        # photo_c.heic is missing
    """
    src = tmp_path / "source"
    tgt = tmp_path / "target"

    _make_file(src / "photo_a.jpg", 1024)
    _make_file(src / "photo_b.jpg", 2048)
    _make_file(src / "photo_c.heic", 3072)

    _make_file(tgt / "sub1" / "photo_a.jpg", 1024)
    _make_file(tgt / "sub2" / "photo_b.jpg", 2048)

    return src, tgt


@pytest.fixture
def dup_dir(tmp_path: Path):
    """Directory with duplicates in different subdirectories.

    root/
        a/pic.jpg   (1024)
        b/pic.jpg   (1024)     ← duplicate
        a/unique.png (512)
    """
    root = tmp_path / "root"
    _make_file(root / "a" / "pic.jpg", 1024)
    _make_file(root / "b" / "pic.jpg", 1024)
    _make_file(root / "a" / "unique.png", 512)
    return root
