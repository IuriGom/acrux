"""Automatic capture of Claude Code sessions by watching transcript files."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.models import Action, Episode

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# User-message prefixes that are harness noise, not real tasks.
_SKIP_TASK_PREFIXES = ("<command-message>", "<command-name>", "<local-command", "<system")


class ClaudeSessionWatcher:
    """Watch ~/.claude/projects/**/*.jsonl for new activity and record episodes."""

    def __init__(
        self,
        config: AcruxConfig,
        interval: float = 5.0,
        finalize_after: float = 300.0,
        projects_dir: Path | None = None,
    ):
        self.config = config
        self.projects_dir = projects_dir or CLAUDE_PROJECTS_DIR
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
        if not self.projects_dir.exists():
            return
        for transcript_path in self.projects_dir.rglob("*.jsonl"):
            try:
                self._process_file(transcript_path, now)
            except Exception:
                pass

    def _process_file(self, path: Path, now: float) -> None:
        key = str(path)
        state = self._state.get(key, {
            "offset": 0,
            "task": "",
            "actions": [],
            "session_id": "",
            "cwd": "",
            "last_mtime": 0.0,
            "finalized": False,
            "agent": "claude",
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
        if obj.get("sessionId") and not state.get("session_id"):
            state["session_id"] = obj["sessionId"]
        if obj.get("cwd") and not state.get("cwd"):
            state["cwd"] = obj["cwd"]

        t = obj.get("type")
        msg = obj.get("message")
        if not isinstance(msg, dict):
            return

        if t == "user" and not state["task"]:
            text = self._user_text(msg.get("content"))
            if text and not text.startswith(_SKIP_TASK_PREFIXES):
                state["task"] = text[:500]
        elif t == "assistant":
            content = msg.get("content")
            if not isinstance(content, list):
                return
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name", "")
                if name:
                    state["actions"].append({"tool": name, "args": block.get("input", {})})

    @staticmethod
    def _user_text(content: Any) -> str:
        """Extract plain text from a Claude user message content payload."""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return str(block.get("text", "")).strip()
        return ""

    def _finalize(self, path: Path, state: dict[str, Any]) -> None:
        session_id = state.get("session_id") or path.stem
        project = self._project_for(path, state)
        actions = []
        for a in state["actions"]:
            args = a.get("args", {})
            command = (
                args.get("command")
                or args.get("file_path")
                or args.get("path")
                or json.dumps(args)[:200]
            )
            actions.append(Action(tool=a["tool"], command=command))
        episode = Episode(
            session_id=session_id,
            task=state["task"],
            project=project,
            actions=actions,
            outcome="auto-captured",
            tags=[state.get("agent", "claude"), "auto-capture"],
            source=f"{state.get('agent', 'claude')}-auto",
        )
        episodic = EpisodicStore(self.config.projects_dir / project / "episodes.db")
        episodic.add(episode)
        state["finalized"] = True

    def _project_for(self, path: Path, state: dict[str, Any]) -> str:
        # Prefer the cwd recorded in transcript events; fall back to the
        # projects dir name, e.g. ~/.claude/projects/-Users-<user>-Desktop-<project>/.
        cwd = state.get("cwd")
        if cwd:
            name = Path(cwd).name
            if name:
                return name
        try:
            project_dir = path.relative_to(self.projects_dir).parts[0]
        except Exception:
            return "default"
        name = project_dir.lstrip("-").split("-")[-1]
        return name or "default"
