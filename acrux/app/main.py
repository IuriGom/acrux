"""Acrux native app backend.

Serves a dark-themed web UI and talks to Ollama + the local acrux memory stores.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import math
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from acrux.config import AcruxConfig
from acrux.embeddings import OllamaEmbedder
from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Action, Episode, Fact
from acrux.sandbox import run_sandboxed
from acrux.utils import PidFile, available_ram_mb, degraded_reason, git_context, is_degraded

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
APP_DIR = Path.home() / ".acrux" / "app"
CHATS_DIR = APP_DIR / "chats"
UPLOADS_DIR = APP_DIR / "uploads"
CHATS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Global config and stores (loaded at startup; user can reload via acrux CLI).
_cfg: AcruxConfig | None = None
_semantic: SemanticStore | None = None
_episodic: EpisodicStore | None = None
_procedural: ProceduralDBStore | None = None
_embedder: OllamaEmbedder | None = None

# In-memory watcher state (background polling threads).
_watchers: dict[str, "WorkspaceWatcher"] = {}

# In-memory replay state keyed by original episode session_id.
_replay_sessions: dict[str, dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_acrux()
    yield
    if _embedder is not None:
        await _embedder.close()


app = FastAPI(title="Acrux", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Require a local token for all HTTP endpoints when api_auth is enabled."""

    async def dispatch(self, request: Request, call_next):
        if not _cfg or not _cfg.api_auth:
            return await call_next(request)
        if request.url.path == "/health":
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        token = request.headers.get("x-acrux-token") or auth.replace("Bearer ", "")
        if token != _cfg.api_token:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


app.add_middleware(TokenAuthMiddleware)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_acrux() -> None:
    global _cfg, _semantic, _episodic, _procedural, _embedder
    _cfg = AcruxConfig.load()
    _embedder = _cfg.create_embedder()
    _semantic = SemanticStore(_cfg.data_dir / "global" / "facts.db", embedder=_embedder)
    _episodic = EpisodicStore(_cfg.data_dir / "global" / "episodes.db")
    _procedural = ProceduralDBStore(_cfg.data_dir / "global" / "skills.db")


def _project_dir(project: str) -> Path:
    return (
        _cfg.data_dir / "projects" / project
        if _cfg
        else Path.home() / ".acrux" / "data" / "projects" / project
    )


_project_stores: dict[str, Any] = {}


def _project_semantic(project: str) -> SemanticStore:
    if project == "global":
        return _semantic
    path = _project_dir(project) / "semantic.db"
    if path.exists():
        # Cache stores: constructing one reloads every embedding and rebuilds
        # the HNSW index, which made multi-project endpoints take ~30s.
        key = str(path)
        store = _project_stores.get(key)
        if store is None:
            store = SemanticStore(path, embedder=_embedder)
            _project_stores[key] = store
        return store
    return _semantic


def _project_episodic(project: str) -> EpisodicStore:
    if project == "global":
        return _episodic
    path = _project_dir(project) / "episodes.db"
    if path.exists():
        key = str(path)
        store = _project_stores.get(key)
        if store is None:
            store = EpisodicStore(path)
            _project_stores[key] = store
        return store
    return _episodic


def _project_procedural(project: str) -> ProceduralDBStore:
    if project == "global":
        return _procedural
    path = _project_dir(project) / "skills.db"
    if path.exists():
        key = str(path)
        store = _project_stores.get(key)
        if store is None:
            store = ProceduralDBStore(path)
            _project_stores[key] = store
        return store
    return _procedural


def _project_for(workspace: str) -> str:
    return Path(workspace).name or "default"


async def _recall_context(project: str, query: str, limit: int = 6) -> str:
    """Build a tagged memory context block for injection into the system prompt."""
    from acrux.retrieval import Stores, recall_context

    if not query.strip():
        return ""
    semantic = _project_semantic(project)
    episodic = _project_episodic(project)
    procedural = _project_procedural(project)
    stores = Stores(semantic=semantic, episodic=episodic, procedural=procedural)
    return await recall_context(
        stores,
        _project_procedural,
        project,
        query,
        limit,
    )


def _record_memory_outcomes(project: str, memory_context: str, success: bool = True) -> None:
    """Update memory confidence/success rates based on whether they helped."""
    from acrux.retrieval import record_memory_outcomes

    semantic = _project_semantic(project)
    procedural = _project_procedural(project)
    record_memory_outcomes(semantic, procedural, memory_context, success)


def _acrux_bin() -> str:
    return str(Path(__file__).parents[1].resolve() / ".venv" / "bin" / "acrux")


def _workspace_safe_path(workspace: str, target: str) -> Path:
    """Resolve target inside workspace and refuse escapes."""
    base = Path(workspace).resolve()
    requested = (base / target).resolve()
    if not str(requested).startswith(str(base)):
        raise ValueError("Path escapes workspace")
    return requested


def _git_info_for(workspace: str) -> dict[str, Any]:
    if not workspace or not Path(workspace).is_dir():
        return {}
    return git_context(workspace)


def _attach_git_info(obj: Fact | Episode, workspace: str) -> None:
    if not obj.git_info:
        obj.git_info = _git_info_for(workspace)


def _find_episode_store(session_id: str) -> tuple[Episode, "EpisodicStore"] | None:
    """Find an episode and its owning store across global and project DBs."""
    if _episodic is not None:
        ep = _episodic.get_by_id(session_id)
        if ep:
            return ep, _episodic
    if _cfg is None:
        return None
    projects_dir = _cfg.data_dir / "projects"
    if not projects_dir.exists():
        return None
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        store = EpisodicStore(project_dir / "episodes.db")
        ep = store.get_by_id(session_id)
        if ep:
            return ep, store
    return None


