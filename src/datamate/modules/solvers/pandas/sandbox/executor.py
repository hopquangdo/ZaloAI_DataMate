"""Chạy code LLM sinh với builtins giới hạn và thời hạn cứng.

Code chỉ được dùng các tên có sẵn trong namespace (T, pd, np, P, …). Bảng được sao chép
ở ``toolkit.build_namespace`` để code không sửa được dữ liệu gốc.
"""

from __future__ import annotations

import builtins
import sys
import threading
import time
import traceback
from collections.abc import Mapping
from typing import Any

from datamate.modules.solvers.pandas.sandbox.errors import ExecutionFailed, Unanswerable
from datamate.modules.solvers.pandas.sandbox.policy import check_code

DEFAULT_TIMEOUT_SECONDS = 30.0

_FILENAME = "<answer>"
_MAX_TRACEBACK_CHARS = 2500
_IMPORTABLE_ROOTS = {"pandas", "numpy", "datetime", "math", "dateutil", "pytz", "decimal"}
_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float",
    "frozenset", "int", "isinstance", "len", "list", "map", "max", "min", "print",
    "range", "repr", "reversed", "round", "set", "sorted", "str", "sum", "tuple",
    "type", "zip", "ValueError", "KeyError", "IndexError", "TypeError", "Exception",
    "ZeroDivisionError", "StopIteration", "True", "False", "None",
)  # fmt: skip


class _DeadlineExceeded(BaseException):
    """Code chạy quá thời hạn; được ném từ hàm trace vào đúng dòng đang chạy."""


def run_code(
    code: str, namespace: Mapping[str, Any], timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> Any:
    """Chạy code (tối đa ``timeout`` giây) và trả về giá trị biến ``answer``."""
    check_code(code)
    scope: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS, **namespace}
    try:
        _exec_with_deadline(compile(code, _FILENAME, "exec"), scope, timeout)
    except (Unanswerable, ExecutionFailed):
        raise
    except Exception as error:
        raise ExecutionFailed(_short_traceback(error)) from error
    if "answer" not in scope:
        raise ExecutionFailed("code chạy xong nhưng không gán `answer`")
    return scope["answer"]


def _exec_with_deadline(compiled: Any, scope: dict[str, Any], timeout: float) -> None:
    """Chạy trong luồng riêng. Hàm trace chỉ theo dõi các dòng của code LLM (``<answer>``) và
    ném ``_DeadlineExceeded`` khi quá hạn, nên vòng lặp Python vô hạn bị dừng hẳn. Một lệnh
    pandas/numpy dài ở tầng C thì không ngắt được: luồng bị bỏ lại (daemon), lượt này lỗi."""
    deadline = time.monotonic() + timeout
    failure: list[BaseException] = []

    def local_trace(frame: Any, event: str, arg: Any) -> Any:
        if time.monotonic() > deadline:
            raise _DeadlineExceeded
        return local_trace

    def global_trace(frame: Any, event: str, arg: Any) -> Any:
        return local_trace if frame.f_code.co_filename == _FILENAME else None

    def target() -> None:
        sys.settrace(global_trace)
        try:
            exec(compiled, scope)
        except BaseException as error:
            failure.append(error)  # chuyển lại cho luồng gọi xử lý
        finally:
            sys.settrace(None)

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout + 2)
    message = (
        f"code chạy quá {timeout:g} giây; hãy viết cách tính nhanh hơn (tránh vòng lặp từng dòng)"
    )
    if worker.is_alive():
        raise ExecutionFailed(message)
    if failure:
        error = failure[0]
        if isinstance(error, _DeadlineExceeded):
            raise ExecutionFailed(message)
        if not isinstance(error, Exception):
            raise ExecutionFailed(type(error).__name__)
        raise error


def _short_traceback(error: BaseException) -> str:
    frames = traceback.extract_tb(error.__traceback__)
    user_lines = [f"  dòng {f.lineno}: {f.line}" for f in frames if f.filename == _FILENAME]
    message = "\n".join([*user_lines, f"{type(error).__name__}: {error}"])
    return message[-_MAX_TRACEBACK_CHARS:]


def _loaded_module_only(name: str, *args: Any, **kwargs: Any) -> Any:
    """pandas/numpy đôi khi import nội bộ khi chạy; chỉ trả module đã nạp, không nạp mới.

    Lệnh ``import`` của chính code LLM đã bị AST chặn ở ``check_code``.
    """
    root = name.partition(".")[0]
    if name not in sys.modules or root not in _IMPORTABLE_ROOTS:
        raise ImportError(f"không được import {name}")
    return sys.modules[root if not kwargs.get("fromlist") and not args[2:3] else name]


_SAFE_BUILTINS: dict[str, Any] = {
    name: getattr(builtins, name) for name in _SAFE_BUILTIN_NAMES if hasattr(builtins, name)
}
_SAFE_BUILTINS["__import__"] = _loaded_module_only
