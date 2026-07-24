# Acrux Spec

Open JSON schemas for Acrux memory records. Any agent or tool can emit these formats to be compatible with Acrux.

## Episode

```json
{
  "session_id": "string",
  "task": "string",
  "project": "string",
  "context": {},
  "actions": [],
  "outcome": "string",
  "root_cause": "string",
  "fix_pattern": "string",
  "tags": ["string"],
  "timestamp": "ISO 8601",
  "corrected": false,
  "compacted": false,
  "source": "string",
  "git_info": {}
}
```

## Fact

```json
{
  "id": 1,
  "project": "string",
  "content": "string",
  "source": "string",
  "tags": ["string"],
  "timestamp": "ISO 8601",
  "confidence": 0.0,
  "verified_count": 0,
  "contradicted_count": 0,
  "stale": false,
  "fact_type": "positive"
}
```

## Skill

```json
{
  "id": "string",
  "project": "string",
  "name": "string",
  "preconditions": ["string"],
  "procedure": ["string"],
  "evidence": [],
  "success_rate": 0.0,
  "verified": false,
  "tags": ["string"],
  "timestamp": "ISO 8601"
}
```

## Validator

Use `acrux validate-spec <file> --kind <episode|fact|skill>` to validate a JSON file against these schemas.
