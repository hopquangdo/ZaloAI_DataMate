import numpy as np
import pandas as pd
import pytest

from datamate.modules.solvers.pandas.sandbox import (
    CodeRejected,
    ExecutionFailed,
    Unanswerable,
    run_code,
)
from datamate.modules.solvers.pandas.toolkit import unanswerable


@pytest.mark.parametrize(
    "code",
    [
        "import os\nanswer = 1",
        "answer = open('x').read()",
        "answer = T.__class__",
        "x = 1",
        "answer = df.to_csv('x')",
    ],
)
def test_rejects_unsafe_or_incomplete_code(code: str) -> None:
    with pytest.raises(CodeRejected):
        run_code(code, {})


@pytest.mark.parametrize(
    "code",
    [
        "answer = pd.read_json('x')",
        "answer = pd.read_pickle('x')",
        "answer = pd.read_excel('x')",
        "pd.DataFrame().to_json('x')\nanswer = 1",
        "pd.DataFrame().to_pickle('x')\nanswer = 1",
        "answer = np.load('x')",
        "answer = np.fromfile('x')",
        "np.save('x', np.zeros(1))\nanswer = 1",
        "answer = pd.io",
    ],
)
def test_rejects_file_io_beyond_read_csv_and_to_csv(code: str) -> None:
    with pytest.raises(CodeRejected):
        run_code(code, {"pd": pd, "np": np})


def test_data_conversions_are_still_allowed() -> None:
    code = (
        "frame = pd.DataFrame({'a': [1, 2]})\n"
        "answer = int(pd.to_numeric('3')) + len(frame['a'].to_list()) + int(frame.to_numpy().sum())"
    )
    assert run_code(code, {"pd": pd}) == 3 + 2 + 3


def test_runs_code_and_reports_errors() -> None:
    namespace = {"T": {"t": pd.DataFrame({"x": [1, 2]})}}
    assert run_code("answer = int(T['t']['x'].sum())", namespace) == 3
    with pytest.raises(ExecutionFailed, match="KeyError"):
        run_code("answer = T['missing']", namespace)


def test_unanswerable_signal_passes_through() -> None:
    with pytest.raises(Unanswerable):
        run_code(
            "unanswerable('không có cột địa chỉ')\nanswer = None", {"unanswerable": unanswerable}
        )


def test_infinite_loop_is_stopped_by_timeout() -> None:
    with pytest.raises(ExecutionFailed, match="quá"):
        run_code("while True:\n    pass\nanswer = {}", {}, timeout=0.3)


def test_code_cannot_swallow_timeout() -> None:
    code = "try:\n    while True:\n        pass\nexcept Exception:\n    pass\nanswer = {}"
    with pytest.raises(ExecutionFailed, match="quá"):
        run_code(code, {}, timeout=0.3)
