"""Tests for the sqlite-vec vector index."""

from pathlib import Path

import pytest

from acrux.vector_sqlite import SqliteVecIndex, SQLITE_VEC_AVAILABLE


@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec not installed")
def test_add_search_remove(tmp_path: Path) -> None:
    idx = SqliteVecIndex(tmp_path / "test.vec", dim=3, enabled=True)
    idx.add(1, [1.0, 0.0, 0.0])
    idx.add(2, [0.0, 1.0, 0.0])
    idx.add(3, [0.9, 0.1, 0.0])
    results = idx.search([1.0, 0.0, 0.0], k=3)
    assert results[0][0] == 1
    assert results[1][0] == 3  # closest second
    idx.remove(1)
    results = idx.search([1.0, 0.0, 0.0], k=3)
    assert results[0][0] == 3


@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec not installed")
def test_filter_ids(tmp_path: Path) -> None:
    idx = SqliteVecIndex(tmp_path / "test.vec", dim=2, enabled=True)
    idx.add(1, [1.0, 0.0])
    idx.add(2, [0.9, 0.1])
    idx.add(3, [0.0, 1.0])
    results = idx.search([1.0, 0.0], k=3, filter_ids={2, 3})
    ids = [r[0] for r in results]
    assert 1 not in ids
    assert set(ids) == {2, 3}
