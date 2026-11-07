import pytest

from datamate.infrastructure.prompt_loader import load_prompt, render_prompt


def test_render_keeps_other_braces_and_does_not_rescan_values():
    text = render_prompt("repair", feedback="lỗi {toolkit} {x}")
    assert "lỗi {toolkit} {x}" in text


def test_missing_variable_raises():
    with pytest.raises(KeyError):
        render_prompt("repair")


def test_system_and_user_prompts_fill_everything():
    system = render_prompt("system", toolkit=load_prompt("toolkit"), rulebook="RULE {1}")
    assert "RULE {1}" in system
    assert '{"type": <kiểu>, "answer": <giá trị>}' in system
    assert "{toolkit}" not in system
    user = render_prompt(
        "user",
        business_id="biz_1",
        readme="readme",
        tables="T",
        question="Q?",
        as_of_date="2026-03-04",
        hints="",
    )
    assert "biz_1" in user and "Q?" in user and "2026-03-04" in user
    assert "```python```" in render_prompt("repair", feedback="x")