def _git_checkout_for_replay(workspace: Path, commit: str, force: bool = False) -> dict[str, Any]:
    """Attempt to checkout ``commit`` in ``workspace``. Returns ok + warning."""
    try:
        status = subprocess.run(
            ["git", "-C", str(workspace), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if status.returncode != 0:
            return {"ok": False, "warning": "Workspace is not a git repository."}
        if status.stdout.strip() and not force:
            return {
                "ok": False,
                "warning": "Workspace has uncommitted changes. Pass force=true to checkout anyway.",
            }
        checkout = subprocess.run(
            ["git", "-C", str(workspace), "checkout", commit],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if checkout.returncode != 0:
            return {
                "ok": False,
                "warning": f"Could not checkout {commit}: {checkout.stderr or checkout.stdout}",
            }
        return {"ok": True, "warning": None}
    except Exception as exc:
        return {"ok": False, "warning": f"Git checkout failed: {exc}"}


def _diff_text(original: str, current: str) -> str:
    """Return a unified-diff-style string between two texts."""
    import difflib

    orig_lines = original.splitlines(keepends=True) or [""]
    curr_lines = current.splitlines(keepends=True) or [""]
    diff = list(difflib.unified_diff(orig_lines, curr_lines, lineterm=""))
    return "".join(diff) if diff else "(no difference)"


def _skill_for_action_verified(action: Action, project: str) -> bool:
    """Return True if a verified procedural skill matches this action."""
    if _procedural is None:
        return False
    query = action.command or action.target or ""
    if not query:
        return False
    for skill in _procedural.search(project, query, limit=10):
        if not skill.verified:
            continue
        procedure_text = " ".join(skill.procedure).lower()
        action_text = query.lower()
        if action_text in procedure_text or any(p.lower() in action_text for p in skill.procedure):
            return True
    return False


def _requires_approval(action: Action, project: str, auto_approve: bool) -> bool:
    """run_command actions require approval unless auto-approve or verified skill."""
    if action.tool != "run_command":
        return False
    if auto_approve:
        return False
    return not _skill_for_action_verified(action, project)


def _action_to_tool_call(action: Action) -> tuple[str, dict[str, Any]]:
    """Convert a stored Action into a tool name and arguments for _execute_tool."""
    if action.tool == "read_file":
        return "read_file", {"path": action.target or ""}
    if action.tool == "list_files":
        return "list_files", {"path": action.target or "."}
    if action.tool == "run_command":
        return "run_command", {"command": action.command or "", "timeout": 30}
    return action.tool, {"target": action.target, "command": action.command}


def _storage_usage() -> dict[str, Any]:
    """Return storage usage for the acrux data directory."""
    if not _cfg:
        return {"used_bytes": 0, "limit_bytes": 0, "percent": 0.0}
    limit = _cfg.storage_limit_bytes
    used = 0
    if _cfg.data_dir.exists():
        for dirpath, _, filenames in os.walk(_cfg.data_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    used += os.path.getsize(fp)
                except OSError:
                    pass
    percent = (used / limit * 100) if limit > 0 else 0.0
    return {
        "used_bytes": used,
        "limit_bytes": limit,
        "percent": round(percent, 2),
        "ok": limit <= 0 or used < limit,
    }


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Watcher
# ---------------------------------------------------------------------------


class WorkspaceWatcher:
    """Lightweight polling-based workspace watcher."""

    IGNORE_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".ruff_cache", ".DS_Store"}

    def __init__(
        self, project: str, workspace: Path, semantic: SemanticStore, interval: float = 5.0
    ):
        self.project = project
        self.workspace = workspace
        self.semantic = semantic
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        if self._thread is not None:
            return
        self._load_state()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _load_state(self) -> None:
        for row in self.semantic.get_watcher_state(self.project):
            self._state[row["path"]] = {
                "mtime": row["last_seen_mtime"],
                "hash": row["last_seen_hash"],
            }

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self._scan()
            except Exception:
                pass

    def _scan(self) -> None:
        for path in self._walk():
            try:
                stat = path.stat()
                mtime = datetime.utcfromtimestamp(stat.st_mtime).isoformat()
                file_hash = _file_hash(path)
                rel = str(path.relative_to(self.workspace))
                prev = self._state.get(rel)
                if prev and prev["hash"] != file_hash:
                    diff = f"{rel} changed (mtime {prev['mtime']} -> {mtime})"
                    self.semantic.set_watcher_state(self.project, rel, mtime, file_hash, diff)
                else:
                    self.semantic.set_watcher_state(self.project, rel, mtime, file_hash, None)
                self._state[rel] = {"mtime": mtime, "hash": file_hash}
            except Exception:
                pass

    def _walk(self) -> list[Path]:
        files: list[Path] = []
        if not self.workspace.exists():
            return files
        for root, dirs, filenames in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            for f in filenames:
                files.append(Path(root) / f)
        return files


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


def _run_health_checks(project: str | None = None) -> list[dict[str, Any]]:
    """Run health checks and store results."""
    if not _cfg:
        return []
    semantic = (
        _semantic
        if _semantic is not None
        else SemanticStore(_cfg.data_dir / "global" / "facts.db", embedder=_embedder)
    )
    checks: list[dict[str, Any]] = []

    # Storage check
    usage = _storage_usage()
    if usage["limit_bytes"] > 0:
        if usage["percent"] >= 95:
            checks.append(
                {
                    "project": project,
                    "check_type": "storage",
                    "severity": "error",
                    "message": f"Storage at {usage['percent']}% of limit",
                }
            )
        elif usage["percent"] >= 80:
            checks.append(
                {
                    "project": project,
                    "check_type": "storage",
                    "severity": "warning",
                    "message": f"Storage at {usage['percent']}% of limit",
                }
            )

    # Checksum verification
    if _cfg and _cfg.data_dir.exists():
        verified = semantic.verify_storage_checksums(_cfg.data_dir)
        if not verified["ok"]:
            checks.append(
                {
                    "project": None,
                    "check_type": "checksum",
                    "severity": "error",
                    "message": f"Checksum mismatches: {len(verified['mismatches'])}, missing: {len(verified['missing'])}",
                }
            )

    # Orphan facts (facts with parent_id pointing to missing parent)
    if project:
        import sqlite3

        with sqlite3.connect(semantic.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, parent_id FROM facts WHERE project = ? AND parent_id IS NOT NULL",
                (project,),
            ).fetchall()
        parent_ids = {r["parent_id"] for r in rows}
        if parent_ids:
            placeholders = ", ".join("?" for _ in parent_ids)
            with sqlite3.connect(semantic.db_path) as conn:
                existing = {
                    r[0]
                    for r in conn.execute(
                        f"SELECT id FROM facts WHERE id IN ({placeholders})", list(parent_ids)
                    ).fetchall()
                }
            orphan_count = sum(1 for r in rows if r["parent_id"] not in existing)
            if orphan_count:
                checks.append(
                    {
                        "project": project,
                        "check_type": "orphan",
                        "severity": "warning",
                        "message": f"{orphan_count} facts reference missing parents",
                    }
                )

    # Conflict check
    if project:
        facts = semantic.get_recent(project, limit=200)
        conflicts = _detect_conflicts_in_memory(facts)
        unresolved = [c for c in conflicts if c.get("resolved") is not True]
        if unresolved:
            checks.append(
                {
                    "project": project,
                    "check_type": "conflict",
                    "severity": "warning",
                    "message": f"{len(unresolved)} unresolved fact conflicts",
                }
            )

    # Stale memory check
    if project:
        stale = semantic.list_stale_facts(project, threshold=0.8, limit=1)
        if stale:
            checks.append(
                {
                    "project": project,
                    "check_type": "stale",
                    "severity": "info",
                    "message": f"{len(stale)} facts are highly stale",
                }
            )

    for check in checks:
        semantic.add_health_check(check)
    return checks


def _detect_conflicts_in_memory(facts: list[Fact]) -> list[dict[str, Any]]:
    contradiction_patterns = [
        ("always", "never"),
        ("must", "must not"),
        ("should", "should not"),
        ("is ", "is not "),
        ("can ", "cannot "),
        ("will ", "will not "),
    ]
    negation_words = ("never", "not", "no ", "cannot")
    conflicts = []
    for i, a in enumerate(facts):
        for b in facts[i + 1 :]:
            a_text = a.content.lower()
            b_text = b.content.lower()
            shared = {t for t in a.content.lower().split() if len(t) > 3} & {
                t for t in b.content.lower().split() if len(t) > 3
            }
            if len(shared) < 2:
                continue
            contradictory = False
            for pos, neg in contradiction_patterns:
                if (pos in a_text and neg in b_text) or (pos in b_text and neg in a_text):
                    contradictory = True
                    break
            if not contradictory:
                a_has_neg = any(n in a_text for n in negation_words)
                b_has_neg = any(n in b_text for n in negation_words)
                if a_has_neg != b_has_neg:
                    contradictory = True
            if contradictory:
                conflicts.append(
                    {
                        "fact_a": a.to_dict(),
                        "fact_b": b.to_dict(),
                        "shared_keywords": sorted(shared),
                    }
                )
    return conflicts


# ---------------------------------------------------------------------------
# Rollback suggestion
# ---------------------------------------------------------------------------


def _rollback_suggestion(project: str, after_command: str | None = None) -> dict[str, Any]:
    """Suggest a rollback based on recent episodes and git state."""
    episodic = _project_episodic(project)
    episodes = episodic.get_recent(project, limit=50)
    failed = [
        e
        for e in episodes
        if any(w in (e.outcome or "").lower() for w in ("error", "fail", "exception"))
    ]
    last_success = next(
        (
            e
            for e in episodes
            if any(w in (e.outcome or "").lower() for w in ("success", "ok", "passed"))
        ),
        None,
    )
    suggestion: dict[str, Any] = {"suggested_command": None, "reason": None, "git_commit": None}
    if last_success and last_success.git_info:
        commit = last_success.git_info.get("commit")
        if commit:
            suggestion["suggested_command"] = f"git checkout {commit}"
            suggestion["reason"] = "Last known successful episode was at this commit"
            suggestion["git_commit"] = commit
    if after_command:
        suggestion["after_command"] = after_command
    suggestion["failed_episodes"] = [
        {"session_id": e.session_id, "task": e.task, "outcome": e.outcome, "timestamp": e.timestamp}
        for e in failed[:5]
    ]
    return suggestion


# ---------------------------------------------------------------------------
# Import / export helpers
# ---------------------------------------------------------------------------


def _parse_markdown_file(path: Path) -> list[dict[str, Any]]:
    """Parse a Markdown file into fact chunks."""
    text = path.read_text(errors="replace")
    frontmatter: dict[str, Any] = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                import yaml

                frontmatter = yaml.safe_load(parts[1]) or {}
                text = parts[2]
            except Exception:
                pass
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    title = frontmatter.get("title", path.stem)
    chunks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current:
                chunks.append("\n".join(current).strip())
                current = []
            current.append(line)
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    if not chunks:
        chunks = [text.strip()]
    facts = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        content = f"{title}\n\n{chunk}" if chunk != text.strip() else chunk
        facts.append({"content": content, "tags": tags, "source": f"import:{path.name}"})
    return facts


async def _import_directory(project: str, directory: Path, source_label: str) -> dict[str, Any]:
    semantic = _project_semantic(project)
    imported = 0
    skipped = 0
    for path in directory.rglob("*.md"):
        try:
            for fact_data in _parse_markdown_file(path):
                fact = Fact(
                    project=project,
                    content=fact_data["content"],
                    source=f"{source_label}:{path.name}",
                    tags=fact_data["tags"],
                )
                await semantic.add(fact)
                imported += 1
        except Exception:
            skipped += 1
    return {"imported": imported, "skipped": skipped}


def _export_markdown(project: str, format: str) -> dict[str, Any]:
    """Export project memory as a Markdown wiki to a temp directory."""
    semantic = _project_semantic(project)
    episodic = _project_episodic(project)
    procedural = _project_procedural(project)
    facts = semantic.list_facts(project, limit=10000)
    episodes = episodic.get_recent(project, limit=10000)
    skills = procedural.get_all(project)
    out_dir = Path.home() / ".acrux" / "exports" / project
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "facts").mkdir(exist_ok=True)
    (out_dir / "episodes").mkdir(exist_ok=True)
    (out_dir / "skills").mkdir(exist_ok=True)

    def slug(text: str) -> str:
        return (
            "".join(c if c.isalnum() or c == " " else " " for c in text)
            .strip()
            .replace(" ", "-")[:50]
        )

    index_lines = [f"# {project} Acrux Wiki", ""]
    for fact in facts:
        name = slug(fact.content[:60])
        path = out_dir / "facts" / f"{name}.md"
        tag_str = ", ".join(f"#{t}" for t in fact.tags) if fact.tags else ""
        path.write_text(f"# {name}\n\n{fact.content}\n\nTags: {tag_str}\n")
        index_lines.append(f"- [[facts/{name}]]")
    for ep in episodes:
        name = slug(ep.task[:60]) or ep.session_id
        month = ep.timestamp[:7] if ep.timestamp else "unknown"
        month_dir = out_dir / "episodes" / month
        month_dir.mkdir(exist_ok=True)
        path = month_dir / f"{name}.md"
        path.write_text(f"# {name}\n\nTask: {ep.task}\nOutcome: {ep.outcome}\n")
        index_lines.append(f"- [[episodes/{month}/{name}]]")
    for skill in skills:
        name = slug(skill.name)
        path = out_dir / "skills" / f"{name}.md"
        procedure_text = "\n".join(skill.procedure)
        path.write_text(f"# {skill.name}\n\n{procedure_text}\n")
        index_lines.append(f"- [[skills/{name}]]")

    if format == "obsidian":
        index_lines.insert(2, "```acrux-graph\nplaceholder\n```")
    (out_dir / "index.md").write_text("\n".join(index_lines))
    return {
        "export_dir": str(out_dir),
        "facts": len(facts),
        "episodes": len(episodes),
        "skills": len(skills),
    }


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@app.get("/api/models")
async def list_models() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            r.raise_for_status()
            models = r.json().get("models", [])
            return {"models": [{"name": m["name"], "size": m.get("size", 0)} for m in models]}
    except Exception as e:
        raise HTTPException(503, f"Ollama unreachable: {e}")


# ---------------------------------------------------------------------------
# Acrux status and control
# ---------------------------------------------------------------------------


@app.get("/api/acrux/status")
async def acrux_status() -> dict[str, Any]:
    pid_file = PidFile()
    degraded = is_degraded()
    usage = _storage_usage()
    status = {
        "running": pid_file.is_running(),
        "profile": _cfg.profile if _cfg else "unknown",
        "reflection_model": _cfg.reflection.routing.get("reflection", _cfg.reflection.model)
        if _cfg
        else "",
        "coding_model": _cfg.reflection.routing.get("coding", _cfg.reflection.model)
        if _cfg
        else "",
        "embedding_model": _cfg.reflection.routing.get("embedding", _cfg.reflection.embedding_model)
        if _cfg
        else "",
        "routing": _cfg.reflection.routing if _cfg else {},
        "provider": _cfg.reflection.provider if _cfg else "none",
        "data_dir": str(_cfg.data_dir) if _cfg else "",
        "facts": _semantic.count() if _semantic else 0,
        "skills": _procedural.count() if _procedural else 0,
        "episodes": _episodic.count() if _episodic else 0,
        "degraded": degraded,
        "reason": degraded_reason() if degraded else None,
        "available_ram_mb": available_ram_mb(),
        "storage": usage,
    }
    return status


@app.post("/api/acrux/start")
async def acrux_start() -> dict[str, str]:
    try:
        subprocess.run(
            [_acrux_bin(), "daemon", "--background", "--mcp", "http"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"status": "started"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Failed to start acrux: {e.stderr or e.stdout}")


@app.post("/api/acrux/stop")
async def acrux_stop() -> dict[str, str]:
    try:
        subprocess.run(
            [_acrux_bin(), "stop"], check=False, capture_output=True, text=True, timeout=30
        )
        return {"status": "stopped"}
    except Exception as e:
        raise HTTPException(500, f"Failed to stop acrux: {e}")


@app.get("/api/acrux/knowledge")
async def acrux_knowledge(project: str = Query(default="default")) -> dict[str, str]:
    """Ask the reflection model to summarize what the acrux knows."""
    if not _cfg or _cfg.reflection.provider == "none":
        return {
            "summary": "No reflection provider configured. The acrux is recording but not summarizing."
        }

    semantic = _project_semantic(project)
    procedural = _project_procedural(project)
    facts = semantic.get_recent(project, limit=50)
    skills = procedural.get_all(project)

    fact_text = "\n".join(f"- {f.content}" for f in facts)
    skill_text = "\n".join(f"- {s.name}: {s.procedure}" for s in skills[:20])

    prompt = (
        "You are the Acrux's self-summary voice. Write a concise, human-readable resume of what the system has learned.\n\n"
        f"Facts ({len(facts)}):\n{fact_text}\n\n"
        f"Skills ({len(skills)}):\n{skill_text}\n\n"
        "Summarize the domains of knowledge, recurring issues, and key procedures in 3-6 sentences."
    )

    try:
        model = _cfg.reflection.routing.get("reflection", _cfg.reflection.model)
        if _cfg.reflection.provider == "ollama":
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"{_cfg.reflection.host}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                )
                r.raise_for_status()
                return {"summary": r.json().get("response", "").strip()}
        # Kimi provider would need an API key; not implemented here.
        return {"summary": "Online reflection provider not yet supported in the app."}
    except Exception as e:
        return {"summary": f"Could not generate summary: {e}"}


@app.get("/api/acrux/context")
async def acrux_context(
    project: str = Query(default="default"),
    query: str = Query(default=""),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict[str, str]:
    """Return a ready-to-inject memory context block for a task."""
    context = await _recall_context(project, query, limit)
    return {"context": context}


@app.post("/api/acrux/reflect")
async def acrux_reflect(
    project: str = Query(default="default"),
    batch_size: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """Run reflection for a project and return the counts."""
    if not _cfg or _cfg.reflection.provider == "none":
        raise HTTPException(400, "Reflection provider is not configured")
    from acrux.reflection.engine import ReflectionEngine

    semantic = _project_semantic(project)
    episodic = _project_episodic(project)
    procedural = _project_procedural(project)
    engine = ReflectionEngine(_cfg, episodic, semantic, procedural)
    result = await engine.reflect_project(project, batch_size)
    return {"status": "ok", **result}


# ---------------------------------------------------------------------------
# Workspace / files
# ---------------------------------------------------------------------------


@app.post("/api/folder/select")
async def select_folder() -> dict[str, str]:
    """Open a native macOS folder picker."""
    script = 'POSIX path of (choose folder with prompt "Choose a workspace folder for Acrux")'
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        path = result.stdout.strip().rstrip("/")
        return {"path": path, "name": Path(path).name}
    except subprocess.CalledProcessError:
        raise HTTPException(400, "Folder selection cancelled")
    except FileNotFoundError:
        raise HTTPException(500, "osascript not found (macOS only)")


@app.get("/api/folder/tree")
async def folder_tree(path: str = Query(...), depth: int = 1) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        raise HTTPException(404, "Folder not found")
    entries = []
    try:
        for item in sorted(target.iterdir()):
            try:
                entries.append(
                    {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": str(item),
                    }
                )
            except PermissionError:
                continue
    except PermissionError:
        raise HTTPException(403, "Permission denied")
    return {"entries": entries}


@app.get("/api/file")
async def read_file_api(path: str = Query(...), max_bytes: int = 200_000) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise HTTPException(404, "File not found")
    try:
        size = target.stat().st_size
        content = target.read_text(errors="replace") if size <= max_bytes else ""
        return {
            "path": str(target),
            "size": size,
            "truncated": size > max_bytes,
            "content": content,
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# Chat persistence
# ---------------------------------------------------------------------------


def _chat_path(chat_id: str) -> Path:
    return CHATS_DIR / f"{chat_id}.json"


@app.get("/api/chats")
async def list_chats() -> dict[str, list[dict[str, Any]]]:
    chats = []
    for p in sorted(CHATS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
            chats.append(
                {
                    "id": data.get("id", p.stem),
                    "title": data.get("title", "Untitled"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                }
            )
        except Exception:
            continue
    return {"chats": chats}


@app.get("/api/chats/{chat_id}")
async def load_chat(chat_id: str) -> dict[str, Any]:
    path = _chat_path(chat_id)
    if not path.exists():
        raise HTTPException(404, "Chat not found")
    return json.loads(path.read_text())


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str) -> dict[str, str]:
    path = _chat_path(chat_id)
    if path.exists():
        path.unlink()
    return {"status": "deleted"}


def _save_chat(
    chat_id: str, title: str, messages: list[dict[str, Any]], meta: dict[str, Any]
) -> None:
    now = datetime.utcnow().isoformat()
    path = _chat_path(chat_id)
    data = {
        "id": chat_id,
        "title": title,
        "created_at": meta.get("created_at") or now,
        "updated_at": now,
        "model": meta.get("model"),
        "workspace": meta.get("workspace"),
        "allowed_tools": meta.get("allowed_tools", []),
        "messages": messages,
    }
    path.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Agent tools
# ---------------------------------------------------------------------------


_ALLOWED_WEB_SCHEMES = {"http", "https"}
_ALLOWED_CONTENT_TYPES = (
    "text/html",
    "text/plain",
    "application/json",
    "application/xml",
)
_MAX_FETCH_BYTES = 2_000_000
_MAX_EXTRACT_BYTES = 200_000
_FETCH_TIMEOUT = 15.0


def _is_private_host(hostname: str) -> bool:
    """Return True if hostname/IP resolves to a private/internal address."""
    host = hostname.lower().strip()
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return bool(
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
        )
    except ValueError:
        pass
    # Resolve and check returned addresses.
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_multicast
                    or ip.is_reserved
                ):
                    return True
            except ValueError:
                continue
    except Exception:
        # If we cannot resolve, block to be safe.
        return True
    return False


def _is_safe_url(url: str) -> tuple[bool, str]:
    """Validate that a URL is safe to fetch."""
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Invalid URL: {exc}"
    if parsed.scheme not in _ALLOWED_WEB_SCHEMES:
        return False, f"Scheme not allowed: {parsed.scheme}"
    host = parsed.hostname
    if not host:
        return False, "URL has no host"
    if _is_private_host(host):
        return False, "Private/internal address blocked"
    return True, ""


async def _web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS

        num_results = max(1, min(int(num_results), 10))

        def _search() -> list[dict[str, Any]]:
            with DDGS(timeout=_FETCH_TIMEOUT) as ddgs:
                return ddgs.text(query, max_results=num_results)

        results = await asyncio.to_thread(_search)
        if not results:
            return "No web results found."
        lines = [f"Web search results for: {query}"]
        for r in results:
            title = r.get("title", "No title")
            href = r.get("href", "")
            body = r.get("body", "")
            lines.append(f"- {title}\n  URL: {href}\n  {body}")
        return "\n\n".join(lines)
    except Exception as exc:
        return f"Web search error: {exc}"


async def _web_fetch(url: str, max_bytes: int = 200_000) -> str:
    """Fetch a public URL and extract readable text."""
    safe, reason = _is_safe_url(url)
    if not safe:
        return f"Blocked: {reason}"
    max_bytes = max(1_000, min(int(max_bytes), _MAX_EXTRACT_BYTES))
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Acrux/1.0"})
            r.raise_for_status()
            content_type = (r.headers.get("content-type", "") or "").lower()
            if content_type and not any(content_type.startswith(t) for t in _ALLOWED_CONTENT_TYPES):
                return f"Blocked content type: {content_type}"
            if len(r.content) > _MAX_FETCH_BYTES:
                return f"Response too large ({len(r.content)} bytes; max {_MAX_FETCH_BYTES})"
            from trafilatura import extract

            text = await asyncio.to_thread(
                extract, r.text, include_comments=False, include_tables=True, deduplicate=True
            )
            if not text:
                text = r.text
            text = text.strip()
            if len(text) > max_bytes:
                text = text[:max_bytes] + "\n... (truncated)"
            return f"Fetched: {url}\n\n{text}"
    except Exception as exc:
        return f"Fetch error: {exc}"


ALL_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file inside the workspace.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path inside the workspace"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a workspace path.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative workspace path, default '.'",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file inside the workspace with the given content. ALWAYS use this to create files — never write files via run_command with echo/cat. After writing, reply with a short confirmation only; do not repeat the content in chat.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path inside the workspace"},
                    "content": {"type": "string", "description": "Full content to write to the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command inside the workspace. Requires user approval unless auto-accept is on. Do NOT use this to write files — use write_file instead.",
            "category": "destructive",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to run"},
                    "timeout": {"type": "integer", "description": "Max seconds", "default": 60},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the public web with DuckDuckGo. Use this when the user asks about current events, external facts, or anything outside local files/memory.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results (1-10)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch readable text from a public http/https URL. Private/internal addresses and binary content are blocked.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Public URL to fetch"},
                    "max_bytes": {"type": "integer", "description": "Max extracted text bytes", "default": 200_000},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "acrux_recall",
            "description": "Search the Acrux's long-term memory for relevant facts or past episodes.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "acrux_remember_fact",
            "description": "Store a fact in the Acrux's long-term memory.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The fact to remember"},
                    "source": {
                        "type": "string",
                        "description": "Where this came from",
                        "default": "acrux-app",
                    },
                    "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "acrux_record_test",
            "description": "Record a test result in the Acrux.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_name": {"type": "string"},
                    "file_path": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "output": {"type": "string"},
                    "duration_ms": {"type": "integer"},
                    "root_cause": {"type": "string"},
                },
                "required": ["test_name", "passed"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "acrux_record_dependency",
            "description": "Record a dependency between project artifacts.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_ref": {"type": "string"},
                    "source_type": {"type": "string"},
                    "target_ref": {"type": "string"},
                    "target_type": {"type": "string"},
                    "dependency_type": {"type": "string"},
                },
                "required": ["source_ref", "target_ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "acrux_record_review",
            "description": "Record a code review comment.",
            "category": "safe",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "line_range": {"type": "string"},
                    "comment": {"type": "string"},
                    "reviewer": {"type": "string"},
                },
                "required": ["file_path", "comment"],
            },
        },
    },
]


def _tool_category(name: str) -> str:
    for t in ALL_TOOLS:
        if t["function"]["name"] == name:
            return t["function"].get("category", "safe")
    return "safe"


def _tools_for(allowed: list[str]) -> list[dict[str, Any]]:
    allowed_set = set(allowed)
    return [t for t in ALL_TOOLS if t["function"]["name"] in allowed_set]


async def _execute_tool(
    name: str,
    arguments: dict[str, Any],
    workspace: str,
    project: str,
    use_memory: bool = True,
) -> str:
    if name == "read_file":
        target = _workspace_safe_path(workspace, arguments.get("path", ""))
        if not target.is_file():
            return f"Error: file not found: {arguments.get('path')}"
        try:
            text = target.read_text(errors="replace")
            return text[:20_000] + ("\n... (truncated)" if len(text) > 20_000 else "")
        except Exception as e:
            return f"Error reading file: {e}"

    if name == "list_files":
        target = _workspace_safe_path(workspace, arguments.get("path", "."))
        if not target.is_dir():
            return f"Error: directory not found: {arguments.get('path')}"
        lines = []
        for item in sorted(target.iterdir()):
            marker = "📁" if item.is_dir() else "📄"
            lines.append(f"{marker} {item.name}")
        return "\n".join(lines) or "(empty)"

    if name == "write_file":
        rel = arguments.get("path", "")
        content = arguments.get("content", "")
        if not rel:
            return "Error: path is required"
        if len(content) > 1_000_000:
            return "Error: content too large (max 1MB)"
        try:
            target = _workspace_safe_path(workspace, rel)
        except ValueError as e:
            return f"Error: {e}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            return f"Wrote {len(content)} bytes to {rel}"
        except Exception as e:
            return f"Error writing file: {e}"

    if name == "run_command":
        cmd = arguments.get("command", "")
        timeout = int(arguments.get("timeout", 60))
        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    cmd,
                    cwd=workspace,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                ),
                timeout=timeout,
            )
            stdout, _ = await proc.communicate()
            out = stdout.decode(errors="replace")[:20_000]
            return f"exit {proc.returncode}\n{out}"
        except asyncio.TimeoutError:
            return f"Error: command timed out after {timeout}s"
        except Exception as e:
            return f"Error running command: {e}"

    if name == "web_search":
        return await _web_search(
            arguments.get("query", ""), arguments.get("num_results", 5)
        )

    if name == "web_fetch":
        return await _web_fetch(
            arguments.get("url", ""), arguments.get("max_bytes", 200_000)
        )

    if name == "acrux_recall":
        if not use_memory:
            return "Memory disabled for this chat"
        query = arguments.get("query", "")
        limit = int(arguments.get("limit", 5))
        parts = [f"Memory search for: {query}"]
        semantic = _project_semantic(project)
        episodic = _project_episodic(project)
        procedural = _project_procedural(project)
        facts = await semantic.search(project, query, limit)
        episodes = episodic.search(project, query, limit)
        skills = procedural.search(project, query, limit)
        if facts:
            parts.append("Facts:")
            for f in facts:
                parts.append(f"- {f.content}")
        if episodes:
            parts.append("Episodes:")
            for e in episodes:
                parts.append(f"- {e.task}: {e.outcome}")
        if skills:
            parts.append("Skills:")
            for s in skills:
                parts.append(f"- {s.name}: {' '.join(s.procedure)}")
        if not facts and not episodes and not skills:
            parts.append("No relevant memories found.")
        return "\n".join(parts)

    if name == "acrux_remember_fact":
        if not use_memory:
            return "Memory disabled for this chat"
        content = arguments.get("content", "")
        if not content:
            return "Error: empty content"
        semantic = _project_semantic(project)
        fact = Fact(
            project=project,
            content=content,
            source=arguments.get("source", "acrux-app"),
            tags=arguments.get("tags", []),
        )
        _attach_git_info(fact, workspace or ".")
        await semantic.add(fact)
        return "Fact stored."

    if name == "acrux_record_test":
        semantic = _project_semantic(project)
        semantic.add_test_result(
            project,
            {
                "test_name": arguments.get("test_name", ""),
                "file_path": arguments.get("file_path"),
                "passed": bool(arguments.get("passed", False)),
                "output": arguments.get("output", ""),
                "duration_ms": int(arguments.get("duration_ms", 0)),
                "root_cause": arguments.get("root_cause"),
            },
        )
        return "Test result recorded."

    if name == "acrux_record_dependency":
        semantic = _project_semantic(project)
        semantic.add_dependencies(
            project,
            [
                {
                    "source_ref": arguments.get("source_ref", ""),
                    "source_type": arguments.get("source_type", "file"),
                    "target_ref": arguments.get("target_ref", ""),
                    "target_type": arguments.get("target_type", "file"),
                    "dependency_type": arguments.get("dependency_type", "depends_on"),
                }
            ],
        )
        return "Dependency recorded."

    if name == "acrux_record_review":
        semantic = _project_semantic(project)
        semantic.add_review(
            project,
            {
                "file_path": arguments.get("file_path", ""),
                "line_range": arguments.get("line_range", ""),
                "comment": arguments.get("comment", ""),
                "reviewer": arguments.get("reviewer", "assistant"),
            },
        )
        return "Review comment recorded."

    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Reasoning extraction
