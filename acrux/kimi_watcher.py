"""Automatic capture of agent sessions by watching session log files."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.models import Action, Episode

AGENT_SESSION_PATHS = {
    "kimi": Path.home() / ".kimi-code" / "sessions",
    "claude": Path.home() / ".claude" / "sessions",
    "cursor": Path.home() / ".cursor" / "sessions",
    "codex": Path.home() / ".codex" / "sessions",
    "gemini": Path.home() / ".gemini" / "sessions",
}

# Tools that only inspect the world; sessions made up solely of these are
# low-signal Q&A and are not worth storing.
READ_ONLY_TOOLS = {
    "read",
    "readmediafile",
    "grep",
    "glob",
    "ls",
    "websearch",
    "fetchurl",
    "todolist",
    "listmcpresources",
    "search",
    "query",
    "view",
}

# Tools that mutate files; their presence makes a session high-signal.
EDIT_TOOLS = {
    "edit",
    "multiedit",
    "write",
    "notebookedit",
    "create",
    "apply_patch",
    "applypatch",
    "str_replace",
    "strreplace",
    "insert",
    "patch",
}

# Substrings in a follow-up user message that indicate the agent was corrected.
_CORRECTION_PATTERNS = (
    "that's wrong",
    "that is wrong",
    "that's not right",
    "that is not right",
    "not what i asked",
    "not what i meant",
    "wrong file",
    "you broke",
    "undo that",
    "revert that",
    "revert the",
    "go back",
)


def _tool_name(action: dict[str, Any]) -> str:
    return str(action.get("tool", "")).lower()


def _is_correction(text: str) -> bool:
    """Heuristic: does this user message correct the agent's previous work?"""
    lowered = text.lower()
    return any(pattern in lowered for pattern in _CORRECTION_PATTERNS)


def _has_file_edit(actions: list[dict[str, Any]]) -> bool:
    return any(_tool_name(a) in EDIT_TOOLS for a in actions)


def _has_fail_then_pass(actions: list[dict[str, Any]]) -> bool:
    """True when a failed tool result is followed by a later successful one."""
    seen_failure = False
    for action in actions:
        is_error = action.get("is_error")
        if is_error is True:
            seen_failure = True
        elif is_error is False and seen_failure:
            return True
    return False


def _is_high_signal(actions: list[dict[str, Any]], corrected: bool) -> bool:
    return corrected or _has_file_edit(actions) or _has_fail_then_pass(actions)


def _should_store(task: str, actions: list[dict[str, Any]], corrected: bool) -> bool:
    """Decide whether an auto-captured session is worth storing.

    High-signal sessions (file edits, fail→pass recovery, user corrections)
    are always kept. Low-signal sessions are skipped: zero tool calls
    (which also covers trivial tasks of a few words with no actions) and
    read-only Q&A sessions that only inspect or search.
    """
    if _is_high_signal(actions, corrected):
        return True
    if not actions:
        return False
    if all(_tool_name(a) in READ_ONLY_TOOLS for a in actions):
        return False
    return True


def _infer_outcome(actions: list[dict[str, Any]]) -> str:
    """Infer an outcome from recorded tool results.

    The most recent tool result decides: a session whose last known command
    succeeded is a success (a fail→pass sequence recovers to success), one
    left on a failing command is an error. Sessions with no result
    information keep the neutral "auto-captured" outcome.
    """
    outcome = "auto-captured"
    for action in actions:
        is_error = action.get("is_error")
        if is_error is None:
            continue
        outcome = "error (inferred)" if is_error else "success (inferred)"
    return outcome


def _record_result(state: dict[str, Any], call_id: Any, result: Any) -> None:
    """Attach a tool result to its pending tool-call action, if any."""
    if not call_id:
        return
    pending = state.setdefault("pending_calls", {})
    action = pending.pop(call_id, None)
    if action is None:
        return
    is_error = False
    output = ""
    if isinstance(result, dict):
        is_error = bool(result.get("isError"))
        output = str(result.get("output", ""))
    elif result is not None:
        output = str(result)
    if not is_error and (
        "command failed with exit code" in output.lower()
        or "command killed by" in output.lower()
    ):
        is_error = True
    action["result"] = output[:300]
    action["is_error"] = is_error


