#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

PASSWORD = "https://www.91xiezhen.top"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg", ".heic", ".heif", ".avif"}


def detect_extractor():
    system = platform.system()
    if system == "Darwin":
        keka = "/Applications/Keka.app/Contents/MacOS/Keka"
        if os.path.exists(keka):
            return [keka, "--ignore-file-access", "--cli", "7zz"]
        print("Warning: Keka not found, falling back to 7z")
    elif system == "Windows":
        for p in [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]:
            if os.path.exists(p):
                return [p]

    fallback = shutil.which("7z")
    if fallback:
        return [fallback]

    print("Error: no extractor found (Keka on macOS, 7-Zip on Windows, or 7z in PATH)")
    sys.exit(1)


EXTRACTOR = detect_extractor()


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
    cmd = EXTRACTOR + ["x", f"-p{PASSWORD}", f"-o{output_dir}", "-y", archive]
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

    total_img = count_images(content_dir)
    direct_img = sum(
        1 for f in os.listdir(content_dir)
        if os.path.isfile(os.path.join(content_dir, f))
        and os.path.splitext(f)[1].lower() in IMAGE_EXTS
    )

    if direct_img >= 2:
        print(f"{indent}  Found {total_img} images")
        return content_dir, os.path.basename(content_dir)

    if total_img >= 2:
        # Images are in a subfolder — find which one
        for entry in sorted(os.listdir(content_dir)):
            sub = os.path.join(content_dir, entry)
            if os.path.isdir(sub) and count_images(sub) >= 2:
                print(f"{indent}  Found {count_images(sub)} images in {entry}")
                return sub, entry
        print(f"{indent}  Only {direct_img} direct images, {total_img} total")
        return content_dir, os.path.basename(content_dir)

    inner = find_inner_archive(content_dir)
    if inner is None:
        print(f"{indent}  No images found, no inner archive")
        return None, None

    print(f"{indent}  Extracting inner archive...")
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


def cleanup_temp(parent):
    for f in os.listdir(parent):
        if f.endswith(".temp") and os.path.isdir(os.path.join(parent, f)):
            shutil.rmtree(os.path.join(parent, f), ignore_errors=True)


def process_archive(archive, output_base):
    result_dir, result_name = extract_recursive(archive)
    if result_dir is None:
        cleanup_temp(os.path.dirname(archive))
        return False

    final_dir, final_name = find_images_folder(result_dir)

    dest = os.path.join(output_base, final_name)
    if os.path.exists(dest):
        shutil.rmtree(dest)

    shutil.move(final_dir, dest)
    print(f"  -> {dest}")

    cleanup_temp(os.path.dirname(archive))
    return True


def process_folder(folder_path, output_base):
    name = os.path.basename(folder_path)

    inner = find_inner_archive(folder_path)
    if inner is None:
        print(f"No archives found in {name}")
        return False

    result_dir, result_name = extract_recursive(inner)
    if result_dir is None:
        cleanup_temp(folder_path)
        return False

    final_dir, final_name = find_images_folder(result_dir)

    dest = os.path.join(output_base, final_name)
    if os.path.exists(dest):
        shutil.rmtree(dest)

    shutil.move(final_dir, dest)
    print(f"  -> {dest}")

    cleanup_temp(folder_path)
    return True


def main():
    args = sys.argv[1:]

    folder_mode = False
    target = os.getcwd()

    if "--folders" in args:
        folder_mode = True
        args.remove("--folders")

    if args:
        target = os.path.abspath(args[0])

    output_dir = os.path.join(target, "Output")
    os.makedirs(output_dir, exist_ok=True)

    if folder_mode:
        folders = sorted(
            f for f in os.listdir(target)
            if os.path.isdir(os.path.join(target, f)) and not f.startswith(".") and f != "Output"
        )
        if not folders:
            print("No subdirectories found.")
            return
        print(f"Found {len(folders)} folder(s)\n")
        success = 0
        for name in folders:
            print(f"Processing folder: {name}")
            if process_folder(os.path.join(target, name), output_dir):
                success += 1
            print()
        print(f"Done: {success}/{len(folders)} extracted to Output/")
        return

    archives = []
    for f in sorted(os.listdir(target)):
        lower = f.lower()
        full = os.path.join(target, f)
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
        print("No archives found. Use --folders to scan subdirectories.")
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
