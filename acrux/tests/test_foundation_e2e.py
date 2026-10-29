import hashlib
import subprocess
import sys

from click.testing import CliRunner

from acrux.backup import BackupService
from acrux.cli import cli
from acrux.config import AcruxConfig, ReflectionConfig
from acrux.daemon import AcruxDaemon
from acrux.memory.episodic import EpisodicStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Episode, Fact
from acrux.utils import PidFile


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_foundation_fail_fix_ingest_reflect_undo_backup_restore(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "app.py").write_text("value = 1\n")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-m", "initial")
    monkeypatch.chdir(repo)

    config = AcruxConfig(
        data_dir=tmp_path / "data",
        reflection=ReflectionConfig(provider="ollama", model="qwen3:8b"),
    )
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: config))
    monkeypatch.setattr(AcruxConfig, "backup_dir", tmp_path / "backups")
    monkeypatch.setattr(PidFile, "is_running", lambda self: False)
    runner = CliRunner()

    failed = runner.invoke(
        cli,
        ["wrap", "--project", "demo", "--", sys.executable, "-c", "import sys; print('boom', file=sys.stderr); sys.exit(9)"],
    )
    assert failed.exit_code == 9
    failed_episode = EpisodicStore(config.projects_dir / "demo" / "episodes.db").get_recent("demo", limit=1)[0]
    assert failed_episode.actions[0].exit_code == 9
    assert "boom" in failed_episode.actions[0].error_signature

    edit = "from pathlib import Path; p = Path('app.py'); p.write_text(p.read_text() + 'fixed = True\\n')"
    passed = runner.invoke(cli, ["wrap", "--project", "demo", "--", sys.executable, "-c", edit])
    assert passed.exit_code == 0, passed.output
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-m", "fix: handle failure")
    first = runner.invoke(cli, ["ingest-git", str(repo), "--project", "demo"])
    second = runner.invoke(cli, ["ingest-git", str(repo), "--project", "demo"])
    assert first.exit_code == second.exit_code == 0
    assert "imported 0" in second.output
    episodes = EpisodicStore(config.projects_dir / "demo" / "episodes.db").list_episodes("demo", limit=100)
    assert any(episode.context.get("classification") == "fix" for episode in episodes)

    reflected = []

    class AcceptanceEngine:
        def __init__(self, cfg, episodic, semantic, procedural):
            self.episodic = episodic
            self.semantic = semantic
            self.procedural = procedural
            reflected.append(episodic.db_path.parent.name)

        async def reflect_project(self, project, batch_size=10, batch_id=None):
            if batch_id is None:
                from acrux.memory.journal import MutationBatch

                with MutationBatch(self.episodic.db_path.parent, "reflection") as batch:
                    return await self.reflect_project(project, batch_size, batch.id)
            fact = Fact(project=project, content="verified recovery fact")
            self.semantic.add_pending_fact(fact, batch_id=batch_id)
            ids = [episode.session_id for episode in self.episodic.get_unreflected(project, limit=100)]
            self.episodic.mark_compacted(ids, batch_id=batch_id)
            return {"facts": 1, "skills": 0}

        async def close(self):
            return None

    monkeypatch.setattr("acrux.daemon.ReflectionEngine", AcceptanceEngine)

    async def forbidden_reverify(project):
        raise AssertionError("automatic re-verification")

    daemon = AcruxDaemon(config)
    monkeypatch.setattr(daemon, "_run_reverify", forbidden_reverify)
    import asyncio

    asyncio.run(daemon._run_reflection())
    assert reflected == ["demo"]
    semantic = SemanticStore(config.projects_dir / "demo" / "semantic.db", embedder=None)
    assert len(semantic.list_pending_facts("demo")) == 1

    from acrux.memory.journal import MutationJournal

    latest = MutationJournal(config.projects_dir / "demo").latest()
    undone = runner.invoke(cli, ["undo", "--last", "--project", "demo", "--yes"])
    assert undone.exit_code == 0, undone.output
    assert semantic.list_pending_facts("demo") == [], (undone.output, latest)
    assert EpisodicStore(config.projects_dir / "demo" / "episodes.db").count_unreflected("demo") > 0

    backup_root = tmp_path / "backups"
    service = BackupService(config.data_dir, backup_root)
    manifest = service.create()
    for file in manifest.files:
        payload = manifest.path / file["path"]
        assert hashlib.sha256(payload.read_bytes()).hexdigest() == file["sha256"]
    episodic = EpisodicStore(config.projects_dir / "demo" / "episodes.db")
    episodic.add(Episode(session_id="post-backup", task="post backup", project="demo"))
    restored = runner.invoke(cli, ["backup", "restore", manifest.id, "--yes"])
    assert restored.exit_code == 0, restored.output
    assert episodic.get_by_id("post-backup") is None
    assert "safety backup" in restored.output

    idle_config = AcruxConfig(data_dir=tmp_path / "idle-data")
    idle_store = EpisodicStore(idle_config.projects_dir / "idle" / "episodes.db")
    idle_store.add(Episode(session_id="idle", task="idle", project="idle", compacted=True))

    def forbidden_embedder():
        raise AssertionError("Ollama/embedder called for idle project")

    monkeypatch.setattr(idle_config, "create_embedder", forbidden_embedder)
    asyncio.run(AcruxDaemon(idle_config)._run_reflection())
