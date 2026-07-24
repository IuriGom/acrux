"""Procedural memory store backed by YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from acrux.models import Skill


class ProceduralStore:
    def __init__(self, skills_path: Path):
        self.skills_path = skills_path
        self.skills_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: tuple[float, list[Skill]] | None = None
        if not self.skills_path.exists():
            self._save([])

    def _load(self) -> list[Skill]:
        if not self.skills_path.exists():
            return []
        # PyYAML parsing of a large skills file takes ~17s; cache by mtime so
        # repeated reads within a process are instant.
        mtime = self.skills_path.stat().st_mtime
        if self._cache and self._cache[0] == mtime:
            return list(self._cache[1])
        loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
        with open(self.skills_path) as f:
            data = yaml.load(f, Loader=loader) or []
        skills = [Skill.from_dict(item) for item in data]
        self._cache = (mtime, skills)
        return list(skills)

    def _save(self, skills: list[Skill]) -> None:
        with open(self.skills_path, "w") as f:
            yaml.safe_dump(
                [s.to_dict() for s in skills], f, default_flow_style=False, sort_keys=False
            )
        self._cache = None

    def get_skills_timeline(
        self,
        project: str,
        since: str | None = None,
        until: str | None = None,
    ) -> list[dict[str, Any]]:
        skills = self.get_all(project)
        result = []
        for skill in skills:
            ts = skill.timestamp
            if since and ts < since:
                continue
            if until and ts > until:
                continue
            result.append({"type": "skill", "timestamp": ts, "data": skill.to_dict()})
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        return result

    def add(self, skill: Skill) -> None:
        skills = self._load()
        # Deduplicate by name within same project
        skills = [s for s in skills if not (s.name == skill.name and s.project == skill.project)]
        skills.append(skill)
        self._save(skills)

    def get_all(self, project: str | None = None) -> list[Skill]:
        skills = self._load()
        if project:
            return [s for s in skills if s.project == project]
        return skills

    def list_skills(
        self,
        project: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Skill]:
        skills = self.get_all(project)
        return skills[offset : offset + limit]

    def delete_by_id(self, skill_id: str) -> bool:
        skills = self._load()
        new_skills = [s for s in skills if s.id != skill_id]
        if len(new_skills) == len(skills):
            return False
        self._save(new_skills)
        return True

    def search(self, project: str, query: str, limit: int = 20) -> list[Skill]:
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        skills = self.get_all(project)
        if not terms:
            return skills[:limit]

        results = []
        for skill in skills:
            text = " ".join(
                [skill.name]
                + skill.preconditions
                + skill.procedure
                + [str(e) for e in skill.evidence]
            ).lower()
            score = sum(1 for t in terms if t in text)
            if score > 0:
                results.append((score, skill))

        results.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in results[:limit]]

    def get_by_id(self, skill_id: str) -> Skill | None:
        for skill in self._load():
            if skill.id == skill_id:
                return skill
        return None

    def update(self, skill: Skill) -> None:
        skills = self._load()
        for i, s in enumerate(skills):
            if s.id == skill.id:
                skills[i] = skill
                self._save(skills)
                return

    def update_success(self, skill_id: str, success: bool = True) -> None:
        skills = self._load()
        for skill in skills:
            if skill.id == skill_id:
                total = sum(1 for _ in skill.evidence) + 1
                successes = sum(1 for e in skill.evidence if e.get("success")) + (
                    1 if success else 0
                )
                skill.success_rate = successes / total if total > 0 else 0.0
                self._save(skills)
                return

    def import_skills(self, skills: list[dict[str, Any]]) -> int:
        existing = self._load()
        existing_names = {(s.name, s.project) for s in existing}
        added = 0
        for data in skills:
            skill = Skill.from_dict(data)
            if (skill.name, skill.project) not in existing_names:
                existing.append(skill)
                existing_names.add((skill.name, skill.project))
                added += 1
        self._save(existing)
        return added

    def export_skills(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._load()]

    def count(self, project: str | None = None) -> int:
        return len(self.get_all(project))
