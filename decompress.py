#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import platform
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PASSWORD = "https://www.91xiezhen.top"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg", ".heic", ".heif", ".avif"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"}

# Concurrency Configurations
MAX_WORKERS = max(1, os.cpu_count() // 2)
PRINT_LOCK = threading.Lock()
MOVE_LOCK = threading.Lock()


def safe_print(*args, **kwargs):
    """Thread-safe print wrapper to prevent terminal output scrambling."""
    with PRINT_LOCK:
        print(*args, **kwargs)


def detect_extractor():
    system = platform.system()
    if system == "Darwin":
        keka = "/Applications/Keka.app/Contents/MacOS/Keka"
        if os.path.exists(keka):
            return [keka, "--ignore-file-access", "--cli", "7zz"]
        safe_print("Warning: Keka not found, falling back to 7z")
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

    safe_print("Error: no extractor found (Keka on macOS, 7-Zip on Windows, or 7z in PATH)")
    sys.exit(1)


EXTRACTOR = detect_extractor()


def count_images(folder):
    count = 0
    for _, _, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                count += 1
    return count


def count_videos(folder):
    count = 0
    for _, _, files in os.walk(folder):
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
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
    
    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
        return False, error_msg
    return True, ""


def extract_recursive(archive, depth=0):
    indent = "  " * depth
    safe_print(f"{indent}Extracting: {os.path.basename(archive)}")

    out_dir = archive + ".temp"
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir, ignore_errors=True)

    success, error_details = extract(archive, out_dir)
    if not success:
        single_line_err = error_details.replace('\n', ' | ')[:150]
        safe_print(f"{indent}  FAILED to extract. Reason: {single_line_err}")
        return None, None

    entries = [e for e in os.listdir(out_dir) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(out_dir, entries[0])):
        content_dir = os.path.join(out_dir, entries[0])
    else:
        content_dir = out_dir

    total_img = count_images(content_dir)
    total_vid = count_videos(content_dir)

    direct_img = sum(
        1 for f in os.listdir(content_dir)
        if os.path.isfile(os.path.join(content_dir, f))
        and os.path.splitext(f)[1].lower() in IMAGE_EXTS
    )
    direct_vid = sum(
        1 for f in os.listdir(content_dir)
        if os.path.isfile(os.path.join(content_dir, f))
        and os.path.splitext(f)[1].lower() in VIDEO_EXTS
    )

    if direct_img >= 2 or direct_vid >= 1:
        safe_print(f"{indent}  Found {total_img} images, {total_vid} videos")
        return content_dir, os.path.basename(content_dir)

    if total_img >= 2 or total_vid >= 1:
        for entry in sorted(os.listdir(content_dir)):
            sub = os.path.join(content_dir, entry)
            if os.path.isdir(sub) and (count_images(sub) >= 2 or count_videos(sub) >= 1):
                safe_print(f"{indent}  Found media in {entry} ({count_images(sub)} images, {count_videos(sub)} videos)")
                return sub, entry
        safe_print(f"{indent}  Only {direct_img} direct images, {direct_vid} direct videos ({total_img} img, {total_vid} vid total)")
        return content_dir, os.path.basename(content_dir)

    inner = find_inner_archive(content_dir)
    if inner is None:
        safe_print(f"{indent}  No media found, no inner archive")
        return None, None

    safe_print(f"{indent}  Extracting inner archive...")
    result_dir, result_name = extract_recursive(inner, depth + 1)

    if result_dir is not None:
        return result_dir, result_name

    return None, None


def find_media_folder(folder):
    current = folder
    while True:
        entries = [e for e in os.listdir(current) if not e.startswith(".")]
        if len(entries) == 1:
            candidate = os.path.join(current, entries[0])
            if os.path.isdir(candidate) and (count_images(candidate) >= 2 or count_videos(candidate) >= 1):
                current = candidate
                continue
        break
    return current, os.path.basename(current)


