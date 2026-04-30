import os
import re
import argparse
import urllib.parse
import difflib
import sys
import json

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Error: Missing required library. {e}")
    print("Please install the required libraries by running:")
    print("pip install requests beautifulsoup4")
    sys.exit(1)

def split_camel_case(s):
    # Splits CamelCase but keeps things like Vol.5 or 3D intact if possible
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    return s

def parse_filename(filename):
    """
    Extracts the search query, resolution, and extension from a filename.
    Returns (query, resolution, ext, skip_search) or (None, None, None, False) if no renaming is needed.
    """
    base_name, ext = os.path.splitext(filename)
    if ext.lower() not in ['.mp4', '.mkv', '.avi', '.wmv', '.mov']:
        return None, None, None, False

    # Extract resolution
    res_match = re.search(r'[\s_]*\(?(\d{3,4}p|4k)\)?', base_name, re.IGNORECASE)
    resolution = res_match.group(1) if res_match else ""

    if resolution:
        base_name = re.sub(r'[\s_]*\(?' + resolution + r'\)?', '', base_name, flags=re.IGNORECASE)

    # Remove tags like [Clips4sale.com]
    base_name = re.sub(r'\[.*?\]', '', base_name)
    
    # Remove dates like YYYY.MM.DD or YYYY-MM-DD
    base_name = re.sub(r'\b\d{4}[.-]\d{2}[.-]\d{2}\b', '', base_name)

    # Convert dot-separated names to spaces (if it looks like a scene release with no spaces)
    if ' ' not in base_name.strip() and '.' in base_name:
        base_name = base_name.replace('.', ' ')

    # Remove trailing duplicate numbers like (1)
    base_name = re.sub(r'\s*\(\d+\)$', '', base_name)
    
    # Clean trailing underscores or dashes
    base_name = base_name.strip('_- ')

    # Remove dot after leading number (e.g. "175. Sex..." -> "175 Sex...")
    base_name = re.sub(r'^(\d+)\.\s+', r'\1 ', base_name)

    # Replace multiple spaces with a single space
    base_name = re.sub(r'\s+', ' ', base_name).strip()

    # Check if already in the target format: purely digits followed by space and text
    if re.match(r'^\d+\s+[a-zA-Z0-9\s\'\-]+$', base_name, re.IGNORECASE):
        # We don't need to search, but we might need to apply the resolution
        return base_name, resolution, ext, True

    base_name = base_name.replace("''", "'")

    # If it has a pattern like 597@... or 734教...
    match = re.match(r'^(\d+)[@\u4e00-\u9fff]', base_name)
    if match:
        return match.group(1).strip(), resolution, ext, False

    # For names like 'Model Mashup - Angel-Desert (MyDirtyHobby) Remix Vol.5'
    # we want to extract everything from the first parenthesis if it exists and has stuff after it
    if '(' in base_name and ')' in base_name:
        m = re.search(r'\((.*?)\)(.*)', base_name)
        if m:
            base_name = m.group(1) + m.group(2)

    # Split by '-' 
    parts = re.split(r'\s*-\s*', base_name)
    parts = [p for p in parts if p]
    if len(parts) > 1:
        base_name = parts[-1]

    # Split CamelCase
    base_name = split_camel_case(base_name)

    # Strip leading punctuation like !! or !
    base_name = re.sub(r'^[^a-zA-Z0-9]+', '', base_name)
    
    # Strip trailing numbers that might be isolated
    base_name = re.sub(r'\s+\d+$', '', base_name)

    query = base_name.strip()
    # Replace multiple spaces with single space again just in case
    query = re.sub(r'\s+', ' ', query)
    
    return query, resolution, ext, False

def get_search_results(query, base_search_url):
    # Extract studio name from the URL if possible to make the web search more accurate
    m = re.search(r'/studio/\d+/([^/]+)', base_search_url)
    studio = m.group(1).replace('-', ' ') if m else "angel the dreamgirl"
    
    search_query = f"{query} {studio} clips4sale"
    
    results = []
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        data = {'q': search_query}
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for a in soup.find_all('a', class_='result__url'):
            title_el = a.find_parent('div', class_='result__body')
            if title_el:
                title_h2 = title_el.find('h2', class_='result__title')
                if title_h2:
                    title = title_h2.text.strip()
                    
                    # Clean up the title a bit by removing the studio suffix and 'Clips4sale' if present
                    title = re.sub(r'\s*[-|]\s*' + re.escape(studio) + r'.*', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'\s*[-|]\s*Clips4sale.*', '', title, flags=re.IGNORECASE)
                    title = title.strip()
                    
                    if title and title not in results:
                        results.append(title)
        return results
    except Exception as e:
        print(f"Error during web search: {e}")
        return []

