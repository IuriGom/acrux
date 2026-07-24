"""Tests for the Claude Code session transcript watcher."""

import json
import time
from pathlib import Path

from acrux.claude_watcher import ClaudeSessionWatcher
from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore

SESSION_ID = "6a2567ca-dafb-4612-9edc-5f3c0f67006a"
CWD = "/Users/test/Desktop/myproj"


def _write_transcript(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")


def _fixture_lines() -> list[dict]:
    return [
        {"type": "permission-mode", "permissionMode": "default", "sessionId": SESSION_ID},
        {
            "type": "user",
            "message": {"role": "user", "content": "<command-message>init</command-message>"},
            "sessionId": SESSION_ID,
            "cwd": CWD,
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": "Fix the flaky login test"}],
            },
            "sessionId": SESSION_ID,
            "cwd": CWD,
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "Let me look at the test."},
                    {"type": "text", "text": "I'll read the failing test first."},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "Read",
                        "input": {"file_path": "/tmp/login_test.py"},
                    },
                ],
            },
            "sessionId": SESSION_ID,
            "cwd": CWD,
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "..."}],
            },
            "sessionId": SESSION_ID,
            "cwd": CWD,
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_2",
                        "name": "Bash",
                        "input": {"command": "pytest tests/test_login.py"},
                    },
                ],
            },
            "sessionId": SESSION_ID,
            "cwd": CWD,
        },
        {
            "type": "user",
            "message": {"role": "user", "content": "Thanks, now update the docs"},
            "sessionId": SESSION_ID,
            "cwd": CWD,
        },
    ]


def _make_watcher(tmp_path: Path, **kwargs) -> ClaudeSessionWatcher:
    config = AcruxConfig(profile="minimal", data_dir=tmp_path / "acrux-data")
    return ClaudeSessionWatcher(
        config,
        projects_dir=tmp_path / ".claude" / "projects",
        **kwargs,
    )


def _transcript_path(tmp_path: Path) -> Path:
    return (
        tmp_path
        / ".claude"
        / "projects"
        / "-Users-test-Desktop-myproj"
        / f"{SESSION_ID}.jsonl"
    )


def test_scan_extracts_task_and_actions(tmp_path: Path) -> None:
    _write_transcript(_transcript_path(tmp_path), _fixture_lines())
    watcher = _make_watcher(tmp_path)
    watcher._scan()

    state = watcher._state[str(_transcript_path(tmp_path))]
    assert state["task"] == "Fix the flaky login test"
    assert state["session_id"] == SESSION_ID
    assert state["cwd"] == CWD
    assert [a["tool"] for a in state["actions"]] == ["Read", "Bash"]
    assert state["actions"][0]["args"] == {"file_path": "/tmp/login_test.py"}
    assert state["actions"][1]["args"] == {"command": "pytest tests/test_login.py"}
    assert not state["finalized"]


def test_finalize_writes_episode(tmp_path: Path) -> None:
    _write_transcript(_transcript_path(tmp_path), _fixture_lines())
    watcher = _make_watcher(tmp_path, finalize_after=0)
    watcher._scan()
    watcher._scan()  # unchanged mtime + finalize_after=0 triggers finalize

    store = EpisodicStore(watcher.config.projects_dir / "myproj" / "episodes.db")
    episode = store.get_by_id(SESSION_ID)
    assert episode is not None
    assert episode.task == "Fix the flaky login test"
    assert episode.project == "myproj"
    assert episode.outcome == "auto-captured"
    assert episode.source == "claude-auto"
    assert episode.tags == ["claude", "auto-capture"]
    assert [a.tool for a in episode.actions] == ["Read", "Bash"]
    assert episode.actions[0].command == "/tmp/login_test.py"
    assert episode.actions[1].command == "pytest tests/test_login.py"

    # Finalizing again must not duplicate or fail.
    watcher._scan()
    assert watcher._state[str(_transcript_path(tmp_path))]["finalized"]


def test_incremental_offset_processing(tmp_path: Path) -> None:
    path = _transcript_path(tmp_path)
    _write_transcript(path, _fixture_lines())
    watcher = _make_watcher(tmp_path)
    watcher._scan()
    state = watcher._state[str(path)]
    assert len(state["actions"]) == 2
    offset = state["offset"]

    with open(path, "a") as f:
        f.write(json.dumps({
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "toolu_3", "name": "Edit",
                     "input": {"file_path": "/tmp/login.py"}},
                ],
            },
            "sessionId": SESSION_ID,
            "cwd": CWD,
        }) + "\n")
    watcher._scan()

    state = watcher._state[str(path)]
    assert state["offset"] > offset
    assert [a["tool"] for a in state["actions"]] == ["Read", "Bash", "Edit"]


def test_handle_event_skips_non_task_messages(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    state: dict = {"task": "", "actions": [], "session_id": "", "cwd": ""}

    # Command wrappers and system messages are not tasks.
    watcher._handle_event(
        {"type": "user", "message": {"role": "user", "content": "<command-message>x</command-message>"}},
        state,
    )
    watcher._handle_event(
        {"type": "user", "message": {"role": "user",
                                     "content": [{"type": "tool_result", "content": "out"}]}},
        state,
    )
    assert state["task"] == ""

    # Plain string content works; list content works; first one wins.
    watcher._handle_event(
        {"type": "user", "message": {"role": "user", "content": "  do the thing  "}},
        state,
    )
    assert state["task"] == "do the thing"
    watcher._handle_event(
        {"type": "user", "message": {"role": "user", "content": "second message"}},
        state,
    )
    assert state["task"] == "do the thing"

    # Noise events are ignored.
    watcher._handle_event({"type": "file-history-snapshot", "snapshot": {}}, state)
    watcher._handle_event({"type": "system", "content": "compact"}, state)
    assert state["actions"] == []


def test_project_fallback_from_dir_name(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    path = (
        watcher.projects_dir / "-Users-test-Desktop-PIA" / f"{SESSION_ID}.jsonl"
    )
    assert watcher._project_for(path, {"cwd": ""}) == "PIA"
    assert watcher._project_for(path, {"cwd": "/Users/test/Desktop/PIA"}) == "PIA"
    assert watcher._project_for(Path("/elsewhere/x.jsonl"), {"cwd": ""}) == "default"


def test_scan_without_projects_dir(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    watcher._scan()  # no ~/.claude/projects -> no-op
    assert watcher._state == {}


def test_start_stop_thread(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path, interval=0.05)
    watcher.start()
    assert watcher._thread is not None
    time.sleep(0.1)
    watcher.stop()
    assert watcher._thread is None
