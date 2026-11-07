"""Bộ giải SQL: LLM viết câu SELECT chạy chỉ đọc trên DuckDB. Xem ../README.md."""

from datamate.modules.solvers.sql.engine import SqlEngine, check_sql
from datamate.modules.solvers.sql.functions import FUNCTIONS_DOC
from datamate.modules.solvers.sql.graph import build_sql_graph

__all__ = ["FUNCTIONS_DOC", "SqlEngine", "build_sql_graph", "check_sql"]
