import argparse
import shutil
import sys
from pathlib import Path

DEFAULT_LIST = Path("/Users/ethanblazkowicz/Downloads/moving.txt")


def main():
    parser = argparse.ArgumentParser(
        description="Move folders or files named in a list file from one directory to another"
    )
    parser.add_argument(
        "source", type=Path, help="Directory containing the folders to move"
    )
    parser.add_argument("destination", type=Path, help="Directory to move folders into")
    parser.add_argument(
        "--list",
        type=Path,
        default=DEFAULT_LIST,
        help=f"Text file with one folder name per line (default: {DEFAULT_LIST})",
    )
    args = parser.parse_args()

    if not args.source.is_dir():
        sys.exit(f"Not a directory: {args.source}")
    if not args.list.is_file():
        sys.exit(f"Not a file: {args.list}")

    names = {
        line.strip()
        for line in args.list.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    if not names:
        sys.exit("List file is empty.")

    entries = [e for e in args.source.iterdir() if e.name in names]
    found = {e.name for e in entries}

    args.destination.mkdir(parents=True, exist_ok=True)

    moved = 0
    skipped = []
    for entry in entries:
        target = args.destination / entry.name
        if target.exists():
            skipped.append(entry.name)
            continue
        shutil.move(entry, target)
        moved += 1

    print(f"Moved {moved} of {len(names)} listed entries to {args.destination}")

    not_found = names - found
    if not_found:
        print(f"\n{len(not_found)} listed folders not found in source:")
        for name in sorted(not_found):
            print(f"  {name}")
    if skipped:
        print(f"\nSkipped {len(skipped)} (same name already exists in destination):")
        for name in skipped:
            print(f"  {name}")


if __name__ == "__main__":
    main()
