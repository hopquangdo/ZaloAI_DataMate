from pathlib import Path

import pytest

from datamate.modules.data.ingestion import cache, get_business


@pytest.fixture(autouse=True)
def _clean_memory_cache():
    cache._memory.clear()
    yield
    cache._memory.clear()


def _write_business(root: Path) -> Path:
    directory = root / "biz_1"
    directory.mkdir()
    (directory / "README.md").write_text("mô tả", encoding="utf-8")
    (directory / "don_hang.csv").write_text("ma,gia\nA1,100\nA2,200\n", encoding="utf-8")
    return directory


def test_loaded_once_per_process(tmp_path: Path) -> None:
    directory = _write_business(tmp_path)
    first = get_business(directory, None)
    assert get_business(directory, None) is first
    assert first.tables["don_hang"]["gia"].tolist() == [100.0, 200.0]


def test_disk_cache_is_reused_across_processes(tmp_path: Path) -> None:
    directory, cache_dir = _write_business(tmp_path), tmp_path / "cache"
    first = get_business(directory, cache_dir)
    assert len(list(cache_dir.glob("*.pkl"))) == 1

    cache._memory.clear()  # giả lập tiến trình mới
    second = get_business(directory, cache_dir)
    assert second is not first
    assert second.tables["don_hang"].equals(first.tables["don_hang"])
    assert len(list(cache_dir.glob("*.pkl"))) == 1


def test_changed_data_invalidates_disk_cache(tmp_path: Path) -> None:
    directory, cache_dir = _write_business(tmp_path), tmp_path / "cache"
    get_business(directory, cache_dir)
    (directory / "don_hang.csv").write_text("ma,gia\nA1,100\nA2,200\nA3,300\n", encoding="utf-8")

    cache._memory.clear()
    business = get_business(directory, cache_dir)
    assert len(business.tables["don_hang"]) == 3
    assert len(list(cache_dir.glob("*.pkl"))) == 2


def test_version_follows_ingestion_source() -> None:
    assert len(cache.ingestion_version()) == 8
