#!/usr/bin/env python3
import re
import sys
import os
import argparse

SRT_TIMESTAMP = re.compile(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})')
SRT_BLOCK = re.compile(r'(\d+\s*\n\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}.*?\n\n)', re.DOTALL)


def ts_to_ms(ts):
    h, m, s, ms = map(int, ts)
    return h * 3600000 + m * 60000 + s * 1000 + ms


def ms_to_ts(ms):
    if ms < 0:
        ms = 0
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def shift_srt(content, offset_ms):
    def replace_timestamps(m):
        return ms_to_ts(ts_to_ms(m.groups()) + offset_ms)

    return SRT_TIMESTAMP.sub(replace_timestamps, content)


def main():
    parser = argparse.ArgumentParser(description="Shift .srt subtitle timestamps by a time offset.")
    parser.add_argument("input", help="Input .srt file")
    parser.add_argument("offset", type=float, help="Offset in seconds (e.g. 1.692, -0.500)")
    parser.add_argument("-o", "--output", help="Output file (default: print to stdout)")
    parser.add_argument("-i", "--in-place", action="store_true", dest="inplace",
                        help="Modify file in-place (creates .bak backup)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    offset_ms = round(args.offset * 1000)
    shifted = shift_srt(content, offset_ms)

    if args.inplace:
        os.rename(args.input, args.input + ".bak")
        with open(args.input, "w", encoding="utf-8") as f:
            f.write(shifted)
        print(f"Shifted by {args.offset:+.3f}s: {args.input} (backup: {args.input}.bak)")
    elif args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(shifted)
        print(f"Shifted by {args.offset:+.3f}s: {args.output}")
    else:
        sys.stdout.write(shifted)


if __name__ == "__main__":
    main()
