SHELL := /bin/bash

REMOTE ?= upstream
BRANCH ?= merge/$(shell date +%Y-%m)

.PHONY: check-links
check-links:
	python3 check_dead_links.py --concurrent 30 --timeout 15

.PHONY: check-links-retry
check-links-retry:
	python3 check_dead_links.py --concurrent 30 --timeout 15 --retry

.PHONY: graveyard
graveyard:
	python3 check_dead_links.py --concurrent 30 --timeout 15 --retry 2>&1 | tee /tmp/graveyard.txt
	@echo "Check /tmp/graveyard.txt for new dead links to add to graveyard.md"

.PHONY: merge-upstream
merge-upstream:
	git fetch $(REMOTE)
	git checkout -b $(BRANCH) $(REMOTE)/main
	python3 merge_all_prs.py

.PHONY: ci
ci:
	python3 check_dead_links.py --concurrent 20 --timeout 10

.PHONY: status
status:
	@git log --oneline -10
	@echo "---"
	@git diff --stat main..HEAD
