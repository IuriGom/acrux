"""Tests for the SQLite procedural memory store."""

from pathlib import Path

from acrux.memory.procedural_db import ProceduralDBStore
from acrux.models import Skill


def test_add_get_all(tmp_path: Path) -> None:
    store = ProceduralDBStore(tmp_path / "skills.db")
    skill = Skill(project="test", name="test_skill", preconditions=["a"], procedure=["one", "two"])
    store.add(skill)
    skills = store.get_all("test")
    assert len(skills) == 1
    assert skills[0].name == "test_skill"
    assert skills[0].procedure == ["one", "two"]


def test_search_and_update(tmp_path: Path) -> None:
    store = ProceduralDBStore(tmp_path / "skills.db")
    skill = Skill(project="test", name="fix_bug", preconditions=["rust"], procedure=["read", "fix"])
    store.add(skill)
    results = store.search("test", "rust fix")
    assert results and results[0].name == "fix_bug"
    skill.verified = True
    store.update(skill)
    assert store.get_by_id(skill.id).verified is True


def test_delete_and_count(tmp_path: Path) -> None:
    store = ProceduralDBStore(tmp_path / "skills.db")
    skill = Skill(project="test", name="delete_me")
    store.add(skill)
    assert store.count("test") == 1
    assert store.delete_by_id(skill.id) is True
    assert store.count("test") == 0


def test_pending_queue(tmp_path: Path) -> None:
    store = ProceduralDBStore(tmp_path / "skills.db")
    skill = Skill(project="test", name="pending_skill")
    store.add_pending(skill)
    pending = store.list_pending("test")
    assert len(pending) == 1
    assert store.promote_pending(skill.id) is True
    assert store.list_pending("test") == []
    assert store.get_all("test")[0].name == "pending_skill"


def test_yaml_migration(tmp_path: Path) -> None:
    import yaml

    yaml_path = tmp_path / "skills.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            [
                {
                    "id": "mig1",
                    "project": "test",
                    "name": "migrated",
                    "preconditions": [],
                    "procedure": ["step"],
                    "evidence": [],
                    "success_rate": 0.0,
                    "verified": False,
                    "tags": [],
                    "timestamp": "2026-01-01T00:00:00",
                }
            ]
        )
    )
    store = ProceduralDBStore(tmp_path / "skills.db")
    skills = store.get_all("test")
    assert any(s.name == "migrated" for s in skills)
