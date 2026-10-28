from click.testing import CliRunner

from acrux.backup import BackupService
from acrux.cli import cli
from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.models import Episode
from acrux.utils import PidFile


def _setup(tmp_path, monkeypatch):
    config = AcruxConfig(data_dir=tmp_path / "data")
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: config))
    monkeypatch.setattr(AcruxConfig, "backup_dir", tmp_path / "backups")
    episodic = EpisodicStore(config.projects_dir / "demo" / "episodes.db")
    episodic.add(Episode(session_id="original", task="original", project="demo"))
    service = BackupService(config.data_dir, config.backup_dir)
    manifest = service.create()
    episodic.add(Episode(session_id="later", task="later", project="demo"))
    return config, episodic, manifest


def test_backup_cli_requires_confirmation_and_running_daemon_stopped(tmp_path, monkeypatch):
    config, episodic, manifest = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(PidFile, "is_running", lambda self: True)
    runner = CliRunner()

    running = runner.invoke(cli, ["backup", "restore", manifest.id, "--yes"])
    assert running.exit_code != 0
    assert episodic.get_by_id("later") is not None

    monkeypatch.setattr(PidFile, "is_running", lambda self: False)
    cancelled = runner.invoke(cli, ["backup", "restore", manifest.id], input="n\n")
    assert cancelled.exit_code == 0
    assert episodic.get_by_id("later") is not None

    restored = runner.invoke(cli, ["backup", "restore", manifest.id, "--yes"])
    assert restored.exit_code == 0, restored.output
    assert episodic.get_by_id("later") is None
    assert manifest.id in restored.output


def test_backup_create_and_list_commands(tmp_path, monkeypatch):
    config, _, manifest = _setup(tmp_path, monkeypatch)
    runner = CliRunner()

    created = runner.invoke(cli, ["backup", "create"])
    assert created.exit_code == 0, created.output
    listed = runner.invoke(cli, ["backup", "list"])
    assert listed.exit_code == 0, listed.output
    assert manifest.id in listed.output
