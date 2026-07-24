"""Base reflection provider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from acrux.models import Episode, Fact, Skill


class ReflectionProvider(ABC):
    @abstractmethod
    async def reflect_episodes(self, episodes: list[Episode]) -> list[Fact]:
        """Extract facts from episodes."""
        ...

    @abstractmethod
    async def extract_skills(self, episodes: list[Episode], facts: list[Fact]) -> list[Skill]:
        """Extract reusable skills from episodes and facts."""
        ...

    def build_reflection_prompt(self, episodes: list[Episode]) -> str:
        text = "\n\n".join(
            f"Task: {e.task}\nOutcome: {e.outcome}\nRoot cause: {e.root_cause}\nFix pattern: {e.fix_pattern}\nTags: {', '.join(e.tags)}"
            for e in episodes
        )
        return (
            "/no_think\n"
            "You are a memory consolidation system for a coding agent. "
            "Review the following session traces and extract concise, reusable facts. "
            "Return ONLY valid JSON: a list of objects with keys "
            '{"content": "...", "source_session_id": "...", "confidence": 0.0-1.0, "tags": ["..."]}. '
            "Only extract facts that are likely to be useful in future coding sessions.\n\n"
            f"{text}\n\nFacts JSON:"
        )

    def build_kimi_reflection_prompt(self, episodes: list[Episode]) -> str:
        text = "\n\n".join(
            f"Task: {e.task}\nOutcome: {e.outcome}\nRoot cause: {e.root_cause}\nFix pattern: {e.fix_pattern}\nActions: {self._summarize_actions(e.actions)}\nTags: {', '.join(e.tags)}"
            for e in episodes
        )
        return (
            "/no_think\n"
            "You are a high-signal memory extractor for a coding assistant. "
            "A session log is noisy. Extract ONLY concrete, reusable knowledge: "
            "exact root causes of failures, precise fixes, verified shell commands, "
            "and stable patterns. Ignore speculation, half-attempts, future plans, "
            "and anything that depends on uncommitted state. "
            "Return ONLY valid JSON: a list of objects with keys "
            '{"content": "...", "source_session_id": "...", "confidence": 0.0-1.0, "tags": ["..."]}. '
            "If nothing useful can be extracted, return [].\n\n"
            f"{text}\n\nUseful facts JSON:"
        )

    def build_kimi_skill_prompt(self, episodes: list[Episode], facts: list[Fact]) -> str:
        ep_text = "\n\n".join(
            f"Task: {e.task}\nOutcome: {e.outcome}\nRoot cause: {e.root_cause}\nFix: {e.fix_pattern}"
            for e in episodes
        )
        fact_text = "\n".join(f"- {f.content}" for f in facts)
        return (
            "/no_think\n"
            "You extract reusable coding skills from noisy coding-assistant session logs. "
            "Create a skill ONLY if the facts describe a repeatable fix or procedure. "
            "A skill has: a name, preconditions (when to apply), and a procedure (steps). "
            "Return only valid JSON in this exact format:\n"
            '{"name": "...", "preconditions": ["..."], "procedure": ["..."], "evidence": [{"session_id": "..."}]}\n\n'
            f"Traces:\n{ep_text}\n\nFacts:\n{fact_text}\n\nSkill JSON:"
        )

    @staticmethod
    def _summarize_actions(actions: list) -> str:
        return "; ".join(
            f"{a.tool}: {a.command or a.target}" for a in actions if a.command or a.target
        )

    def build_skill_prompt(self, episodes: list[Episode], facts: list[Fact]) -> str:
        ep_text = "\n\n".join(
            f"Task: {e.task}\nOutcome: {e.outcome}\nRoot cause: {e.root_cause}\nFix: {e.fix_pattern}"
            for e in episodes
        )
        fact_text = "\n".join(f"- {f.content}" for f in facts)
        return (
            "/no_think\n"
            "You are a skill extraction system for a coding agent. "
            "Given session traces and extracted facts, generate a reusable skill. "
            "A skill has: a name, preconditions (when to apply), and a procedure (steps). "
            "Return only valid JSON in this exact format:\n"
            '{"name": "...", "preconditions": ["..."], "procedure": ["..."], "evidence": [{"session_id": "..."}]}\n\n'
            f"Traces:\n{ep_text}\n\nFacts:\n{fact_text}\n\nSkill JSON:"
        )
