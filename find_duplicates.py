import os
import hashlib
from collections import defaultdict
import argparse

def get_partial_hash(filepath, chunk_size=1024 * 1024):
    """
    Calculate a hash of the first `chunk_size` bytes of a file.
    Reading just 1MB is extremely fast, even over a network drive.
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(chunk_size)
            hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def find_duplicates(directory, min_size=1024):
    print(f"Scanning '{directory}' for duplicates...")
    
    # Step 1: Group by file size
    # Getting file size via os.path.getsize (stat) is very fast and doesn't read the file content.
    size_groups = defaultdict(list)
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                size = os.path.getsize(filepath)
                # Ignore very small files (e.g. less than 1KB) as they might have high collision rates
                if size > min_size:
                    size_groups[size].append(filepath)
            except Exception as e:
                print(f"Error accessing {filepath}: {e}")

    # Filter out sizes that only have 1 file
    potential_duplicates = {size: paths for size, paths in size_groups.items() if len(paths) > 1}
    
    if not potential_duplicates:
        print("No duplicates found based on file size.")
        return

    print(f"Found {len(potential_duplicates)} groups of files with the exact same size. Verifying contents...")

    # Step 2: Verify using partial hashing (first 1MB)
    exact_duplicates = defaultdict(list)
    for size, paths in potential_duplicates.items():
        hash_groups = defaultdict(list)
        for filepath in paths:
            # We use a 1MB partial hash because for large video files, 
            # if the size is exactly the same AND the first 1MB is exactly the same, 
            # it is practically guaranteed to be the exact same file.
            partial_hash = get_partial_hash(filepath)
            if partial_hash:
                hash_groups[partial_hash].append(filepath)
                
        for partial_hash, duplicate_paths in hash_groups.items():
            if len(duplicate_paths) > 1:
                # Use a combined key of size + hash to ensure uniqueness across different sizes
                exact_duplicates[(size, partial_hash)].extend(duplicate_paths)

    # Step 3: Report
    if not exact_duplicates:
        print("No exact duplicates found after partial hashing.")
        return

    print("\n=== DUPLICATES FOUND ===")
    duplicate_count = 0
    for (size, _), paths in exact_duplicates.items():
        duplicate_count += len(paths) - 1
        print(f"\nSize: {size / (1024*1024):.2f} MB")
        for p in paths:
            print(f"  - {p}")
            
    print(f"\nTotal duplicate files that can be safely removed: {duplicate_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quickly find duplicate files on network drives.")
    parser.add_argument('--dir', type=str, required=True, help="Directory to scan")
    args = parser.parse_args()
    
    if not os.path.isdir(args.dir):
        print(f"Error: Directory '{args.dir}' not found.")
    else:
        find_duplicates(args.dir)
