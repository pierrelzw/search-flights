"""Tests for argument parsing and mode detection."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import subprocess

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "search_flights.py")


def run_script(args, expect_error=False):
    """Run the script with --help or invalid args to test parsing (no API calls)."""
    result = subprocess.run(
        [sys.executable, SCRIPT] + args,
        capture_output=True, text=True,
    )
    if expect_error:
        assert result.returncode != 0
    return result


class TestArgParsing:
    def test_help(self):
        result = run_script(["--help"])
        assert result.returncode == 0
        assert "origin" in result.stdout
        assert "--one-way" in result.stdout

    def test_missing_mode_args(self):
        """No date args should produce an error."""
        result = run_script(["YVR", "PEK"], expect_error=True)
        assert "specify either" in result.stderr.lower() or result.returncode != 0

    def test_oneway_requires_depart(self):
        """--one-way without --depart should fail."""
        result = run_script(["YVR", "PEK", "--one-way"], expect_error=True)
        assert result.returncode != 0
