"""No-op reflection provider."""

from __future__ import annotations

from acrux.models import Episode, Fact, Skill
from acrux.reflection.base import ReflectionProvider


class NoneProvider(ReflectionProvider):
    async def reflect_episodes(self, episodes: list[Episode]) -> list[Fact]:
        return []

    async def reflect_kimi_episodes(self, episodes: list[Episode]) -> list[Fact]:
        return []

    async def extract_skills(
        self, episodes: list[Episode], facts: list[Fact], feedback: str | None = None
    ) -> list[Skill]:
        return []

    async def extract_kimi_skills(
        self, episodes: list[Episode], facts: list[Fact], retries: int = 2, feedback: str | None = None
    ) -> list[Skill]:
        return []
