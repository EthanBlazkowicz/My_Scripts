#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

TS_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")
LINE_RE = re.compile(
    r"^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})(.*)$"
)


def parse_fps(value: str) -> float:
    """Accept '23.976', '24', or '24000/1001'."""
    value = value.strip()
    if "/" in value:
        a, b = value.split("/", 1)
        return float(a) / float(b)
    return float(value)


def parse_ts(ts: str) -> int:
    m = TS_RE.match(ts.strip())
    if not m:
        raise ValueError(f"Bad timestamp: {ts!r}")
    h, mnt, s, ms = map(int, m.groups())
    return ((h * 60 + mnt) * 60 + s) * 1000 + ms


def format_ts(ms: float) -> str:
    ms = int(round(ms))
    if ms < 0:
        ms = 0

    h, ms = divmod(ms, 3600_000)
    mnt, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)

    return f"{h:02d}:{mnt:02d}:{s:02d},{ms:03d}"


def convert_srt(text: str, factor: float) -> str:
    out_lines = []

    for line in text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            out_lines.append(line)
            continue

        start_s, end_s, suffix = m.groups()

        start = parse_ts(start_s)
        end = parse_ts(end_s)

        new_start = start * factor
        new_end = end * factor

        out_lines.append(f"{format_ts(new_start)} --> {format_ts(new_end)}{suffix}")

    result = "\n".join(out_lines)
    if text.endswith("\n"):
        result += "\n"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Convert all .srt files in a folder for FPS changes."
    )
    parser.add_argument("folder", type=Path, help="Folder containing .srt files")
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Process .srt files in subfolders too",
    )
    parser.add_argument(
        "--from-fps",
        type=parse_fps,
        default=24.0,
        help="FPS the subtitles were made for. Default: 24",
    )
    parser.add_argument(
        "--to-fps",
        type=parse_fps,
        default=24000 / 1001,
        help="Target FPS. Default: 24000/1001 = 23.976...",
    )
    parser.add_argument(
        "--suffix",
        default="_converted",
        help="Output suffix before .srt. Default: _converted",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing converted files"
    )

    args = parser.parse_args()

    folder = args.folder
    if not folder.is_dir():
        raise SystemExit(f"Not a folder: {folder}")

    pattern = "**/*.srt" if args.recursive else "*.srt"
    files = sorted(folder.glob(pattern))

    if not files:
        print("No .srt files found.")
        return

    factor = args.from_fps / args.to_fps

    print(f"FPS conversion: {args.from_fps} -> {args.to_fps}")
    print(f"factor = {factor:.12f}")
    print()

    for src in files:
        # Avoid re-processing already converted files
        if src.stem.endswith(args.suffix):
            print(f"Skip already converted: {src}")
            continue

        dst = src.with_name(src.stem + args.suffix + ".srt")

        if dst.exists() and not args.overwrite:
            print(f"Skip existing: {dst}")
            continue

        text = src.read_text(encoding="utf-8-sig")
        converted = convert_srt(text, factor)
        dst.write_text(converted, encoding="utf-8")

        print(f"Wrote {dst}")


if __name__ == "__main__":
    main()
