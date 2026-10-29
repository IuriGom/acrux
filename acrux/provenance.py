"""Git worktree delta capture."""

from __future__ import annotations

import difflib
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from acrux.capture import cap_text, is_secret_path, redact_text
from acrux.models import CodeChange


@dataclass
class WorktreeSnapshot:
    repo_root: Path
    project: str
    session_id: str
    before: dict[str, bytes]

    @classmethod
    def capture(cls, path: Path, project: str, session_id: str) -> WorktreeSnapshot:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        root = Path(result.stdout.strip())
        return cls(root, project, session_id, cls(root, project, session_id, {})._read_files())

    def _read_files(self) -> dict[str, bytes]:
        result = subprocess.run(
            ["git", "-C", str(self.repo_root), "ls-files", "-co", "--exclude-standard", "-z"],
            check=True,
            capture_output=True,
        )
        files = {}
        for raw_path in result.stdout.decode("utf-8", errors="surrogateescape").split("\0"):
            if not raw_path:
                continue
            relative = Path(raw_path)
            path = self.repo_root / relative
            if is_secret_path(relative) or path.is_symlink() or not path.is_file():
                continue
            files[relative.as_posix()] = path.read_bytes()
        return files

    def changes_since(self) -> list[CodeChange]:
        try:
            after = self._read_files()
            changes = []
            for file_path in sorted(set(self.before) | set(after)):
                old = self.before.get(file_path)
                new = after.get(file_path)
                if old == new:
                    continue
                change_type = "add" if old is None else "delete" if new is None else "modify"
                content = new if new is not None else old or b""
                content_hash = hashlib.sha256(content).hexdigest()
                if b"\0" in content:
                    changes.append(
                        CodeChange(
                            project=self.project,
                            session_id=self.session_id,
                            file_path=file_path,
                            change_type="binary",
                            diff=f"Binary file {file_path} changed\n",
                            source="wrap",
                            content_hash=content_hash,
                        )
                    )
                    continue
                old_lines = (old or b"").decode("utf-8", errors="replace").splitlines(True)
                new_lines = (new or b"").decode("utf-8", errors="replace").splitlines(True)
                diff = "".join(
                    difflib.unified_diff(
                        old_lines,
                        new_lines,
                        fromfile=f"a/{file_path}",
                        tofile=f"b/{file_path}",
                        n=0,
                    )
                )
                changes.append(
                    CodeChange(
                        project=self.project,
                        session_id=self.session_id,
                        file_path=file_path,
                        change_type=change_type,
                        diff=diff,
                        source="wrap",
                        content_hash=content_hash,
                    )
                )

            deleted = {change.content_hash: change for change in changes if change.change_type == "delete"}
            removed = set()
            for change in changes:
                if change.change_type != "add" or change.content_hash not in deleted:
                    continue
                previous = deleted[change.content_hash]
                change.change_type = "rename"
                change.diff = f"rename from {previous.file_path} to {change.file_path}\n{change.diff}"
                removed.add(previous.file_path)
            changes = [change for change in changes if change.file_path not in removed]

            remaining = 262144
            for change in changes:
                if change.change_type == "binary":
                    continue
                change.diff = redact_text(change.diff)
                limit = min(32768, remaining)
                change.diff, truncated = cap_text(change.diff, limit=limit)
                change.truncated = change.truncated or truncated
                remaining -= len(change.diff.encode("utf-8"))
            return changes
        finally:
            self.before = {}
