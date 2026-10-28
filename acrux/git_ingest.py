"""Deterministic Git history ingestion."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from acrux.capture import cap_text, redact_text
from acrux.memory.episodic import EpisodicStore
from acrux.memory.semantic import SemanticStore
from acrux.models import CodeChange, Episode


@dataclass
class CommitFile:
    path: str
    diff: str
    added_module: bool = False
    added_exports: bool = False
    modifies_existing_functions: bool = False
    status: str = "M"


def _is_docs(path: str) -> bool:
    lowered = path.casefold()
    return lowered.startswith("docs/") or Path(lowered).suffix in {".md", ".rst", ".txt"} or "readme" in Path(lowered).name


def _is_test(path: str) -> bool:
    lowered = path.casefold()
    name = Path(lowered).name
    return lowered.startswith(("tests/", "test/")) or name.startswith("test_") or name.endswith("_test.py")


def classify_commit(subject: str, files: list[CommitFile]) -> tuple[str, float]:
    if files and all(_is_docs(file.path) for file in files):
        return "docs", 0.98
    if files and all(_is_test(file.path) for file in files):
        return "test", 0.98
    lowered = subject.casefold()
    if re.search(r"\b(fix|bugfix|hotfix|regression)\b", lowered):
        return "fix", 0.95
    adds_feature = any(file.added_module or file.added_exports for file in files)
    if (
        any(file.modifies_existing_functions for file in files)
        and not adds_feature
        and any(re.search(r"(?i)except|error|catch|raise|panic|rescue", file.diff) for file in files)
    ):
        return "fix", 0.75
    if re.search(r"\b(refactor|restructure|rename|move)\b", lowered) or (
        files and all(file.status.startswith("R") for file in files)
    ):
        return "refactor", 0.9
    if re.search(r"\b(feat|feature|add|implement)", lowered) or adds_feature:
        return "feature", 0.85
    return "chore", 0.65


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _metadata(path: Path, max_commits: int | None) -> list[dict[str, str | list[str]]]:
    args = ["log", "--format=%H%x1f%P%x1f%an%x1f%cI%x1f%s"]
    if max_commits is not None:
        args.append(f"--max-count={max_commits}")
    commits = []
    for line in _git(path, *args).splitlines():
        sha, parents, author, committed_at, subject = line.split("\x1f", 4)
        commits.append(
            {
                "sha": sha,
                "parents": parents.split() if parents else [],
                "author": author,
                "committed_at": committed_at,
                "subject": subject,
            }
        )
    return commits


def _files(path: Path, sha: str) -> list[CommitFile]:
    output = _git(
        path,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-status",
        "-r",
        "--first-parent",
        "-z",
        sha,
    )
    parts = output.split("\0")
    files = []
    index = 0
    while index < len(parts):
        status = parts[index]
        if not status:
            index += 1
            continue
        index += 1
        old_path = parts[index]
        index += 1
        file_path = old_path
        if status.startswith("R"):
            file_path = parts[index]
            index += 1
        diff = _git(path, "show", "--format=", "--unified=0", "--first-parent", sha, "--", file_path)
        binary = "Binary files" in diff or "GIT binary patch" in diff
        if binary:
            diff = f"Binary file {file_path} changed\n"
        else:
            diff, _ = cap_text(redact_text(diff), limit=32768)
        added_lines = "\n".join(
            line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
        )
        added_module = status == "A" and Path(file_path).suffix in {
            ".py", ".js", ".ts", ".tsx", ".rs", ".go", ".swift", ".c", ".cc", ".cpp", ".java"
        } and not _is_test(file_path) and not _is_docs(file_path)
        added_exports = bool(
            re.search(r"(?i)\b(def|class|function|export|pub fn|func)\b", added_lines)
        )
        modifies_existing = status == "M" and bool(added_lines)
        files.append(
            CommitFile(
                path=file_path,
                diff=diff,
                added_module=added_module,
                added_exports=added_exports,
                modifies_existing_functions=modifies_existing,
                status=status,
            )
        )
    return files


def ingest_git(
    path: Path,
    project: str,
    semantic: SemanticStore,
    episodic: EpisodicStore,
    max_commits: int | None = None,
) -> dict[str, int]:
    root = Path(_git(path, "rev-parse", "--show-toplevel").strip())
    commits = _metadata(root, max_commits)
    prepared = [(commit, _files(root, str(commit["sha"]))) for commit in commits]
    imported = 0
    change_count = 0
    for commit, files in prepared:
        sha = str(commit["sha"])
        session_id = f"git-{sha}"
        if episodic.get_by_id(session_id) is not None:
            continue
        classification, confidence = classify_commit(str(commit["subject"]), files)
        for file in files:
            change_type = (
                "add"
                if file.status == "A"
                else "delete"
                if file.status == "D"
                else "rename"
                if file.status.startswith("R")
                else "binary"
                if file.diff.startswith("Binary file")
                else "modify"
            )
            semantic.add_code_change(
                CodeChange(
                    project=project,
                    session_id=session_id,
                    commit_sha=sha,
                    file_path=file.path,
                    change_type=change_type,
                    diff=file.diff,
                    source="git-ingest",
                    content_hash=hashlib.sha256(
                        f"{file.path}\0{file.diff}".encode("utf-8")
                    ).hexdigest(),
                )
            )
            change_count += 1
        episodic.add(
            Episode(
                session_id=session_id,
                task=str(commit["subject"]),
                project=project,
                context={
                    "classification": classification,
                    "classification_confidence": confidence,
                    "author": commit["author"],
                    "committed_at": commit["committed_at"],
                    "parents": commit["parents"],
                    "repository": root.name,
                },
                outcome="committed",
                tags=["git", classification],
                compacted=True,
                source="git-ingest",
                git_info={"commit": sha},
            )
        )
        imported += 1
    return {"commits": len(prepared), "imported": imported, "code_changes": change_count}
