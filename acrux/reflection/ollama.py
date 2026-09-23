"""Ollama reflection provider."""

from __future__ import annotations

import json

import httpx

from acrux.models import Episode, Fact, Skill
from acrux.reflection.base import ReflectionProvider


class OllamaProvider(ReflectionProvider):
    def __init__(self, model: str = "qwen3:14b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")
        self.client = httpx.AsyncClient(timeout=600.0)

    async def reflect_episodes(self, episodes: list[Episode], retries: int = 2) -> list[Fact]:
        if not episodes:
            return []
        # Small models intermittently bail with "[]" on borderline input even
        # when facts exist; retry a couple of times before accepting empty.
        for attempt in range(retries + 1):
            prompt = self.build_reflection_prompt(episodes)
            response = await self._generate(prompt)
            facts = self._parse_facts_json(response, episodes)
            if facts:
                return facts
        return []

    async def extract_skills(
        self, episodes: list[Episode], facts: list[Fact], retries: int = 2
    ) -> list[Skill]:
        if not episodes:
            return []

        project = episodes[0].project
        for attempt in range(retries + 1):
            prompt = self.build_skill_prompt(episodes, facts)
            response = await self._generate(prompt)
            skill = self._parse_skill_json(response, project, episodes)
            if skill:
                return [skill]
            if attempt < retries:
                continue
        return []

    async def reflect_kimi_episodes(self, episodes: list[Episode], retries: int = 2) -> list[Fact]:
        if not episodes:
            return []
        for attempt in range(retries + 1):
            prompt = self.build_kimi_reflection_prompt(episodes)
            response = await self._generate(prompt, temperature=0.15)
            facts = self._parse_facts_json(response, episodes, source_override="kimi-reflection")
            if facts:
                return facts
        return []

    async def extract_kimi_skills(
        self, episodes: list[Episode], facts: list[Fact], retries: int = 2
    ) -> list[Skill]:
        if not episodes:
            return []

        project = episodes[0].project
        for attempt in range(retries + 1):
            prompt = self.build_kimi_skill_prompt(episodes, facts)
            response = await self._generate(prompt, temperature=0.15)
            skill = self._parse_skill_json(response, project, episodes)
            if skill:
                skill.tags = ["kimi"]
                return [skill]
            if attempt < retries:
                continue
        return []

    async def _generate(self, prompt: str, temperature: float = 0.2) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Disable reasoning-mode: thinking tokens count against num_predict,
            # and when the trace is long the actual response comes back EMPTY,
            # which silently yielded "+0 facts" reflections. The /no_think prompt
            # prefix is not honored through /api/generate; this flag is.
            "think": False,
            # Reflection prompts are short; don't let the server's global
            # OLLAMA_CONTEXT_LENGTH (256k) inflate the KV cache. At 256k even a
            # 4B model allocates ~23 GB of context and swaps itself to death.
            "options": {"temperature": temperature, "num_predict": 1024, "num_ctx": 16384},
        }
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    def _parse_facts_json(
        self, text: str, episodes: list[Episode], source_override: str | None = None
    ) -> list[Fact]:
        data = self._extract_json_array(text)
        if data is None:
            return []
        facts = []
        project = episodes[0].project
        git_info = episodes[0].git_info if episodes else None
        default_source = source_override or episodes[0].session_id
        default_tags = episodes[0].tags
        for item in data:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if len(content) < 10:
                continue
            source = item.get("source_session_id") or default_source
            confidence = float(item.get("confidence", 0.5))
            tags = item.get("tags") or default_tags
            if isinstance(tags, str):
                tags = [tags]
            facts.append(
                Fact(
                    project=project,
                    content=content,
                    source=source,
                    confidence=confidence,
                    tags=list(tags),
                    git_info=git_info,
                )
            )
        return facts

    def _parse_skill_json(
        self, text: str, project: str, episodes: list[Episode]
    ) -> Skill | None:
        data = self._extract_json_object(text)
        if not data:
            return None
        name = (data.get("name") or "").strip()
        if not name:
            return None
        preconditions = data.get("preconditions") or []
        procedure = data.get("procedure") or []
        evidence = data.get("evidence") or []
        valid_ids = {e.session_id for e in episodes}
        fixed_evidence = []
        for ev in evidence:
            if isinstance(ev, dict):
                sid = ev.get("session_id") or ev.get("id")
                if sid in valid_ids:
                    fixed_evidence.append(ev)
        if not fixed_evidence:
            fixed_evidence = [{"session_id": e.session_id} for e in episodes]
        if isinstance(preconditions, str):
            preconditions = [preconditions]
        if isinstance(procedure, str):
            procedure = [procedure]
        if not preconditions or not procedure:
            return None
        return Skill(
            project=project,
            name=name,
            preconditions=list(preconditions),
            procedure=list(procedure),
            evidence=fixed_evidence,
            verified=False,
        )

    @staticmethod
    def _extract_json_array(text: str) -> list | None:
        # Try to find a JSON array in the text, possibly wrapped in markdown.
        candidates = [text]
        if "```" in text:
            blocks = text.split("```")
            candidates.extend(blocks)
        for candidate in candidates:
            candidate = candidate.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            start = candidate.find("[")
            end = candidate.rfind("]")
            if start == -1 or end == -1 or end <= start:
                continue
            try:
                data = json.loads(candidate[start : end + 1])
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _extract_json_object(text: str) -> dict | None:
        candidates = [text]
        if "```" in text:
            blocks = text.split("```")
            candidates.extend(blocks)
        for candidate in candidates:
            candidate = candidate.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end <= start:
                continue
            try:
                data = json.loads(candidate[start : end + 1])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
        return None
