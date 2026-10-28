"""Data models for acrux memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from acrux.utils import utcnow
from typing import Any
from uuid import uuid4


@dataclass
class Action:
    tool: str
    target: str = ""
    command: str = ""
    result: str = ""
    diff: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error_signature: str = ""
    output_truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "target": self.target,
            "command": self.command,
            "result": self.result,
            "diff": self.diff,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error_signature": self.error_signature,
            "output_truncated": self.output_truncated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        return cls(
            tool=data.get("tool", ""),
            target=data.get("target", ""),
            command=data.get("command", ""),
            result=data.get("result", ""),
            diff=data.get("diff", ""),
            exit_code=data.get("exit_code"),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            error_signature=data.get("error_signature", ""),
            output_truncated=data.get("output_truncated", False),
        )


@dataclass
class CodeChange:
    project: str
    session_id: str = ""
    commit_sha: str | None = None
    file_path: str = ""
    change_type: str = "modify"
    diff: str = ""
    truncated: bool = False
    source: str = "wrap"
    timestamp: str = field(default_factory=lambda: utcnow().isoformat())
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "session_id": self.session_id,
            "commit_sha": self.commit_sha,
            "file_path": self.file_path,
            "change_type": self.change_type,
            "diff": self.diff,
            "truncated": self.truncated,
            "source": self.source,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeChange:
        return cls(**data)


@dataclass
class Episode:
    session_id: str
    task: str
    project: str
    context: dict[str, Any] = field(default_factory=dict)
    actions: list[Action] = field(default_factory=list)
    outcome: str = ""
    root_cause: str = ""
    fix_pattern: str = ""
    tags: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: utcnow().isoformat())
    corrected: bool = False
    compacted: bool = False
    source: str = ""
    git_info: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task": self.task,
            "project": self.project,
            "context": self.context,
            "actions": [a.to_dict() for a in self.actions],
            "outcome": self.outcome,
            "root_cause": self.root_cause,
            "fix_pattern": self.fix_pattern,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "corrected": self.corrected,
            "compacted": self.compacted,
            "source": self.source,
            "git_info": self.git_info,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Episode:
        return cls(
            session_id=data.get("session_id", str(uuid4())),
            task=data.get("task", ""),
            project=data.get("project", "default"),
            context=data.get("context", {}),
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            outcome=data.get("outcome", ""),
            root_cause=data.get("root_cause", ""),
            fix_pattern=data.get("fix_pattern", ""),
            tags=data.get("tags", []),
            timestamp=data.get("timestamp", utcnow().isoformat()),
            corrected=data.get("corrected", False),
            compacted=data.get("compacted", False),
            source=data.get("source", ""),
            git_info=data.get("git_info"),
        )


@dataclass
class Fact:
    project: str
    content: str
    source: str = ""
    tags: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: utcnow().isoformat())
    id: int | None = None
    confidence: float = 0.0
    verified_count: int = 0
    contradicted_count: int = 0
    stale: bool = False
    git_info: dict[str, Any] | None = None
    # New shared schema fields
    parent_id: int | None = None
    version_group_id: int | None = None
    is_current: bool = True
    fact_type: str = "positive"  # positive | negative
    cluster_id: int | None = None
    inheritance_mode: str = "none"  # none | inherits | shared
    decay_score: float = 0.0
    last_recalled_at: str | None = None
    checksum: str | None = None
    recall_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project": self.project,
            "content": self.content,
            "source": self.source,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "verified_count": self.verified_count,
            "contradicted_count": self.contradicted_count,
            "stale": self.stale,
            "git_info": self.git_info,
            "parent_id": self.parent_id,
            "version_group_id": self.version_group_id,
            "is_current": self.is_current,
            "fact_type": self.fact_type,
            "cluster_id": self.cluster_id,
            "inheritance_mode": self.inheritance_mode,
            "decay_score": self.decay_score,
            "last_recalled_at": self.last_recalled_at,
            "checksum": self.checksum,
            "recall_count": self.recall_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Fact:
        return cls(
            project=data.get("project", "default"),
            content=data.get("content", ""),
            source=data.get("source", ""),
            tags=data.get("tags", []),
            timestamp=data.get("timestamp", utcnow().isoformat()),
            id=data.get("id"),
            confidence=data.get("confidence", 0.0),
            verified_count=data.get("verified_count", 0),
            contradicted_count=data.get("contradicted_count", 0),
            stale=data.get("stale", False),
            git_info=data.get("git_info"),
            parent_id=data.get("parent_id"),
            version_group_id=data.get("version_group_id"),
            is_current=data.get("is_current", True),
            fact_type=data.get("fact_type", "positive"),
            cluster_id=data.get("cluster_id"),
            inheritance_mode=data.get("inheritance_mode", "none"),
            decay_score=data.get("decay_score", 0.0),
            last_recalled_at=data.get("last_recalled_at"),
            checksum=data.get("checksum"),
            recall_count=data.get("recall_count", 0),
        )

    def default_confidence(self) -> float:
        """Return the default confidence for this fact based on its source."""
        source_lower = (self.source or "").lower()
        if "verified" in source_lower or "skill" in source_lower:
            return 0.9
        if "kimi" in source_lower:
            return 0.7
        if "llm" in source_lower or "model" in source_lower or "reflection" in source_lower:
            return 0.7
        if "compaction" in source_lower:
            return 0.6
        if "user" in source_lower:
            return 0.8
        return 0.5

    def update_confidence(self) -> None:
        """Recalculate confidence from base, verified_count and contradicted_count."""
        base = self.default_confidence()
        total = max(1, self.verified_count + self.contradicted_count)
        verified_ratio = self.verified_count / total
        contradicted_ratio = self.contradicted_count / total
        self.confidence = max(0.0, min(1.0, base + 0.2 * verified_ratio - 0.3 * contradicted_ratio))


@dataclass
class Skill:
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    project: str = "default"
    name: str = ""
    preconditions: list[str] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0
    verified: bool = False
    tags: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: utcnow().isoformat())
    # Extended capability fields
    parameters: dict[str, str] = field(default_factory=dict)  # e.g. {"test_command": "pytest tests/"}
    composition: list[str] = field(default_factory=list)  # skill IDs this skill calls
    precondition_checks: list[str] = field(default_factory=list)  # executable checks
    cost: str = "unknown"  # low | medium | high | unknown
    risk: str = "unknown"  # read-only | edits | destructive | unknown

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project": self.project,
            "name": self.name,
            "preconditions": self.preconditions,
            "procedure": self.procedure,
            "evidence": self.evidence,
            "success_rate": self.success_rate,
            "verified": self.verified,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "parameters": self.parameters,
            "composition": self.composition,
            "precondition_checks": self.precondition_checks,
            "cost": self.cost,
            "risk": self.risk,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Skill:
        return cls(
            id=data.get("id", str(uuid4())[:8]),
            project=data.get("project", "default"),
            name=data.get("name", ""),
            preconditions=data.get("preconditions", []),
            procedure=data.get("procedure", []),
            evidence=data.get("evidence", []),
            success_rate=data.get("success_rate", 0.0),
            verified=data.get("verified", False),
            tags=data.get("tags", []),
            timestamp=data.get("timestamp", utcnow().isoformat()),
            parameters=data.get("parameters", {}),
            composition=data.get("composition", []),
            precondition_checks=data.get("precondition_checks", []),
            cost=data.get("cost", "unknown"),
            risk=data.get("risk", "unknown"),
        )
