import shutil
import sqlite3

import pytest
from click.testing import CliRunner

import acrux.backup as backup_module
from acrux.backup import BackupService
from acrux.cli import cli
from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.memory.journal import MutationBatch
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Episode, Fact, Skill
from acrux.undo import UndoCoordinator
from acrux.utils import PidFile


def test_same_name_skill_upsert_undo_restores_original(tmp_path):
    store = ProceduralDBStore(tmp_path / "skills.db")
    original = Skill(id="old", project="demo", name="same", procedure=["old"])
    store.add(original)
    replacement = Skill(id="new", project="demo", name="same", procedure=["new"])
    with MutationBatch(tmp_path, "skill.add") as batch:
        store.add(replacement, batch_id=batch.id)

    UndoCoordinator(tmp_path).undo(batch.id)

    assert store.get_by_id("old").procedure == ["old"]
    assert store.get_by_id("new") is None


def test_undo_retry_after_mark_failure_is_idempotent(tmp_path, monkeypatch):
    store = EpisodicStore(tmp_path / "episodes.db")
    with MutationBatch(tmp_path, "episode.add") as batch:
        store.add(Episode(session_id="one", task="one", project="demo"), batch_id=batch.id)
    journal = batch.journal
    original_mark = journal.mark_undone
    monkeypatch.setattr(journal, "mark_undone", lambda batch_id: (_ for _ in ()).throw(RuntimeError("crash")))
    coordinator = UndoCoordinator(tmp_path)
    coordinator.journal = journal
    with pytest.raises(RuntimeError, match="crash"):
        coordinator.undo(batch.id)
    assert store.get_by_id("one") is None

    monkeypatch.setattr(journal, "mark_undone", original_mark)
    result = coordinator.undo(batch.id)
    assert result.restored_entries == 1
    assert journal.get(batch.id).undone is True


def test_backup_rejects_symlinked_parent(tmp_path):
    service, _ = _backup_service(tmp_path)
    manifest = service.create()
    backup_dir = manifest.path
    actual = backup_dir / "projects" / "demo"
    external = tmp_path / "external"
    shutil.copytree(actual, external)
    shutil.rmtree(actual)
    actual.symlink_to(external, target_is_directory=True)

    with pytest.raises(Exception):
        service.restore(manifest.id)


def test_wrap_redacts_command_and_task(tmp_path, monkeypatch):
    config = AcruxConfig(data_dir=tmp_path / "data")
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: config))
    secret = "supersecret"
    result = CliRunner().invoke(cli, ["wrap", "--project", "demo", "--", "/bin/echo", f"api_token={secret}"])

    assert result.exit_code == 0
    episode = EpisodicStore(config.projects_dir / "demo" / "episodes.db").get_recent("demo", limit=1)[0]
    assert secret not in episode.task
    assert secret not in episode.actions[0].command
    assert episode.actions[0].stdout == "api_token=[REDACTED]\n"


@pytest.mark.asyncio
async def test_recall_changes_do_not_conflict_or_roll_back(tmp_path):
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    fact = Fact(project="demo", content="before content")
    with MutationBatch(tmp_path, "fact.add") as first:
        await store.add(fact, batch_id=first.id)
    with MutationBatch(tmp_path, "fact.update") as second:
        await store.update_fact(fact.id, content="after content", batch_id=second.id)
    await store.search("demo", "after", limit=1)

    UndoCoordinator(tmp_path).undo(second.id)

    restored = store.get_by_id(fact.id)
    assert restored.content == "before content"
    assert restored.recall_count >= 1
    assert restored.last_recalled_at is not None


def test_backup_excludes_metrics_and_health(tmp_path):
    service, _ = _backup_service(tmp_path)
    semantic_path = service.data_dir / "projects" / "demo" / "semantic.db"
    SemanticStore(semantic_path, embedder=None)._ensure_metrics_table()
    with sqlite3.connect(semantic_path) as conn:
        conn.execute("INSERT INTO metrics (project, metric, value, timestamp) VALUES ('demo', 'm', 1, 'now')")
        conn.execute("INSERT INTO health_checks (project, check_type, severity, message, created_at) VALUES ('demo', 'check', 'info', 'message', 'now')")
        conn.commit()

    manifest = service.create()

    with sqlite3.connect(manifest.path / "projects" / "demo" / "semantic.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM health_checks").fetchone()[0] == 0


def test_restore_removes_later_databases(tmp_path):
    service, _ = _backup_service(tmp_path)
    manifest = service.create()
    later = EpisodicStore(service.data_dir / "projects" / "later" / "episodes.db")
    later.add(Episode(session_id="later", task="later", project="later"))

    service.restore(manifest.id)

    assert not (service.data_dir / "projects" / "later" / "episodes.db").exists()


def test_backup_holds_one_lock_per_project(tmp_path, monkeypatch):
    service, _ = _backup_service(tmp_path)
    calls = []
    real_lock = backup_module.project_write_lock

    class RecordingLock:
        def __init__(self, project_dir):
            self.project_dir = project_dir
            self.lock = real_lock(project_dir)

        def __enter__(self):
            calls.append(("enter", self.project_dir))
            return self.lock.__enter__()

        def __exit__(self, *args):
            calls.append(("exit", self.project_dir))
            return self.lock.__exit__(*args)

    monkeypatch.setattr(backup_module, "project_write_lock", RecordingLock)
    service.create()

    assert [call for call in calls if call[0] == "enter"] == [("enter", service.data_dir / "projects" / "demo")]


def _backup_service(tmp_path):
    data_dir = tmp_path / "data"
    episodic = EpisodicStore(data_dir / "projects" / "demo" / "episodes.db")
    episodic.add(Episode(session_id="original", task="original", project="demo"))
    SemanticStore(data_dir / "projects" / "demo" / "semantic.db", embedder=None)
    return BackupService(data_dir, tmp_path / "backups"), episodic
