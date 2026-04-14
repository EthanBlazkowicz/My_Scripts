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

## Requirements

```bash
pip install requests pyperclip
```

Or use the included virtual environment:
```bash
.venv\Scripts\activate
```

## Notes

- Scripts use ANSI color codes for terminal output
- Both scripts handle Ctrl+C gracefully
