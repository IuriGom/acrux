import sys

from click.testing import CliRunner

from acrux.capture import cap_text, normalize_error, redact_text
from acrux.cli import cli
from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.models import Action


def test_stream_caps_preserve_utf8():
    capped, truncated = cap_text("🧠" * 5000)

    assert truncated is True
    assert len(capped.encode("utf-8")) <= 16384
    assert capped.encode("utf-8").decode("utf-8") == capped
    assert cap_text("small") == ("small", False)


def test_redaction_and_error_signature():
    text = (
        "Authorization: Bearer abcdef123456\n"
        "api_token=supersecret password: anothersecret\n"
        "https://user:pass@example.com/path\n"
        "-----BEGIN PRIVATE KEY-----\nsecret-key-material\n-----END PRIVATE KEY-----"
    )
    redacted = redact_text(text)

    for secret in ("abcdef123456", "supersecret", "anothersecret", "user:pass", "secret-key-material"):
        assert secret not in redacted
    assert "[REDACTED]" in redacted

    signature = normalize_error(
        1,
        "",
        "Traceback /Users/alice/project/test.py:123 ValueError: bad value at 0x7fabc123",
    )
    assert "ValueError" in signature
    assert "/Users" not in signature
    assert ":123" not in signature
    assert "0x7fabc123" not in signature
    assert normalize_error(0, "", "") == ""


def test_old_action_deserialization_has_neutral_capture_fields():
    action = Action.from_dict({"tool": "run_command", "result": "success"})

    assert action.exit_code is None
    assert action.stdout == ""
    assert action.stderr == ""
    assert action.error_signature == ""
    assert action.output_truncated is False


def test_wrap_preserves_exit_status_and_records_bounded_evidence(tmp_path, monkeypatch):
    config = AcruxConfig(data_dir=tmp_path / "data")
    monkeypatch.setattr(AcruxConfig, "load", classmethod(lambda cls: config))
    command = (
        "import sys; print('captured-out'); "
        "print('captured-error', file=sys.stderr); sys.exit(7)"
    )

    result = CliRunner().invoke(
        cli,
        ["wrap", "--project", "test", "--", sys.executable, "-c", command],
    )

    assert result.exit_code == 7
    assert "captured-out" in result.output
    assert "captured-error" in result.output
    episode = EpisodicStore(
        config.projects_dir / "test" / "episodes.db"
    ).get_recent("test", limit=1)[0]
    action = episode.actions[0]
    assert action.exit_code == 7
    assert action.stdout == "captured-out\n"
    assert action.stderr == "captured-error\n"
    assert "captured-error" in action.error_signature
    assert action.output_truncated is False
