import subprocess
import sys

from click.testing import CliRunner

from acrux.cli import cli
from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.memory.semantic import SemanticStore
from acrux.models import CodeChange


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_code_changes_upsert_is_idempotent(tmp_path):
    store = SemanticStore(tmp_path / "semantic.db", embedder=None)
    change = CodeChange(
        project="test",
        session_id="session-1",
        commit_sha="abc123",
        file_path="src/example.py",
        change_type="modify",
        diff="+new line\n",
        source="git-ingest",
        content_hash="hash-1",
    )

    first_id = store.add_code_change(change)
    second_id = store.add_code_change(change)

    assert first_id == second_id
    assert len(store.list_code_changes("test")) == 1
    assert store.list_code_changes("test", session_id="session-1")[0].diff == "+new line\n"
    assert store.list_code_changes("test", commit_sha="abc123")[0].file_path == "src/example.py"
    assert store.list_code_changes("test", file_path="src/example.py")[0].content_hash == "hash-1"


def test_wrap_links_only_command_delta_to_episode(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "tracked.txt").write_text("base\n")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    (repo / "tracked.txt").write_text("base\npreexisting\n")

    config = AcruxConfig(data_dir=tmp_path / "data")
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: config))
    monkeypatch.chdir(repo)
    command = (
        "from pathlib import Path; "
        "p = Path('tracked.txt'); p.write_text(p.read_text() + 'command\\n')"
    )
    result = CliRunner().invoke(
        cli,
        ["wrap", "--project", "test", "--", sys.executable, "-c", command],
    )

    assert result.exit_code == 0, result.output
    episode = EpisodicStore(config.projects_dir / "test" / "episodes.db").get_recent(
        "test", limit=1
    )[0]
    semantic = SemanticStore(config.projects_dir / "test" / "semantic.db", embedder=None)
    changes = semantic.list_code_changes("test", session_id=episode.session_id)
    assert len(changes) == 1
    assert changes[0].file_path == "tracked.txt"
    assert "command" in changes[0].diff
    assert "preexisting" not in changes[0].diff
