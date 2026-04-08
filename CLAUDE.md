# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

search-flights is a **Claude Code skill** that searches and compares flight prices using Google Flights data. Users describe travel needs in natural language (Chinese or English), Claude extracts structured parameters, the script executes searches, and Claude presents results with analysis.

## Architecture

```
SKILL.md                      # Entry point: parse user input → run script → present results
scripts/
  search_flights.py           # Core search engine (flexible/exact/one-way modes)
search_flight/
  resolve.py                  # City/airport name resolution
  format.py                   # Result formatting utilities
tests/                        # Unit tests (no API calls)
.claude-plugin/
  plugin.json                 # Plugin metadata (version, author, keywords)
```

**Search modes**: Flexible date range (Phase 1 coarse scan → Phase 2 detail), exact dates (Phase 2 only), one-way.

## Installation

**End-user** (via plugin marketplace):

```bash
claude plugin marketplace add pierrelzw/zhiwei_skills
claude plugin install search-flights@pierrelzw --scope user
```

**Developer** (local symlink for active development):

```bash
git clone https://github.com/pierrelzw/search-flights ~/codes/search-flights
cd ~/codes/search-flights && bash setup.sh
ln -s ~/codes/search-flights ~/.claude/skills/search-flights
```

> Do not use both install methods simultaneously — remove the symlink before plugin install, or vice versa.

## Publishing

Plugin metadata lives in `.claude-plugin/plugin.json`. This is the canonical version/metadata file.

**Version bump workflow**:

1. Update `version` in `.claude-plugin/plugin.json`
2. Sync the version in `~/codes/zhiwei_skills/.claude-plugin/marketplace.json` (search-flights entry)
3. Validate: `claude plugin validate .claude-plugin/plugin.json`
4. Commit and push both repos

## Key Rules

- Scripts must run with `.venv/bin/python3`, never system Python.
- If `.venv` does not exist, create it first: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- City/airport mapping is handled by the script, not by Claude — Claude only converts natural language to structured parameters.

## Testing

```bash
.venv/bin/python -m pytest tests/ -v
```

All tests are pure unit tests with no API calls.
