import subprocess

from click.testing import CliRunner

from acrux.cli import cli
from acrux.config import AcruxConfig
from acrux.git_ingest import CommitFile, classify_commit, ingest_git
from acrux.memory.episodic import EpisodicStore
from acrux.memory.semantic import SemanticStore


def _git(repo, *args, output=False):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip() if output else ""


def _commit(repo, path, content, subject):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", subject)


def test_error_handling_in_new_feature_module_is_feature():
    files = [
        CommitFile(
            path="src/retry.py",
            diff="+def retry():\n+    try:\n+        pass\n+    except Exception:\n+        raise\n",
            added_module=True,
            added_exports=True,
            modifies_existing_functions=False,
        )
    ]

    assert classify_commit("Add retry module", files)[0] == "feature"
    existing_fix = CommitFile(
        path="src/retry.py",
        diff="+    except Exception:\n+        raise\n",
        added_module=False,
        added_exports=False,
        modifies_existing_functions=True,
    )
    assert classify_commit("Handle failures", [existing_fix])[0] == "fix"
    docs = CommitFile(path="docs/fix.md", diff="+fix guide\n")
    assert classify_commit("fix: clarify behavior", [docs])[0] == "docs"


def _history_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _commit(repo, "src/app.py", "def run():\n    return 1\n", "initial implementation")
    _commit(repo, "docs/usage.md", "fix usage docs\n", "fix: usage documentation")
    _commit(repo, "tests/test_app.py", "def test_run():\n    assert True\n", "add tests")
    _commit(
        repo,
        "src/app.py",
        "def run():\n    try:\n        return 1\n    except Exception:\n        raise\n",
        "fix: handle errors",
    )
    _git(repo, "mv", "src/app.py", "src/core.py")
    _git(repo, "commit", "-m", "refactor: rename app module")
    _commit(repo, "src/retry.py", "def retry():\n    return 2\n", "add retry feature")
    _commit(repo, "pyproject.toml", "[build-system]\n", "chore: update build")
    _git(repo, "checkout", "-b", "topic")
    _commit(repo, "topic.txt", "topic\n", "add topic")
    _git(repo, "checkout", "main")
    _commit(repo, "main.txt", "main\n", "add main")
    _git(repo, "merge", "--no-ff", "topic", "-m", "merge: topic")
    _git(repo, "commit", "--allow-empty", "-m", "chore: empty commit")
    return repo


def test_ingest_is_idempotent_and_never_calls_llm(tmp_path):
    repo = _history_repo(tmp_path)

    class ForbiddenEmbedder:
        dim = None

        async def embed(self, text):
            raise AssertionError("LLM/embedder call forbidden")

    semantic = SemanticStore(tmp_path / "semantic.db", embedder=ForbiddenEmbedder())
    episodic = EpisodicStore(tmp_path / "episodes.db")

    first = ingest_git(repo, "test", semantic, episodic)
    episode_count = episodic.count("test")
    change_count = len(semantic.list_code_changes("test", limit=1000))
    second = ingest_git(repo, "test", semantic, episodic)

    assert first["commits"] == 11
    assert second["commits"] == 11
    assert second["imported"] == 0
    assert episodic.count("test") == episode_count
    assert len(semantic.list_code_changes("test", limit=1000)) == change_count
    classifications = {
        episode.context["classification"]
        for episode in episodic.list_episodes("test", limit=100)
    }
    assert classifications == {"feature", "fix", "refactor", "docs", "test", "chore"}
    assert all("@" not in (episode.context.get("repository", "")) for episode in episodic.list_episodes("test", limit=100))


def test_ingest_git_cli(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _commit(repo, "README.md", "hello\n", "docs: initial")
    config = AcruxConfig(data_dir=tmp_path / "data")
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: config))

    result = CliRunner().invoke(cli, ["ingest-git", str(repo), "--project", "test"])

    assert result.exit_code == 0, result.output
    assert EpisodicStore(config.projects_dir / "test" / "episodes.db").count("test") == 1
