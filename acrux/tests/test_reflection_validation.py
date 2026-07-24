"""Tests for structured reflection validation."""

from acrux.models import Episode
from acrux.reflection.ollama import OllamaProvider


def test_parse_facts_json_valid() -> None:
    provider = OllamaProvider()
    episodes = [Episode(session_id="s1", task="t", project="test", outcome="ok")]
    text = '[{"content": "This is a useful fact about the codebase.", "confidence": 0.9, "tags": ["rust"]}]'
    facts = provider._parse_facts_json(text, episodes)
    assert len(facts) == 1
    assert facts[0].content.startswith("This is a useful fact")
    assert facts[0].confidence == 0.9
    assert facts[0].tags == ["rust"]


def test_parse_facts_json_invalid() -> None:
    provider = OllamaProvider()
    episodes = [Episode(session_id="s1", task="t", project="test", outcome="ok")]
    assert provider._parse_facts_json("not json at all", episodes) == []
    assert provider._parse_facts_json("[{\"content\": \"short\"}]", episodes) == []


def test_parse_facts_json_with_markdown() -> None:
    provider = OllamaProvider()
    episodes = [Episode(session_id="s1", task="t", project="test", outcome="ok")]
    text = '```json\n[{"content": "A longer useful fact.", "confidence": 0.8}]\n```'
    facts = provider._parse_facts_json(text, episodes)
    assert len(facts) == 1


def test_parse_skill_json_valid() -> None:
    provider = OllamaProvider()
    episodes = [Episode(session_id="s1", task="t", project="test", outcome="ok")]
    text = '{"name": "fix_bug", "preconditions": ["rust"], "procedure": ["read", "fix"], "evidence": [{"session_id": "s1"}]}'
    skill = provider._parse_skill_json(text, "test", episodes)
    assert skill is not None
    assert skill.name == "fix_bug"
    assert skill.evidence[0]["session_id"] == "s1"


def test_parse_skill_json_invalid() -> None:
    provider = OllamaProvider()
    episodes = [Episode(session_id="s1", task="t", project="test", outcome="ok")]
    assert provider._parse_skill_json("not json", "test", episodes) is None
    assert provider._parse_skill_json('{"name": ""}', "test", episodes) is None