# ---------------------------------------------------------------------------


def _extract_word_target(text: str) -> int | None:
    """Look for an explicit word-count request like '1000 words', '500 word'."""
    import re
    match = re.search(r"(\d+)\s*word(?:s)?\b", text.lower())
    if match:
        return int(match.group(1))
    return None


async def _expand_file_to_word_count(workspace: str, rel: str, target: int, model: str) -> tuple[int, int]:
    """Directly ask the model to expand a written file to the requested word count.

    Returns (previous_word_count, new_word_count). If expansion fails or is not
    needed, new_word_count equals previous_word_count.
    """
    try:
        target = max(target, 50)
        path = _workspace_safe_path(workspace, rel)
        text = path.read_text(errors="ignore")
        prev = len(text.split())
        if prev >= int(target * 0.9):
            return prev, prev
        prompt = (
            f"The following markdown document is currently about {prev} words. "
            f"Rewrite and expand it to approximately {target} words. "
            "Keep the same structure, tone, and headings. Add depth, examples, and detail. "
            "Output ONLY the full expanded markdown document, with no extra commentary.\n\n"
            f"{text}"
        )
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.4, "num_predict": int(target * 1.8)},
                },
            )
            r.raise_for_status()
            expanded = r.json().get("response", "").strip()
        if not expanded:
            return prev, prev
        # Strip any wrapping the model might add.
        for prefix in ("```markdown", "```"):
            if expanded.startswith(prefix):
                expanded = expanded[len(prefix):].strip()
        if expanded.endswith("```"):
            expanded = expanded[:-3].strip()
        path.write_text(expanded)
        new = len(expanded.split())
        return prev, new
    except Exception:
        return 0, 0


_WRITE_EXTENSIONS = {
    "md", "txt", "py", "js", "ts", "html", "css", "json", "yaml", "yml",
    "go", "rs", "c", "cpp", "swift", "java", "kt", "php", "rb", "sh",
}
_WRITE_VERBS = {"write", "create", "generate", "produce", "make", "build", "draft"}


def _extract_file_target(text: str, workspace: str = "") -> Path | None:
    """Find a writable file path in the user's message.

    Handles quoted paths, escaped spaces, absolute paths, and paths relative to
    the selected workspace.
    """
    marker = "\x00"
    normalized = text.replace("\\ ", marker)

    # 1) Quoted paths
    for quote in ('"', "'"):
        pattern = re.compile(
            re.escape(quote)
            + r"([^\n" + re.escape(quote) + r"]+\.\w{1,10})"
            + re.escape(quote)
        )
        for m in pattern.finditer(normalized):
            candidate = m.group(1).replace(marker, " ")
            target = _resolve_write_target(candidate, workspace)
            if target:
                return target

    # 2) Bare paths ending in a writable extension
    pattern = re.compile(
        r"(?:^|\s)([^\s\"']+\.\w{1,10})(?=[\s.,;:!?]|$)", re.IGNORECASE
    )
    for m in pattern.finditer(normalized):
        candidate = m.group(1).replace(marker, " ")
        target = _resolve_write_target(candidate, workspace)
        if target:
            return target

    return None


def _resolve_write_target(candidate: str, workspace: str) -> Path | None:
    """Return a safe, absolute Path for a candidate file string."""
    candidate = candidate.strip().strip("\"'")
    ext = Path(candidate).suffix.lstrip(".").lower()
    if ext not in _WRITE_EXTENSIONS:
        return None

    p = Path(candidate).expanduser()
    if p.is_absolute():
        p = p.resolve()
    elif workspace:
        try:
            p = _workspace_safe_path(workspace, candidate)
        except Exception:
            return None
    else:
        return None

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return p


