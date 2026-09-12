# Python Utility Scripts

A collection of standalone Python scripts for everyday automation tasks.

Companion repo: `~/Code/Naughty_Scripts` — adult-content-related scripts (Beautyleg downloader/renamers, etc.) live there.

## Scripts

### organize_episodes.py

Renames TV show episode files in a standardized format.

**What it does:**

- Processes folders named `Season 1`, `Season 2`, etc.
- Renames video files and subtitles to `{ShowTitle} S01E001.mkv` format
- Deletes unwanted files (`.txt`, `.nfo`, `.jpg`, etc.)

**Usage:**

```bash
python organize_episodes.py
```

You'll be prompted for:

1. Show title (used in the renamed files)
2. Target directory (or press Enter for current directory)

**Supported formats:**

- Videos: `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.m4v`
- Subtitles: `.srt`, `.ass`, `.vtt`, `.sub`, `.ssa`

---

### get_real_link.py

Extracts direct download links from URLs that redirect.

**What it does:**

- Sends a HEAD request to the URL
- Captures the redirect location from 3xx responses
- Copies the direct link to your clipboard

**Usage:**

```bash
python get_real_link.py
```

Enter a URL when prompted. The resolved link will be printed and copied to your clipboard.

---

### find_duplicates.py

Quickly finds duplicate files on network drives using partial hashing.

**What it does:**

- Instantly groups files by exact byte size.
- Verifies duplicates by calculating an MD5 hash of only the first 1MB of data.
- Drastically speeds up duplicate detection for large video files over a network.

**Usage:**

```bash
python find_duplicates.py --dir /path/to/network/drive
```

---

### remove_resolutions.py

Removes resolution tags (e.g., 360p, 720p, 1080p, 2160p, 4K) from the end of filenames.

**What it does:**

- Scans a directory for files containing common resolution tags at the end of their names.
- Renames the files to remove those tags (e.g., "Video 1080p.mp4" -> "Video.mp4").
- Performs the actual renaming by default, with an option to do a dry-run.

**Usage:**

```bash
# Rename files in the current directory
python remove_resolutions.py

# Rename files in a specific directory
python remove_resolutions.py /path/to/videos

# Preview changes without renaming
python remove_resolutions.py /path/to/videos --dry-run
```

---

### shift_srt.py

Shifts `.srt` subtitle timestamps by a specified offset to sync web-rip subs with blu-ray video.

**What it does:**

- Parses `.srt` timestamps in `HH:MM:SS,mmm` format.
- Applies a positive or negative offset (in seconds, with millisecond precision).
- Clamps negative timestamps to `00:00:00,000`.
- Supports modifying in-place (with `.bak` backup) or writing to a new file.

**Usage:**

```bash
# Print shifted subtitles to stdout
python shift_srt.py input.srt 1.692

# Write to a new file
python shift_srt.py input.srt -0.500 -o output.srt

# Modify in-place (creates input.srt.bak)
python shift_srt.py input.srt 0.750 -i
```

**Offset format:** Seconds as float (e.g. `1.692`, `-0.500`, `10.0`).

---

### sync_finder.py

Batch-computes audio timeline offsets between Blu-ray and streaming versions of episodes over SMB/Samba, for subtitle syncing.

**What it does:**

- Streams the first N seconds of audio from each file via FFmpeg (no temp files, minimal network reads).
- Cross-correlates the waveforms (numpy/scipy) to find the exact offset.
- Writes offsets to a report file, one per episode pair, for use with `shift_srt.py`.
- Matches episodes across two folders via `S01E01` / `1x01` style identifiers.

**Requirements:** FFmpeg on PATH; run with the included venv (numpy, scipy).

**Usage:**

```bash
.venv/bin/python sync_finder.py -b /bluray/season1 -s /streaming/season1 -o offsets.txt
```

---

### find_missing_numbers.py

Finds gaps in `No.XXX` numbering across files/folders in a directory.

**What it does:**

- Scans a directory for names containing `No.###` (case-insensitive).
- Reports the covered range, items without a number, and every missing number in between.

**Usage:**

```bash
python find_missing_numbers.py /path/to/folders
```

---

### find_small_photo_folders.py

Flags folders that contain suspiciously small photos (likely broken/thumbnail-only downloads).

**What it does:**

- Recursively walks a directory.
- Prints the folder name if it contains any image between 40KB and 100KB.
- Progress counter goes to stderr.

**Usage:**

```bash
python find_small_photo_folders.py /path/to/photo/library
```

---

### move_folders.py

Moves folders or files named in a list file from one directory to another.

**What it does:**

- Reads a list file with one name per line (default: `~/Downloads/moving.txt`).
- Moves each matching folder or file from the source to the destination.
- Skips names that already exist in the destination; reports listed names not found.

**Usage:**

```bash
python move_folders.py /source /destination
python move_folders.py /source /destination --list ~/my_list.txt
```

---

### video_extractor.py

Flattens videos out of per-folder subdirectories into a single `Output/` folder.

**What it does:**

- Scans every subdirectory of the target directory in parallel.
- Moves each video found (recursively) into `Output/`, named after its folder.
- Multiple videos in one folder get `_2`, `_3` suffixes.

**Usage:**

```bash
python video_extractor.py            # current directory
python video_extractor.py /some/dir
```

---

### scan_watermark.py

Scans a folder of videos for a static bright watermark in the top-right corner and lists the watermarked ones.

**What it does:**

- Samples a few keyframes per video via FFmpeg — never reads whole files.
- Takes a per-pixel minimum composite over the sampled frames, so the static watermark survives while varying backgrounds cancel out.
- Applies a white top-hat filter (keeps thin bright strokes like text, ignores flat bright areas like walls/sky) and flags videos whose stroke-pixel ratio exceeds a threshold.
- Built for network/cloud drives (e.g. CloudDrive2 over SMB): reads are sequential with minimal seeks.

**Sampling modes:**

- `--first-frame` — reads only the first keyframe (~0.4MB per video). Cheapest pass for cloud drives; recheck "clean" files with a wider pass.
- default `--span 25` — one sequential read of the first 25s, decoding only keyframes.
- `--span 0` — seeks across the full duration (most robust, most bandwidth).

**Usage:**

```bash
# cheap first pass over a cloud drive
python scan_watermark.py /Volumes/cloud/videos --first-frame --print-clean

# follow-up pass with wider sampling
python scan_watermark.py /Volumes/cloud/videos --print-clean

# verbose: show per-video box size and frame count
python scan_watermark.py /Volumes/cloud/videos -v
```

The watermark region defaults to frame fractions `0.87,0.04,0.97,0.105` (measured on 4K Beautyleg rips); override with `--box X0,Y0,X1,Y1` if the mark sits elsewhere. `--save-crops DIR` dumps each video's composite crop as a PGM for visual verification.

---

## Requirements

Most scripts are stdlib-only. `sync_finder.py` additionally needs FFmpeg plus numpy and scipy — use the included venv:

```bash
.venv/bin/python sync_finder.py ...
```

`scan_watermark.py` needs FFmpeg and ffprobe on PATH but is otherwise stdlib-only.