class KimiSessionWatcher:
    """Watch agent session directories for new JSONL activity and record episodes."""

    def __init__(
        self,
        config: AcruxConfig,
        agents: list[str] | None = None,
        interval: float = 5.0,
        finalize_after: float = 300.0,
    ):
        self.config = config
        self.agents = agents or list(AGENT_SESSION_PATHS.keys())
        self.interval = interval
        self.finalize_after = finalize_after
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self._scan()
            except Exception:
                pass

    def _scan(self) -> None:
        now = time.time()
        for agent in self.agents:
            sessions_dir = AGENT_SESSION_PATHS.get(agent)
            if not sessions_dir or not sessions_dir.exists():
                continue
            for wire_path in sessions_dir.rglob("*.jsonl"):
                if "agents/main" not in str(wire_path):
                    continue
                try:
                    self._process_file(wire_path, now, agent)
                except Exception:
                    pass

    def _process_file(self, path: Path, now: float, agent: str) -> None:
        key = str(path)
        state = self._state.get(key, {
            "offset": 0,
            "task": "",
            "actions": [],
            "pending_calls": {},
            "corrected": False,
            "last_mtime": 0.0,
            "finalized": False,
            "agent": agent,
        })
        try:
            stat = path.stat()
        except OSError:
            return

        if stat.st_mtime == state["last_mtime"]:
            if (
                not state["finalized"]
                and state.get("task")
                and now - stat.st_mtime > self.finalize_after
            ):
                self._finalize(path, state)
            return

        with open(path, "r", errors="replace") as f:
            f.seek(state["offset"])
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                self._handle_event(obj, state)
            state["offset"] = f.tell()
        state["last_mtime"] = stat.st_mtime
        self._state[key] = state

    def _handle_event(self, obj: dict[str, Any], state: dict[str, Any]) -> None:
        t = obj.get("type")
        if t == "context.append_message":
            msg = obj.get("message", {})
            if msg.get("role") == "user":
                content = msg.get("content", [])
                if content and content[0].get("type") == "text":
                    text = content[0].get("text", "")
                    if not text.startswith("<system"):
                        if not state["task"]:
                            state["task"] = text[:500]
                        elif _is_correction(text):
                            state["corrected"] = True
        elif t == "context.append_loop_event":
            ev = obj.get("event", {})
            if ev.get("type") == "tool.call":
                name = ev.get("name", "")
                args = ev.get("args", {})
                if name:
                    action: dict[str, Any] = {
                        "tool": name,
                        "args": args,
                        "result": "",
                        "is_error": None,
                    }
                    state["actions"].append(action)
                    call_id = ev.get("toolCallId")
                    if call_id:
                        state.setdefault("pending_calls", {})[call_id] = action
            elif ev.get("type") == "tool.result":
                _record_result(state, ev.get("toolCallId"), ev.get("result"))
        # Generic message format for other agents
        elif t == "message" and obj.get("role") == "user":
            content = obj.get("content", "")
            if isinstance(content, list) and content and content[0].get("type") == "text":
                content = content[0].get("text", "")
            if isinstance(content, str) and not content.startswith("<system"):
                if not state["task"]:
                    state["task"] = content[:500]
                elif _is_correction(content):
                    state["corrected"] = True
        elif t == "tool_call":
            name = obj.get("name", "")
            args = obj.get("args", {})
            if name:
                action = {"tool": name, "args": args, "result": "", "is_error": None}
                state["actions"].append(action)
                call_id = obj.get("id") or obj.get("toolCallId")
                if call_id:
                    state.setdefault("pending_calls", {})[call_id] = action
        elif t == "tool_result":
            _record_result(state, obj.get("id") or obj.get("toolCallId"), obj.get("result"))

    def _finalize(self, path: Path, state: dict[str, Any]) -> None:
        # path: <sessions>/wd_<name>_<hash>/ses_.../agents/main/wire.jsonl
        session_id = path.parents[2].name
        project = self._project_for(path)
        corrected = bool(state.get("corrected"))
        raw_actions = state["actions"]
        if not _should_store(state["task"], raw_actions, corrected):
            state["finalized"] = True
            return
        actions = []
        for a in raw_actions:
            args = a.get("args", {})
            command = args.get("command") or args.get("path") or json.dumps(args)[:200]
            actions.append(
                Action(tool=a["tool"], command=command, result=a.get("result", ""))
            )
        tags = [state.get("agent", "agent"), "auto-capture"]
        if _is_high_signal(raw_actions, corrected):
            tags.append("signal:high")
        episode = Episode(
            session_id=session_id,
            task=state["task"],
            project=project,
            actions=actions,
            outcome=_infer_outcome(raw_actions),
            tags=tags,
            source=f"{state.get('agent', 'agent')}-auto",
            corrected=corrected,
        )
        episodic = EpisodicStore(self.config.projects_dir / project / "episodes.db")
        episodic.add(episode)
        state["finalized"] = True

    def _project_for(self, path: Path) -> str:
        # path: <sessions>/wd_<name>_<hash>/ses_.../agents/main/wire.jsonl
        try:
            wd_dir = path.parents[3]
            name = wd_dir.name
            if name.startswith("wd_"):
                name = name[3:]
            if "_" in name:
                name = name.rsplit("_", 1)[0]
            return name or "default"
        except Exception:
            return "default"
