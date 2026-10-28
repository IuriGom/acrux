import subprocess
from pathlib import Path

from acrux.provenance import WorktreeSnapshot


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "tracked.txt").write_text("base\n")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    return repo


def test_dirty_baseline_excludes_preexisting_changes(tmp_path):
    repo = _repo(tmp_path)
    (repo / "tracked.txt").write_text("base\npreexisting\n")
    (repo / "old-untracked.txt").write_text("old\n")
    snapshot = WorktreeSnapshot.capture(repo, "test", "session-1")

    (repo / "tracked.txt").write_text("base\npreexisting\ncommand\n")
    (repo / "new.txt").write_text("new\n")
    changes = snapshot.changes_since()

    by_path = {change.file_path: change for change in changes}
    assert set(by_path) == {"tracked.txt", "new.txt"}
    assert "command" in by_path["tracked.txt"].diff
    assert "preexisting" not in by_path["tracked.txt"].diff
    assert "base" not in by_path["tracked.txt"].diff
    assert by_path["new.txt"].change_type == "add"
    assert by_path["new.txt"].session_id == "session-1"


def test_binary_secret_and_symlink_paths(tmp_path):
    repo = _repo(tmp_path)
    snapshot = WorktreeSnapshot.capture(repo, "test", "session-2")

    (repo / "image.bin").write_bytes(b"\x00\x01\x02")
    (repo / ".env").write_text("SECRET=do-not-read\n")
    (repo / "id_rsa").write_text("private-key\n")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n")
    (repo / "escape.txt").symlink_to(outside)
    changes = snapshot.changes_since()

    assert len(changes) == 1
    assert changes[0].file_path == "image.bin"
    assert changes[0].change_type == "binary"
    assert "Binary" in changes[0].diff
    assert "SECRET" not in changes[0].diff


def test_per_file_and_session_diff_limits(tmp_path):
    repo = _repo(tmp_path)
    snapshot = WorktreeSnapshot.capture(repo, "test", "session-3")

    for index in range(12):
        (repo / f"large-{index}.txt").write_text(f"{index}\n" + ("x" * 40000))
    changes = snapshot.changes_since()

    assert len(changes) == 12
    assert all(len(change.diff.encode("utf-8")) <= 32768 for change in changes)
    assert sum(len(change.diff.encode("utf-8")) for change in changes) <= 262144
    assert any(change.truncated for change in changes)
