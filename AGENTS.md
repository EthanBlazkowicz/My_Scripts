# AGENTS.md — Instructions for AI coding assistants

This repo is a collection of standalone Python utility scripts.

## Companion repo

Adult-content-related scripts (Beautyleg downloader/renamers, scrapers, etc.) live in `~/Code/Naughty_Scripts`, not here. Don't recreate them in this repo or document them in this README.

## Conventions

- **No comments in code.** Code should be self-documenting.
- **Minimal dependencies.** Prefer stdlib. Only add dependencies when unavoidable.
- **Media tasks use FFmpeg via subprocess.** Don't add Python media libraries (cv2, PIL, numpy) for decoding frames/audio; shell out to `ffmpeg`/`ffprobe` instead, and prefer read patterns that minimize bytes and seeks (see `sync_finder.py`, `scan_watermark.py`).
- **Standalone scripts.** Each script is independently runnable (`python script.py`).
- **No shebang.** Scripts are run via `python script.py` or `uv run script.py`, not executed directly.
- **Cross-platform when practical.** macOS is primary, but avoid hardcoding paths when possible.

## Running scripts

```bash
uv run ~/Code/My_Scripts/script.py [args]
# or
python ~/Code/My_Scripts/script.py [args]
```

## Testing

- Scripts are tested ad-hoc by the user.
- No formal test framework is used.
- After modifying a script, verify with a quick manual test if possible.

## Files

- `README.md` — documentation for all scripts. Update when adding or changing a script.
- `AGENTS.md` — this file. AI instructions.
