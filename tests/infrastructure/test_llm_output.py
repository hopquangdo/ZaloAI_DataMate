from datamate.infrastructure.llm_output import extract_code


def test_takes_last_closed_block() -> None:
    text = "```python\nanswer = 1\n```\nsửa lại:\n```python\nanswer = 2\n```"
    assert extract_code(text) == "answer = 2"


def test_block_without_language_tag() -> None:
    assert extract_code("```\nanswer = 3\n```") == "answer = 3"


def test_unclosed_block_is_recovered() -> None:
    assert extract_code("```python\nanswer = 4") == "answer = 4"


def test_bare_assignment_without_fence() -> None:
    assert extract_code("answer = 5") == "answer = 5"


def test_no_code_is_falsy() -> None:
    assert extract_code("Xin lỗi, tôi không biết.") is None
    assert not extract_code(
        "```python\n```"
    )  # khối rỗng trả "", node generate coi là không có code
