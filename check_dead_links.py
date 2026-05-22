#!/usr/bin/env python3
"""Check for dead links in README.md.

Usage:
    python3 check_dead_links.py                  # check all links
    python3 check_dead_links.py --concurrent 20  # 20 concurrent checks (default)
    python3 check_dead_links.py --timeout 10     # 10s timeout per request (default)
"""

import re
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

REPO = Path(__file__).parent
README = REPO / "README.md"

LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

def extract_links(text, source_file="README.md"):
    links = []
    for i, line in enumerate(text.split("\n"), 1):
        for match in LINK_RE.finditer(line):
            url = match.group(2)
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https"):
                links.append((i, url.strip(), match.group(1)))
    return links

def check_url(url, timeout=10):
    result = {"url": url, "status": None, "error": None}
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (compatible; LinkChecker)"})
        result["status"] = resp.status_code
        if resp.status_code >= 400:
            result["error"] = f"HTTP {resp.status_code}"
    except requests.ConnectionError:
        result["error"] = "Connection failed"
    except requests.Timeout:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)
    return result

def main():
    parser = argparse.ArgumentParser(description="Check for dead links in README.md")
    parser.add_argument("--concurrent", type=int, default=20, help="Concurrent checks (default: 20)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    parser.add_argument("--retry", action="store_true", help="Retry failed links once")
    args = parser.parse_args()

    text = README.read_text()
    links = extract_links(text)
    print(f"Found {len(links)} links in README.md")

    dead = []
    ok = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=args.concurrent) as pool:
        fut_map = {pool.submit(check_url, url, args.timeout): (line, url, name)
                   for line, url, name in links}

        done = 0
        for fut in as_completed(fut_map):
            line, url, name = fut_map[fut]
            result = fut.result()
            done += 1

            elapsed = time.time() - start
            pct = done / len(links) * 100
            eta = (elapsed / done) * (len(links) - done) if done > 0 else 0

            status_line = f"[{done}/{len(links)}] {pct:.0f}% ETA {eta:.0f}s"

            if result["error"]:
                print(f"{status_line} DEAD  line {line:4d} {url}  ({result['error']})")
                if args.retry:
                    retry_result = check_url(url, args.timeout)
                    if not retry_result["error"]:
                        print(f"         -> Retry OK: HTTP {retry_result['status']}")
                        ok += 1
                        continue
                dead.append((line, url, name, result["error"]))
            elif result["status"] and result["status"] >= 400:
                print(f"{status_line} DEAD  line {line:4d} {url}  (HTTP {result['status']})")
                if args.retry:
                    retry_result = check_url(url, args.timeout)
                    if retry_result["status"] and retry_result["status"] < 400:
                        print(f"         -> Retry OK: HTTP {retry_result['status']}")
                        ok += 1
                        continue
                dead.append((line, url, name, f"HTTP {result['status']}"))
            else:
                ok += 1
                if done <= 3 or done % 100 == 0:
                    print(f"{status_line} OK    line {line:4d} {url}")

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Checked {len(links)} links in {elapsed:.0f}s")
    print(f"OK: {ok}, Dead: {len(dead)}")

    if dead:
        print(f"\n--- Dead Links ({len(dead)}) ---")
        for line, url, name, reason in dead:
            print(f"  line {line:4d} [{name}]({url})  ({reason})")
        sys.exit(1)

if __name__ == "__main__":
    main()
