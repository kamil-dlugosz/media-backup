"""Recursive media-file discovery with metadata extraction."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

MEDIA_EXTENSIONS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif",
    ".mp4", ".mov", ".avi", ".mkv",
    ".raw", ".dng", ".cr2", ".nef",
}

IMAGE_EXTENSIONS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif",
    ".raw", ".dng", ".cr2", ".nef",
}

VIDEO_EXTENSIONS: Set[str] = {".mp4", ".mov", ".avi", ".mkv"}


@dataclass
class MediaFile:
    """Metadata for one media file."""
    path: Path
    rel_path: str          # relative to the scanned root
    name: str
    size: int
    mtime: float
    ext: str

    exif_date: Optional[datetime] = None
    width: Optional[int] = None
    height: Optional[int] = None
    framerate: Optional[float] = None

    @property
    def is_image(self) -> bool:
        return self.ext in IMAGE_EXTENSIONS

    @property
    def is_video(self) -> bool:
        return self.ext in VIDEO_EXTENSIONS


def _read_image_metadata(mf: MediaFile) -> None:
    """Populate EXIF date, width, height from an image file."""
    try:
        from PIL import Image
        from PIL.ExifTags import Base as ExifBase
    except ImportError:
        return

    try:
        with Image.open(mf.path) as img:
            mf.width, mf.height = img.size
            exif = img.getexif()
            if exif:
                raw_date = exif.get(ExifBase.DateTimeOriginal) or exif.get(
                    ExifBase.DateTimeDigitized
                )
                if raw_date:
                    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                        try:
                            mf.exif_date = datetime.strptime(raw_date, fmt)
                            break
                        except (ValueError, TypeError):
                            continue
    except Exception:
        pass


def _read_video_metadata(mf: MediaFile) -> None:
    """Populate resolution and framerate from a video file (needs pymediainfo)."""
    try:
        from pymediainfo import MediaInfo
    except ImportError:
        return

    try:
        info = MediaInfo.parse(str(mf.path))
        for track in info.tracks:
            if track.track_type == "Video":
                if track.width and track.height:
                    mf.width = int(track.width)
                    mf.height = int(track.height)
                if track.frame_rate:
                    mf.framerate = float(track.frame_rate)
                break
    except Exception:
        pass


def scan_directory(
    root: Path,
    *,
    read_metadata: bool = False,
    label: Optional[str] = None,
) -> List[MediaFile]:
    """Walk *root* and return MediaFile entries for every media file found.

    Shows a Rich progress bar while scanning.  Set *read_metadata* to also
    extract EXIF / video metadata (slower — used for tiebreaking).
    """
    display_label = label or root.name or str(root)

    files: List[MediaFile] = []

    all_paths: List[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname in filenames:
            p = Path(dirpath) / fname
            ext = p.suffix.lower()
            if ext in MEDIA_EXTENSIONS:
                all_paths.append(p)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} files"),
        transient=True,
    ) as progress:
        task = progress.add_task(f"Scanning {display_label}…", total=len(all_paths))

        for p in all_paths:
            try:
                stat = p.stat()
            except OSError:
                progress.advance(task)
                continue

            ext = p.suffix.lower()
            mf = MediaFile(
                path=p,
                rel_path=str(p.relative_to(root)),
                name=p.name,
                size=stat.st_size,
                mtime=stat.st_mtime,
                ext=ext,
            )

            if read_metadata:
                if mf.is_image:
                    _read_image_metadata(mf)
                elif mf.is_video:
                    _read_video_metadata(mf)

            files.append(mf)
            progress.advance(task)

    return files


def build_flat_index(
    files: List[MediaFile],
) -> Dict[str, List[MediaFile]]:
    """Index files by lowercase filename → list of MediaFile.

    Used by coverage-check to match files regardless of directory structure.
    """
    index: Dict[str, List[MediaFile]] = {}
    for mf in files:
        key = mf.name.lower()
        index.setdefault(key, []).append(mf)
    return index
