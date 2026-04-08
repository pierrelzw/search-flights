#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Creating Python virtual environment..."
python3 -m venv .venv

echo "Installing dependencies..."
.venv/bin/pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "To use this skill in Claude Code, symlink it:"
echo "  ln -s $(pwd) ~/.claude/skills/search-flights"