def delete_archive_files(archive):
    """Safely deletes single-file archives and sweeps entire volume sets (.001, .z01)."""
    try:
        dir_path = os.path.dirname(archive)
        file_name = os.path.basename(archive)
        lower_name = file_name.lower()
        
        if lower_name.endswith(".7z.001"):
            prefix = file_name[:-4]  # Everything matching 'filename.7z.'
            for f in os.listdir(dir_path):
                if f.startswith(prefix) and f[len(prefix):].isdigit():
                    os.remove(os.path.join(dir_path, f))
        elif lower_name.endswith(".zip"):
            prefix = file_name[:-4]  # Pure filename base
            if os.path.exists(archive):
                os.remove(archive)
            for f in os.listdir(dir_path):
                f_lower = f.lower()
                if f_lower.startswith(prefix.lower() + ".z") and f_lower[len(prefix)+2:].isdigit():
                    os.remove(os.path.join(dir_path, f))
        else:
            if os.path.exists(archive):
                os.remove(archive)
        safe_print(f"  Deleted source archive: {file_name}")
    except Exception as e:
        safe_print(f"  Warning: Could not delete source archive file(s) for {os.path.basename(archive)}: {e}")


def handle_output_movement(final_dir, final_name, output_base):
    video_files = []
    for root, _, files in os.walk(final_dir):
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
                video_files.append(os.path.join(root, f))

    with MOVE_LOCK:
        if video_files:
            for i, vid_path in enumerate(sorted(video_files)):
                ext = os.path.splitext(vid_path)[1]
                suffix = f"_{i+1}" if len(video_files) > 1 else ""
                new_vid_name = f"{final_name}{suffix}{ext}"
                dest_vid = os.path.join(output_base, new_vid_name)
                
                if os.path.exists(dest_vid):
                    if os.path.isdir(dest_vid):
                        shutil.rmtree(dest_vid)
                    else:
                        os.remove(dest_vid)
                        
                shutil.move(vid_path, dest_vid)
                safe_print(f"  -> {dest_vid}")
        else:
            dest = os.path.join(output_base, final_name)
            if os.path.exists(dest):
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
                    
            shutil.move(final_dir, dest)
            safe_print(f"  -> {dest}")


def process_archive(archive, output_base):
    safe_print(f"Processing archive: {os.path.basename(archive)}")
    temp_dir = archive + ".temp"
    
    result_dir, result_name = extract_recursive(archive)
    if result_dir is None:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    final_dir, final_name = find_media_folder(result_dir)
    handle_output_movement(final_dir, final_name, output_base)
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    # Successfully processed and moved; wipe out the source archive file(s)
    delete_archive_files(archive)
    safe_print("")
    return True


def process_folder(folder_path, output_base):
    name = os.path.basename(folder_path)
    safe_print(f"Processing folder: {name}")

    inner = find_inner_archive(folder_path)
    if inner is None:
        safe_print(f"No archives found in {name}\n")
        return False

    temp_dir = inner + ".temp"
    result_dir, result_name = extract_recursive(inner)
    if result_dir is None:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    final_dir, final_name = find_media_folder(result_dir)
    handle_output_movement(final_dir, final_name, output_base)
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    # Wipe out the inner archive inside the folder now that it's uncompressed safely
    delete_archive_files(inner)
    safe_print("")
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
            safe_print("No subdirectories found.")
            return
        safe_print(f"Found {len(folders)} folder(s) | Running with {MAX_WORKERS} workers.\n")
        
        success = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_folder, os.path.join(target, name), output_dir) for name in folders]
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    success += 1
                    
        safe_print(f"Done: {success}/{len(folders)} processed.")
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
        safe_print("No archives found. Use --folders to scan subdirectories.")
        return

    safe_print(f"Found {len(archives)} archive(s) | Running with {MAX_WORKERS} workers.\n")
    
    success = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_archive, arch, output_dir) for arch in archives]
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                success += 1

    safe_print(f"Done: {success}/{len(archives)} extracted and cleaned up.")


if __name__ == "__main__":
    main()