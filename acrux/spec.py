"""Acrux open spec: episode, fact, and skill JSON schemas with validation."""

from __future__ import annotations

from typing import Any

EPISODE_SCHEMA = {
    "type": "object",
    "required": ["session_id", "task", "project"],
    "properties": {
        "session_id": {"type": "string"},
        "task": {"type": "string"},
        "project": {"type": "string"},
        "context": {"type": "object"},
        "actions": {"type": "array"},
        "outcome": {"type": "string"},
        "root_cause": {"type": "string"},
        "fix_pattern": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "timestamp": {"type": "string"},
        "corrected": {"type": "boolean"},
        "compacted": {"type": "boolean"},
        "source": {"type": "string"},
        "git_info": {"type": ["object", "null"]},
    },
}

FACT_SCHEMA = {
    "type": "object",
    "required": ["project", "content"],
    "properties": {
        "id": {"type": ["integer", "null"]},
        "project": {"type": "string"},
        "content": {"type": "string"},
        "source": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "timestamp": {"type": "string"},
        "confidence": {"type": "number"},
        "verified_count": {"type": "integer"},
        "contradicted_count": {"type": "integer"},
        "stale": {"type": "boolean"},
        "fact_type": {"type": "string"},
    },
}

SKILL_SCHEMA = {
    "type": "object",
    "required": ["project", "name", "preconditions", "procedure"],
    "properties": {
        "id": {"type": "string"},
        "project": {"type": "string"},
        "name": {"type": "string"},
        "preconditions": {"type": "array", "items": {"type": "string"}},
        "procedure": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array"},
        "success_rate": {"type": "number"},
        "verified": {"type": "boolean"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "timestamp": {"type": "string"},
    },
}

SCHEMAS = {"episode": EPISODE_SCHEMA, "fact": FACT_SCHEMA, "skill": SKILL_SCHEMA}


def validate(data: dict[str, Any], kind: str) -> list[str]:
    """Validate a dict against a schema. Returns a list of errors."""
    schema = SCHEMAS.get(kind)
    if not schema:
        return [f"Unknown schema kind: {kind}"]
    errors: list[str] = []
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"missing required field: {field}")
    for field, rules in schema.get("properties", {}).items():
        if field not in data:
            continue
        value = data[field]
        expected = rules.get("type")
        if expected and not _type_matches(value, expected):
            errors.append(f"field {field} has wrong type: expected {expected}")
    return errors


def _type_matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_type_matches(value, e) for e in expected)
    mapping = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "object": dict,
        "array": list,
        "null": type(None),
    }
    py_type = mapping.get(expected)
    if py_type is None:
        return True
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, py_type)
