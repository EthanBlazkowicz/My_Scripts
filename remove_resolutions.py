import os
import re
import argparse
import sys

def remove_resolution_tags(directory, dry_run=False):
    # Regex to match space + resolution at the end of the filename (excluding extension)
    # The resolution can be 360p, 720p, 1080p, 2160p, 4K
    pattern = re.compile(r'\s*(?:360p|720p|1080p|2160p|4k)(?=\.[^.]+$|$)', re.IGNORECASE)
    
    renamed_count = 0
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        # Skip directories
        if not os.path.isfile(file_path):
            continue
            
        new_filename = pattern.sub('', filename)
        
        if new_filename != filename:
            new_file_path = os.path.join(directory, new_filename)
            
            # Avoid overwriting existing files
            if os.path.exists(new_file_path):
                print(f"Skipping '{filename}': Target '{new_filename}' already exists.")
                continue
                
            print(f"Before: {filename}")
            print(f"After:  {new_filename}")
            print("-" * 40)
            
            if not dry_run:
                try:
                    os.rename(file_path, new_file_path)
                    renamed_count += 1
                except Exception as e:
                    print(f"Error renaming '{filename}': {e}")
                    
    if dry_run:
        print("\nThis was a DRY RUN. No files were actually renamed.")
    else:
        print(f"\nSuccessfully renamed {renamed_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove resolution tags (e.g., 1080p, 4K) from the end of filenames.")
    parser.add_argument("directory", nargs="?", default=".", help="Directory containing the files (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry-run without renaming the files")
    
    args = parser.parse_args()
    
    target_dir = args.directory
    if not os.path.isdir(target_dir):
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)
        
    remove_resolution_tags(target_dir, dry_run=args.dry_run)
