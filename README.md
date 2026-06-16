# Python Utility Scripts

A collection of standalone Python scripts for everyday automation tasks.

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

### rename_c4s.py

Renames video files based on Clips4sale search results.

**What it does:**
- Parses original filenames to extract a search query and resolution.
- Uses DuckDuckGo HTML search to find the matching C4S clip ID.
- Automatically prepends the clip ID to the filename.
- Remembers the last used directory and search URL via `~/.rename_c4s_config.json`.
- Safely handles duplicate files by prefixing `0Duplicate `.

**Usage:**
```bash
python rename_c4s.py
python rename_c4s.py --dir /path/to/videos --url "https://www..." --dry-run
```

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

---

### decompress.py

Recursively extracts split archives (`.7z.001`, `.z01`+`.zip`, `.gz`, `.rar`, etc.) until it finds the folder containing images.

**What it does:**
- Detects OS: uses Keka on macOS, 7-Zip on Windows, or `7z` from PATH as fallback.
- Archives may be nested — an outer `.gz` might contain `.7z.001`+`.7z.002`, which in turn contains the images.
- Extracts recursively until a folder with 2+ images is found.
- Moves the innermost image folder into `Output/`, named after that folder (not the archive).
- Cleans up temp `.temp` directories after each archive.

**Usage:**
```bash
# Target archive files in current directory
python decompress.py

# Target archive files in a specific directory
python decompress.py /path/to/files

# Target subdirectories (each containing archives)
python decompress.py --folders
python decompress.py --folders /path/to/dirs
```

**Password:**
The password is hardcoded in the script (`PASSWORD` variable). Update it if needed.

---

### rename.py

Renames Xiuren-related folders into a standardized `[Xiuren秀人网]YYYY.MM.DD NO.XXXX ...` format.

**What it does:**
- Normalizes tag variants (`[XiuRen秀人网]`, `[XIUREN秀人网]`) to `[Xiuren秀人网]`.
- Removes stray spaces after the tag and before size brackets.
- Normalizes `No.` to `NO.`.
- Strips XR code prefixes (e.g., `XR20200228N02016`).
- **Pure number folders** (e.g. `2334`) — looks up the number in `~/Downloads/the_list.txt` and generates the full name.
- **XR+number folders** (e.g. `XR1739`) — same lookup, extracts date from the entry, formats with `NO.{num}`.

**Usage:**
```bash
python rename.py
python rename.py /path/to/folders
```

**Lookup file:** `~/Downloads/the_list.txt` — one name per line, blank lines ignored.

---

## Requirements

```bash
pip install requests pyperclip beautifulsoup4
```

Or use the included virtual environment:
```bash
.venv\Scripts\activate
```

## Notes

- Scripts use ANSI color codes for terminal output
- Both scripts handle Ctrl+C gracefully
