#!/usr/bin/env python3
"""Merge all upstream PRs into a new branch, then deduplicate README.md entries."""

import subprocess
import re
import os
import sys
from pathlib import Path

REPO = Path("/Users/charley/gits/awesome-ai-tools")
os.chdir(REPO)

def run(cmd, check=True, capture=True):
    result = subprocess.run(cmd, capture_output=capture, text=True, cwd=REPO)
    if check and result.returncode != 0:
        print(f"FAILED: {' '.join(cmd)}")
        print(result.stdout)
        print(result.stderr)
        if capture:
            return result
    return result

# Step 1: Create a new branch from upstream/main
print("=== Creating merge-all branch ===")
run(["git", "checkout", "-b", "merge-all-prs", "upstream/main"], check=False)

# Step 2: Configure union merge driver for README.md
print("=== Setting up union merge driver for README.md ===")
run(["git", "config", "merge.union.driver", "true"])
Path(".gitattributes").write_text("README.md merge=union\n")

# Step 3: Get all PR refs sorted numerically
print("=== Collecting PR refs ===")
result = run(["git", "branch", "-a"])
pr_refs = []
for line in result.stdout.split("\n"):
    line = line.strip().replace("remotes/", "")
    if "upstream/pr/" in line:
        pr_refs.append(line)

def sort_key(ref):
    try:
        return int(ref.split("/")[-1])
    except ValueError:
        return 0

pr_refs.sort(key=sort_key)
print(f"Found {len(pr_refs)} PRs. Starting merge...")

# Step 4: Merge each PR
success = 0
failed = 0
skipped_no_diff = 0

for i, ref in enumerate(pr_refs):
    pr_num = ref.split("/")[-1]
    if (i + 1) % 100 == 0:
        print(f"Progress: {i+1}/{len(pr_refs)} (success: {success}, failed: {failed}, skipped: {skipped_no_diff})")

    diff_check = run(["git", "diff", "--quiet", f"upstream/main...{ref}"], check=False, capture=False)
    if diff_check.returncode == 0:
        skipped_no_diff += 1
        continue

    result = run(["git", "merge", "--no-edit", ref], check=False)
    if result.returncode == 0:
        success += 1
    else:
        status = run(["git", "status", "--porcelain"])
        has_other_conflicts = False
        for line in status.stdout.split("\n"):
            if line.startswith("UU ") and "README.md" not in line:
                has_other_conflicts = True
                break

        if has_other_conflicts:
            print(f"PR #{pr_num}: Non-README conflict, aborting merge")
            run(["git", "merge", "--abort"], check=False)
            failed += 1
        else:
            readme_status = run(["git", "status", "--porcelain", "README.md"])
            if "UU" in readme_status.stdout:
                print(f"PR #{pr_num}: Resolving README.md conflict manually")
                content = Path("README.md").read_text()
                content = re.sub(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> .*?\n',
                                 r'\1\2', content, flags=re.DOTALL)
                Path("README.md").write_text(content)
                run(["git", "add", "README.md"])

            remaining = run(["git", "diff", "--cached", "--name-only", "--diff-filter=U"], check=False)
            if remaining.stdout.strip():
                print(f"PR #{pr_num}: Other staged conflicts remain, aborting")
                run(["git", "merge", "--abort"], check=False)
                failed += 1
            else:
                run(["git", "commit", "--no-edit"], check=False)
                success += 1

print(f"\n=== Merge complete: {success} merged, {failed} failed, {skipped_no_diff} skipped ===")

# Step 5: Deduplicate entries
print("\n=== Deduplicating README.md entries ===")
content = Path("README.md").read_text()

lines = content.split("\n")
seen_links = set()
deduped_lines = []
dup_count = 0

for line in lines:
    match = re.match(r'^-\s*\[([^\]]+)\]\(([^)]+)\)', line)
    if match:
        url = match.group(2).rstrip("/")
        if url in seen_links:
            dup_count += 1
            continue
        seen_links.add(url)
    deduped_lines.append(line)

Path("README.md").write_text("\n".join(deduped_lines))
print(f"Removed {dup_count} duplicate entries")

# Step 6: Commit dedup
run(["git", "add", "README.md", ".gitattributes"])
run(["git", "commit", "-m", "Merge all upstream PRs and deduplicate entries"], check=False)

print("\n=== Done! Branch 'merge-all-prs' is ready ===")
