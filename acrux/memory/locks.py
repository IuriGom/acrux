"""Project-local write locks."""

from __future__ import annotations

import fcntl
from pathlib import Path


class ProjectLockError(RuntimeError):
    pass


class ProjectWriteLock:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.path = project_dir / ".write.lock"
        self._handle = None

    def __enter__(self):
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._handle.close()
            self._handle = None
            raise ProjectLockError(f"Project write lock is held: {self.path}") from exc
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None
        return False


def project_write_lock(project_dir: Path) -> ProjectWriteLock:
    return ProjectWriteLock(project_dir)
