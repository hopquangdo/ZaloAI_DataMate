from pathlib import Path

from datamate.infrastructure.jsonl import JsonlWriter, read_jsonl


def test_missing_file_has_no_records(tmp_path: Path) -> None:
    assert list(read_jsonl(tmp_path / "none.jsonl")) == []


def test_round_trip_keeps_unicode_and_appends(tmp_path: Path) -> None:
    path = tmp_path / "out" / "run.jsonl"
    writer = JsonlWriter(path)
    writer.write({"id": "q1", "answer": "Cà phê sữa"})
    writer.close()
    again = JsonlWriter(path)
    again.write({"id": "q2", "answer": 3})
    again.close()
    assert list(read_jsonl(path)) == [
        {"id": "q1", "answer": "Cà phê sữa"},
        {"id": "q2", "answer": 3},
    ]
    assert "Cà phê sữa" in path.read_text(encoding="utf-8")  # không bị escape \uXXXX


def test_blank_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    path.write_text('{"id": 1}\n\n{"id": 2}\n', encoding="utf-8")
    assert [r["id"] for r in read_jsonl(path)] == [1, 2]
