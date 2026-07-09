#!/usr/bin/env python3
import os
import sys
import shutil
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"}

# Concurrency Configurations
MAX_WORKERS = max(1, os.cpu_count() // 2)
PRINT_LOCK = threading.Lock()
MOVE_LOCK = threading.Lock()


def safe_print(*args, **kwargs):
    """Thread-safe print wrapper to prevent terminal output scrambling."""
    with PRINT_LOCK:
        print(*args, **kwargs)


def process_folder(folder_path, output_base):
    """Scans a single folder for videos, renames them to the folder's name, and moves them."""
    folder_name = os.path.basename(folder_path)
    video_files = []

    # Recursively look for any videos inside this folder
    for root, _, files in os.walk(folder_path):
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXTS:
                video_files.append(os.path.join(root, f))

    if not video_files:
        return False

    safe_print(f"Processing folder: {folder_name} ({len(video_files)} video(s) found)")

    # Thread-safe block for filesystem modifications
    with MOVE_LOCK:
        for i, vid_path in enumerate(sorted(video_files)):
            ext = os.path.splitext(vid_path)[1]
            # If a folder happens to have multiple videos, give them numbered suffixes
            suffix = f"_{i+1}" if len(video_files) > 1 else ""
            new_vid_name = f"{folder_name}{suffix}{ext}"
            dest_vid = os.path.join(output_base, new_vid_name)

            # Prevent collision crashes
            if os.path.exists(dest_vid):
                if os.path.isdir(dest_vid):
                    shutil.rmtree(dest_vid)
                else:
                    os.remove(dest_vid)

            shutil.move(vid_path, dest_vid)
            safe_print(f"  -> {dest_vid}")
            
    return True


def main():
    target = os.getcwd()

    # Allow passing a specific path as a command-line argument
    if sys.argv[1:]:
        target = os.path.abspath(sys.argv[1])

    output_dir = os.path.join(target, "Output")
    os.makedirs(output_dir, exist_ok=True)

    # Gather all subdirectories, ignoring hidden ones and the Output folder itself
    folders = sorted(
        f for f in os.listdir(target)
        if os.path.isdir(os.path.join(target, f)) 
        and not f.startswith(".") 
        and f != "Output"
    )

    if not folders:
        safe_print("No subdirectories found to scan.")
        return

    safe_print(f"Found {len(folders)} folder(s) to scan | Running with {MAX_WORKERS} workers.\n")

    success = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all folder scanning tasks to the thread pool
        futures = [executor.submit(process_folder, os.path.join(target, name), output_dir) for name in folders]
        
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                success += 1

    safe_print(f"\nDone: Extracted videos from {success}/{len(folders)} folders into Output/")


if __name__ == "__main__":
    main()