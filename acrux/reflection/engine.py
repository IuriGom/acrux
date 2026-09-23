"""Reflection engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from acrux.config import AcruxConfig
from acrux.models import Episode
from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.reflection.base import ReflectionProvider
from acrux.reflection.kimi import KimiProvider
from acrux.reflection.none import NoneProvider
from acrux.reflection.ollama import OllamaProvider

if TYPE_CHECKING:
    from acrux.mcp_server import AcruxMCPServer


class ReflectionEngine:
    def __init__(
        self,
        config: AcruxConfig,
        episodic: EpisodicStore,
        semantic: SemanticStore,
        procedural: ProceduralDBStore,
        mcp_server: "AcruxMCPServer | None" = None,
    ):
        self.config = config
        self.episodic = episodic
        self.semantic = semantic
        self.procedural = procedural
        self.mcp_server = mcp_server
        self.provider = self._create_provider()

    def _create_provider(self) -> ReflectionProvider:
        provider = self.config.reflection.provider
        if provider == "ollama":
            return OllamaProvider(self.config.reflection.model, self.config.reflection.host)
        if provider == "kimi":
            return KimiProvider(self.mcp_server)
        return NoneProvider()

    async def reflect_project(self, project: str, batch_size: int = 10) -> dict[str, int]:
        from acrux.utils import available_ram_mb, set_degraded

        batch_size = min(batch_size, self.config.max_batch_size)
        if not self.config.check_storage_budget():
            raise RuntimeError("Storage budget exceeded. Run 'acrux prune' or increase the limit.")

        ram = available_ram_mb()
        ram_target = self.config.ram_target_bytes // (1024 * 1024)
        threshold = max(ram_target // 2, 300)
        if ram < threshold:
            set_degraded(
                f"Low RAM: {ram} MB available (threshold {threshold} MB); skipping reflection"
            )
            return {"facts": 0, "skills": 0}

        episodes = self.episodic.get_unreflected(project, limit=batch_size)
        if not episodes:
            return {"facts": 0, "skills": 0}

        from acrux.verify import SkillVerifier

        verifier = SkillVerifier(self.episodic, self.procedural)

        # Correction-weighted pass: user corrections are the highest-signal data.
        corrected = [e for e in episodes if e.corrected]
        remaining = [e for e in episodes if not e.corrected]
        total_facts = 0
        total_skills = 0

        if corrected:
            facts = await self.provider.reflect_kimi_episodes(corrected)
            for fact in facts:
                fact.tags = list(set(fact.tags + ["correction", "high-signal"]))
                fact.confidence = min(1.0, fact.confidence + 0.2)
                self.semantic.add_pending_fact(fact)
            total_facts += len(facts)
            skills = await self.provider.extract_kimi_skills(corrected, facts)
            validated = 0
            for skill in skills:
                validated += await self._validate_skill(
                    skill,
                    project,
                    verifier,
                    lambda fb, c=corrected, f=facts: self.provider.extract_kimi_skills(
                        c, f, feedback=fb
                    ),
                    extra_tags=["correction"],
                )
            total_skills += validated
            if facts or validated:
                self.episodic.mark_compacted([e.session_id for e in corrected])

        kimi_episodes = [e for e in remaining if self._is_kimi(e)]
        normal_episodes = [e for e in remaining if not self._is_kimi(e)]

        if kimi_episodes:
            for cluster in await self._cluster_episodes(kimi_episodes):
                facts = await self.provider.reflect_kimi_episodes(cluster)
                for fact in facts:
                    self.semantic.add_pending_fact(fact)
                total_facts += len(facts)

                skills = await self.provider.extract_kimi_skills(cluster, facts)
                validated = 0
                for skill in skills:
                    validated += await self._validate_skill(
                        skill,
                        project,
                        verifier,
                        lambda fb, c=cluster, f=facts: self.provider.extract_kimi_skills(
                            c, f, feedback=fb
                        ),
                    )
                total_skills += validated

                if facts or validated:
                    self.episodic.mark_compacted([e.session_id for e in cluster])

        if normal_episodes:
            for cluster in await self._cluster_episodes(normal_episodes):
                facts = await self.provider.reflect_episodes(cluster)
                for fact in facts:
                    self.semantic.add_pending_fact(fact)
                total_facts += len(facts)

                skills = await self.provider.extract_skills(cluster, facts)
                validated = 0
                for skill in skills:
                    validated += await self._validate_skill(
                        skill,
                        project,
                        verifier,
                        lambda fb, c=cluster, f=facts: self.provider.extract_skills(
                            c, f, feedback=fb
                        ),
                    )
                total_skills += validated

                if facts or validated:
                    self.episodic.mark_compacted([e.session_id for e in cluster])

        return {"facts": total_facts, "skills": total_skills}

    async def _validate_skill(
        self,
        skill,
        project: str,
        verifier,
        retry_extract,
        extra_tags: list[str] | None = None,
    ) -> int:
        """Verify a generated skill; on rejection, retry once with the errors as feedback."""
        skill.project = project
        if extra_tags:
            skill.tags = list(set(skill.tags + extra_tags))
        ok, errors = await verifier.verify(skill)
        if ok:
            self.procedural.add_pending(skill)
            return 1
        if retry_extract is not None:
            retried = await retry_extract("; ".join(errors))
            for candidate in retried:
                candidate.project = project
                if extra_tags:
                    candidate.tags = list(set(candidate.tags + extra_tags))
                ok, _ = await verifier.verify(candidate)
                if ok:
                    self.procedural.add_pending(candidate)
                    return 1
        self._log_skill_rejected(project, skill, errors)
        return 0

    async def _cluster_episodes(self, episodes: list[Episode]) -> list[list[Episode]]:
        """Cluster episodes by embedding similarity; fall back to tags."""
        embedder = getattr(self.semantic, "embedder", None)
        if not embedder or len(episodes) < 2:
            return self._cluster_by_tags(episodes)

        try:
            from acrux.embeddings import cosine_similarity

            texts = [
                f"{e.task} {e.outcome} {e.root_cause} {e.fix_pattern}" for e in episodes
            ]
            vectors = [await embedder.embed(t) for t in texts]
            clusters: list[list[int]] = []
            for i, vec in enumerate(vectors):
                placed = False
                for cluster in clusters:
                    centroid = self._centroid([vectors[j] for j in cluster])
                    if cosine_similarity(vec, centroid) >= 0.75:
                        cluster.append(i)
                        placed = True
                        break
                if not placed:
                    clusters.append([i])
            return [[episodes[i] for i in cluster] for cluster in clusters]
        except Exception:
            return self._cluster_by_tags(episodes)

    @staticmethod
    def _centroid(vectors: list[list[float]]) -> list[float]:
        if not vectors:
            return []
        dim = len(vectors[0])
        return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]

    @staticmethod
    def _cluster_by_tags(episodes: list[Episode]) -> list[list[Episode]]:
        """Group episodes by shared tags so reflection extracts coherent topics."""
        clusters: dict[tuple, list[Episode]] = {}
        for ep in episodes:
            key = tuple(sorted(ep.tags)) if ep.tags else (ep.task.split()[0] if ep.task else "unknown",)
            clusters.setdefault(key, []).append(ep)
        return list(clusters.values())

    def _log_skill_rejected(self, project: str, skill, errors: list[str]) -> None:
        import logging

        logging.getLogger("acrux").warning(
            "Skill rejected for project %s: %s (%s)", project, skill.name, ", ".join(errors)
        )

    @staticmethod
    def _is_kimi(episode: Episode) -> bool:
        if episode.source and episode.source.lower().startswith("kimi"):
            return True
        return any(str(tag).lower() == "kimi" for tag in episode.tags)

    async def reflect_all(self, batch_size: int = 10) -> dict[str, dict[str, int]]:
        if not self.config.check_storage_budget():
            raise RuntimeError("Storage budget exceeded. Run 'acrux prune' or increase the limit.")

        # Discover projects from data directory
        projects = [p.name for p in self.config.projects_dir.iterdir() if p.is_dir()]
        results = {}
        for project in projects:
            results[project] = await self.reflect_project(project, batch_size)
        return results
