from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src" / "spice_mcp"

ALLOWED_COLLECT_FILES = {
    SRC_ROOT / "polars_utils.py",
    SRC_ROOT / "adapters" / "dune" / "client.py",
}

ALLOWED_DATAFRAME_FILES = {
    SRC_ROOT / "polars_utils.py",
    SRC_ROOT / "adapters" / "dune" / "extract.py",
    SRC_ROOT / "adapters" / "dune" / "client.py",
    SRC_ROOT / "adapters" / "dune" / "cache.py",
}


def iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        yield path


def test_no_direct_collect_on_lazyframe():
    violations = []
    for path in iter_python_files(SRC_ROOT):
        if path in ALLOWED_COLLECT_FILES:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "collect":
                    violations.append((path, node.lineno))
    assert not violations, f"Disallowed LazyFrame.collect usage: {violations}"


def test_no_polars_dataframe_construction():
    violations = []
    for path in iter_python_files(SRC_ROOT):
        if path in ALLOWED_DATAFRAME_FILES:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "DataFrame":
                    violations.append((path, node.lineno))
                if isinstance(func, ast.Attribute) and func.attr.startswith("read_"):
                    violations.append((path, node.lineno))
    assert not violations, f"Disallowed eager polars usage: {violations}"
