from datamate.modules.understanding.examples import load_examples, parse_example, render_examples


def test_every_example_has_both_solvers() -> None:
    examples = load_examples()
    assert len(examples) >= 5
    for example in examples:
        assert example.description
        assert set(example.solutions) == {"pandas", "sql"}, example.name


def test_each_solver_gets_its_own_language_and_the_canonical_tables() -> None:
    sql, pandas = render_examples("sql"), render_examples("pandas")
    assert "```sql" in sql and "```python" not in sql
    assert "```python" in pandas and "```sql" not in pandas
    assert 'FROM "don_chuan"' in sql and 'T["don_chuan"]' in pandas


def test_examples_are_identical_for_every_question() -> None:
    assert render_examples("sql") == render_examples("sql")
    assert render_examples("khong_co") == ""


def test_parse_example_reads_description_and_both_solutions() -> None:
    text = "mô tả: mẫu\n\n## pandas\n```python\nx = 1\n```\n\n## sql\n```sql\nSELECT 1\n```\n"
    example = parse_example("demo", text)
    assert example.description == "mẫu"
    assert set(example.solutions) == {"pandas", "sql"}
