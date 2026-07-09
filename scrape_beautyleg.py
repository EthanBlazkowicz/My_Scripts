import re
import urllib.request
import time

BASE_URL = "https://en.taotu.org/publisher/Beautyleg/page-{}.html"
MIN_NO = 1601
MAX_NO = 1891
OUTPUT_FILE = "beautyleg_1891_1601.txt"

h2_pattern = re.compile(
    r"<h2>\[Beautyleg\].*?(\d{4}\.\d{2}\.\d{2}).*?No\.(\d+).*?</h2>"
)

results = []

for page_num in range(79, 66, -1):
    url = BASE_URL.format(page_num)
    print(f"Fetching page {page_num}...")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Error fetching page {page_num}: {e}")
        continue

    for match in h2_pattern.finditer(html):
        date = match.group(1)
        no = int(match.group(2))
        if MIN_NO <= no <= MAX_NO:
            results.append((no, date))

    time.sleep(1)

results.sort(key=lambda x: x[0], reverse=True)

with open(OUTPUT_FILE, "w") as f:
    for no, date in results:
        f.write(f"{date} No.{no}\n")

print(f"Done. {len(results)} entries written to {OUTPUT_FILE}")
