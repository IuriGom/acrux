import json
from pathlib import Path

import pytest

from acrux.backup import BackupError, BackupService
from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.memory.journal import MutationJournal
from acrux.models import Episode


def _service(tmp_path):
    data_dir = tmp_path / "data"
    episodic = EpisodicStore(data_dir / "projects" / "demo" / "episodes.db")
    episodic.add(Episode(session_id="original", task="original", project="demo"))
    MutationJournal(data_dir / "projects" / "demo")
    return BackupService(data_dir, tmp_path / "backups"), episodic


def test_backup_restore_round_trip_and_safety(tmp_path):
    service, episodic = _service(tmp_path)
    (service.data_dir.parent / "config.yaml").write_text("api_token: never-back-up\n")

    manifest = service.create()
    episodic.add(Episode(session_id="later", task="later", project="demo"))

    result = service.restore(manifest.id)

    assert result.safety_backup_id != manifest.id
    assert episodic.get_by_id("original") is not None
    assert episodic.get_by_id("later") is None
    payload_text = "\n".join(path.read_text(errors="ignore") for path in (tmp_path / "backups" / manifest.id).rglob("*") if path.is_file())
    assert "never-back-up" not in payload_text
    safety = service.get(result.safety_backup_id)
    assert safety is not None
    assert any(info.id == result.safety_backup_id and info.valid for info in service.list())


def test_failed_replacement_rolls_back_to_safety_backup(tmp_path, monkeypatch):
    service, episodic = _service(tmp_path)
    manifest = service.create()
    episodic.add(Episode(session_id="later", task="later", project="demo"))
    replace = service._replace_payload
    calls = 0

    def fail_after_replace(staging, data):
        nonlocal calls
        calls += 1
        replace(staging, data)
        if calls == 1:
            raise BackupError("simulated replacement failure")

    monkeypatch.setattr(service, "_replace_payload", fail_after_replace)
    with pytest.raises(BackupError, match="simulated"):
        service.restore(manifest.id)

    assert episodic.get_by_id("later") is not None
    assert episodic.get_by_id("original") is not None


def test_restore_rejects_checksum_mismatch(tmp_path):
    service, episodic = _service(tmp_path)
    manifest = service.create()
    payload = tmp_path / "backups" / manifest.id / "projects" / "demo" / "episodes.db"
    payload.write_bytes(b"corrupted")

    with pytest.raises(BackupError):
        service.restore(manifest.id)
    assert episodic.get_by_id("original") is not None


def test_restore_rejects_traversal_and_symlinks_before_mutation(tmp_path):
    service, episodic = _service(tmp_path)
    manifest = service.create()
    backup_dir = tmp_path / "backups" / manifest.id
    manifest_path = backup_dir / "manifest.json"
    data = json.loads(manifest_path.read_text())
    original = episodic.get_by_id("original")

    data["files"][0]["path"] = "../escape.db"
    manifest_path.write_text(json.dumps(data))
    with pytest.raises(BackupError):
        service.restore(manifest.id)
    assert episodic.get_by_id("original").to_dict() == original.to_dict()

    data["files"][0]["path"] = "projects/demo/episodes.db"
    manifest_path.write_text(json.dumps(data))
    payload = backup_dir / "projects" / "demo" / "episodes.db"
    payload.unlink()
    payload.symlink_to(tmp_path / "outside.db")
    with pytest.raises(BackupError):
        service.restore(manifest.id)
    assert episodic.get_by_id("original").to_dict() == original.to_dict()


def test_backup_dir_defaults_outside_data_dir():
    config = AcruxConfig()
    assert config.backup_dir == Path.home() / ".acrux" / "backups"
    assert config.data_dir not in config.backup_dir.parents
