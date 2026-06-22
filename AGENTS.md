# AGENTS.md — Instructions for AI coding assistants

This repo is a collection of standalone Python utility scripts.

## Conventions

- **No comments in code.** Code should be self-documenting.
- **Minimal dependencies.** Prefer stdlib. Only add dependencies when unavoidable.
- **Standalone scripts.** Each script is independently runnable (`python script.py`).
- **No shebang.** Scripts are run via `python script.py` or `uv run script.py`, not executed directly.
- **Cross-platform when practical.** macOS is primary, but avoid hardcoding paths when possible.

## Running scripts

```bash
uv run ~/Code/My-Scripts/script.py [args]
# or
python ~/Code/My-Scripts/script.py [args]
```

## Testing

- Scripts are tested ad-hoc by the user.
- No formal test framework is used.
- After modifying a script, verify with a quick manual test if possible.

## Files

- `README.md` — documentation for all scripts. Update when adding or changing a script.
- `AGENTS.md` — this file. AI instructions.
