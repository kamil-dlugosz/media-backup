# Media Backup Verification Tool

Verify that your photo and video backups are consistent across phones, laptop, and
external drives. Detect duplicates, find coverage gaps, and check that your two
backup drives are in sync — all from an interactive terminal session. **No files
are ever deleted or modified.**

## Installation

```bash
git clone https://github.com/kamil-dlugosz/media-backup.git
cd media-backup
poetry install
```

To launch:

```bash
poetry run media-backup
# or
poetry run python -m media_backup
```

## Quick Start

```
$ media-backup

  Media Backup Tool v0.1.0
  Type 'help' for commands, 'quit' to exit.

> set SSD D:\Backup
  ✓ SSD = D:\Backup

> set HDD E:\Backup
  ✓ HDD = E:\Backup

> sync-check
  Scanning SSD... [████████████] 12,340 files
  Scanning HDD... [████████████] 12,338 files
  ┌──────────────────────────────────────────┐
  │ Only in SSD          2 files             │
  │ Only in HDD          0 files             │
  │ Diverged (size)      1 file              │
  └──────────────────────────────────────────┘

> set laptop1 C:\Users\You\Pictures\2024-vacation
> safe-to-clear laptop1
  Checking laptop1 → SSD... 100% covered
  Checking laptop1 → HDD... 100% covered
  ✓ SAFE TO DELETE — all 84 files exist on both drives

> quit
```

## Commands

### Session Management

| Command | Description |
|---|---|
| `set <name> <path>` | Register a named path for this session. `SSD` and `HDD` are special names used by `sync-check` and `safe-to-clear`. |
| `unset <name>` | Remove a named path. |
| `paths` | List all currently set paths. |
| `help` | Show command reference. |
| `quit` / `exit` | End the session. All paths are forgotten. |

### Verification Commands

**`sync-check`** — *Requires SSD and HDD*

Compare two external drives by directory structure. Shows files only on one drive
and files at the same path with different sizes (diverged).

**`coverage-check <source> <target>`**

Check whether every media file in `<source>` exists somewhere in `<target>`,
regardless of folder structure. Matches by filename + file size. Arguments accept
path names (e.g. `phone1`, `SSD`) or raw filesystem paths.

**`safe-to-clear <dir>`** — *Requires SSD and HDD*

Check if a laptop directory can be safely deleted because all its files exist on
both external drives. Reports `SAFE TO DELETE` when every file is matched,
`PROBABLY SAFE` when all files are accounted for but some matches are ambiguous
(same name, different size, no metadata to confirm), or `NOT SAFE` when files
are missing from at least one drive.

**`duplicates <dir>`**

Find files with the same name and size in different subdirectories of a given path.

**`timeline-gaps <dir> [--min-gap N]`**

Scan EXIF dates across all files in a directory (all subdirs flattened into one
timeline) and report date ranges with no photos. Default gap threshold: 7 days.

## Comparison Strategy

Files are matched by **name + size** (no content hashing — too slow for large
media libraries). When a name matches but size differs, the tool checks additional
metadata as a tiebreaker:

- **Images**: EXIF `DateTimeOriginal`, width, height (via Pillow)
- **Videos**: resolution, framerate (via pymediainfo, if installed)

Match confidence is reported as: `exact` (name + size match), `likely` (name matches,
metadata agrees), `ambiguous` (name matches, insufficient metadata), `mismatch`
(name matches but metadata disagrees), or `missing` (no candidate with that name).

Supported media extensions: `.jpg` `.jpeg` `.png` `.heic` `.heif` `.mp4` `.mov`
`.avi` `.mkv` `.raw` `.dng` `.cr2` `.nef`

## Notes

- **No files are ever deleted or modified.** This tool is strictly read-only.
- Paths set during a session are forgotten when you quit.
- The tool runs on the laptop and accesses drives/phone dumps mounted as regular directories.
- Install `pymediainfo` for video metadata support: `pip install pymediainfo`
