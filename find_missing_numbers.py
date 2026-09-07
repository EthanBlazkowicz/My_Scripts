import argparse
import re
import sys
from pathlib import Path

NUM_RE = re.compile(r"No\.(\d+)", re.IGNORECASE)


def main():
    parser = argparse.ArgumentParser(
        description="Find missing issue numbers in file/folder names like '... No.001 ...'"
    )
    parser.add_argument(
        "target", type=Path, help="Directory containing the numbered folders/files"
    )
    args = parser.parse_args()

    if not args.target.is_dir():
        sys.exit(f"Not a directory: {args.target}")

    numbers = set()
    skipped = []
    for entry in args.target.iterdir():
        match = NUM_RE.search(entry.name)
        if match:
            numbers.add(int(match.group(1)))
        else:
            skipped.append(entry.name)

    if not numbers:
        sys.exit("No files or folders matching 'No.XXX' pattern found.")

    lo, hi = min(numbers), max(numbers)
    missing = sorted(set(range(lo, hi + 1)) - numbers)

    print(f"Found {len(numbers)} numbered items, range {lo:03d} to {hi:03d}.")
    if skipped:
        print(f"\n{len(skipped)} items without a number:")
        for name in skipped:
            print(f"  {name}")

    if missing:
        print(f"\nMissing ({len(missing)}):")
        for n in missing:
            print(f"  No.{n:03d}")
    else:
        print("\nNo missing numbers.")


if __name__ == "__main__":
    main()
