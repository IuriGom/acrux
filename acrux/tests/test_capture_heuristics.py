"""Tests for W2 capture heuristics: low-signal filtering and outcome inference."""

from pathlib import Path

from acrux.config import AcruxConfig
from acrux.kimi_watcher import (
    KimiSessionWatcher,
    _has_fail_then_pass,
    _has_file_edit,
    _infer_outcome,
    _is_correction,
    _record_result,
    _should_store,
)
from acrux.memory.episodic import EpisodicStore


def _action(tool: str, command: str = "", is_error: bool | None = None) -> dict:
    return {
        "tool": tool,
        "args": {"command": command} if command else {},
        "result": "",
        "is_error": is_error,
    }


# --- _should_store -------------------------------------------------------


def test_should_store_skips_zero_tool_calls() -> None:
    task = "what does the verifier module do in this project exactly?"
    assert _should_store(task, [], corrected=False) is False


def test_should_store_skips_short_task_with_no_actions() -> None:
    assert _should_store("hi there", [], corrected=False) is False


def test_should_store_skips_read_only_qa() -> None:
    actions = [
        _action("Read"),
        _action("Grep"),
        _action("WebSearch", is_error=False),
    ]
    task = "where is the session watcher implemented in this codebase?"
    assert _should_store(task, actions, corrected=False) is False


def test_should_store_keeps_file_edits() -> None:
    actions = [_action("Read"), _action("Edit", is_error=False)]
    assert _should_store("fix the bug", actions, corrected=False) is True


def test_should_store_keeps_fail_then_pass() -> None:
    actions = [
        _action("Bash", "pytest -q", is_error=True),
        _action("Bash", "pytest -q", is_error=False),
    ]
    assert _should_store("make the tests pass", actions, corrected=False) is True


def test_should_store_keeps_corrected_without_actions() -> None:
    assert _should_store("do something", [], corrected=True) is True


def test_should_store_keeps_mutating_session_without_edits() -> None:
    actions = [_action("Bash", "pytest -q", is_error=False)]
    task = "run the test suite and report any failures you find"
    assert _should_store(task, actions, corrected=False) is True


# --- outcome inference ---------------------------------------------------


def test_infer_outcome_defaults_to_auto_captured() -> None:
    actions = [_action("Read"), _action("Bash", "ls")]
    assert _infer_outcome(actions) == "auto-captured"


def test_infer_outcome_success() -> None:
    actions = [
        _action("Edit", is_error=False),
        _action("Bash", "pytest -q", is_error=False),
    ]
    assert _infer_outcome(actions) == "success (inferred)"


def test_infer_outcome_error() -> None:
    actions = [
        _action("Bash", "pytest -q", is_error=False),
        _action("Bash", "pytest -q", is_error=True),
    ]
    assert _infer_outcome(actions) == "error (inferred)"


def test_infer_outcome_fail_then_pass_recovers() -> None:
    actions = [
        _action("Bash", "pytest -q", is_error=True),
        _action("Edit", is_error=False),
        _action("Bash", "pytest -q", is_error=False),
    ]
    assert _infer_outcome(actions) == "success (inferred)"


def test_has_fail_then_pass() -> None:
    assert _has_fail_then_pass([_action("Bash", is_error=True)]) is False
    assert _has_fail_then_pass(
        [_action("Bash", is_error=False), _action("Bash", is_error=True)]
    ) is False
    assert _has_fail_then_pass(
        [_action("Bash", is_error=True), _action("Bash", is_error=False)]
    ) is True


def test_has_file_edit() -> None:
    assert _has_file_edit([_action("Read"), _action("Bash")]) is False
    assert _has_file_edit([_action("Read"), _action("Write")]) is True
    assert _has_file_edit([_action("apply_patch")]) is True


def test_is_correction() -> None:
    assert _is_correction("That's wrong, revert that change") is True
    assert _is_correction("not what I asked for") is True
    assert _is_correction("please add tests for this") is False


def test_record_result_marks_failure_from_output_text() -> None:
    action = _action("Bash", "pytest -q")
    state = {"pending_calls": {"call-1": action}}
    _record_result(state, "call-1", {"output": "Command failed with exit code: 1"})
    assert action["is_error"] is True
    assert "exit code" in action["result"]


# --- end-to-end through the watcher --------------------------------------


def _make_watcher(tmp_path: Path) -> KimiSessionWatcher:
    data_dir = tmp_path / "data"
    config = AcruxConfig(
        data_dir=data_dir,
        global_dir=data_dir / "global",
        log_dir=tmp_path / "logs",
    )
    return KimiSessionWatcher(config, agents=["kimi"])


def _wire_path(tmp_path: Path) -> Path:
    return (
        tmp_path
        / "sessions"
        / "wd_myproj_ab12cd34ef56"
        / "ses_123"
        / "agents"
        / "main"
        / "wire.jsonl"
    )


