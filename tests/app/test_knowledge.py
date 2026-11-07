from pathlib import Path

import pytest

from datamate.app.knowledge import load_knowledge

TRAIN = Path("dataset/train/train")


def test_missing_files_are_reported_by_name(tmp_path):
    with pytest.raises(FileNotFoundError, match=r"rulebook.md"):
        load_knowledge(tmp_path)


@pytest.mark.skipif(not TRAIN.exists(), reason="chưa có dataset")
def test_loads_train_knowledge():
    knowledge = load_knowledge(TRAIN)
    assert "doanh thu" in knowledge.rulebook.lower()
    assert knowledge.lunar.table["lunar_year"].notna().all()
