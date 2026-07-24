"""Utilities for acrux CLI and server."""

from __future__ import annotations

import logging
import os
import signal
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml


PID_FILE = Path.home() / ".acrux" / "acrux.pid"

_degraded = False
_degraded_reason: str | None = None


def set_degraded(reason: str) -> None:
    global _degraded, _degraded_reason
    _degraded = True
    _degraded_reason = reason


def clear_degraded() -> None:
    global _degraded, _degraded_reason
    _degraded = False
    _degraded_reason = None


def is_degraded() -> bool:
    return _degraded


def degraded_reason() -> str | None:
    return _degraded_reason


def available_ram_mb() -> int:
    """Return available RAM in MB. Uses psutil if installed, otherwise macOS fallbacks."""
    try:
        import psutil

        return int(psutil.virtual_memory().available / (1024 * 1024))
    except Exception:
        pass

    # macOS fallback via vm_stat
    try:
        result = subprocess.run(["vm_stat"], capture_output=True, text=True, check=False)
        pages_free = 0
        page_size = 4096
        for line in result.stdout.splitlines():
            if "page size of" in line:
                try:
                    page_size = int(line.split("page size of")[1].split("bytes")[0].strip())
                except Exception:
                    pass
            elif "Pages free" in line or "Pages inactive" in line or "Pages speculative" in line:
                try:
                    pages_free += int(line.split(":")[1].strip().rstrip("."))
                except Exception:
                    pass
        return int(pages_free * page_size / (1024 * 1024))
    except Exception:
        pass

    # sysctl fallback
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=False
        )
        total_bytes = int(result.stdout.strip())
        # Rough heuristic: assume 20% available if no better data
        return int(total_bytes * 0.2 / (1024 * 1024))
    except Exception:
        return 0


def setup_logging(log_dir: Path, name: str = "acrux") -> logging.Logger:
    """Configure file logging for acrux."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(log_dir / "acrux.log")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("acrux")


@dataclass
class StorageInfo:
    total_bytes: int
    used_bytes: int
    free_bytes: int
    acrux_bytes: int

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024**3)

    @property
    def used_gb(self) -> float:
        return self.used_bytes / (1024**3)

    @property
    def free_gb(self) -> float:
        return self.free_bytes / (1024**3)

    @property
    def acrux_gb(self) -> float:
        return self.acrux_bytes / (1024**3)


def get_storage_info(path: Path) -> StorageInfo:
    """Return storage usage for the filesystem containing path plus acrux size."""
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bavail * stat.f_frsize
    used = total - free
    acrux_bytes = _dir_size(path)
    return StorageInfo(total, used, free, acrux_bytes)


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for entry in os.scandir(path):
        if entry.is_file(follow_symlinks=False):
            total += entry.stat().st_size
        elif entry.is_dir(follow_symlinks=False):
            total += _dir_size(Path(entry.path))
    return total


def format_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


class PidFile:
    """Simple PID file for background acrux server."""

    def __init__(self, path: Path = PID_FILE):
        self.path = path

    def read(self) -> int | None:
        if not self.path.exists():
            return None
        try:
            return int(self.path.read_text().strip())
        except (ValueError, OSError):
            return None

    def write(self, pid: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(pid))

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def is_running(self) -> bool:
        pid = self.read()
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            self.clear()
            return False

    def stop(self) -> bool:
        pid = self.read()
        if pid is None:
            return False
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except (OSError, ProcessLookupError):
            self.clear()
            return False


def list_ollama_models(host: str = "http://localhost:11434") -> list[dict[str, Any]]:
    """List pulled Ollama models."""
    try:
        response = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=10.0)
        response.raise_for_status()
        return response.json().get("models", [])
    except Exception as exc:
        raise RuntimeError(f"Could not reach Ollama at {host}: {exc}") from exc


def validate_acrux_data(data_dir: Path) -> dict[str, Any]:
    """Check integrity of acrux databases and skills files."""
    projects_dir = data_dir / "projects"
    errors = []
    warnings = []
    checked = 0

    if not projects_dir.exists():
        return {"ok": False, "errors": ["projects directory missing"], "warnings": [], "checked": 0}

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        checked += 1
        episodic_db = project_dir / "episodes.db"
        semantic_db = project_dir / "semantic.db"
        skills_yaml = project_dir / "skills.yaml"

        for db_path in [episodic_db, semantic_db]:
            if db_path.exists():
                try:
                    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                        conn.execute("PRAGMA integrity_check").fetchone()
                except sqlite3.Error as exc:
                    errors.append(f"{db_path}: {exc}")

        if skills_yaml.exists():
            try:
                with open(skills_yaml) as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as exc:
                errors.append(f"{skills_yaml}: {exc}")

        if not any(p.exists() for p in [episodic_db, semantic_db, skills_yaml]):
            warnings.append(f"{project_dir.name}: empty project (no data files)")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "checked": checked}


def tail_log(log_path: Path, lines: int = 50) -> str:
    """Return last N lines of a log file."""
    if not log_path.exists():
        return "(log file not found)"
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), str(log_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout or "(empty log)"
    except Exception as exc:
        return f"(could not read log: {exc})"


def git_context(path: Path | str) -> dict[str, Any]:
    """Return git branch, commit, dirty flag and diff summary for ``path``.

    Returns an empty dict if ``path`` is not inside a git repository or git is
    not installed.
    """
    target = Path(path)
    try:
        import shutil

        if not shutil.which("git"):
            return {}
        cwd = target if target.is_dir() else target.parent
        repo_root = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if repo_root.returncode != 0:
            return {}
        branch = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        commit = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        dirty = subprocess.run(
            ["git", "-C", str(cwd), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        diff_stat = subprocess.run(
            ["git", "-C", str(cwd), "diff", "--stat"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return {
            "branch": branch.stdout.strip() if branch.returncode == 0 else "",
            "commit": commit.stdout.strip() if commit.returncode == 0 else "",
            "dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else False,
            "diff_summary": diff_stat.stdout.strip().splitlines()[-1].strip()
            if diff_stat.returncode == 0 and diff_stat.stdout.strip()
            else "",
        }
    except Exception:
        return {}


def prune_if_needed(data_dir: Path, limit_bytes: int, retention_days: int) -> int:
    """Prune old episodes/facts until storage is under limit. Returns items removed."""
    if limit_bytes <= 0:
        return 0
    from acrux.memory.episodic import EpisodicStore
    from acrux.memory.semantic import SemanticStore

    removed = 0
    for _ in range(5):  # avoid infinite loop
        current = _dir_size(data_dir)
        if current <= limit_bytes:
            break
        # Prune half the retention window each iteration
        retention_days = max(1, retention_days // 2)
        for project_dir in (data_dir / "projects").iterdir():
            if not project_dir.is_dir():
                continue
            episodic = EpisodicStore(project_dir / "episodes.db")
            semantic = SemanticStore(project_dir / "semantic.db")
            removed += episodic.prune_old(retention_days)
            removed += semantic.prune_old(retention_days)
    return removed
