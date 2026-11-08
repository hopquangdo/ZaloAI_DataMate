"""Luật sandbox kiểm tra trên AST trước khi chạy.

Đây là lưới chặn các sai sót thường gặp của code do LLM sinh (import, đọc/ghi file, truy cập
dunder), KHÔNG phải ranh giới bảo mật: code vẫn chạy cùng tiến trình với pandas/numpy đầy đủ
nên một danh sách cấm không thể kín. Chỉ chạy code do chính hệ thống này sinh ra.
"""

from __future__ import annotations

import ast

from datamate.modules.solvers.pandas.sandbox.errors import CodeRejected

# Module chuẩn vô hại, đã nằm sẵn trong namespace hoặc cần cho datetime/pandas khi chạy.
SAFE_IMPORT_ROOTS = frozenset(
    {"pandas", "numpy", "datetime", "math", "dateutil", "pytz", "decimal", "re", "calendar",
     "statistics", "collections", "itertools", "functools", "time", "_strptime", "locale"}
)
_FORBIDDEN_CALLS = {
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "input", "breakpoint", "exit", "quit", "help",
}  # fmt: skip

# pandas: mọi read_* / to_* đều đọc hoặc ghi dữ liệu ra ngoài, trừ các phép đổi kiểu dưới đây.
_FORBIDDEN_PREFIXES = ("read_", "to_")
_ALLOWED_CONVERSIONS = {
    "to_numpy", "to_list", "to_dict", "to_frame", "to_series", "to_records", "to_datetime",
    "to_numeric", "to_timedelta", "to_period", "to_timestamp", "to_pydatetime", "to_flat_index",
}  # fmt: skip
# numpy và các đường vào module I/O của pandas.
_FORBIDDEN_ATTRIBUTES = {
    "io", "load", "loads", "save", "savez", "savez_compressed", "savetxt", "loadtxt",
    "genfromtxt", "fromfile", "tofile", "fromregex", "memmap", "dump", "dumps", "open",
}  # fmt: skip


def check_code(code: str) -> None:
    """Ném CodeRejected nếu code vi phạm luật; không chạy code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        raise CodeRejected(f"SyntaxError dòng {error.lineno}: {error.msg}") from error
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            a.name.partition(".")[0] not in SAFE_IMPORT_ROOTS for a in node.names
        ):
            raise CodeRejected("chỉ được import module chuẩn an toàn; dùng pd, np, T, P… có sẵn")
        if isinstance(node, ast.ImportFrom) and (
            (node.module or "").partition(".")[0] not in SAFE_IMPORT_ROOTS
        ):
            raise CodeRejected("chỉ được import module chuẩn an toàn; dùng pd, np, T, P… có sẵn")
        if isinstance(node, ast.Attribute) and _is_forbidden_attribute(node.attr):
            raise CodeRejected(f"không được dùng thuộc tính .{node.attr}")
        if isinstance(node, ast.Name) and (node.id in _FORBIDDEN_CALLS or node.id.startswith("__")):
            raise CodeRejected(f"không được dùng {node.id}")
    assigns = any(
        isinstance(node, ast.Assign) and any(_assigns_answer(t) for t in node.targets)
        for node in ast.walk(tree)
    )
    gives_up = any(  # unanswerable("lý do") là cách nói "dữ liệu không đủ", không cần biến answer
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "unanswerable"
        for node in ast.walk(tree)
    )
    if not (assigns or gives_up):
        raise CodeRejected("code phải gán biến `answer`")


def _is_forbidden_attribute(name: str) -> bool:
    if name.startswith("__") or name in _FORBIDDEN_ATTRIBUTES:
        return True
    return name.startswith(_FORBIDDEN_PREFIXES) and name not in _ALLOWED_CONVERSIONS


def _assigns_answer(target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == "answer"
