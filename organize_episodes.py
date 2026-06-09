import os
import re
from pathlib import Path

# ANSI color codes for terminal output
class Colors:
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    DARK_GREEN = '\033[32m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

def organize_tv_show_episodes():
    # Ask for inputs after the script runs
    show_title = input("Enter the Show Title: ").strip()
    target_directory = input("Enter the Target Directory (leave blank for current directory '.'): ").strip()
    
    if not target_directory:
        target_directory = "."
        
    target_path = Path(target_directory).expanduser().resolve()
    
    # Validate directory
    if not target_path.exists() or not target_path.is_dir():
        print(f"{Colors.RED}Error: The directory '{target_directory}' does not exist.{Colors.RESET}")
        return

    # Define what files to keep and rename
    video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.m4v'}
    sub_extensions = {'.srt', '.ass', '.vtt', '.sub', '.ssa'}

    # Get all subdirectories that match the naming pattern "Season X" or "Season XX"
    season_pattern = re.compile(r"^Season\s+(\d+)$", re.IGNORECASE)
    season_folders = []
    
    for item in target_path.iterdir():
        if item.is_dir():
            match = season_pattern.match(item.name)
            if match:
                season_folders.append((item, match.group(1)))
                
    if not season_folders:
        print(f"{Colors.YELLOW}No folders matching 'Season XX' found in '{target_directory}'.{Colors.RESET}")
        return

    for folder, season_num in season_folders:
        # Extract and pad the season number
        season_pad = f"{int(season_num):02d}"
        print(f"\n{Colors.CYAN}--- Processing: {folder.name} ---{Colors.RESET}")

        # Get all files within the current season folder (skip hidden/macOS metadata files)
        all_files = [f for f in folder.iterdir() if f.is_file() and not f.name.startswith('.')]
        
        # Sort files alphabetically, case-insensitive (Mimics PowerShell's Sort-Object Name)
        all_files.sort(key=lambda x: x.name.lower())

        # Separate files by extension
        video_files = [f for f in all_files if f.suffix.lower() in video_extensions]
        sub_files = [f for f in all_files if f.suffix.lower() in sub_extensions]
        unwanted_files = [f for f in all_files if f.suffix.lower() not in video_extensions and f.suffix.lower() not in sub_extensions]

        # 1. Delete unwanted files (like .txt, .nfo, .jpg)
        for file in unwanted_files:
            print(f"{Colors.RED}Deleting unwanted file: {file.name}{Colors.RESET}")
            try:
                file.unlink()
            except Exception as e:
                print(f"{Colors.RED}Failed to delete {file.name}: {e}{Colors.RESET}")

        # 2. Process Video and Subtitle files
        total_videos = len(video_files)
        if total_videos == 0:
            print(f"{Colors.YELLOW}No video files found to rename.{Colors.RESET}")
            continue

        digits = 3 if total_videos >= 100 else 2

        for i in range(total_videos):
            video = video_files[i]
            ep_number = f"{i + 1:0{digits}d}"
            
            # The exact name prefix for both the video and the subtitle
            new_base_name = f"{show_title} S{season_pad}E{ep_number}"
            
            # Rename the Video
            new_video_name = f"{new_base_name}{video.suffix}"
            new_video_path = folder / new_video_name
            print(f"{Colors.GREEN}Renaming Video: {video.name} -> {new_video_name}{Colors.RESET}")
            video.rename(new_video_path)

            # Rename the corresponding Subtitle
            if i < len(sub_files):
                sub = sub_files[i]
                new_sub_name = f"{new_base_name}{sub.suffix}"
                new_sub_path = folder / new_sub_name
                print(f"{Colors.DARK_GREEN}Renaming Subtitle: {sub.name} -> {new_sub_name}{Colors.RESET}")
                sub.rename(new_sub_path)
        
        # Quick safety check in case there are more subtitles than videos
        if len(sub_files) > total_videos:
            print(f"{Colors.YELLOW}Warning: There are more subtitle files ({len(sub_files)}) than video files ({total_videos}). Some subtitles were left un-renamed.{Colors.RESET}")

    print(f"\n{Colors.MAGENTA}[✓] Done! All season folders processed safely.{Colors.RESET}")

if __name__ == "__main__":
    try:
        organize_tv_show_episodes()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Script cancelled by user.{Colors.RESET}")