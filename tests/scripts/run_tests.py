#!/usr/bin/env python3
"""
Simple wrapper to run the comprehensive test runner.

Usage examples:
- Run all tiers:          python tests/scripts/run_tests.py
- Run only Tier 1 and 3:  python tests/scripts/run_tests.py -t 1 -t 3
- Stop on first failure:  python tests/scripts/run_tests.py --stop
"""
from __future__ import annotations

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main(argv: list[str]) -> int:
    runner = HERE / "comprehensive_test_runner.py"
    return __import__("runpy").run_path(str(runner), run_name="__main__").get("_exitcode", 0) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
