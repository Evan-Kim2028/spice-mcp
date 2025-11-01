#!/usr/bin/env python3
"""
Comprehensive test runner for the Dune MCP project.

Features:
- Tiered execution (Tier 1..4) with selective runs via --tier/-t
- Environment validation (expects .env with DUNE_API_KEY when required)
- Per-script timeouts and rich summary reporting
- Optional stop-on-first-failure and junit-style report export
"""
from __future__ import annotations

import argparse
import os
import sys
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent


@dataclass
class Script:
    name: str
    timeout: int = 300
    requires_api_key: bool = False


# Tiers definition (ordered)
TIERS: dict[int, list[Script]] = {
    1: [
        Script("test_api_health.py", requires_api_key=True),
        Script("test_query_lifecycle.py", requires_api_key=True),
    ],
    2: [
        Script("test_data_types.py", requires_api_key=True),
        Script("test_performance.py", requires_api_key=True, timeout=600),
    ],
    3: [
        Script("test_mcp_simulation.py"),
        Script("test_dune_connectivity.py", requires_api_key=True),
        Script("test_dune_query_execution.py", requires_api_key=True),
        Script("test_mcp_tools.py"),
    ],
    4: [
        Script("test_resilience.py", requires_api_key=True, timeout=600),
        Script("test_resource_management.py"),
        Script("test_error_handling.py", requires_api_key=True),
        Script("test_cache_functionality.py"),
    ],
}


def load_env_api_key() -> str | None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return None
    key = None
    with env_file.open() as fh:
        for line in fh:
            s = line.strip()
            if s.startswith("DUNE_API_KEY="):
                key = s.split("=", 1)[1]
                break
    return key


def run_script(script: Script, api_key: str | None) -> Tuple[bool, str]:
    script_path = SCRIPTS_DIR / script.name
    env = os.environ.copy()
    if script.requires_api_key:
        if not api_key:
            return False, f"Missing DUNE_API_KEY for {script.name}"
        env.setdefault("DUNE_API_KEY", api_key)

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=script.timeout,
            env=env,
        )
        ok = proc.returncode == 0
        out = proc.stdout + ("\nSTDERR:\n" + proc.stderr if proc.stderr else "")
        return ok, out
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {script.timeout}s"
    except Exception as e:  # pragma: no cover
        return False, f"ERROR: {e}"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dune MCP comprehensive test runner")
    p.add_argument("--tier", "-t", action="append", type=int, choices=sorted(TIERS.keys()),
                   help="Tier(s) to run. Repeatable. Default: all tiers")
    p.add_argument("--stop", "--bail", action="store_true", help="Stop on first failure")
    p.add_argument("--junit", type=Path, help="Write a minimal JUnit XML report to this path")
    return p.parse_args(list(argv))


def main(argv: Iterable[str] = tuple()) -> int:
    args = parse_args(argv)

    tiers = args.tier or sorted(TIERS.keys())
    api_key = load_env_api_key()

    all_results: list[tuple[str, bool, str]] = []
    for tier in tiers:
        print("\n" + "=" * 70)
        print(f"Running Tier {tier}")
        print("=" * 70)
        for script in TIERS[tier]:
            print(f"\n--- {script.name} ---")
            ok, output = run_script(script, api_key)
            status = "PASSED" if ok else "FAILED"
            print(output)
            print(f"[{status}] {script.name}")
            all_results.append((script.name, ok, output))
            if args.stop and not ok:
                return _finalize(all_results, args.junit)

    return _finalize(all_results, args.junit)


def _finalize(results: list[tuple[str, bool, str]], junit_path: Path | None) -> int:
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    for name, ok, _ in results:
        print(f"{'✅' if ok else '❌'} {name}")
    print(f"\nResults: {passed}/{total} passed")

    if junit_path:
        _write_junit(junit_path, results)
        print(f"JUnit report written to {junit_path}")

    return 0 if passed == total else 1


def _write_junit(path: Path, results: list[tuple[str, bool, str]]) -> None:
    # Minimal JUnit XML for CI systems
    import xml.etree.ElementTree as ET

    testsuite = ET.Element("testsuite", name="dune-mcp", tests=str(len(results)))
    for name, ok, output in results:
        case = ET.SubElement(testsuite, "testcase", name=name)
        if not ok:
            failure = ET.SubElement(case, "failure", message="failed")
            failure.text = output[-10000:]  # limit size

    tree = ET.ElementTree(testsuite)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
