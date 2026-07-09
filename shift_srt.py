import re
import sys
import os
import argparse

SRT_TIMESTAMP = re.compile(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})')
SRT_BLOCK = re.compile(
    r'(\d+\s*\n'
    r'\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}'
    r'.*?)(?=\n\n|\Z)',
    re.DOTALL,
)

ENCODINGS = ["utf-8-sig", "utf-16", "utf-16-le", "gbk", "gb18030", "big5", "latin-1"]


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

    lines = content.splitlines(keepends=True)
    result = []
    for line in lines:
        if "-->" in line:
            line = SRT_TIMESTAMP.sub(replace_timestamps, line)
        result.append(line)
    return "".join(result)


def read_file(path):
    for enc in ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
    return None, None


def write_file(path, content, encoding):
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


def shift_file(path, offset_s, inplace=False):
    content, enc = read_file(path)
    if content is None:
        print(f"Error: could not decode {path}", file=sys.stderr)
        return False

    offset_ms = round(offset_s * 1000)
    shifted = shift_srt(content, offset_ms)

    if inplace:
        bak = path + ".bak"
        os.rename(path, bak)
        write_file(path, shifted, enc)
        print(f"Shifted by {offset_s:+.3f}s: {path} (backup: {bak})")
    else:
        sys.stdout.write(shifted)
    return True


def parse_blocks(content):
    return SRT_BLOCK.findall(content.strip())


def renumber_blocks(blocks, start=1):
    result = []
    n = start
    for block in blocks:
        _, _, rest = block.partition("\n")
        result.append(f"{n}\n{rest}")
        n += 1
    return result


def blocks_to_text(blocks):
    return "\n\n".join(blocks) + "\n"


def concat_mode(base_path, concat_path, shift_s):
    content1, enc1 = read_file(base_path)
    content2, enc2 = read_file(concat_path)
    for name, c in ((base_path, content1), (concat_path, content2)):
        if c is None:
            print(f"Error: could not decode {name}", file=sys.stderr)
            sys.exit(1)

    shifted2 = shift_srt(content2, round(shift_s * 1000))
    blocks1 = parse_blocks(content1)
    blocks2 = parse_blocks(shifted2)
    blocks2 = renumber_blocks(blocks2, start=len(blocks1) + 1)

    return blocks_to_text(blocks1 + blocks2), enc1


def batch_mode(folder, offset_file):
    if not os.path.isdir(folder):
        print(f"Error: folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(offset_file) as f:
            offsets = [float(line.strip()) for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: offset file not found: {offset_file}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: invalid offset in {offset_file}: {e}", file=sys.stderr)
        sys.exit(1)

    srt_files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".srt"))

    if len(offsets) < len(srt_files):
        print(
            f"Error: {len(offsets)} offset(s) for {len(srt_files)} .srt files",
            file=sys.stderr,
        )
        sys.exit(1)

    for path, offset in zip(srt_files, offsets):
        full_path = os.path.join(folder, path)
        shift_file(full_path, offset, inplace=True)


def main():
    parser = argparse.ArgumentParser(
        description="Shift .srt subtitle timestamps by a time offset."
    )
    parser.add_argument("input", nargs="?", help="Input .srt file")
    parser.add_argument("offset", nargs="?", type=float, help="Offset in seconds (e.g. 1.692, -0.500)")
    parser.add_argument("-o", "--output", help="Output file (default: print to stdout)")
    parser.add_argument(
        "-i",
        "--in-place",
        action="store_true",
        dest="inplace",
        help="Modify file in-place (creates .bak backup)",
    )
    parser.add_argument(
        "--folder",
        help="Batch mode: folder with .srt files",
    )
    parser.add_argument(
        "--offset-file",
        help="Batch mode: file with one offset per line (applied to sorted .srt files)",
    )
    parser.add_argument(
        "--concat",
        metavar="FILE",
        help="Second .srt file to shift and append to input",
    )
    parser.add_argument(
        "--shift-concat",
        type=float,
        metavar="SECONDS",
        help="Offset in seconds for the --concat file",
    )

    args = parser.parse_args()

    if args.concat or args.shift_concat is not None:
        if not args.concat or args.shift_concat is None:
            parser.error("--concat and --shift-concat must be used together")
        if not args.input:
            parser.error("input file is required as the base for --concat")
        merged, enc = concat_mode(args.input, args.concat, args.shift_concat)
        if args.output:
            write_file(args.output, merged, enc)
            print(f"Merged: {args.input} + {args.concat} -> {args.output}")
        else:
            sys.stdout.write(merged)
        return

    if args.folder or args.offset_file:
        if not args.folder or not args.offset_file:
            parser.error("--folder and --offset-file must be used together")
        batch_mode(args.folder, args.offset_file)
        return

    if not args.input or args.offset is None:
        parser.error("input file and offset are required in single-file mode")

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    content, enc = read_file(args.input)
    if content is None:
        print(f"Error: could not decode {args.input}", file=sys.stderr)
        sys.exit(1)

    offset_ms = round(args.offset * 1000)
    shifted = shift_srt(content, offset_ms)

    if args.inplace:
        bak = args.input + ".bak"
        os.rename(args.input, bak)
        write_file(args.input, shifted, enc)
        print(f"Shifted by {args.offset:+.3f}s: {args.input} (backup: {bak})")
    elif args.output:
        write_file(args.output, shifted, enc)
        print(f"Shifted by {args.offset:+.3f}s: {args.output}")
    else:
        sys.stdout.write(shifted)


if __name__ == "__main__":
    main()
