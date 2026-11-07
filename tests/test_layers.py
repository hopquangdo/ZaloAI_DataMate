"""Khoá chiều phụ thuộc giữa các tầng: chỉ được import tầng thấp hơn hoặc cùng tầng.

    core ← infrastructure ← domain ← data ← understanding ← solvers ← decision ← app

Thêm vào đó: các bộ giải trong ``solvers`` độc lập, không import lẫn nhau.
Kiểm tra bằng AST nên bắt được cả import nằm trong hàm.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "datamate"
ORDER = ["core", "infrastructure", "domain", "data", "understanding", "solvers", "decision", "app"]


def _layer(parts: list[str]) -> str | None:
    """Tầng của một module theo tên dạng ['datamate', ...]."""
    if len(parts) > 2 and parts[1] == "modules":
        return parts[2]
    return parts[1] if len(parts) > 1 else None


def _module_parts(path: Path) -> list[str]:
    parts = ["datamate", *path.relative_to(SRC).with_suffix("").parts]
    return parts[:-1] if parts[-1] == "__init__" else parts


def _imports(path: Path) -> list[list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[list[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias.name.split(".") for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append(node.module.split("."))
    return [parts for parts in found if parts[0] == "datamate"]


FILES = sorted(SRC.rglob("*.py"))


def test_every_layer_exists():
    present = {p.name for p in SRC.iterdir() if p.is_dir()} | {
        p.name for p in (SRC / "modules").iterdir() if p.is_dir()
    }
    assert set(ORDER) <= present


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(SRC)))
def test_imports_only_go_down(path: Path):
    source = _module_parts(path)
    source_layer = _layer(source)
    if source_layer not in ORDER:
        return
    problems = []
    for target in _imports(path):
        target_layer = _layer(target)
        if target_layer not in ORDER:
            continue
        if ORDER.index(target_layer) > ORDER.index(source_layer):
            problems.append(f"{'.'.join(target)} (tầng {target_layer} > {source_layer})")
        is_solver = source_layer == target_layer == "solvers"
        if is_solver and len(source) > 3 and len(target) > 3 and source[3] != target[3]:
            problems.append(f"{'.'.join(target)} (hai bộ giải không được import nhau)")
    assert not problems, "import ngược tầng:\n  " + "\n  ".join(problems)
