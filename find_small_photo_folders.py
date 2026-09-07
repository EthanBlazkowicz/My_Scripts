#!/usr/bin/env python3
import os
import sys

PHOTO_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
)

SIZE_LOWER_LIMIT = 40 * 1024
SIZE_LIMIT = 100 * 1024


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <folder>", file=sys.stderr)
        sys.exit(1)

    root = sys.argv[1]

    scanned_folders = 0

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for filename in filenames:
            if filename.lower().endswith(PHOTO_EXTENSIONS):
                filepath = os.path.join(dirpath, filename)
                if SIZE_LOWER_LIMIT <= os.path.getsize(filepath) <= SIZE_LIMIT:
                    print(os.path.basename(os.path.normpath(dirpath)))
                    break

        scanned_folders += 1
        print(f"Scanned {scanned_folders} folders", file=sys.stderr)


if __name__ == "__main__":
    main()
