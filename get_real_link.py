import sys
import requests
import pyperclip
from urllib.parse import urljoin

# ANSI color codes for terminal output
class Colors:
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'

def get_real_download_link(url: str):
    try:
        # Send a HEAD request without automatically following redirects
        response = requests.head(url, allow_redirects=False, timeout=10)

        # Check if the status code indicates a redirect (3xx)
        if 300 <= response.status_code < 400:
            # Extract the redirected URL
            real_link = response.headers.get('Location')
            
            # Ensure the link is absolute (just in case the server returns a relative path)
            if real_link:
                real_link = urljoin(url, real_link)
            
            print(f"{Colors.GREEN}Real Download Link:{Colors.RESET}")
            print(real_link)
            
            # Copy to clipboard
            try:
                pyperclip.copy(real_link)
                print(f"{Colors.CYAN}[✓] Link successfully copied to clipboard!{Colors.RESET}")
            except pyperclip.PyperclipException:
                print(f"{Colors.YELLOW}[!] Could not copy to clipboard. Ensure 'xclip' or 'xsel' is installed.{Colors.RESET}")

        else:
            print(f"{Colors.YELLOW}No redirect found. The provided link might already be the direct link:{Colors.RESET}")
            print(url)
            
            # Copy the original link to clipboard anyway
            try:
                pyperclip.copy(url)
                print(f"{Colors.CYAN}[✓] Link successfully copied to clipboard!{Colors.RESET}")
            except pyperclip.PyperclipException:
                print(f"{Colors.YELLOW}[!] Could not copy to clipboard. Ensure 'xclip' or 'xsel' is installed.{Colors.RESET}")

    except requests.RequestException as e:
        print(f"{Colors.RED}Failed to resolve URL. Error: {e}{Colors.RESET}", file=sys.stderr)

if __name__ == "__main__":
    # Example usage or interactive prompt
    print("--- Real Link Extractor ---")
    test_url = input("Enter the URL: ").strip()
    
    if test_url:
        get_real_download_link(test_url)