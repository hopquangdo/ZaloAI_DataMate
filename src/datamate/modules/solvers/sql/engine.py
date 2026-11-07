"""Engine SQL cho vòng lặp LLM: LLM viết một câu SELECT, chạy chỉ đọc trên DuckDB trong bộ nhớ.

Hợp đồng với LLM (xem assets/prompts/sql_system.md):
- một khối ```sql```; dòng đầu là ``-- type: <kiểu đáp án>``;
- dữ liệu không đủ để trả lời → chỉ một dòng ``-- unanswerable: <lý do>``.
Kết quả: 1 ô cho number/percent/string/date/boolean; cột đầu cho list; cả bảng cho table.
"""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from typing import Any

import duckdb
import pandas as pd

from datamate.infrastructure.llm_loop import AttemptError
from datamate.modules.domain.answer import Answer, AnswerType, FormatError, coerce_answer
from datamate.modules.solvers.sql.functions import register_functions

DEFAULT_TIMEOUT_SECONDS = 30.0
# rào mở phải ở đầu dòng, để dấu đóng của một khối khác không bị hiểu là mở khối mới
_SQL_BLOCK = re.compile(r"^```[ \t]*sql[ \t]*\n(.*?)^```", re.S | re.M | re.I)
_PLAIN_BLOCK = re.compile(r"^```[ \t]*\n(.*?)^```", re.S | re.M)
_TYPE = re.compile(r"^\s*--\s*type\s*:\s*(\w+)", re.I | re.M)
_UNANSWERABLE = re.compile(r"^\s*--\s*unanswerable\s*:\s*(.+)$", re.I | re.M)
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|create|drop|alter|attach|detach|copy|export|import|install|load|"
    r"pragma|set|call|read_\w+|glob|httpfs|system)\b",
    re.I,
)
_SCALAR_TYPES = {"number", "percent", "string", "date", "boolean"}


_PANDAS_TABLE = re.compile(r"""T\[\s*(["'])(.+?)\1\s*\](?:\[\s*(["'])(.+?)\3\s*\])?""")


def rewrite_pandas_refs(sql: str) -> str:
    """Model hay chép cách ghi của mô tả bảng: T["B"] → "B", T["B"]["Cột"] → "B"."Cột"."""

    def repl(match: re.Match[str]) -> str:
        table, column = match.group(2), match.group(4)
        return f'"{table}"."{column}"' if column else f'"{table}"'

    return _PANDAS_TABLE.sub(repl, sql)


def _strip_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines()).strip()


def check_sql(sql: str) -> None:
    """Chỉ cho một câu SELECT / WITH, không lệnh ghi hay đọc file."""
    body = _strip_comments(sql).rstrip(";").strip()
    if not body:
        raise AttemptError("Khối ```sql``` không có câu truy vấn.")
    if ";" in body:
        raise AttemptError("Chỉ được viết MỘT câu truy vấn (không có ';' ở giữa).")
    if not re.match(r"^(select|with)\b", body, re.I):
        raise AttemptError("Câu truy vấn phải bắt đầu bằng SELECT hoặc WITH.")
    match = _FORBIDDEN.search(body)
    if match:
        raise AttemptError(f"Không được dùng '{match.group(0)}' (chỉ đọc dữ liệu đã nạp).")


def _value(answer_type: str, frame: pd.DataFrame) -> Any:
    if answer_type in _SCALAR_TYPES:
        if frame.shape != (1, 1):
            raise AttemptError(
                f"Kiểu {answer_type} cần đúng 1 dòng × 1 cột, truy vấn trả {frame.shape[0]} dòng × "
                f"{frame.shape[1]} cột."
            )
        return frame.iat[0, 0]
    if answer_type == "list":
        if frame.shape[1] != 1:
            raise AttemptError(f"Kiểu list cần đúng 1 cột, truy vấn trả {frame.shape[1]} cột.")
        return frame.iloc[:, 0].tolist()
    if answer_type == "table":
        return {"columns": [str(c) for c in frame.columns], "rows": frame.values.tolist()}
    raise AttemptError(f"Kiểu '{answer_type}' không hợp lệ.")


class SqlEngine:
    language = "sql"

    def __init__(
        self,
        tables_factory: Callable[[], dict[str, pd.DataFrame]],
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._tables_factory = tables_factory
        self._timeout = timeout

    def extract(self, reply: str) -> str | None:
        blocks = _SQL_BLOCK.findall(reply) or _PLAIN_BLOCK.findall(reply)
        if blocks:
            return str(blocks[-1]).strip() or None
        if _UNANSWERABLE.search(reply) or re.search(r"^\s*(select|with)\b", reply, re.I | re.M):
            return reply.strip()
        return None

    def run(self, code: str) -> Answer:
        unanswerable = _UNANSWERABLE.search(code)
        if unanswerable and not _strip_comments(code):
            return Answer.unanswerable(unanswerable.group(1).strip())
        type_match = _TYPE.search(code)
        if type_match is None:
            raise AttemptError("Thiếu dòng đầu `-- type: <kiểu>` (number, percent, string, ...).")
        answer_type = type_match.group(1).lower()
        if answer_type not in {t.value for t in AnswerType} - {"abstain", "unanswerable"}:
            raise AttemptError(f"Kiểu '{answer_type}' không hợp lệ.")
        code = rewrite_pandas_refs(code)
        check_sql(code)
        frame = self._query(_strip_comments(code).rstrip(";"))
        try:
            return coerce_answer({"type": answer_type, "answer": _value(answer_type, frame)})
        except FormatError as error:
            raise AttemptError(f"FormatError: {error}") from error

    def _query(self, sql: str) -> pd.DataFrame:
        connection = duckdb.connect(":memory:")
        timer = threading.Timer(self._timeout, connection.interrupt)
        try:
            for name, table in self._tables_factory().items():
                connection.register(name, table)
            register_functions(connection)
            timer.start()
            return connection.execute(sql).df()
        except duckdb.InterruptException as error:
            raise AttemptError(f"Truy vấn chạy quá {self._timeout:.0f} giây.") from error
        except duckdb.Error as error:
            raise AttemptError(f"{type(error).__name__}: {str(error)[:600]}") from error
        finally:
            timer.cancel()
            connection.close()

    def describe(self, candidate: Answer) -> dict[str, Any]:
        return candidate.to_json()
