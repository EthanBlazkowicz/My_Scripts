#!/usr/bin/env python3
import os
import sys
import re
from pathlib import Path

LIST_FILE = os.path.expanduser("~/Downloads/the_list.txt")
DATES_FILE = os.path.expanduser("~/Downloads/dates.txt")


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
            # Matches strings like "2020.03.06 No.1891"
            match = re.match(r'(\d{4}\.\d{2}\.\d{2})\s+(?:No|NO)\.(\d+)', line, re.IGNORECASE)
            if match:
                date, num = match.groups()
                dates_map[num] = date
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
    # Replace regular slash with full-width slash inside brackets (macOS compat)
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

    # If it already has NO.{num} after the date, it's already in target format
    if re.search(r'\d{4}\.\d{2}\.\d{2} NO\.' + num + r'\b', name):
        return name

    # If it has XR code, remove it and insert NO.{num} after date
    if re.search(r'XR\d+N\d+\s+', name):
        name = re.sub(r'XR\d+N\d+\s+', '', name)
        name = re.sub(r'(\d{4}\.\d{2}\.\d{2})', rf'\1 NO.{num}', name)
        return clean_new_name(name)

    # Otherwise just return the cleaned entry
    return name


def derive_name(name, entries, dates_map):
    # 1. Handle BEAUTYLEG format variations (with an existing date string)
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

    # 2. Handle BEAUTYLEG format variations (WITHOUT a date string - requires lookup)
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
        
        # Resolve date via scraped mapping index
        if num in dates_map:
            date = dates_map[num]
            if rest:
                rest = re.sub(r'\[([^\]]*)/([^\]]*)\]', r'[\1／\2]', rest)
                return f"[BEAUTYLEG美腿写真] {date} {num_str} {rest}"
            return f"[BEAUTYLEG美腿写真] {date} {num_str}"
        else:
            print(f"  Skipping: No date mapping found for issue No.{num} in dates.txt")
            return None

    # Fallback to existing Xiuren logic if not a BeautyLeg format
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
        # Remove XR code prefix if present
        new_name = re.sub(r'\[Xiuren秀人网\]XR\d+N\d+\s+', '[Xiuren秀人网]', new_name)
        return new_name

    print(f"  Unknown format, skipping: {name}")
    return None


def main():
    folder = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    entries = load_list()
    dates_map = load_dates_map()
    
    if not entries:
        print(f"Warning: {LIST_FILE} is empty or not found")
    if not dates_map:
        print(f"Warning: {DATES_FILE} is empty or not found")

    folders = sorted(
        f for f in os.listdir(folder)
        if os.path.isdir(os.path.join(folder, f)) and not f.startswith(".") and f != "Output"
    )

    if not folders:
        print("No subdirectories found.")
        return

    print(f"Found {len(folders)} folder(s)\n")
    renamed = 0
    for name in folders:
        src = os.path.join(folder, name)
        new_name = derive_name(name, entries, dates_map)
        if new_name is None or new_name == name:
            print()
            continue
        dst = os.path.join(folder, new_name)
        if os.path.exists(dst):
            print(f"  Target already exists, skipping: {new_name}\n")
            continue
        os.rename(src, dst)
        print(f"  Renamed: {name}\n      -> {new_name}\n")
        renamed += 1

    print(f"Done: {renamed}/{len(folders)} renamed")


if __name__ == "__main__":
    main()