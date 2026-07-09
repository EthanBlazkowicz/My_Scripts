#!/usr/bin/env python3
import os
import sys
import re
import argparse
from pathlib import Path

LIST_FILE = os.path.expanduser("~/Downloads/the_list.txt")
DATES_FILE = os.path.expanduser("~/Downloads/dates.txt")

# Video extensions to process when running in video mode
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.rmvb', '.wmv', '.mov', '.flv'}


def load_list():
    if not os.path.exists(LIST_FILE):
        return []
    with open(LIST_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def load_dates_map():
    if not os.path.exists(DATES_FILE):
        return {}
    dates_map = {}
    with open(DATES_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r'(\d{4}\.\d{2}\.\d{2})\s+(?:No|NO)\.(\d+)', line, re.IGNORECASE)
            if match:
                date, num = match.groups()
                # Store by standardized integer string key for easier cross-lookup
                dates_map[str(int(num))] = date
    return dates_map


def find_entry(num, entries):
    for entry in entries:
        if f"NO.{num}" in entry or f"No.{num}" in entry or f"N0{num}" in entry:
            return entry
        if re.search(rf'\b{num}\b', entry):
            return entry
    return None


def clean_new_name(name):
    name = re.sub(r'\[(?:XiuRen|XIUREN)秀人网\]', '[Xiuren秀人网]', name)
    name = re.sub(r'\[Xiuren秀人网\]\s+', '[Xiuren秀人网]', name)
    name = re.sub(r'\bNo\.', 'NO.', name)
    name = re.sub(r'\s+(\[)', r'\1', name)
    name = re.sub(r'\[([^\]]*)/([^\]]*)\]', r'[\1／\2]', name)
    return name


def handle_number_folder(num, entries):
    return handle_xr_folder(num, entries)


def handle_xr_folder(num, entries):
    entry = find_entry(num, entries)
    if not entry:
        print(f"  No entry found for number {num}")
        return None

    name = clean_new_name(entry)

    if re.search(r'\d{4}\.\d{2}\.\d{2} NO\.' + num + r'\b', name):
        return name

    if re.search(r'XR\d+N\d+\s+', name):
        name = re.sub(r'XR\d+N\d+\s+', '', name)
        name = re.sub(r'(\d{4}\.\d{2}\.\d{2})', rf'\1 NO.{num}', name)
        return clean_new_name(name)

    return name


def derive_name(name, entries, dates_map):
    # Handle BEAUTYLEG folder format variations
    bl_match = re.match(
        r'^\[?(?:BeautyLeg|Be)(?:\s*美腿\s*(?:写真|寫真))?\]?(?:\s*美腿\s*(?:写真|寫真))?\s*(\d{4}\.\d{2}\.\d{2})\s*((?:No|NO)\.\d+)\s*(.*)$',
        name,
        re.IGNORECASE
    )
    if bl_match:
        date = bl_match.group(1)
        num_str = bl_match.group(2)
        rest = bl_match.group(3).strip()
        print(f"  BeautyLeg folder detected (with date): {name}")
        
        if rest:
            rest = re.sub(r'\[([^\]]*)/([^\]]*)\]', r'[\1／\2]', rest)
            return f"[BEAUTYLEG美腿写真] {date} {num_str} {rest}"
        return f"[BEAUTYLEG美腿写真] {date} {num_str}"

    # Handle BEAUTYLEG folder format variations (WITHOUT a date string)
    bl_nodate_match = re.match(
        r'^\[?(?:BeautyLeg|Be)(?:\s*美腿\s*(?:写真|寫真))?\]?(?:\s*美腿\s*(?:写真|寫真))?\s*((?:No|NO)\.(\d+))\s*(.*)$',
        name,
        re.IGNORECASE
    )
    if bl_nodate_match:
        num_str = bl_nodate_match.group(1)
        num = bl_nodate_match.group(2)
        rest = bl_nodate_match.group(3).strip()
        print(f"  BeautyLeg folder detected (missing date): {name}")
        
        raw_num_key = str(int(num))
        if raw_num_key in dates_map:
            date = dates_map[raw_num_key]
            if rest:
                rest = re.sub(r'\[([^\]]*)/([^\]]*)\]', r'[\1／\2]', rest)
                return f"[BEAUTYLEG美腿写真] {date} {num_str} {rest}"
            return f"[BEAUTYLEG美腿写真] {date} {num_str}"
        else:
            print(f"  Skipping: No date mapping found for issue No.{num} in dates.txt")
            return None

    if name.isdigit():
        print(f"  Pure number: {name}")
        return handle_number_folder(name, entries)

    if re.match(r'XR\d+$', name, re.IGNORECASE):
        num = re.match(r'XR(\d+)$', name, re.IGNORECASE).group(1)
        print(f"  XR format: {name} -> number {num}")
        return handle_xr_folder(num, entries)

    if re.match(r'\[(?:Xiuren|XiuRen|XIUREN)秀人网\]', name):
        print(f"  Tagged folder: {name}")
        new_name = clean_new_name(name)
        new_name = re.sub(r'\[Xiuren秀人网\]XR\d+N\d+\s+', '[Xiuren秀人网]', new_name)
        return new_name

    print(f"  Unknown format, skipping: {name}")
    return None


def derive_video_name(filename, dates_map):
    base, ext = os.path.splitext(filename)
    
    # 1. Match when filename already contains the date explicitly
    # Captures Date, then prefixes like No, NO, N0, or HD followed by digits, and trailing text
    match = re.search(r'(\d{4}\.\d{2}\.\d{2})\s*(?:(?:No|NO|N0|HD)\.?\s*(\d+))\s*(.*)$', base, re.IGNORECASE)
    if match:
        date = match.group(1)
        num = match.group(2)
        rest = match.group(3).strip()
        
        # Standardize numbering syntax (Pads numbers under 1000 to 3 digits; e.g., 63 -> 063)
        val = int(num)
        num_str = f"{val:03d}" if val < 1000 else str(val)
        
        if rest:
            rest = re.sub(r'\[([^\]]*)/([^\]]*)\]', r'[\1／\2]', rest)
            return f"[Beautyleg] {date} No.{num_str} {rest}{ext}"
        return f"[Beautyleg] {date} No.{num_str}{ext}"

    # 2. Match when filename has NO date (e.g., "[Beautyleg] No.1629 Lucy") -> Pull from dates.txt
    nodate_match = re.search(r'(?:No|NO|N0|HD)\.?\s*(\d+)\s*(.*)$', base, re.IGNORECASE)
    if nodate_match:
        num = nodate_match.group(1)
        rest = nodate_match.group(2).strip()
        
        raw_num_key = str(int(num))
        if raw_num_key in dates_map:
            date = dates_map[raw_num_key]
            val = int(num)
            num_str = f"{val:03d}" if val < 1000 else str(val)
            
            if rest:
                rest = re.sub(r'\[([^\]]*)/([^\]]*)\]', r'[\1／\2]', rest)
                return f"[Beautyleg] {date} No.{num_str} {rest}{ext}"
            return f"[Beautyleg] {date} No.{num_str}{ext}"
            
    return None


def main():
    parser = argparse.ArgumentParser(description="Rename photo collection directories and video assets.")
    parser.add_argument("path", nargs="?", default=os.getcwd(), help="Target operating path directory")
    parser.add_argument("-v", "--videos", action="store_true", help="Process and rename video files instead of directories")
    args = parser.parse_args()

    folder = os.path.abspath(args.path)
    entries = load_list()
    dates_map = load_dates_map()
    
    if not entries:
        print(f"Warning: {LIST_FILE} is empty or not found")
    if not dates_map:
        print(f"Warning: {DATES_FILE} is empty or not found")

    # Filter items depending on directory vs video mode selection
    if args.videos:
        items = sorted(
            f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f)) and os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
        )
        mode_label = "video file(s)"
    else:
        items = sorted(
            f for f in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, f)) and not f.startswith(".") and f != "Output"
        )
        mode_label = "folder(s)"

    if not items:
        print(f"No matchable {mode_label} found.")
        return

    print(f"Found {len(items)} {mode_label}\n")
    renamed = 0
    
    for name in items:
        src = os.path.join(folder, name)
        
        if args.videos:
            new_name = derive_video_name(name, dates_map)
        else:
            new_name = derive_name(name, entries, dates_map)
            
        if new_name is None or new_name == name:
            continue
            
        dst = os.path.join(folder, new_name)
        if os.path.exists(dst):
            print(f"  Target already exists, skipping: {new_name}\n")
            continue
            
        os.rename(src, dst)
        print(f"  Renamed: {name}\n      -> {new_name}\n")
        renamed += 1

    print(f"Done: {renamed}/{len(items)} renamed")


if __name__ == "__main__":
    main()