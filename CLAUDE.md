# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

A collection of standalone Python utility scripts for everyday automation tasks. Each script is self-contained with no interdependencies.

## Scripts

### organize_episodes.py
Renames TV show episode files in `Season X` folder structure. Key behaviors:
- Processes folders matching `Season \d+` pattern
- Renames videos and subtitles to `{ShowTitle} S{XX}E{XXX}{ext}` format
- Episode numbers are zero-padded (2 digits if <100 episodes, 3 digits otherwise)
- Deletes non-video/non-subtitle files (.txt, .nfo, .jpg, etc.)
- Supported video extensions: `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.m4v`
- Supported subtitle extensions: `.srt`, `.ass`, `.vtt`, `.sub`, `.ssa`
- Files are sorted alphabetically before numbering (mimics PowerShell's `Sort-Object Name`)

### get_real_link.py
Extracts direct download links from redirect URLs. Key behaviors:
- Sends HEAD request with `allow_redirects=False` to capture redirect location
- Returns the `Location` header from 3xx responses
- Handles both absolute and relative redirect URLs via `urljoin()`
- Automatically copies result to clipboard using `pyperclip`
- 10-second timeout on requests

## Dependencies

Scripts require:
- `requests` - HTTP library for get_real_link.py
- `pyperclip` - Clipboard operations for get_real_link.py

Virtual environment is located at `.venv/`.

## Common Operations

Run a script:
```bash
python organize_episodes.py
python get_real_link.py
```

## Code Conventions

- ANSI color codes are defined in a `Colors` class at the top of each script
- User input is gathered via `input()` prompts at runtime
- Scripts use `if __name__ == "__main__"` entry points with try/except for `KeyboardInterrupt`