def choose_best_match(query, results):
    # Only consider results that start with a number (the C4S clip ID)
    valid_results = [r for r in results if re.match(r'^\d+', r)]
    if not valid_results:
        return None
        
    query_lower = query.lower()
    
    # Find results where query is a direct substring
    substring_matches = [r for r in valid_results if query_lower in r.lower()]
    if substring_matches:
        # Return the shortest match to avoid matching an overly long combination title
        return min(substring_matches, key=len)
        
    # If no substring match, use difflib
    best_match = None
    highest_ratio = 0
    for r in valid_results:
        # compare with the title without the leading number (and optional dot)
        title_no_num = re.sub(r'^\d+\.?\s+', '', r)
        ratio = difflib.SequenceMatcher(None, query_lower, title_no_num.lower()).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = r
            
    if highest_ratio > 0.7:  # Lowered slightly to account for DuckDuckGo's "c**" censorship
        return best_match
        
    return None

def main():
    parser = argparse.ArgumentParser(description="Rename video files based on Clips4Sale search results.")
    parser.add_argument('--dir', type=str, help="Directory containing the video files")
    parser.add_argument('--url', type=str, help="Base search URL")
    parser.add_argument('--dry-run', action='store_true', help="Run without actually renaming files")
    
    args = parser.parse_args()
    
    config_file = os.path.expanduser('~/.rename_c4s_config.json')
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except Exception:
            pass

    default_dir = config.get('last_dir', '')
    directory = args.dir
    if not directory:
        prompt = f"Enter the directory containing the video files [{default_dir}]: " if default_dir else "Enter the directory containing the video files: "
        directory = input(prompt).strip()
        if not directory:
            directory = default_dir
            
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return

    default_url = config.get('last_url', "https://www.clips4sale.com/studio/68591/angel-the-dreamgirl/Cat0-AllCategories/Page1/C4SSort-added_at/Limit24/search")
    base_url = args.url
    if not base_url:
        base_url = input(f"Enter the base search URL [{default_url}]: ").strip()
        if not base_url:
            base_url = default_url

    base_url = base_url.rstrip('/')

    config['last_dir'] = os.path.abspath(directory)
    config['last_url'] = base_url
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Warning: Could not save configuration to {config_file}: {e}")

    print(f"\nScanning directory: {directory}")
    if args.dry_run:
        print("=== DRY RUN MODE: No files will be modified ===")

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue

        query, resolution, ext, skip_search = parse_filename(filename)
        if not query:
            continue

        print(f"\nProcessing: '{filename}'")
        
        if skip_search:
            print(f"  -> Format already matches. Skipping search.")
            best_match = query
        else:
            print(f"  Extracted Query: '{query}'")
            results = get_search_results(query, base_url)
            
            # Match results
            best_match = choose_best_match(query, results)
            
            if not best_match:
                print(f"  -> No confident match found. Skipping.")
                continue
                
            # Extract the leading number from the matched title
            m = re.match(r'^(\d+)', best_match)
            if m:
                clip_number = m.group(1)
                # Instead of using the search engine's title (which might be censored like 'c**'),
                # we just prepend the clip number to our extracted clean query.
                best_match = f"{clip_number} {query}"
            else:
                best_match = query

            print(f"  Matched Title: '{best_match}'")
        
        # Construct new filename
        new_name = best_match
        if resolution:
            new_name += f" {resolution}"
        new_name += ext
        
        # Clean invalid characters for filesystem
        new_name = re.sub(r'[\\/*?:"<>|]', "", new_name)
        
        if filename == new_name:
            print(f"  -> Name is already correct. Skipping.")
            continue
            
        new_filepath = os.path.join(directory, new_name)
        
        while os.path.exists(new_filepath):
            new_name = "0Duplicate " + new_name
            new_filepath = os.path.join(directory, new_name)
            
        print(f"  -> Renaming to: '{new_name}'")
        if not args.dry_run:
            try:
                os.rename(filepath, new_filepath)
                print(f"  -> Successfully renamed.")
            except Exception as e:
                print(f"  -> Error renaming: {e}")

if __name__ == "__main__":
    main()
