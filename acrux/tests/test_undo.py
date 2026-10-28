import sqlite3

import pytest
from click.testing import CliRunner

from acrux.cli import cli
from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.memory.journal import MutationBatch, MutationJournal
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Episode, Fact, Skill
from acrux.undo import UndoConflictError, UndoCoordinator, UndoError


def test_incomplete_batch_recovers_with_exact_command(tmp_path):
    journal = MutationJournal(tmp_path)
    batch_id = journal.begin("reflection")
    journal.record_before(
        batch_id,
        tmp_path / "episodes.db",
        "episodes",
        "session_id",
        "crashed",
        None,
    )
    store = EpisodicStore(tmp_path / "episodes.db")
    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "INSERT INTO episodes (session_id, task, project) VALUES (?, ?, ?)",
            ("crashed", "partial", tmp_path.name),
        )
        conn.commit()

    result = UndoCoordinator(tmp_path).undo(batch_id)

    assert result.restored_entries == 1
    assert store.get_by_id("crashed") is None
    assert journal.incomplete() == []
    with MutationBatch(tmp_path, "next"):
            pass


@pytest.mark.asyncio
async def test_multi_store_undo_restores_rows_fts_vectors_and_pending(tmp_path):
    project = tmp_path.name
    episodic = EpisodicStore(tmp_path / "episodes.db")
    procedural = ProceduralDBStore(tmp_path / "skills.db")
    semantic = SemanticStore(tmp_path / "semantic.db", embedder=None)
    original = Episode(session_id="original", task="restore me", project=project)
    episodic.add(original)

    with MutationBatch(tmp_path, "reflection") as batch:
        episodic.delete_by_id("original", batch_id=batch.id)
        episodic.add(
            Episode(session_id="new", task="new episode", project=project),
            batch_id=batch.id,
        )
        procedural.add_pending(
            Skill(project=project, name="pending", procedure=["one", "two"]),
            batch_id=batch.id,
        )
        semantic.add_pending_fact(
            Fact(project=project, content="pending fact"),
            batch_id=batch.id,
        )
        await semantic.add(
            Fact(project=project, content="vector and FTS fact"),
            batch_id=batch.id,
        )

    UndoCoordinator(tmp_path).undo(last=True)

    assert episodic.get_by_id("original").task == "restore me"
    assert episodic.get_by_id("new") is None
    assert episodic.search_fts(project, "restore")[0].session_id == "original"
    assert procedural.list_pending(project) == []
    assert semantic.list_pending_facts(project) == []
    assert semantic.search_fts(project, "vector") == []
    reopened = SemanticStore(tmp_path / "semantic.db", embedder=None)
    assert reopened.search_fts(project, "vector") == []


def test_undo_conflict_and_unknown_batch_are_atomic(tmp_path):
    project = tmp_path.name
    store = EpisodicStore(tmp_path / "episodes.db")
    with MutationBatch(tmp_path, "episode.add") as batch:
        store.add(Episode(session_id="changed", task="before", project=project), batch_id=batch.id)
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("UPDATE episodes SET task = 'later' WHERE session_id = 'changed'")
        conn.commit()

    with pytest.raises(UndoConflictError):
        UndoCoordinator(tmp_path).undo(batch.id)
    assert store.get_by_id("changed").task == "later"
    with pytest.raises(UndoError):
        UndoCoordinator(tmp_path).undo("unknown")


def test_undo_cli_requires_confirmation(tmp_path, monkeypatch):
    project = tmp_path.name
    config = AcruxConfig(data_dir=tmp_path)
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: config))
    store = EpisodicStore(tmp_path / "projects" / project / "episodes.db")
    project_dir = store.db_path.parent
    with MutationBatch(project_dir, "episode.add") as batch:
        store.add(Episode(session_id="cli", task="cli", project=project), batch_id=batch.id)

    result = CliRunner().invoke(cli, ["undo", batch.id, "--project", project], input="n\n")
    assert result.exit_code == 0
    assert store.get_by_id("cli") is not None

    result = CliRunner().invoke(cli, ["undo", batch.id, "--project", project, "--yes"])
    assert result.exit_code == 0, result.output
    assert store.get_by_id("cli") is None
