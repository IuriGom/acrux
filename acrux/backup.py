"""Checked SQLite backup and restore."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from acrux.memory.locks import project_write_lock
from acrux.utils import utcnow


class BackupError(RuntimeError):
    pass


@dataclass
class BackupManifest:
    id: str
    path: Path
    created_at: str
    files: list[dict]
    schema_versions: dict[str, int]
    excluded: list[str]


@dataclass
class BackupInfo:
    id: str
    path: Path
    created_at: str
    project_count: int
    size: int
    valid: bool


@dataclass
class RestoreResult:
    backup_id: str
    safety_backup_id: str


class BackupService:
    def __init__(self, data_dir: Path, backup_root: Path):
        self.data_dir = data_dir
        self.backup_root = backup_root

    def create(self) -> BackupManifest:
        self.backup_root.mkdir(parents=True, exist_ok=True)
        backup_id = f"{utcnow().strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
        destination = self.backup_root / backup_id
        destination.mkdir()
        files = []
        schema_versions = {}
        for source in self._database_paths():
            relative = source.relative_to(self.data_dir).as_posix()
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with project_write_lock(source.parent), sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
                src.backup(dst)
                schema_versions[relative] = int(src.execute("PRAGMA user_version").fetchone()[0])
            files.append(self._file_metadata(relative, target))
        created_at = utcnow().isoformat()
        excluded = ["configuration", "api_tokens", "logs", "pid_files", "lock_files", "derived_indexes"]
        manifest = BackupManifest(backup_id, destination, created_at, files, schema_versions, excluded)
        (destination / "manifest.json").write_text(
            json.dumps(
                {
                    "format_version": 1,
                    "id": backup_id,
                    "created_at": created_at,
                    "files": files,
                    "schema_versions": schema_versions,
                    "excluded": excluded,
                },
                indent=2,
            )
        )
        return manifest

    def list(self) -> list[BackupInfo]:
        if not self.backup_root.exists():
            return []
        infos = []
        for manifest_path in sorted(self.backup_root.glob("*/manifest.json")):
            try:
                data = self._read_manifest(manifest_path.parent)
                files = self._validate(manifest_path.parent)
                valid = True
                size = sum(file["size"] for file in files)
            except BackupError:
                data = json.loads(manifest_path.read_text())
                valid = False
                size = 0
            projects = {
                PurePosixPath(file.get("path", "")).parts[1]
                for file in data.get("files", [])
                if PurePosixPath(file.get("path", "")).parts[:1] == ("projects",)
                and len(PurePosixPath(file.get("path", "")).parts) > 2
            }
            infos.append(
                BackupInfo(
                    id=data.get("id", manifest_path.parent.name),
                    path=manifest_path.parent,
                    created_at=data.get("created_at", ""),
                    project_count=len(projects),
                    size=size,
                    valid=valid,
                )
            )
        return infos

    def get(self, backup_id: str) -> BackupInfo | None:
        return next((info for info in self.list() if info.id == backup_id), None)

    def restore(self, reference: str) -> RestoreResult:
        candidate = Path(reference)
        backup_dir = candidate if candidate.is_dir() else self.backup_root / reference
        data = self._read_manifest(backup_dir)
        files = self._validate(backup_dir)
        staging = self.data_dir.parent / f".acrux-restore-{uuid.uuid4().hex}"
        staging.mkdir(parents=True)
        safety = None
        try:
            for file in files:
                source = backup_dir / file["path"]
                target = staging / file["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                self._integrity_check(target)
            safety = self.create()
            self._replace_payload(staging, data)
            shutil.rmtree(staging, ignore_errors=True)
            return RestoreResult(data["id"], safety.id)
        except Exception:
            if safety is not None:
                self._replace_payload(safety.path, self._read_manifest(safety.path))
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def _database_paths(self) -> list[Path]:
        if not self.data_dir.exists():
            return []
        paths = []
        for pattern in ("global/*.db", "projects/*/*.db"):
            for path in self.data_dir.glob(pattern):
                if path.is_file() and not path.is_symlink():
                    paths.append(path)
        return sorted(paths)

    def _file_metadata(self, relative: str, path: Path) -> dict:
        parts = PurePosixPath(relative).parts
        return {
            "path": relative,
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "role": parts[0],
            "project": parts[1] if parts[0] == "projects" else "global",
        }

    def _read_manifest(self, backup_dir: Path) -> dict:
        try:
            data = json.loads((backup_dir / "manifest.json").read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise BackupError(f"Invalid backup manifest: {backup_dir}") from exc
        if data.get("format_version") != 1 or not data.get("id"):
            raise BackupError("Unsupported backup manifest")
        return data

    def _validate(self, backup_dir: Path) -> list[dict]:
        data = self._read_manifest(backup_dir)
        files = data.get("files")
        if not isinstance(files, list) or not files:
            raise BackupError("Backup has no payload files")
        for relative, version in data.get("schema_versions", {}).items():
            if not isinstance(version, int) or version < 0:
                raise BackupError(f"Invalid schema version for {relative}")
            if relative.endswith("semantic.db") and version > 1:
                raise BackupError("Backup schema is newer than this Acrux")
        for file in files:
            relative = file.get("path", "")
            pure = PurePosixPath(relative)
            if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
                raise BackupError(f"Unsafe backup path: {relative}")
            payload = backup_dir / pure
            if payload.is_symlink() or not payload.is_file():
                raise BackupError(f"Invalid backup payload: {relative}")
            if payload.resolve().parent != (backup_dir / pure.parent).resolve():
                raise BackupError(f"Backup path escapes payload directory: {relative}")
            if payload.stat().st_size != file.get("size"):
                raise BackupError(f"Backup size mismatch: {relative}")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            if digest != file.get("sha256"):
                raise BackupError(f"Backup checksum mismatch: {relative}")
            self._integrity_check(payload)
        return files

    @staticmethod
    def _integrity_check(path: Path) -> None:
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        except sqlite3.Error as exc:
            raise BackupError(f"Invalid SQLite payload: {path.name}") from exc
        if result != "ok":
            raise BackupError(f"SQLite integrity check failed: {result}")

    def _replace_payload(self, staging: Path, manifest: dict) -> None:
        try:
            for file in manifest["files"]:
                source = staging / file["path"]
                target = self.data_dir / file["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                for suffix in ("-wal", "-shm"):
                    target.with_name(target.name + suffix).unlink(missing_ok=True)
                source.replace(target)
        except Exception as exc:
            raise BackupError(f"Could not replace live data: {exc}") from exc
