#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path

KEKA_7ZZ = ["/Applications/Keka.app/Contents/MacOS/Keka", "--ignore-file-access", "--cli", "7zz"]
PASSWORD = "https://www.91xiezhen.top"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg", ".heic", ".heif", ".avif"}


def count_images(folder):
    count = 0
    for _, _, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                count += 1
    return count


def find_inner_archive(folder):
    for root, dirs, files in os.walk(folder):
        for f in sorted(files):
            lower = f.lower()
            full = os.path.join(root, f)
            if lower.endswith(".7z.001"):
                return full
            if lower.endswith(".z01"):
                base = full[:-4]
                zip_path = base + ".zip"
                if os.path.exists(zip_path):
                    return zip_path
                return full
    for root, dirs, files in os.walk(folder):
        for f in sorted(files):
            lower = f.lower()
            full = os.path.join(root, f)
            if any(lower.endswith(ext) for ext in [".7z", ".zip", ".rar", ".gz", ".bz2", ".xz", ".tar", ".tgz"]):
                return full
    return None


def extract(archive, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    cmd = KEKA_7ZZ + ["x", f"-p{PASSWORD}", f"-o{output_dir}", "-y", archive]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def extract_recursive(archive, depth=0):
    indent = "  " * depth
    print(f"{indent}Extracting: {os.path.basename(archive)}")

    out_dir = archive + ".temp"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)

    if not extract(archive, out_dir):
        print(f"{indent}  FAILED to extract")
        return None, None

    entries = [e for e in os.listdir(out_dir) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(out_dir, entries[0])):
        content_dir = os.path.join(out_dir, entries[0])
    else:
        content_dir = out_dir

    img_count = count_images(content_dir)
    if img_count >= 2:
        print(f"{indent}  Found {img_count} images")
        return content_dir, os.path.basename(content_dir)

    inner = find_inner_archive(content_dir)
    if inner is None:
        print(f"{indent}  Only {img_count} images, no inner archive found")
        return None, None

    print(f"{indent}  Found {img_count} images, extracting inner archive...")
    result_dir, result_name = extract_recursive(inner, depth + 1)

    if result_dir is not None:
        return result_dir, result_name

    return None, None


def find_images_folder(folder):
    current = folder
    while True:
        entries = [e for e in os.listdir(current) if not e.startswith(".")]
        if len(entries) == 1:
            candidate = os.path.join(current, entries[0])
            if os.path.isdir(candidate) and count_images(candidate) >= 2:
                current = candidate
                continue
        break
    return current, os.path.basename(current)


def process_archive(archive, output_base):
    result_dir, result_name = extract_recursive(archive)
    if result_dir is None:
        return False

    final_dir, final_name = find_images_folder(result_dir)

    dest = os.path.join(output_base, final_name)
    if os.path.exists(dest):
        shutil.rmtree(dest)

    shutil.move(final_dir, dest)
    print(f"  -> {dest}")

    # Clean up all .temp dirs from this archive
    parent = os.path.dirname(archive)
    for f in os.listdir(parent):
        if f.endswith(".temp") and os.path.isdir(os.path.join(parent, f)):
            shutil.rmtree(os.path.join(parent, f), ignore_errors=True)

    return True


def main():
    folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    output_dir = os.path.join(folder, "Output")
    os.makedirs(output_dir, exist_ok=True)

    archives = []
    for f in sorted(os.listdir(folder)):
        lower = f.lower()
        full = os.path.join(folder, f)
        if not os.path.isfile(full):
            continue
        if lower.endswith((".z01", ".z02", ".z03", ".z04", ".z05")):
            continue
        if ".7z." in lower and not lower.endswith(".7z.001"):
            continue
        if lower.endswith(".7z.001"):
            archives.append(full)
            continue
        if lower.endswith(".zip"):
            archives.append(full)
            continue
        if any(lower.endswith(ext) for ext in [".gz", ".7z", ".rar", ".bz2", ".xz", ".tar", ".tgz", ".tbz2"]):
            archives.append(full)

    if not archives:
        print("No archives found.")
        return

    print(f"Found {len(archives)} archive(s)\n")
    success = 0
    for arch in archives:
        if process_archive(arch, output_dir):
            success += 1
        print()

    print(f"Done: {success}/{len(archives)} extracted to Output/")


if __name__ == "__main__":
    main()
