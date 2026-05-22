# Maintenance

This repo tracks upstream [mahseema/awesome-ai-tools](https://github.com/mahseema/awesome-ai-tools)
and applies curated PR merges, deduplication, and link-rot monitoring.

## Monthly Cycle

### 1. Merge upstream PRs

```bash
make merge-upstream
```

Fetches all PRs from the `upstream` remote, merges only those with a diff
against `upstream/main` (skipping no-diff and non-README-conflict PRs), then
deduplicates entries by URL. Pushes to `merge/YYYY-MM`.

If `make merge-upstream` fails on a non-README conflict, the PR is skipped.
Check `scripts/merge_all_prs.py` for details.

### 2. Check dead links

```bash
make check-links
make graveyard
```

Scans every `[text](url)` in README.md. 4xx/5xx responses and connection
failures are reported. Run with `--retry` once to filter transient failures
before updating the graveyard.

### 3. Update graveyard

```bash
make graveyard
```

Appends newly dead links to `graveyard.md` with line number, URL, and error.
Remove entries that come back alive before committing.

### 4. Cull dead entries (quarterly)

Tools dead for 2+ check cycles should be either:
- **Removed** from README and moved to graveyard permanently
- **Replaced** with an active alternative if one exists
- **Noted** with a `[†]` marker in the description

## New Tool Intake

1. Receive submission (PR, issue, or dangling file like `Untitled`)
2. Vet the tool: check link, verify description, ensure it fits a section
3. Add to the appropriate section alphabetically
4. Run `make check-links` before committing

## Before Pushing

```bash
make ci
```

Runs the check-links script (no retry) to catch broken URLs before they land.