def _user_msg(text: str) -> dict:
    return {
        "type": "context.append_message",
        "message": {"role": "user", "content": [{"type": "text", "text": text}]},
    }


def _tool_call(call_id: str, name: str, args: dict) -> dict:
    return {
        "type": "context.append_loop_event",
        "event": {
            "type": "tool.call",
            "toolCallId": call_id,
            "name": name,
            "args": args,
        },
    }


def _tool_result(call_id: str, output: str, is_error: bool = False) -> dict:
    result: dict = {"output": output}
    if is_error:
        result["isError"] = True
    return {
        "type": "context.append_loop_event",
        "event": {"type": "tool.result", "toolCallId": call_id, "result": result},
    }


def _run_session(watcher: KimiSessionWatcher, path: Path, events: list[dict]) -> dict:
    state: dict = {
        "offset": 0,
        "task": "",
        "actions": [],
        "pending_calls": {},
        "corrected": False,
        "last_mtime": 0.0,
        "finalized": False,
        "agent": "kimi",
    }
    for event in events:
        watcher._handle_event(event, state)
    watcher._finalize(path, state)
    return state


def _stored_episode(watcher: KimiSessionWatcher) -> object:
    store = EpisodicStore(watcher.config.projects_dir / "myproj" / "episodes.db")
    return store.get_by_id("ses_123")


def test_finalize_skips_read_only_qa_session(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    events = [
        _user_msg("where is the episodic store implemented in this project?"),
        _tool_call("c1", "Grep", {"pattern": "class EpisodicStore"}),
        _tool_result("c1", "acrux/memory/episodic.py:15"),
        _tool_call("c2", "Read", {"path": "acrux/memory/episodic.py"}),
        _tool_result("c2", "class EpisodicStore: ..."),
    ]
    state = _run_session(watcher, _wire_path(tmp_path), events)
    assert state["finalized"] is True
    assert _stored_episode(watcher) is None


def test_finalize_stores_edit_session_with_high_signal_and_success(
    tmp_path: Path,
) -> None:
    watcher = _make_watcher(tmp_path)
    events = [
        _user_msg("fix the broken parser and make the test suite pass again"),
        _tool_call("c1", "Edit", {"path": "acrux/parser.py"}),
        _tool_result("c1", "ok"),
        _tool_call("c2", "Bash", {"command": "pytest -q"}),
        _tool_result("c2", "12 passed"),
    ]
    _run_session(watcher, _wire_path(tmp_path), events)
    episode = _stored_episode(watcher)
    assert episode is not None
    assert episode.project == "myproj"
    assert episode.outcome == "success (inferred)"
    assert "signal:high" in episode.tags
    assert episode.actions[0].tool == "Edit"


def test_finalize_stores_fail_then_pass_as_high_signal(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    events = [
        _user_msg("make the failing parser tests pass again please"),
        _tool_call("c1", "Bash", {"command": "pytest -q"}),
        _tool_result("c1", "1 failed", is_error=True),
        _tool_call("c2", "Bash", {"command": "pytest -q"}),
        _tool_result("c2", "12 passed"),
    ]
    _run_session(watcher, _wire_path(tmp_path), events)
    episode = _stored_episode(watcher)
    assert episode is not None
    assert episode.outcome == "success (inferred)"
    assert "signal:high" in episode.tags


def test_finalize_infers_error_for_failing_session(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    events = [
        _user_msg("run the full test suite and fix every single failure found"),
        _tool_call("c1", "Bash", {"command": "pytest -q"}),
        _tool_result("c1", "3 failed", is_error=True),
    ]
    _run_session(watcher, _wire_path(tmp_path), events)
    episode = _stored_episode(watcher)
    assert episode is not None
    assert episode.outcome == "error (inferred)"
    assert "signal:high" not in episode.tags
    # EpisodicStore tags error outcomes automatically.
    assert "error" in episode.tags


def test_finalize_stores_corrected_session_without_actions(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    events = [
        _user_msg("rename the helper function to something shorter"),
        _user_msg("that's wrong, revert that change"),
    ]
    _run_session(watcher, _wire_path(tmp_path), events)
    episode = _stored_episode(watcher)
    assert episode is not None
    assert episode.corrected is True
    assert "signal:high" in episode.tags
    assert episode.outcome == "auto-captured"


def test_finalize_handles_generic_agent_format(tmp_path: Path) -> None:
    watcher = _make_watcher(tmp_path)
    events = [
        {"type": "message", "role": "user", "content": "update the config loader"},
        {
            "type": "tool_call",
            "id": "g1",
            "name": "write",
            "args": {"path": "acrux/config.py"},
        },
        {"type": "tool_result", "id": "g1", "result": {"output": "done"}},
    ]
    _run_session(watcher, _wire_path(tmp_path), events)
    episode = _stored_episode(watcher)
    assert episode is not None
    assert episode.outcome == "success (inferred)"
    assert "signal:high" in episode.tags
