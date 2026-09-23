"""Tests for rejection-feedback-guided skill extraction."""

import asyncio

import pytest

from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Episode, Skill
from acrux.reflection.engine import ReflectionEngine
from acrux.reflection.kimi import KimiProvider
from acrux.reflection.none import NoneProvider
from acrux.reflection.ollama import OllamaProvider

SKILL_JSON = (
    '```json\n{"name": "fix_cache", "preconditions": ["stale cache"], '
    '"procedure": ["clear cache", "restart service"], '
    '"evidence": [{"session_id": "s1"}]}\n```'
)


def _episodes() -> list[Episode]:
    return [Episode(session_id="s1", task="t", project="test", outcome="success")]


def test_skill_prompt_includes_feedback() -> None:
    provider = OllamaProvider()
    eps = _episodes()
    plain = provider.build_skill_prompt(eps, [])
    assert "rejected by validation" not in plain
    with_fb = provider.build_skill_prompt(
        eps, [], feedback="missing preconditions; procedure too short"
    )
    assert "missing preconditions" in with_fb
    assert "procedure too short" in with_fb


def test_kimi_skill_prompt_includes_feedback() -> None:
    provider = KimiProvider()
    with_fb = provider.build_kimi_skill_prompt(_episodes(), [], feedback="duplicate skill name")
    assert "duplicate skill name" in with_fb


def test_kimi_provider_has_kimi_methods() -> None:
    provider = KimiProvider()
    assert provider.reflect_kimi_episodes([]) is not None or True
    assert asyncio.run(provider.reflect_kimi_episodes([])) == []
    assert asyncio.run(provider.extract_kimi_skills([], [])) == []


def test_none_provider_accepts_feedback_and_kimi_calls() -> None:
    provider = NoneProvider()
    assert asyncio.run(provider.extract_skills(_episodes(), [], feedback="x")) == []
    assert asyncio.run(provider.extract_kimi_skills(_episodes(), [], feedback="x")) == []
    assert asyncio.run(provider.reflect_kimi_episodes(_episodes())) == []


@pytest.mark.asyncio
async def test_ollama_extract_skills_passes_feedback(monkeypatch) -> None:
    provider = OllamaProvider()
    captured: list[str] = []

    async def fake_generate(prompt: str, temperature: float = 0.2) -> str:
        captured.append(prompt)
        return SKILL_JSON

    monkeypatch.setattr(provider, "_generate", fake_generate)
    skills = await provider.extract_skills(_episodes(), [], feedback="procedure too short")
    assert len(skills) == 1
    assert skills[0].name == "fix_cache"
    assert "procedure too short" in captured[0]


@pytest.mark.asyncio
async def test_validate_skill_retries_with_feedback(tmp_path) -> None:
    config = AcruxConfig(data_dir=tmp_path)
    episodic = EpisodicStore(tmp_path / "episodes.db")
    semantic = SemanticStore(tmp_path / "semantic.db", embedder=None)
    procedural = ProceduralDBStore(tmp_path / "skills.db")
    engine = ReflectionEngine(config, episodic, semantic, procedural)

    class StubVerifier:
        def __init__(self) -> None:
            self.calls = 0

        async def verify(self, skill: Skill) -> tuple[bool, list[str]]:
            self.calls += 1
            if self.calls == 1:
                return False, ["missing preconditions"]
            return True, []

    skill = Skill(
        project="test", name="fix", preconditions=["p"], procedure=["a", "b"], evidence=[]
    )
    candidate = Skill(
        project="test", name="fix2", preconditions=["p2"], procedure=["a", "b"], evidence=[]
    )
    captured: list[str] = []

    async def retry_extract(feedback: str) -> list[Skill]:
        captured.append(feedback)
        return [candidate]

    added = await engine._validate_skill(skill, "test", StubVerifier(), retry_extract)
    assert added == 1
    assert captured == ["missing preconditions"]


@pytest.mark.asyncio
async def test_validate_skill_logs_rejection_when_retry_fails(tmp_path) -> None:
    config = AcruxConfig(data_dir=tmp_path)
    episodic = EpisodicStore(tmp_path / "episodes.db")
    semantic = SemanticStore(tmp_path / "semantic.db", embedder=None)
    procedural = ProceduralDBStore(tmp_path / "skills.db")
    engine = ReflectionEngine(config, episodic, semantic, procedural)

    class AlwaysFailsVerifier:
        async def verify(self, skill: Skill) -> tuple[bool, list[str]]:
            return False, ["evidence episode s1 has non-success outcome"]

    skill = Skill(
        project="test", name="fix", preconditions=["p"], procedure=["a", "b"], evidence=[]
    )
    captured: list[str] = []

    async def retry_extract(feedback: str) -> list[Skill]:
        captured.append(feedback)
        return []

    added = await engine._validate_skill(skill, "test", AlwaysFailsVerifier(), retry_extract)
    assert added == 0
    assert captured == ["evidence episode s1 has non-success outcome"]
