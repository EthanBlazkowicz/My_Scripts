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