async def _direct_write_longform(
    user_text: str,
    target_path: Path,
    word_target: int,
    model: str,
) -> tuple[int, str]:
    """Generate a long-form document in one direct Ollama call and write it.

    Returns (word_count, full_text). The caller is responsible for streaming
    progress and confirmation to the UI so the full document can stay out of
    the chat transcript.
    """
    word_target = max(word_target, 50)
    ext = target_path.suffix.lstrip(".").lower()
    format_hint = (
        "Use Markdown formatting (headings, bullets, paragraphs). "
        if ext in {"md", "markdown", "mdown"}
        else ""
    )

    prompt = (
        "/no_think\n"
        "You are an expert writer and assistant. "
        "Follow the user's request exactly and produce the requested document.\n\n"
        f"User request: {user_text}\n\n"
        f"Your target is at least {word_target} words, ending as close to {word_target} words as possible. "
        "Do not stop early. Continue adding depth, examples, sub-sections, and nuance until you reach the target. "
        "Do not wrap the output in markdown code fences. "
        f"{format_hint}"
        "Output ONLY the document content, with no extra commentary."
    )

    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.4,
                    "num_predict": int(word_target * 2.2),
                    "num_ctx": 8192,
                },
            },
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()

    # Strip possible code fences
    for prefix in ("```markdown", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    target_path.write_text(text, encoding="utf-8")
    word_count = len(text.split())
    return word_count, text


def _extract_reasoning(text: str, native_reasoning: str = "") -> tuple[str, str]:
    """Split reasoning tags from final content.

    Handles:
      - Ollama's native `message.reasoning` field (Qwen3, DeepSeek-R1, etc.)
      - <think>...</think> tags
      - <reasoning>...</reasoning> tags
    """
    if native_reasoning:
        return native_reasoning.strip(), text.strip()

    for open_tag, close_tag in (("<think>", "</think>"), ("<reasoning>", "</reasoning>")):
        if open_tag in text and close_tag in text:
            start = text.index(open_tag) + len(open_tag)
            end = text.index(close_tag, start)
            reasoning = text[start:end].strip()
            remainder = text[: text.index(open_tag)] + text[end + len(close_tag) :]
            return reasoning, remainder.strip()

    return "", text.strip()


# ---------------------------------------------------------------------------
# WebSocket chat
# ---------------------------------------------------------------------------


async def _race_with_stop(
    coro: asyncio.Task,
    stop_event: asyncio.Event,
    timeout: float | None = None,
) -> Any:
    """Await ``coro`` until it finishes, ``stop_event`` is set, or ``timeout`` expires.

    Returns the coroutine's result. Raises ``asyncio.CancelledError`` if stopped
    by the user or ``asyncio.TimeoutError`` on timeout. The coroutine task is
    cancelled in both stop/timeout cases.
    """
    stop_task = asyncio.create_task(stop_event.wait())
    tasks: set[asyncio.Task] = {coro, stop_task}
    timeout_task: asyncio.Task | None = None
    if timeout is not None:
        timeout_task = asyncio.create_task(asyncio.sleep(timeout))
        tasks.add(timeout_task)

    done: set[asyncio.Task] = set()
    pending: set[asyncio.Task] = set()
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    if coro in done:
        return await coro
    if stop_task in done:
        coro.cancel()
        try:
            await coro
        except asyncio.CancelledError:
            pass
        raise asyncio.CancelledError("Stopped by user")
    if timeout_task is not None and timeout_task in done:
        coro.cancel()
        try:
            await coro
        except asyncio.CancelledError:
            pass
        raise asyncio.TimeoutError("Generation timed out")
    return await coro


async def _receive_loop(
    websocket: WebSocket, message_queue: asyncio.Queue, stop_event: asyncio.Event
) -> None:
    """Read all WebSocket messages and route pings/stops separately."""
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            msg_type = msg.get("type")
            if msg_type == "ping":
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception:
                    pass
            elif msg_type == "stop":
                stop_event.set()
            else:
                await message_queue.put(msg)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await message_queue.put(None)


async def _dequeue(
    message_queue: asyncio.Queue, stop_event: asyncio.Event
) -> Any | None:
    """Return the next queued message, or None if a stop was requested."""
    if stop_event.is_set():
        return None
    get_task = asyncio.create_task(message_queue.get())
    stop_task = asyncio.create_task(stop_event.wait())
    done: set[asyncio.Task] = set()
    pending: set[asyncio.Task] = set()
    try:
        done, pending = await asyncio.wait(
            {get_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    if stop_event.is_set():
        return None
    return await get_task


async def _wait_for_tool_approval(
    message_queue: asyncio.Queue,
    stop_event: asyncio.Event,
    tool_id: str,
    timeout: float = 600.0,
) -> dict[str, Any] | None:
    """Wait for an approval matching ``tool_id``.

    Stale approvals/denials for other tool ids are drained and ignored so they
    cannot accidentally deny a later tool call. Non-approval messages (e.g. a
    new user message arriving out of band) are re-queued for the next consumer.
    Returns ``None`` if the user stopped or the wait timed out.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        if stop_event.is_set():
            return None
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return None

        get_task = asyncio.create_task(message_queue.get())
        stop_task = asyncio.create_task(stop_event.wait())
        timeout_task = asyncio.create_task(asyncio.sleep(remaining))
        done: set[asyncio.Task] = set()
        pending: set[asyncio.Task] = set()
        try:
            done, pending = await asyncio.wait(
                {get_task, stop_task, timeout_task}, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        if stop_task in done:
            return None
        if timeout_task in done:
            return None

        msg = await get_task
        if msg is None:
            return None
        msg_type = msg.get("type")
        msg_id = msg.get("id")
        if msg_type in ("approve_tool", "deny_tool") and msg_id == tool_id:
            return msg
        if msg_type in ("approve_tool", "deny_tool") and msg_id != tool_id:
            # Drain stale approval/denial.
            continue
        # Re-queue unrelated messages so they are not lost.
        try:
            message_queue.put_nowait(msg)
        except Exception:
            pass
        # A non-approval message while waiting means the user did something else;
        # treat as denial to avoid hanging.
        return None


async def _run_generation(
    websocket: WebSocket,
    chat_id: str,
    start_msg: dict[str, Any],
    messages: list[dict[str, Any]],
    meta: dict[str, Any],
    title: str,
    stop_event: asyncio.Event,
    message_queue: asyncio.Queue,
) -> str:
    """Run one assistant generation turn, honoring stop requests."""
    stop_event.clear()
    user_text = start_msg.get("message", "")
    word_target = _extract_word_target(user_text)
    model = start_msg.get("model", _cfg.reflection.model if _cfg else "qwen3:14b")
    workspace = start_msg.get("workspace", "")
    auto_accept = bool(start_msg.get("auto_accept", False))
    use_memory = bool(start_msg.get("use_memory", True))
    allowed_tools = start_msg.get("allowed_tools", [t["function"]["name"] for t in ALL_TOOLS])
    meta.update(
        {
            "model": model,
            "workspace": workspace,
            "allowed_tools": allowed_tools,
            "use_memory": use_memory,
        }
    )

    if workspace and not Path(workspace).exists():
        await websocket.send_json(
            {"type": "error", "message": "Workspace folder does not exist"}
        )
        return title

    # Append user message.
    messages.append(
        {
            "role": "user",
            "content": user_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    if not title or title == "New task":
        title = user_text[:40] + ("..." if len(user_text) > 40 else "")
    _save_chat(chat_id, title, messages, meta)

    # Fast path: explicit word-count document requests skip the slow tool loop.
    if (
        word_target
        and model
        and model != "kimi"
        and any(v in user_text.lower() for v in _WRITE_VERBS)
    ):
        target_path = _extract_file_target(user_text, workspace)
        if target_path:
            try:
                await websocket.send_json({"type": "assistant_start"})
                await websocket.send_json(
                    {"type": "content", "content": f"Writing {target_path.name}..."}
                )
                word_count, _ = await _direct_write_longform(
                    user_text, target_path, word_target, model
                )
                confirmation = (
                    f"Wrote {target_path.name} ({word_count} words) to "
                    f"{target_path.parent}."
                )
                await websocket.send_json(
                    {"type": "content", "content": f"\n{confirmation}"}
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": confirmation,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                await websocket.send_json({"type": "done"})
                _save_chat(chat_id, title, messages, meta)
                return title
            except Exception:
                # Fall back to the normal tool-loop path.
                pass

    project = _project_for(workspace) if workspace else "default"
    project_prompt = ""
    if workspace:
        semantic_project = _project_semantic(project)
        prompt_row = semantic_project.get_system_prompt(project)
        if prompt_row:
            project_prompt = prompt_row.get("prompt_text", "") + "\n"
    word_target_hint = f"The user requested approximately {word_target} words. Meet this target closely; do not undershoot by more than 10%.\n" if word_target else ""
    memory_context = await _recall_context(project, user_text, limit=8)
    if memory_context:
        memory_context = "\n" + memory_context + "\n\n"
    system_prompt = (
        "/no_think\n"
        "You are the Acrux assistant, the execution layer of the Acrux memory system. "
        "You are a senior engineer, writer, analyst, and problem solver with local file access, long-term memory, and web access. "
        "Your single purpose is to execute the user's request completely, accurately, and with no unnecessary back-and-forth.\n\n"
        "MANDATORY RULES — follow these above all else:\n\n"
        "1. IDENTITY\n"
        "   - You are the Acrux assistant. Acrux is the memory/logging system around you; do not confuse yourself with the system.\n"
        "   - Be direct, concise, and useful. No filler, no apologies, no \"As an AI\", no unsolicited warnings.\n\n"
        "2. OBEY THE SPEC\n"
        "   - Treat every user message as a specification. Follow it literally.\n"
        "   - If the user asks for N words, lines, files, sections, examples, tests, etc., produce exactly N unless it is impossible.\n"
        "   - If the user names a format (.md, .py, .json, table, CSV, list, etc.), use that format exactly.\n"
        "   - If the user names a path, use that path exactly. Relative paths are inside the workspace; absolute paths are used as given.\n\n"
        "3. NO HALLUCINATION\n"
        "   - You MUST NOT invent APIs, functions, file paths, environment details, security risks, or failure modes.\n"
        "   - If you lack information, use acrux_recall, read_file, list_files, web_search, or web_fetch to verify. If still unknown, say \"I don't know\" — do not guess.\n\n"
        "4. REASONING\n"
        "   - Think step by step internally. NEVER output <think>, <reasoning>, or any internal planning.\n"
        "   - For math/logic, show only the minimal steps needed; otherwise give the answer directly.\n\n"
        "5. FILES\n"
        "   - To create or modify files, ALWAYS use the write_file tool. NEVER use run_command with echo/cat/heredoc to write files.\n"
        "   - write_file content MUST be the complete final file. Do not abbreviate with \"... rest unchanged\".\n"
        "   - After writing, the assistant chat message must be a one-sentence confirmation only. Never paste the file content into chat.\n\n"
        "6. TOOLS\n"
        "   - Read relevant files before editing. Use read_file, list_files, and grep as needed.\n"
        "   - Do not make redundant tool calls.\n"
        "   - run_command is only for actions that cannot be done with a file tool. Destructive commands require approval.\n\n"
        "7. MEMORY\n"
        "   - Before assuming anything about the project, prior tasks, or user preferences, recall or read first.\n"
        "   - The final answer will be recorded as an episode; make it clear and complete.\n"
        "   - When you use recalled memory, cite the source tag (e.g. [memory:fact:42], [memory:skill:abc123]) in your response.\n\n"
        "8. CODING\n"
        "   - Write complete, idiomatic, production-quality code.\n"
        "   - Include error handling, validation, and edge cases matching the task scope.\n"
        "   - Add or update tests if the project has tests. Do not break existing code; update callers when interfaces change.\n"
        "   - Match the existing style, naming, and structure of the codebase.\n\n"
        "9. WRITING\n"
        "   - Match the requested length, style, tone, and point of view exactly.\n"
        "   - Do not wrap markdown output in ```markdown fences when writing files.\n\n"
        "10. VERIFICATION\n"
        "    - Before finishing, mentally verify that your output satisfies every part of the user's request. If it does not, continue.\n\n"
        "11. WEB RESEARCH\n"
        "    - If the user asks about current events, external facts, or anything outside local files/memory, use web_search.\n"
        "    - If the user gives a URL, use web_fetch to read it.\n"
        "    - Only fetch public http/https URLs. NEVER fetch private/internal addresses, file:// URLs, or execute downloaded content.\n"
        "    - Summarize sources and cite URLs. Do not dump raw HTML into chat.\n\n"
        f"Current workspace: {workspace or '(none)'}\n"
        f"{project_prompt}"
        f"{memory_context}"
        f"{word_target_hint}"
    )

    ollama_messages = [{"role": "system", "content": system_prompt}]
    # Include recent messages for context (last 20).
    for m in messages[-21:-1]:
        ollama_messages.append({"role": m["role"], "content": m.get("content", "")})
        if "tool_calls" in m:
            ollama_messages[-1]["tool_calls"] = m["tool_calls"]
        if "tool_results" in m:
            for tr in m["tool_results"]:
                ollama_messages.append({"role": "tool", "content": tr["output"]})
    ollama_messages.append({"role": "user", "content": user_text})

    max_turns = 10
    loop_mode = bool(start_msg.get("loop_mode", False))
    checkpoint_interval = int(start_msg.get("checkpoint_interval", 3))
    checkpoint_tools = start_msg.get("checkpoint_tools", ["run_command"])
    meta.update(
        {
            "loop_mode": loop_mode,
            "checkpoint_interval": checkpoint_interval,
            "checkpoint_tools": checkpoint_tools,
        }
    )

    stopped = False

    for turn in range(max_turns):
        if stop_event.is_set():
            stopped = True
            break

        tools = _tools_for(allowed_tools)
        # Qwen3's streaming path is unreliable when many tools are present
        # (it tends to reason indefinitely without emitting content or tool_calls).
        # Fall back to non-streaming for tool-enabled turns so tool execution is reliable.
        use_streaming = not tools
        options = {"temperature": 0.4}
        if word_target:
            options["num_predict"] = int(word_target * 1.8)
        payload: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": use_streaming,
            "options": options,
        }
        if tools:
            payload["tools"] = tools

        accumulated_content = ""
        accumulated_thinking = ""
        tool_calls: list[dict[str, Any]] = []
        sent_assistant_start = False
        stream_error: str | None = None

        if use_streaming:
            chunk_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

            async def _stream_ollama() -> None:
                try:
                    async with httpx.AsyncClient(timeout=600.0) as client:
                        async with client.stream(
                            "POST", f"{OLLAMA_HOST}/api/chat", json=payload
                        ) as response:
                            response.raise_for_status()
                            async for line in response.aiter_lines():
                                if not line.strip():
                                    continue
                                try:
                                    chunk = json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                                await chunk_queue.put(chunk)
                                if chunk.get("done"):
                                    break
                except asyncio.CancelledError:
                    raise
                except httpx.HTTPStatusError as e:
                    await chunk_queue.put({"_error": f"HTTP error: {e.response.status_code}"})
                except httpx.RequestError as e:
                    await chunk_queue.put({"_error": f"Request error: {e}"})
                except Exception as e:
                    await chunk_queue.put({"_error": str(e)})
                finally:
                    await chunk_queue.put(None)

            stream_task = asyncio.create_task(_stream_ollama())

            try:
                while True:
                    get_chunk = asyncio.create_task(chunk_queue.get())
                    stop_wait = asyncio.create_task(stop_event.wait())
                    timeout_wait = asyncio.create_task(asyncio.sleep(60.0))
                    done_tasks: set[asyncio.Task] = set()
                    pending_tasks: set[asyncio.Task] = set()
                    try:
                        done_tasks, pending_tasks = await asyncio.wait(
                            {get_chunk, stop_wait, timeout_wait}, return_when=asyncio.FIRST_COMPLETED
                        )
                    finally:
                        for task in pending_tasks:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                    if stop_wait in done_tasks:
                        stream_task.cancel()
                        try:
                            await stream_task
                        except asyncio.CancelledError:
                            pass
                        stopped = True
                        break

                    if timeout_wait in done_tasks:
                        stream_task.cancel()
                        try:
                            await stream_task
                        except asyncio.CancelledError:
                            pass
                        stream_error = "Generation timed out after 60 seconds of no response"
                        break

                    chunk = await get_chunk
                    if chunk is None:
                        break

                    if "_error" in chunk:
                        stream_error = chunk["_error"]
                        break

                    msg = chunk.get("message", {})
                    delta_content = msg.get("content", "")
                    delta_thinking = msg.get("thinking", "") or msg.get("reasoning", "")
                    done = chunk.get("done", False)

                    for tc in msg.get("tool_calls", []):
                        tid = tc.get("id")
                        if tid:
                            tool_calls = [t for t in tool_calls if t.get("id") != tid]
                            tool_calls.append(tc)
                        else:
                            tool_calls.append(tc)

                    if delta_thinking:
                        accumulated_thinking += delta_thinking

                    if delta_content:
                        if not sent_assistant_start:
                            await websocket.send_json({"type": "assistant_start"})
                            sent_assistant_start = True
                        accumulated_content += delta_content
                        await websocket.send_json(
                            {"type": "content", "content": delta_content}
                        )

                    if done:
                        break
            except asyncio.CancelledError:
                stream_task.cancel()
                try:
                    await stream_task
                except asyncio.CancelledError:
                    pass
                stopped = True
        else:
            async with httpx.AsyncClient(timeout=600.0) as client:
                post_task: asyncio.Task = asyncio.create_task(
                    client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
                )
                try:
                    r = await _race_with_stop(post_task, stop_event, timeout=300.0)
                    r.raise_for_status()
                    result = r.json()
                except httpx.HTTPStatusError as e:
                    stream_error = f"HTTP error: {e.response.status_code}"
                except httpx.RequestError as e:
                    stream_error = f"Request error: {e}"
                except asyncio.TimeoutError:
                    stream_error = "Generation timed out after 300 seconds"
                except asyncio.CancelledError:
                    stopped = True
                except Exception as e:
                    stream_error = str(e)
                else:
                    assistant_msg = result.get("message", {})
                    accumulated_content = assistant_msg.get("content", "")
                    accumulated_thinking = (
                        assistant_msg.get("reasoning", "") or assistant_msg.get("thinking", "")
                    )
                    tool_calls = assistant_msg.get("tool_calls", [])
                    if accumulated_content:
                        await websocket.send_json({"type": "assistant_start"})
                        for token in accumulated_content.split(" "):
                            await websocket.send_json(
                                {"type": "content", "content": token + " "}
                            )

        if stopped:
            break

        if stream_error:
            await websocket.send_json({"type": "error", "message": stream_error})
            return title

        reasoning, final_content = _extract_reasoning(
            accumulated_content, accumulated_thinking
        )

        if not tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": final_content,
                    "reasoning": reasoning,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            _record_memory_outcomes(project, memory_context, success=True)
            await websocket.send_json({"type": "done"})
            _save_chat(chat_id, title, messages, meta)
            return title

        # There are tool calls. Determine if a checkpoint is needed.
        tool_calls_data = []
        tool_results_data = []
        any_destructive = False
        for tc in tool_calls:
            name = tc.get("function", {}).get("name", tc.get("name"))
            if _tool_category(name) in ("destructive", "irreversible"):
                any_destructive = True
        needs_checkpoint = (
            loop_mode
            and not auto_accept
            and (any_destructive or (turn + 1) % checkpoint_interval == 0)
        )
        auto_accept_batch = False
        if needs_checkpoint:
            await websocket.send_json(
                {
                    "type": "checkpoint",
                    "turn": turn + 1,
                    "tool_count": len(tool_calls),
                    "message": "Approve this batch of tool calls?",
                }
            )
            cp = await _dequeue(message_queue, stop_event)
            if cp is None:
                cp = {"action": "stop"}
            action = cp.get("action", "step")
            if action == "stop":
                await websocket.send_json(
                    {"type": "error", "message": "Agent loop stopped at checkpoint"}
                )
                return title
            if action == "resume":
                auto_accept_batch = True

        for tc in tool_calls:
            name = tc.get("function", {}).get("name", tc.get("name"))
            args = tc.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            tool_id = str(uuid.uuid4())
            tool_calls_data.append({"id": tool_id, "name": name, "arguments": args})

            if not auto_accept and not auto_accept_batch:
                await websocket.send_json(
                    {
                        "type": "tool_call",
                        "id": tool_id,
                        "name": name,
                        "arguments": args,
                    }
                )
                # Wait for approve / deny.
                approval = await _wait_for_tool_approval(message_queue, stop_event, tool_id)
                if approval is None or approval.get("type") != "approve_tool":
                    output = "Tool execution denied by user."
                    await websocket.send_json(
                        {"type": "tool_result", "id": tool_id, "output": output}
                    )
                    tool_results_data.append(
                        {"id": tool_id, "name": name, "output": output}
                    )
                    continue

            output = await _execute_tool(
                name, args, workspace or ".", project, use_memory
            )

            # If the user asked for a specific word count, expand the file now.
            if name == "write_file" and word_target:
                rel = args.get("path", "")
                if rel:
                    prev, new = await _expand_file_to_word_count(
                        workspace or ".", rel, word_target, model
                    )
                    if new > prev:
                        output += (
                            f"\n\nExpanded from {prev} to {new} words "
                            f"to meet the requested {word_target} words."
                        )

            await websocket.send_json(
                {"type": "tool_result", "id": tool_id, "name": name, "output": output}
            )
            tool_results_data.append({"id": tool_id, "name": name, "output": output})

            # On error in loop mode, offer a checkpoint before continuing.
            if loop_mode and any(
                w in (output or "").lower() for w in ("error", "fail", "exception")
            ):
                await websocket.send_json(
                    {
                        "type": "checkpoint",
                        "turn": turn + 1,
                        "tool": name,
                        "message": f"Tool {name} reported an error. Continue?",
                    }
                )
                cp = await _dequeue(message_queue, stop_event)
                if cp is None:
                    cp = {"action": "stop"}
                if cp.get("action", "step") == "stop":
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Agent loop stopped after tool error",
                        }
                    )
                    return title

        # Append assistant turn with tool calls and results.
        messages.append(
            {
                "role": "assistant",
                "content": final_content,
                "reasoning": reasoning,
                "tool_calls": tool_calls_data,
                "tool_results": tool_results_data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        _save_chat(chat_id, title, messages, meta)

        # Build next Ollama messages.
        ollama_messages.append(
            {
                "role": "assistant",
                "content": final_content,
                "tool_calls": [
                    {"function": {"name": tc["name"], "arguments": tc["arguments"]}}
                    for tc in tool_calls_data
                ],
            }
        )
        for tr in tool_results_data:
            ollama_messages.append({"role": "tool", "content": tr["output"]})

    else:
        await websocket.send_json({"type": "error", "message": "Too many tool turns"})
        return title

    if stopped:
        reasoning, final_content = _extract_reasoning(
            accumulated_content, accumulated_thinking
        )
        messages.append(
            {
                "role": "assistant",
                "content": final_content,
                "reasoning": reasoning,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await websocket.send_json({"type": "stopped"})
        _save_chat(chat_id, title, messages, meta)

    return title


@app.websocket("/ws/chat/{chat_id}")
async def chat_socket(websocket: WebSocket, chat_id: str) -> None:
    if _cfg and _cfg.api_auth:
        auth = websocket.headers.get("authorization", "")
        token = (
            websocket.query_params.get("token")
            or websocket.headers.get("x-acrux-token")
            or auth.replace("Bearer ", "")
        )
        if token != _cfg.api_token:
            await websocket.close(code=4401)
            return
    await websocket.accept()

    # Load or create chat metadata.
    path = _chat_path(chat_id)
    if path.exists():
        data = json.loads(path.read_text())
        messages = data.get("messages", [])
        meta = {
            "created_at": data.get("created_at"),
            "model": data.get("model"),
            "workspace": data.get("workspace"),
            "allowed_tools": data.get("allowed_tools", []),
        }
        title = data.get("title", "Untitled")
    else:
        messages = []
        meta = {}
        title = "New task"

    message_queue: asyncio.Queue = asyncio.Queue()
    stop_event = asyncio.Event()
    receive_task = asyncio.create_task(
        _receive_loop(websocket, message_queue, stop_event)
    )

    try:
        while True:
            msg = await message_queue.get()
            if msg is None:
                break
            msg_type = msg.get("type")

            # --- Start a new assistant turn ---
            if msg_type == "start":
                title = await _run_generation(
                    websocket,
                    chat_id,
                    msg,
                    messages,
                    meta,
                    title,
                    stop_event,
                    message_queue,
                )
                stop_event.clear()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# Memory management endpoints
# ---------------------------------------------------------------------------


def _parse_duration(value: str) -> int | None:
    value = value.strip().lower()
    if value.endswith("d"):
        try:
            return int(value[:-1])
        except ValueError:
            return None
    try:
        return int(value)
    except ValueError:
        return None


@app.post("/api/acrux/compact")
async def compact_memory(
    project: str = Query(default="default"),
    days: int = Query(default=30, ge=1),
) -> dict[str, Any]:
    """Summarize old episodes into facts and mark them compacted.

    Kimi episodes are processed with a strict, high-signal prompt so they do not
    pollute normal user task memory.
    """
    if not _cfg or _cfg.reflection.provider != "ollama":
        return {"status": "skipped", "message": "Compaction requires ollama reflection provider."}

    from acrux.reflection.ollama import OllamaProvider

    episodic = _project_episodic(project)
    semantic = _project_semantic(project)
    procedural = _project_procedural(project)
    old_episodes = episodic.get_old(project, days)
    if not old_episodes:
        return {"status": "ok", "facts_added": 0, "episodes_compacted": 0}

    provider = OllamaProvider(
        _cfg.reflection.routing.get("reflection", _cfg.reflection.model),
        _cfg.reflection.host,
    )

    def is_kimi(e: Episode) -> bool:
        if e.source and e.source.lower().startswith("kimi"):
            return True
        return any(str(tag).lower() == "kimi" for tag in e.tags)

    kimi_episodes = [e for e in old_episodes if is_kimi(e)]
    normal_episodes = [e for e in old_episodes if not is_kimi(e)]

    total_facts = 0
    total_skills = 0

    try:
        if kimi_episodes:
            facts = await provider.reflect_kimi_episodes(kimi_episodes)
            for fact in facts:
                await semantic.add(fact)
            total_facts += len(facts)
            skills = await provider.extract_kimi_skills(kimi_episodes, facts)
            for skill in skills:
                skill.project = project
                procedural.add(skill)
            total_skills += len(skills)

        if normal_episodes:
            facts = await provider.reflect_episodes(normal_episodes)
            for fact in facts:
                await semantic.add(fact)
            total_facts += len(facts)
            skills = await provider.extract_skills(normal_episodes, facts)
            for skill in skills:
                skill.project = project
                procedural.add(skill)
            total_skills += len(skills)
    except Exception as e:
        raise HTTPException(503, f"Could not compact memory: {e}")

    episodic.mark_compacted([e.session_id for e in old_episodes])
    return {
        "status": "ok",
        "facts_added": total_facts,
        "skills_added": total_skills,
        "episodes_compacted": len(old_episodes),
        "kimi_episodes": len(kimi_episodes),
        "normal_episodes": len(normal_episodes),
    }


@app.post("/api/skills/{skill_id}/verify")
async def verify_skill(
    skill_id: str,
    workspace: str = Query(...),
    project: str = Query(default=""),
) -> dict[str, Any]:
    """Run a skill's procedure as a shell script in the workspace and record the result."""
    project = project or _project_for(workspace)
    procedural = _project_procedural(project)
    skill = procedural.get_by_id(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")

    if not Path(workspace).is_dir():
        raise HTTPException(400, "Workspace does not exist")

    script = "\n".join(skill.procedure)
    start = time.time()
    exit_code, output = await run_sandboxed(script, workspace, timeout=120)
    success = exit_code == 0

    elapsed = time.time() - start
    skill.verified = success
    skill.evidence.append(
        {
            "success": success,
            "output": output,
            "elapsed": elapsed,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    total = len(skill.evidence)
    successes = sum(1 for e in skill.evidence if e.get("success"))
    skill.success_rate = successes / total if total > 0 else 0.0
    procedural.update(skill)

    return {
        "skill_id": skill.id,
        "name": skill.name,
        "verified": skill.verified,
        "success_rate": skill.success_rate,
        "exit_code": exit_code,
        "output": output,
    }


@app.get("/api/acrux/conflicts")
async def detect_conflicts(
    project: str = Query(default="default"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """Detect potentially contradictory facts in a project."""
    semantic = _project_semantic(project)
    facts = semantic.get_recent(project, limit=limit)

    # Common contradiction markers
    contradiction_patterns = [
        ("always", "never"),
        ("must", "must not"),
        ("should", "should not"),
        ("is ", "is not "),
        ("can ", "cannot "),
        ("will ", "will not "),
    ]
    negation_words = ("never", "not", "no ", "cannot")

    def _keywords(text: str) -> set[str]:
        return {t for t in text.lower().split() if len(t) > 3}

    conflicts = []
    for i, a in enumerate(facts):
        for b in facts[i + 1 :]:
            a_text = a.content.lower()
            b_text = b.content.lower()
            shared = _keywords(a.content) & _keywords(b.content)
            if len(shared) < 2:
                continue

            contradictory = False
            for pos, neg in contradiction_patterns:
                if pos in a_text and neg in b_text:
                    contradictory = True
                    break
                if pos in b_text and neg in a_text:
                    contradictory = True
                    break

            # Generic negation conflict: one statement negates a shared verb/term
            if not contradictory:
                a_has_neg = any(n in a_text for n in negation_words)
                b_has_neg = any(n in b_text for n in negation_words)
                if a_has_neg != b_has_neg:
                    contradictory = True

            if contradictory:
                if a.id is not None:
                    semantic.record_conflict(a.id)
                if b.id is not None:
                    semantic.record_conflict(b.id)
                conflicts.append(
                    {
                        "fact_a": {
                            "id": a.id,
                            "content": a.content,
                            "timestamp": a.timestamp,
                            "source": a.source,
                        },
                        "fact_b": {
                            "id": b.id,
                            "content": b.content,
                            "timestamp": b.timestamp,
                            "source": b.source,
                        },
                        "shared_keywords": sorted(shared),
                    }
                )

    return {"project": project, "conflicts": conflicts, "count": len(conflicts)}


@app.get("/api/acrux/prune-suggestions")
async def prune_suggestions(
    project: str = Query(default="default"),
    older_than: str = Query(default="30d"),
) -> dict[str, Any]:
    """Suggest memory items that can be pruned."""
    days = _parse_duration(older_than)
    if days is None:
        raise HTTPException(400, f"Invalid duration: {older_than}")

    semantic = _project_semantic(project)
    episodic = _project_episodic(project)

    duplicates = semantic.get_duplicate_facts(project, limit=20)
    old_unrecalled = semantic.get_old_unrecalled_facts(project, days, limit=20)
    failed = episodic.get_failed(project, limit=20)

    return {
        "project": project,
        "older_than_days": days,
        "duplicate_facts": {
            "count": len(duplicates),
            "sample": duplicates,
        },
        "old_unrecalled_facts": {
            "count": len(old_unrecalled),
            "sample": old_unrecalled,
        },
        "failed_episodes": {
            "count": len(failed),
            "sample": [
                {
                    "id": e.session_id,
                    "task": e.task,
                    "outcome": e.outcome,
                    "timestamp": e.timestamp,
                }
                for e in failed
            ],
        },
    }


def _parse_tags(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


@app.get("/api/search")
async def unified_search(
    project: str = Query(default="default"),
    query: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    error_only: bool = Query(default=False),
    tags: str = Query(default=""),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    fact_type: str | None = Query(default=None),
) -> dict[str, Any]:
    """Natural-language search across facts, episodes, and skills."""
    tag_list = _parse_tags(tags)
    semantic = _project_semantic(project)
    episodic = _project_episodic(project)
    procedural = _project_procedural(project)

    facts = (
        await semantic.search(
            project, query, limit, tags=tag_list, since=since, until=until, fact_type=fact_type
        )
        if query
        else semantic.list_facts(
            project, tags=tag_list, limit=limit, since=since, until=until, fact_type=fact_type
        )
    )
    episodes = episodic.search(project, query, limit, error_only=error_only)
    episodes = [e for e in episodes if _matches_tag_filter(e.tags, tag_list)]
    skills = procedural.search(project, query, limit)
    skill_tag_list = _parse_tags(tags)
    skills = [
        s
        for s in skills
        if not skill_tag_list
        or _matches_tag_filter(
            [s.name] + s.preconditions + s.procedure,
            skill_tag_list,
        )
    ]

    results = []
    for f in facts:
        results.append(
            {
                "type": "fact",
                "id": f.id,
                "source": f.source,
                "timestamp": f.timestamp,
                "content": f.content,
                "project": f.project,
                "tags": f.tags,
                "confidence": f.confidence,
                "git_info": f.git_info,
                "fact_type": f.fact_type,
            }
        )
    for e in episodes:
        results.append(
            {
                "type": "episode",
                "source": e.session_id,
                "timestamp": e.timestamp,
                "content": f"{e.task}: {e.outcome}",
                "project": e.project,
                "tags": e.tags,
                "git_info": e.git_info,
            }
        )
    for s in skills:
        results.append(
            {
                "type": "skill",
                "source": s.id,
                "timestamp": s.timestamp,
                "content": f"{s.name}: {' '.join(s.procedure)}",
                "project": s.project,
                "verified": s.verified,
            }
        )

    # Sort by recency
    results.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return {"project": project, "query": query, "results": results[:limit]}


def _matches_tag_filter(item_tags: list[str], filter_tags: list[str]) -> bool:
    if not filter_tags:
        return True
    item_set = set(item_tags)
    return any(t in item_set for t in filter_tags)


# ---------------------------------------------------------------------------
# Memory inspector endpoints
# ---------------------------------------------------------------------------


def _global_all_facts(
    semantic: SemanticStore,
    tags: list[str],
    limit: int,
    offset: int,
    since: str | None,
    until: str | None,
    fact_type: str | None,
    cluster_id: int | None,
) -> list[Any]:
    """Return facts from all projects stored in the global semantic DB."""
    with sqlite3.connect(semantic.db_path) as conn:
        rows = conn.execute("SELECT DISTINCT project FROM facts").fetchall()
        projects = sorted({r[0] for r in rows if r[0]})
    all_facts: list[Any] = []
    for p in projects:
        all_facts.extend(
            semantic.list_facts(
                p,
                tags=tags,
                limit=limit,
                offset=0,
                since=since,
                until=until,
                fact_type=fact_type,
                cluster_id=cluster_id,
            )
        )
    all_facts.sort(key=lambda f: getattr(f, "timestamp", ""), reverse=True)
    return all_facts[offset : offset + limit]


def _global_all_episodes(
    episodic: EpisodicStore,
    tags: list[str],
    limit: int,
    offset: int,
) -> list[Any]:
    with sqlite3.connect(episodic.db_path) as conn:
        rows = conn.execute("SELECT DISTINCT project FROM episodes").fetchall()
        projects = sorted({r[0] for r in rows if r[0]})
    all_eps: list[Any] = []
    for p in projects:
        all_eps.extend(episodic.list_episodes(p, tags=tags, limit=limit, offset=0))
    all_eps.sort(key=lambda e: getattr(e, "timestamp", ""), reverse=True)
    return all_eps[offset : offset + limit]


def _global_all_skills(procedural: ProceduralDBStore, limit: int, offset: int) -> list[Any]:
    skills = procedural.get_all()
    skills.sort(key=lambda s: getattr(s, "timestamp", ""), reverse=True)
    return skills[offset : offset + limit]


@app.get("/api/memories/facts")
async def list_facts(
    project: str = Query(default="default"),
    tags: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    fact_type: str | None = Query(default=None),
    cluster_id: int | None = Query(default=None),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    # When falling back to global memory, show facts from all training topics.
    if semantic is _semantic:
        facts = _global_all_facts(
            semantic, _parse_tags(tags), limit, offset, since, until, fact_type, cluster_id
        )
    else:
        facts = semantic.list_facts(
            project,
            tags=_parse_tags(tags),
            limit=limit,
            offset=offset,
            since=since,
            until=until,
            fact_type=fact_type,
            cluster_id=cluster_id,
        )
    return {
        "project": project,
        "count": len(facts),
        "facts": [f.to_dict() for f in facts],
    }


@app.get("/api/memories/episodes")
async def list_episodes(
    project: str = Query(default="default"),
    tags: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    episodic = _project_episodic(project)
    if episodic is _episodic:
        episodes = _global_all_episodes(episodic, _parse_tags(tags), limit, offset)
    else:
        episodes = episodic.list_episodes(project, tags=_parse_tags(tags), limit=limit, offset=offset)
    return {
        "project": project,
        "count": len(episodes),
        "episodes": [e.to_dict() for e in episodes],
    }


@app.get("/api/memories/skills")
async def list_skills(
    project: str = Query(default="default"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    procedural = _project_procedural(project)
    if procedural is _procedural:
        skills = _global_all_skills(procedural, limit, offset)
    else:
        skills = procedural.list_skills(project, limit=limit, offset=offset)
    return {
        "project": project,
        "count": len(skills),
        "skills": [s.to_dict() for s in skills],
    }


@app.delete("/api/memories/facts/{fact_id}")
async def delete_fact(fact_id: int, project: str = Query(default="default")) -> dict[str, Any]:
    semantic = _project_semantic(project)
    if semantic.delete_by_id(fact_id):
        return {"status": "deleted", "id": fact_id}
    raise HTTPException(404, "Fact not found")


@app.delete("/api/memories/episodes/{session_id}")
async def delete_episode(
    session_id: str, project: str = Query(default="default")
) -> dict[str, Any]:
    episodic = _project_episodic(project)
    if episodic.delete_by_id(session_id):
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(404, "Episode not found")


# ---------------------------------------------------------------------------
# Episode replay
# ---------------------------------------------------------------------------


@app.post("/api/episodes/{session_id}/replay")
async def start_replay(
    session_id: str,
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start a replay session for an episode.

    If the original git commit is recorded, the workspace will be checked out
    to that commit when the repo is clean or ``force`` is true. Otherwise a
    warning is returned and the replay waits.
    """
    found = _find_episode_store(session_id)
    if not found:
        raise HTTPException(404, "Episode not found")
    episode, store = found

    req = request or {}
    workspace = req.get("workspace") or episode.context.get("workspace") or str(Path.cwd())
    workspace_path = Path(workspace).expanduser().resolve()
    force = bool(req.get("force", False))
    auto_approve = bool(req.get("auto_approve", False))

    existing = _replay_sessions.get(session_id)
    if existing and existing.get("status") == "waiting" and force:
        # User is forcing a previously blocked replay.
        existing["force"] = True
        existing["status"] = "running"
        existing["warnings"] = [
            w for w in existing.get("warnings", []) if "uncommitted changes" not in w
        ]
    else:
        warnings: list[str] = []
        git_checkout_ok = False
        commit = (episode.git_info or {}).get("commit")
        if commit and (workspace_path / ".git").is_dir():
            checkout_result = _git_checkout_for_replay(workspace_path, commit, force)
            if not checkout_result["ok"]:
                if "uncommitted changes" in (checkout_result["warning"] or ""):
                    state: dict[str, Any] = {
                        "session_id": session_id,
                        "episode": episode,
                        "store": store,
                        "workspace": str(workspace_path),
                        "project": episode.project,
                        "current_step": 0,
                        "outputs": [],
                        "divergences": [],
                        "warnings": [checkout_result["warning"]],
                        "status": "waiting",
                        "git_checkout_ok": False,
                        "auto_approve": auto_approve,
                        "force": False,
                    }
                    _replay_sessions[session_id] = state
                    return {
                        "session_id": session_id,
                        "status": "waiting",
                        "message": checkout_result["warning"],
                        "total_steps": len(episode.actions),
                        "current_step": 0,
                    }
                warnings.append(checkout_result["warning"])
            else:
                git_checkout_ok = True
        elif commit:
            warnings.append(
                "Original commit recorded but workspace is not a git repo; replaying against current workspace."
            )
        else:
            warnings.append("No original git commit recorded; replaying against current workspace.")

        state = {
            "session_id": session_id,
            "episode": episode,
            "store": store,
            "workspace": str(workspace_path),
            "project": episode.project,
            "current_step": 0,
            "outputs": [],
            "divergences": [],
            "warnings": warnings,
            "status": "running",
            "git_checkout_ok": git_checkout_ok,
            "auto_approve": auto_approve,
            "force": force,
        }
        _replay_sessions[session_id] = state

    state = _replay_sessions[session_id]
    return {
        "session_id": session_id,
        "status": state["status"],
        "total_steps": len(episode.actions),
        "current_step": state["current_step"],
        "warnings": state["warnings"],
    }


@app.get("/api/episodes/{session_id}/replay/status")
async def replay_status(session_id: str) -> dict[str, Any]:
    """Return current replay step, original action, proposed action and diff."""
    state = _replay_sessions.get(session_id)
    if not state:
        raise HTTPException(404, "Replay session not found")
    episode: Episode = state["episode"]
    step = state["current_step"]
    total = len(episode.actions)
    action: Action | None = episode.actions[step] if step < total else None
    proposed = None
    requires_approval = False
    if action:
        proposed = action.to_dict()
        requires_approval = _requires_approval(
            action, state["project"], state.get("auto_approve", False)
        )
    last_output = state["outputs"][-1] if state["outputs"] else None
    return {
        "session_id": session_id,
        "status": state["status"],
        "total_steps": total,
        "current_step": step,
        "original_action": action.to_dict() if action else None,
        "proposed_action": proposed,
        "requires_approval": requires_approval,
        "output_preview": last_output,
        "diff": state["divergences"][-1] if state["divergences"] else None,
        "divergences": state["divergences"],
        "warnings": state["warnings"],
        "git_checkout_ok": state.get("git_checkout_ok", False),
    }


@app.post("/api/episodes/{session_id}/replay/step")
async def replay_step(
    session_id: str,
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the next replay action after approval."""
    state = _replay_sessions.get(session_id)
    if not state:
        raise HTTPException(404, "Replay session not found")
    if state["status"] == "aborted":
        raise HTTPException(400, "Replay has been aborted")
    if state["status"] == "completed":
        raise HTTPException(400, "Replay already completed")
    if state["status"] == "waiting":
        raise HTTPException(
            400, "Replay is waiting for workspace confirmation. Pass force=true to start."
        )

    req = request or {}
    if req.get("auto_approve") is not None:
        state["auto_approve"] = bool(req.get("auto_approve"))

    episode: Episode = state["episode"]
    step = state["current_step"]
    if step >= len(episode.actions):
        raise HTTPException(400, "No more actions to replay")

    action = episode.actions[step]
    if _requires_approval(action, state["project"], state.get("auto_approve", False)):
        return {
            "session_id": session_id,
            "status": "waiting_approval",
            "message": "run_command action requires approval",
            "current_step": step,
            "original_action": action.to_dict(),
            "proposed_action": action.to_dict(),
        }

    name, arguments = _action_to_tool_call(action)
    try:
        output = await _execute_tool(
            name, arguments, state["workspace"], state["project"], use_memory=False
        )
    except Exception as exc:
        output = f"Error executing {name}: {exc}"

    stored_result = action.result or ""
    divergence = _diff_text(stored_result, output)
    state["outputs"].append(output)
    state["divergences"].append(divergence)
    step += 1
    state["current_step"] = step

    if step >= len(episode.actions):
        state["status"] = "completed"
        matches = sum(1 for d in state["divergences"] if d == "(no difference)")
        outcome = (
            f"Replay of {session_id} completed. "
            f"{matches}/{len(episode.actions)} actions matched; "
            f"{len(episode.actions) - matches} diverged."
        )
        replay_episode = Episode(
            session_id=str(uuid.uuid4()),
            task=f"Replay: {episode.task}",
            project=episode.project,
            context={
                "original_session_id": session_id,
                "workspace": state["workspace"],
                "git_checkout_ok": state.get("git_checkout_ok", False),
            },
            actions=[
                Action(
                    tool=a.tool,
                    target=a.target,
                    command=a.command,
                    result=out,
                    diff=div,
                )
                for a, out, div in zip(episode.actions, state["outputs"], state["divergences"])
            ],
            outcome=outcome,
            tags=["replay"] + [t for t in episode.tags if t != "replay"],
            source="replay",
            git_info=_git_info_for(state["workspace"]),
        )
        store: EpisodicStore = state["store"]
        store.add(replay_episode)
        return {
            "session_id": session_id,
            "status": "completed",
            "total_steps": len(episode.actions),
            "current_step": step,
            "output_preview": output,
            "diff": divergence,
            "divergences": state["divergences"],
            "warnings": state["warnings"],
            "new_episode_id": replay_episode.session_id,
            "outcome": outcome,
        }

    return {
        "session_id": session_id,
        "status": "running",
        "total_steps": len(episode.actions),
        "current_step": step,
        "output_preview": output,
        "diff": divergence,
        "divergences": state["divergences"],
        "warnings": state["warnings"],
    }


@app.post("/api/episodes/{session_id}/replay/abort")
async def replay_abort(session_id: str) -> dict[str, Any]:
    """Stop a replay session and discard its in-memory state."""
    state = _replay_sessions.pop(session_id, None)
    if not state:
        raise HTTPException(404, "Replay session not found")
    state["status"] = "aborted"
    return {"session_id": session_id, "status": "aborted"}


@app.post("/api/episodes/{session_id}/replay/restore")
async def replay_restore_commit(session_id: str) -> dict[str, Any]:
    """Restore the workspace to the original episode's git commit."""
    state = _replay_sessions.get(session_id)
    if not state:
        raise HTTPException(404, "Replay session not found")
    episode: Episode = state["episode"]
    commit = (episode.git_info or {}).get("commit")
    if not commit:
        raise HTTPException(400, "No original commit recorded for this episode")
    workspace = Path(state["workspace"])
    if not (workspace / ".git").is_dir():
        raise HTTPException(400, "Workspace is not a git repository")
    result = _git_checkout_for_replay(workspace, commit, force=True)
    if not result["ok"]:
        raise HTTPException(500, result["warning"] or "Restore failed")
    state["warnings"] = [w for w in state.get("warnings", []) if "uncommitted changes" not in w]
    state["git_checkout_ok"] = True
    if state["status"] == "waiting":
        state["status"] = "running"
    return {"session_id": session_id, "status": state["status"], "commit": commit}


@app.delete("/api/memories/skills/{skill_id}")
async def delete_skill(skill_id: str, project: str = Query(default="default")) -> dict[str, Any]:
    procedural = _project_procedural(project)
    if procedural.delete_by_id(skill_id):
        return {"status": "deleted", "id": skill_id}
    raise HTTPException(404, "Skill not found")


@app.patch("/api/memories/facts/{fact_id}")
async def patch_fact(
    fact_id: int,
    project: str = Query(default="default"),
    content: str = Query(default=""),
    tags: str = Query(default=""),
    parent_id: int | None = Query(default=None),
    fact_type: str = Query(default=""),
    inheritance_mode: str = Query(default=""),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    tag_list = _parse_tags(tags) if tags else None
    updated = await semantic.update_fact(
        fact_id,
        content=content if content else None,
        tags=tag_list,
        parent_id=parent_id,
        fact_type=fact_type if fact_type else None,
        inheritance_mode=inheritance_mode if inheritance_mode else None,
    )
    if not updated:
        raise HTTPException(404, "Fact not found")
    return {"status": "updated", "fact": updated.to_dict()}


# ---------------------------------------------------------------------------
# Fact creation (negative knowledge support)
# ---------------------------------------------------------------------------


@app.post("/api/memories/facts")
async def create_fact(
    request: dict[str, Any],
    project: str = Query(default="default"),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    fact = Fact(
        project=project,
        content=request.get("content", ""),
        source=request.get("source", "acrux-app"),
        tags=request.get("tags", []),
        fact_type=request.get("fact_type", "positive"),
        parent_id=request.get("parent_id"),
        inheritance_mode=request.get("inheritance_mode", "none"),
    )
    _attach_git_info(fact, request.get("workspace", "."))
    await semantic.add(fact)
    return {"status": "created", "fact": fact.to_dict()}


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------


@app.get("/api/memories/facts/{fact_id}/tree")
async def get_fact_tree(
    fact_id: int,
    project: str = Query(default="default"),
    depth: int = Query(default=3, ge=1, le=10),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    tree = semantic.get_tree(fact_id, depth=depth)
    if not tree:
        raise HTTPException(404, "Fact not found")
    return {"tree": tree}


@app.post("/api/memories/facts/{fact_id}/children")
async def create_child_fact(
    fact_id: int,
    request: dict[str, Any],
    project: str = Query(default="default"),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    parent = semantic.get_by_id(fact_id)
    if not parent:
        raise HTTPException(404, "Parent fact not found")
    fact = Fact(
        project=project,
        content=request.get("content", ""),
        source=request.get("source", "acrux-app"),
        tags=request.get("tags", []),
        fact_type=request.get("fact_type", "positive"),
    )
    _attach_git_info(fact, request.get("workspace", "."))
    await semantic.create_child_fact(fact_id, fact)
    return {"status": "created", "fact": fact.to_dict()}


@app.post("/api/memories/facts/{fact_id}/link")
async def link_facts(
    fact_id: int,
    request: dict[str, Any],
    project: str = Query(default="default"),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    target_id = request.get("target_fact_id")
    relation_type = request.get("relation_type", "related")
    strength = float(request.get("strength", 0.5))
    if not target_id:
        raise HTTPException(400, "target_fact_id required")
    source = semantic.get_by_id(fact_id)
    target = semantic.get_by_id(int(target_id))
    if not source or not target:
        raise HTTPException(404, "Fact not found")
    link_id = semantic.link_facts(project, fact_id, int(target_id), relation_type, strength)
    return {"status": "linked", "id": link_id}


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------


@app.get("/api/memories/facts/{fact_id}/versions")
async def list_fact_versions(
    fact_id: int,
    project: str = Query(default="default"),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    fact = semantic.get_by_id(fact_id)
    if not fact:
        raise HTTPException(404, "Fact not found")
    return {"fact_id": fact_id, "versions": semantic.get_versions(fact_id)}


@app.post("/api/memories/facts/{fact_id}/versions/{version_id}/restore")
async def restore_fact_version(
    fact_id: int,
    version_id: int,
    project: str = Query(default="default"),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    restored = await semantic.restore_version(fact_id, version_id)
    if not restored:
        raise HTTPException(404, "Fact or version not found")
    return {"status": "restored", "fact": restored.to_dict()}


# ---------------------------------------------------------------------------
# Temporal timeline
# ---------------------------------------------------------------------------


@app.get("/api/acrux/timeline")
async def acrux_timeline(
    project: str = Query(default="default"),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    episodic = _project_episodic(project)
    procedural = _project_procedural(project)
    facts = semantic.get_facts_timeline(project, since=since, until=until)
    versions = semantic.get_versions_timeline(project, since=since, until=until)
    episodes = episodic.get_episodes_timeline(project, since=since, until=until)
    skills = procedural.get_skills_timeline(project, since=since, until=until)
    merged = facts + versions + episodes + skills
    merged.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return {"project": project, "items": merged[:limit], "count": len(merged[:limit])}


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------


@app.post("/api/acrux/decay")
async def compute_decay(
    project: str = Query(default="default"),
    half_life_days: float = Query(default=30.0, ge=1.0),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    updated = semantic.compute_decay_scores(project, half_life_days=half_life_days)
    return {"project": project, "updated": updated}


@app.get("/api/acrux/decay")
async def list_decay(
    project: str = Query(default="default"),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    facts = semantic.list_stale_facts(project, threshold=threshold, limit=limit)
    return {"project": project, "threshold": threshold, "facts": [f.to_dict() for f in facts]}


# ---------------------------------------------------------------------------
# Cross-project inheritance
# ---------------------------------------------------------------------------


@app.get("/api/projects/{project}/inheritance")
async def get_inheritance(project: str) -> dict[str, Any]:
    semantic = _project_semantic(project)
    return {"project": project, "layers": semantic.list_project_layers(project)}


@app.post("/api/projects/{project}/inheritance")
async def add_inheritance(
    project: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    base_project = request.get("base_project")
    layer_order = int(request.get("layer_order", 0))
    if not base_project:
        raise HTTPException(400, "base_project required")
    layer_id = semantic.add_project_layer(project, base_project, layer_order)
    return {"status": "added", "id": layer_id}


@app.delete("/api/projects/{project}/inheritance/{base_project}")
async def remove_inheritance(project: str, base_project: str) -> dict[str, Any]:
    semantic = _project_semantic(project)
    if semantic.remove_project_layer(project, base_project):
        return {"status": "removed"}
    raise HTTPException(404, "Layer not found")


@app.get("/api/projects/{project}/effective-facts")
async def effective_facts(
    project: str,
    limit: int = Query(default=500, ge=1, le=2000),
) -> dict[str, Any]:
    if not _cfg:
        raise HTTPException(503, "Acrux not configured")
    semantic = _project_semantic(project)
    facts = semantic.get_effective_facts(project, _cfg.data_dir, limit=limit)
    return {"project": project, "count": len(facts), "facts": facts}


# ---------------------------------------------------------------------------
# Auto-clustering
# ---------------------------------------------------------------------------


@app.post("/api/acrux/cluster")
async def cluster_facts(
    project: str = Query(default="default"),
    max_clusters: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    result = semantic.cluster_facts(project, max_clusters=max_clusters)
    return {"project": project, **result}


@app.get("/api/acrux/clusters")
async def list_clusters(
    project: str = Query(default="default"),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    if project == "global":
        with sqlite3.connect(semantic.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM clusters ORDER BY updated_at DESC").fetchall()
        clusters = [
            {
                "id": row["id"],
                "project": row["project"],
                "label": row["label"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "fact_count": conn.execute(
                    "SELECT COUNT(*) FROM facts WHERE cluster_id = ?", (row["id"],)
                ).fetchone()[0],
            }
            for row in rows
        ]
        return {"project": project, "clusters": clusters}
    return {"project": project, "clusters": semantic.list_clusters(project)}


def _build_project_graph(project: str, max_nodes: int = 200) -> dict[str, Any]:
    """Build a knowledge graph for a single project."""
    semantic = _project_semantic(project)
    episodic = _project_episodic(project)
    procedural = _project_procedural(project)

    clusters = semantic.list_clusters(project)[:50]
    facts = semantic.list_facts(project, limit=100)
    episodes = episodic.list_episodes(project, limit=50)
    skills = procedural.list_skills(project, limit=50)

    # Cap total nodes to keep payloads small on weak machines.
    total = 1 + len(clusters) + len(facts) + len(episodes) + len(skills)
    if total > max_nodes:
        # Trim larger categories proportionally.
        facts = facts[: max(10, int(len(facts) * max_nodes / total))]
        episodes = episodes[: max(5, int(len(episodes) * max_nodes / total))]
        skills = skills[: max(5, int(len(skills) * max_nodes / total))]
        clusters = clusters[: max(5, int(len(clusters) * max_nodes / total))]

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()

    def add_node(
        node_id: str,
        node_type: str,
        label: str,
        snippet: str,
        size: float,
        color: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "label": label,
                "content_snippet": snippet,
                "size": size,
                "color": color,
                "x": 0.0,
                "y": 0.0,
                "meta": meta or {},
            }
        )

    project_id = f"project:{project}"
    add_node(project_id, "project", project, f"Project {project}", 15.0, "#E8E8E9")

    # Clusters orbit the project.
    for i, cluster in enumerate(clusters):
        cid = f"cluster:{project}:{cluster['id']}"
        label = cluster.get("label") or f"Cluster {cluster['id']}"
        add_node(
            cid,
            "cluster",
            label,
            f"{cluster.get('fact_count', 0)} facts",
            11.0,
            "#8AA0AF",
            {"cluster_id": cluster["id"], "project": project},
        )
        edges.append({"source": project_id, "target": cid, "type": "contains", "strength": 0.5})

    # Facts attach to their cluster or the project.
    fact_node_ids: dict[int, str] = {}
    for fact in facts:
        fid = f"fact:{project}:{fact.id}"
        fact_node_ids[fact.id] = fid
        color = "#A66B6B" if fact.fact_type == "negative" else "#7FA68A"
        snippet = fact.content
        if len(snippet) > 120:
            snippet = snippet[:120] + "..."
        add_node(
            fid,
            "fact",
            f"Fact {fact.id}",
            snippet,
            4.5 + min(fact.confidence * 1.5, 1.5),
            color,
            {"fact_id": fact.id, "fact_type": fact.fact_type, "cluster_id": fact.cluster_id, "project": project},
        )
        if fact.cluster_id:
            edges.append(
                {
                    "source": f"cluster:{project}:{fact.cluster_id}",
                    "target": fid,
                    "type": "contains",
                    "strength": 0.7,
                }
            )
        else:
            edges.append({"source": project_id, "target": fid, "type": "contains", "strength": 0.3})

    # Fact relationships.
    if facts:
        relationships = semantic.get_relationships(project)
        seen_rels: set[tuple[str, str]] = set()
        for rel in relationships:
            source_id = fact_node_ids.get(rel.get("source_fact_id"))
            target_id = fact_node_ids.get(rel.get("target_fact_id"))
            if not source_id or not target_id:
                continue
            key = tuple(sorted([source_id, target_id]))
            if key in seen_rels:
                continue
            seen_rels.add(key)
            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "type": rel.get("relation_type", "related"),
                    "strength": rel.get("strength", 0.5),
                }
            )

    # Episodes link to the project and loosely to facts sharing tags.
    episode_node_ids: dict[str, str] = {}
    for episode in episodes:
        eid = f"episode:{project}:{episode.session_id}"
        episode_node_ids[episode.session_id] = eid
        snippet = episode.outcome or episode.task
        if len(snippet) > 120:
            snippet = snippet[:120] + "..."
        add_node(
            eid,
            "episode",
            episode.task or episode.session_id,
            snippet,
            7.0,
            "#B89B6D",
            {"session_id": episode.session_id, "project": project},
        )
        edges.append({"source": project_id, "target": eid, "type": "contains", "strength": 0.4})

    # Skills link to the project.
    for skill in skills:
        sid = f"skill:{project}:{skill.id}"
        add_node(
            sid,
            "skill",
            skill.name,
            "\n".join(skill.preconditions[:2]),
            8.0,
            "#A48BB5",
            {"skill_id": skill.id, "project": project},
        )
        edges.append({"source": project_id, "target": sid, "type": "contains", "strength": 0.5})

    # Cross-link episodes to facts with overlapping tags.
    fact_tag_index: dict[str, list[int]] = defaultdict(list)
    for fact in facts:
        for tag in fact.tags:
            fact_tag_index[tag.lower()].append(fact.id)

    for episode in episodes:
        eid = episode_node_ids.get(episode.session_id)
        if not eid:
            continue
        linked_facts: set[int] = set()
        for tag in episode.tags:
            for fid in fact_tag_index.get(tag.lower(), []):
                linked_facts.add(fid)
        for fid in linked_facts:
            edges.append(
                {"source": eid, "target": fact_node_ids[fid], "type": "relates_to", "strength": 0.3}
            )

    # Assign hierarchical radial positions with spacing that scales with node counts
    # so larger projects do not collapse into a messy blob.
    def layout_ring(
        node_subset: list[dict[str, Any]], radius: float, start_angle: float = 0.0
    ) -> None:
        count = len(node_subset)
        if count == 0:
            return
        step = (2 * math.pi) / count
        for i, node in enumerate(node_subset):
            angle = start_angle + i * step
            node["x"] = round(radius * math.cos(angle), 3)
            node["y"] = round(radius * math.sin(angle), 3)

    project_node = next((n for n in nodes if n["id"] == project_id), None)
    if project_node:
        project_node["x"] = 0.0
        project_node["y"] = 0.0

    cluster_nodes = [n for n in nodes if n["type"] == "cluster"]
    skill_nodes = [n for n in nodes if n["type"] == "skill"]
    episode_nodes = [n for n in nodes if n["type"] == "episode"]

    # Tighter project ring, but more breathing room inside each project so
    # clusters/skills/episodes/facts do not sit on top of each other.
    cluster_radius = max(36.0, 11.0 * len(cluster_nodes))
    layout_ring(cluster_nodes, cluster_radius)

    skill_radius = cluster_radius + max(40.0, 10.0 * len(skill_nodes))
    layout_ring(skill_nodes, skill_radius, math.pi / 4)

    episode_radius = cluster_radius + max(40.0, 10.0 * len(episode_nodes))
    layout_ring(episode_nodes, episode_radius, math.pi)

    # Distribute facts evenly around their parent (cluster or project) so they
    # never pile on top of each other. Multiple rings are used when a parent has
    # many facts.
    cluster_positions = {n["id"]: (n["x"], n["y"]) for n in cluster_nodes}
    facts_per_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        if node["type"] != "fact":
            continue
        parent = next(
            (e["source"] for e in edges if e["target"] == node["id"] and e["type"] == "contains"),
            project_id,
        )
        facts_per_parent[parent].append(node)

    def layout_facts_around(cx: float, cy: float, facts: list[dict[str, Any]], base_radius: float) -> None:
        count = len(facts)
        if count == 0:
            return
        # Pack ~6 facts per ring so they do not overlap.
        per_ring = 6
        ring_spacing = 20.0
        offset_angle = math.radians(hash(facts[0]["id"]) % 360)
        for i, fact in enumerate(facts):
            ring = i // per_ring
            idx_in_ring = i % per_ring
            facts_in_ring = min(per_ring, count - ring * per_ring)
            angle_step = (2 * math.pi) / max(1, facts_in_ring)
            # Stagger rings so nodes do not line up vertically.
            ring_offset = (math.pi / per_ring) * ring
            angle = offset_angle + ring * 0.3 + idx_in_ring * angle_step + ring_offset
            radius = base_radius + ring * ring_spacing
            fact["x"] = round(cx + radius * math.cos(angle), 3)
            fact["y"] = round(cy + radius * math.sin(angle), 3)

    for parent, facts in facts_per_parent.items():
        cx, cy = cluster_positions.get(parent, (0.0, 0.0))
        # Project-center facts need more room than cluster-center facts.
        base_radius = 32.0 if parent == project_id else 24.0
        # If there are very many facts, start farther out.
        base_radius = max(base_radius, 14.0 + 6.0 * math.sqrt(len(facts)))
        layout_facts_around(cx, cy, facts, base_radius)

    return {
        "project": project,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def _build_global_graph(max_nodes: int = 300) -> dict[str, Any]:
    """Build a knowledge graph from the global memory stores.

    Each distinct project stored in the global semantic DB gets its own project
    node connected to the acrux root, so training-corpus topics (rust, python,
    vision, etc.) appear in the global graph even when no per-project directory
    exists under ~/.acrux/data/projects.
    """
    if not _cfg or not _semantic:
        return {"project": "global", "node_count": 0, "edge_count": 0, "nodes": [], "edges": []}

    # Discover projects stored in global semantic memory.
    with sqlite3.connect(_semantic.db_path) as conn:
        rows = conn.execute("SELECT DISTINCT project FROM facts").fetchall()
        projects = sorted({r[0] for r in rows if r[0]})

    all_nodes: list[dict[str, Any]] = []
    all_edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    acrux_id = "acrux:root"

    def add_node(
        node_id: str,
        node_type: str,
        label: str,
        snippet: str,
        size: float,
        color: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        all_nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "label": label,
                "content_snippet": snippet,
                "size": size,
                "color": color,
                "x": 0.0,
                "y": 0.0,
                "meta": meta or {},
            }
        )

    # Show only the most useful nodes per project in the global overview.
    per_project_max = max(6, max_nodes // (max(1, len(projects)) * 2))

    for project in projects:
        facts = _semantic.list_facts(project, limit=per_project_max)
        episodes = _episodic.get_recent(project, limit=max(3, per_project_max // 4))
        skills = _procedural.get_all(project)[: max(3, per_project_max // 4)]

        project_id = f"project:{project}"
        add_node(
            project_id,
            "project",
            project,
            f"Global training project: {project}",
            15.0,
            "#E8E8E9",
            {"project": project},
        )
        all_edges.append({"source": acrux_id, "target": project_id, "type": "contains", "strength": 0.6})

        fact_node_ids: dict[int, str] = {}
        for fact in facts:
            fid = f"fact:{project}:{fact.id}"
            fact_node_ids[fact.id] = fid
            snippet = fact.content
            if len(snippet) > 120:
                snippet = snippet[:120] + "..."
            add_node(
                fid,
                "fact",
                f"Fact {fact.id}",
                snippet,
                4.5 + min(fact.confidence * 1.5, 1.5),
                "#A66B6B" if fact.fact_type == "negative" else "#7FA68A",
                {"fact_id": fact.id, "fact_type": fact.fact_type, "project": project},
            )
            all_edges.append({"source": project_id, "target": fid, "type": "contains", "strength": 0.3})

        for episode in episodes:
            eid = f"episode:{project}:{episode.session_id}"
            snippet = episode.outcome or episode.task
            if len(snippet) > 120:
                snippet = snippet[:120] + "..."
            add_node(
                eid,
                "episode",
                episode.task or episode.session_id,
                snippet,
                7.0,
                "#B89B6D",
                {"session_id": episode.session_id, "project": project},
            )
            all_edges.append({"source": project_id, "target": eid, "type": "contains", "strength": 0.4})

        for skill in skills:
            sid = f"skill:{project}:{skill.id}"
            add_node(
                sid,
                "skill",
                skill.name,
                "\n".join(skill.preconditions[:2]),
                8.0,
                "#A48BB5",
                {"skill_id": skill.id, "project": project},
            )
            all_edges.append({"source": project_id, "target": sid, "type": "contains", "strength": 0.5})

    # Simple radial layout per project so topics don't overlap.
    angle_step = (2 * math.pi) / max(1, len(projects))
    project_nodes = [n for n in all_nodes if n["type"] == "project"]
    for i, pnode in enumerate(project_nodes):
        angle = i * angle_step
        radius = max(150.0, 40.0 * math.sqrt(len(projects)))
        pnode["x"] = round(radius * math.cos(angle), 3)
        pnode["y"] = round(radius * math.sin(angle), 3)

    # Layout child nodes in a ring around their project node.
    for pnode in project_nodes:
        children = [n for n in all_nodes if n.get("meta", {}).get("project") == pnode["meta"].get("project") and n["id"] != pnode["id"]]
        count = len(children)
        if count == 0:
            continue
        step = (2 * math.pi) / count
        # Space children by count so adjacent nodes never touch: a full ring
        # gives ~2.6 world units of arc per child (node diameter is ~12).
        child_radius = max(40.0, 2.6 * count)
        for i, child in enumerate(children):
            angle = i * step
            child["x"] = round(pnode["x"] + child_radius * math.cos(angle), 3)
            child["y"] = round(pnode["y"] + child_radius * math.sin(angle), 3)

    return {
        "project": "global",
        "node_count": len(all_nodes),
        "edge_count": len(all_edges),
        "nodes": all_nodes,
        "edges": all_edges,
    }


@app.get("/api/acrux/graph")
async def global_graph(
    max_nodes: int = Query(default=300, ge=1, le=1000),
) -> dict[str, Any]:
    """Return a global knowledge graph spanning all projects and global memory."""
    if not _cfg:
        raise HTTPException(500, "Acrux not loaded")

    all_nodes: list[dict[str, Any]] = []
    all_edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()

    acrux_id = "acrux:root"
    all_nodes.append({
        "id": acrux_id,
        "type": "acrux",
        "label": "Global Acrux",
        "content_snippet": "Global memory across all projects",
        "size": 30.0,
        "color": "#FFFFFF",
        "x": 0.0,
        "y": 0.0,
        "meta": {},
    })
    node_ids.add(acrux_id)

    projects: list[str] = []
    projects_dir = _cfg.projects_dir
    if projects_dir.exists():
        projects = sorted(
            p.name for p in projects_dir.iterdir()
            if p.is_dir()
        )

    per_project_max = max(8, max_nodes // (max(1, len(projects)) * 2))

    for project in projects:
        try:
            subgraph = _build_project_graph(project, max_nodes=per_project_max)
        except Exception:
            continue

        for node in subgraph["nodes"]:
            if node["id"] not in node_ids:
                node_ids.add(node["id"])
                all_nodes.append(node)

        for edge in subgraph["edges"]:
            all_edges.append(edge)

        project_node_id = f"project:{project}"
        if project_node_id in node_ids:
            all_edges.append({
                "source": acrux_id,
                "target": project_node_id,
                "type": "contains",
                "strength": 0.6,
            })

    # Include global memory (training corpus, global facts/skills/episodes).
    try:
        global_subgraph = _build_global_graph(max_nodes=max_nodes)
        for node in global_subgraph["nodes"]:
            if node["id"] not in node_ids:
                node_ids.add(node["id"])
                all_nodes.append(node)
        for edge in global_subgraph["edges"]:
            all_edges.append(edge)
    except Exception:
        pass

    # Unified layout: an inner ring close to the acrux for the projects with
    # the most memories (training topics), and an outer ring for small/empty
    # projects, so the view stays compact around the acrux root.
    project_nodes = [n for n in all_nodes if n["type"] == "project"]
    child_counts: dict[str, int] = {p["id"]: 0 for p in project_nodes}
    for n in all_nodes:
        if n["type"] == "project":
            continue
        proj = n.get("meta", {}).get("project")
        if proj:
            pid = f"project:{proj}"
            if pid in child_counts:
                child_counts[pid] += 1
    project_nodes.sort(key=lambda p: -child_counts.get(p["id"], 0))

    inner = project_nodes[:10]
    outer = project_nodes[10:]
    inner_radius = max(170.0, 20.0 * len(inner))
    outer_radius = inner_radius + max(140.0, 10.0 * len(outer)) if outer else inner_radius

    def _place_ring(ring_projects: list[dict[str, Any]], radius: float, start_angle: float = 0.0) -> None:
        step = (2 * math.pi) / max(1, len(ring_projects))
        for i, pnode in enumerate(ring_projects):
            angle = start_angle + i * step
            new_x = radius * math.cos(angle)
            new_y = radius * math.sin(angle)
            dx = new_x - pnode["x"]
            dy = new_y - pnode["y"]
            pnode["x"] = round(new_x, 3)
            pnode["y"] = round(new_y, 3)
            # Project nodes from _build_project_graph carry no meta; take the
            # name from the node id so their children get shifted along too.
            pname = pnode.get("meta", {}).get("project") or pnode["id"].split(":", 1)[1]
            for n in all_nodes:
                if n["id"] == pnode["id"]:
                    continue
                if n.get("meta", {}).get("project") == pname:
                    n["x"] = round(n["x"] + dx, 3)
                    n["y"] = round(n["y"] + dy, 3)

    _place_ring(inner, inner_radius)
    # Stagger the outer ring so its clusters sit in the gaps of the inner ring.
    _place_ring(outer, outer_radius, start_angle=math.pi / max(1, len(outer)))

    return {
        "project": "global",
        "node_count": len(all_nodes),
        "edge_count": len(all_edges),
        "nodes": all_nodes,
        "edges": all_edges,
    }


@app.get("/api/projects/{project}/graph")
async def project_graph(
    project: str,
    max_nodes: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    """Return a project knowledge graph as nodes and edges."""
    return _build_project_graph(project, max_nodes=max_nodes)


# ---------------------------------------------------------------------------
# Test results
# ---------------------------------------------------------------------------


@app.post("/api/projects/{project}/tests")
async def record_test(
    project: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    test_id = semantic.add_test_result(project, request)
    return {"status": "recorded", "id": test_id}


@app.get("/api/projects/{project}/tests")
async def list_tests(
    project: str,
    passed: bool | None = Query(default=None),
    file_path: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    return {
        "project": project,
        "tests": semantic.get_test_results(
            project, passed=passed, file_path=file_path, limit=limit
        ),
    }


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@app.post("/api/projects/{project}/dependencies")
async def record_dependencies(
    project: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    deps = request.get("dependencies", [])
    count = semantic.add_dependencies(project, deps)
    return {"status": "recorded", "count": count}


@app.get("/api/projects/{project}/dependencies")
async def list_dependencies(
    project: str,
    source: str | None = Query(default=None),
    target: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    return {
        "project": project,
        "dependencies": semantic.get_dependencies(
            project,
            source=source,
            target=target,
            source_type=source_type,
            target_type=target_type,
            limit=limit,
        ),
    }


# ---------------------------------------------------------------------------
# Code reviews
# ---------------------------------------------------------------------------


@app.post("/api/projects/{project}/reviews")
async def record_review(
    project: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    review_id = semantic.add_review(project, request)
    return {"status": "recorded", "id": review_id}


@app.get("/api/projects/{project}/reviews")
async def list_reviews(
    project: str,
    file_path: str | None = Query(default=None),
    resolution: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    return {
        "project": project,
        "reviews": semantic.get_reviews(
            project, file_path=file_path, resolution=resolution, limit=limit
        ),
    }


# ---------------------------------------------------------------------------
# Skill suggestions
# ---------------------------------------------------------------------------


@app.get("/api/skills/suggest")
async def suggest_skills(
    project: str = Query(default="default"),
    query: str = Query(...),
    limit: int = Query(default=5, ge=1, le=50),
) -> dict[str, Any]:
    """Return procedural skills relevant to the user's query with a score."""
    procedural = _project_procedural(project)
    skills = procedural.search(project, query, limit=limit * 3)
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    scored = []
    for skill in skills:
        text = " ".join(
            [skill.name] + skill.preconditions + skill.procedure + [str(e) for e in skill.evidence]
        ).lower()
        if not terms:
            score = 0.0
        else:
            score = sum(1 for t in terms if t in text) / len(terms)
        scored.append(
            {
                "skill": skill.to_dict(),
                "score": min(1.0, score),
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {
        "project": project,
        "query": query,
        "suggestions": scored[:limit],
    }


# ---------------------------------------------------------------------------
# Periodic re-verification
# ---------------------------------------------------------------------------


@app.post("/api/acrux/reverify")
async def reverify_facts(
    project: str = Query(default="default"),
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """Re-verify oldest/least-confident facts using the reflection model."""
    if not _cfg or _cfg.reflection.provider != "ollama":
        return {
            "status": "skipped",
            "message": "Re-verification requires ollama reflection provider.",
        }

    semantic = _project_semantic(project)
    facts = semantic.get_facts_for_reverify(project, limit=limit)
    if not facts:
        return {"status": "ok", "checked": 0, "results": []}

    model = _cfg.reflection.routing.get("reflection", _cfg.reflection.model)
    results = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for fact in facts:
            prompt = (
                "You are a fact-checking assistant. Evaluate whether the following statement "
                "is still true. Answer with exactly one word: Yes, No, or Uncertain.\n\n"
                f"Statement: {fact.content}\n\nVerdict:"
            )
            try:
                r = await client.post(
                    f"{_cfg.reflection.host}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                )
                r.raise_for_status()
                verdict = r.json().get("response", "Uncertain").strip().split()[0]
            except Exception as exc:
                verdict = f"error: {exc}"
            updated = semantic.record_verification(fact.id, verdict) if fact.id else None
            results.append(
                {
                    "fact_id": fact.id,
                    "content": fact.content,
                    "verdict": verdict,
                    "confidence": updated.confidence if updated else fact.confidence,
                    "stale": updated.stale if updated else fact.stale,
                }
            )

    return {"status": "ok", "checked": len(results), "results": results}


# ---------------------------------------------------------------------------
# Phase 2: Memory I/O and automation
# ---------------------------------------------------------------------------


@app.post("/api/import/notion")
async def import_notion(
    project: str = Query(default="default"),
    directory: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    """Import a Notion Markdown export into semantic memory."""
    if file:
        import zipfile
        import tempfile

        suffix = Path(file.filename or "export.zip").suffix
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / f"export{suffix}"
            archive_path.write_bytes(await file.read())
            extract_dir = Path(tmp) / "notion"
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, "r") as z:
                    z.extractall(extract_dir)
            else:
                extract_dir = Path(tmp)
            result = await _import_directory(project, extract_dir, "notion-import")
        return {"project": project, **result}
    if directory:
        result = await _import_directory(project, Path(directory), "notion-import")
        return {"project": project, **result}
    raise HTTPException(400, "Provide a file or directory")


@app.post("/api/import/obsidian")
async def import_obsidian(
    project: str = Query(default="default"),
    directory: str = Form(...),
) -> dict[str, Any]:
    """Import an Obsidian vault directory into semantic memory."""
    result = await _import_directory(project, Path(directory), "obsidian-import")
    return {"project": project, **result}


@app.get("/api/export/markdown")
async def export_markdown(
    project: str = Query(default="default"),
    format: str = Query(default="plain"),
) -> dict[str, Any]:
    """Export project memory as a Markdown wiki."""
    return _export_markdown(project, format)


# ---------------------------------------------------------------------------
# File summaries
# ---------------------------------------------------------------------------


@app.post("/api/projects/{project}/file-summaries")
async def summarize_file(
    project: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    """Summarize a file and cache the result."""
    path_str = request.get("path")
    workspace = request.get("workspace", ".")
    if not path_str:
        raise HTTPException(400, "path required")
    target = _workspace_safe_path(workspace, path_str)
    if not target.is_file():
        raise HTTPException(404, "File not found")
    stat = target.stat()
    mtime = datetime.utcfromtimestamp(stat.st_mtime).isoformat()
    content_hash = _file_hash(target)
    semantic = _project_semantic(project)
    existing = semantic.get_file_summaries(project, path=path_str, limit=1)
    if existing and existing[0].get("content_hash") == content_hash:
        return {"status": "cached", "summary": existing[0]}

    text = target.read_text(errors="replace")
    lines = text.splitlines()
    if _cfg and _cfg.reflection.provider != "none":
        summary = _heuristic_summary(lines)
    else:
        summary = _heuristic_summary(lines)
    summary_record = {
        "path": path_str,
        "summary": summary,
        "content_hash": content_hash,
        "last_modified": mtime,
    }
    summary_id = semantic.add_file_summary(project, summary_record)
    return {"status": "summarized", "id": summary_id, "summary": summary}


def _heuristic_summary(lines: list[str]) -> str:
    """Generate a simple heuristic summary from file lines."""
    docstring: list[str] = []
    body: list[str] = []
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            in_docstring = not in_docstring
            continue
        if in_docstring:
            docstring.append(stripped)
        elif stripped:
            body.append(stripped)
    if docstring:
        return " ".join(docstring[:10])
    return " ".join(body[:10])


@app.get("/api/projects/{project}/file-summaries")
async def list_file_summaries(
    project: str,
    path: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    semantic = _project_semantic(project)
    return {
        "project": project,
        "summaries": semantic.get_file_summaries(project, path=path, limit=limit),
    }


# ---------------------------------------------------------------------------
# Workspace watcher
# ---------------------------------------------------------------------------


@app.post("/api/projects/{project}/watcher/start")
async def start_watcher(
    project: str,
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if _cfg and _cfg.profile == "minimal":
        return {"status": "disabled", "reason": "watcher disabled on minimal profile"}
    workspace = (request or {}).get("workspace", ".")
    ws_path = Path(workspace).expanduser().resolve()
    if not ws_path.is_dir():
        raise HTTPException(400, "Workspace does not exist")
    semantic = _project_semantic(project)
    if project in _watchers:
        _watchers[project].stop()
    watcher = WorkspaceWatcher(project, ws_path, semantic)
    watcher.start()
    _watchers[project] = watcher
    return {"status": "started", "project": project, "workspace": str(ws_path)}


@app.post("/api/projects/{project}/watcher/stop")
async def stop_watcher(project: str) -> dict[str, Any]:
    watcher = _watchers.pop(project, None)
    if watcher:
        watcher.stop()
        return {"status": "stopped", "project": project}
    return {"status": "not_running", "project": project}


@app.get("/api/projects/{project}/watcher/status")
async def watcher_status(project: str) -> dict[str, Any]:
    watcher = _watchers.get(project)
    semantic = _project_semantic(project)
    state = semantic.get_watcher_state(project)
    return {
        "project": project,
        "running": watcher.is_running() if watcher else False,
        "state_count": len(state),
    }


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


@app.get("/api/acrux/health")
async def acrux_health(
    project: str | None = Query(default=None),
    unresolved_only: bool = Query(default=False),
    limit: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    if not _cfg:
        raise HTTPException(503, "Acrux not configured")
    semantic = (
        _semantic
        if _semantic is not None
        else SemanticStore(_cfg.data_dir / "global" / "facts.db", embedder=_embedder)
    )
    checks = semantic.get_health_checks(
        project=project,
        unresolved_only=unresolved_only,
        limit=limit,
    )
    return {"checks": checks, "count": len(checks)}


@app.post("/api/acrux/health/run")
async def run_health(
    project: str | None = Query(default=None),
) -> dict[str, Any]:
    checks = _run_health_checks(project)
    return {"status": "ok", "checks_added": len(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------


@app.get("/api/acrux/checksums")
async def acrux_checksums() -> dict[str, Any]:
    if not _cfg:
        raise HTTPException(503, "Acrux not configured")
    semantic = (
        _semantic
        if _semantic is not None
        else SemanticStore(_cfg.data_dir / "global" / "facts.db", embedder=_embedder)
    )
    return semantic.verify_storage_checksums(_cfg.data_dir)


# ---------------------------------------------------------------------------
# Rollback suggestions
# ---------------------------------------------------------------------------


@app.get("/api/projects/{project}/rollback-suggestion")
async def rollback_suggestion(
    project: str,
    after_command: str | None = Query(default=None),
) -> dict[str, Any]:
    return _rollback_suggestion(project, after_command)


# ---------------------------------------------------------------------------
# Custom system prompts
# ---------------------------------------------------------------------------


@app.get("/api/projects/{project}/system-prompt")
async def get_system_prompt(project: str) -> dict[str, Any]:
    semantic = _project_semantic(project)
    prompt = semantic.get_system_prompt(project)
    if not prompt:
        raise HTTPException(404, "No custom prompt set")
    return prompt


@app.post("/api/projects/{project}/system-prompt")
async def set_system_prompt(
    project: str,
    request: dict[str, Any],
) -> dict[str, Any]:
    prompt_text = request.get("prompt_text", "")
    semantic = _project_semantic(project)
    semantic.set_system_prompt(project, prompt_text)
    return {"status": "saved", "project": project}


# ---------------------------------------------------------------------------
# Launcher entry point
# ---------------------------------------------------------------------------


def run_server(host: str = "127.0.0.1", port: int = 11438) -> None:
    import uvicorn

    uvicorn.run("acrux.app.main:app", host=host, port=port, log_level="info")
