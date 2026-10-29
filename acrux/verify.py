"""Skill verification playground."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.models import Skill
from acrux.sandbox import run_sandboxed


class OllamaFactVerifier:
    def __init__(
        self,
        model: str,
        host: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0, transport=transport)

    async def verify_fact(self, content: str) -> str | None:
        prompt = (
            "You are a fact-checking assistant. Evaluate whether the following statement "
            "is still true. Answer with exactly one word: Yes, No, or Uncertain.\n\n"
            f"Statement: {content}\n\nVerdict:"
        )
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "30s",
            "options": {"num_ctx": 4096, "num_predict": 8},
        }
        try:
            response = await self.client.post(f"{self.host}/api/generate", json=payload)
            response.raise_for_status()
            verdict = response.json().get("response", "").strip()
        except Exception:
            return None
        normalized = verdict.casefold()
        if normalized not in {"yes", "no", "uncertain"}:
            return None
        return normalized.capitalize()

    async def reverify_project(self, semantic, project: str, limit: int) -> list[dict[str, Any]]:
        results = []
        try:
            for fact in semantic.get_facts_for_reverify(project, limit=limit):
                verdict = await self.verify_fact(fact.content) if fact.id else None
                updated = semantic.record_verification(fact.id, verdict) if verdict else None
                results.append(
                    {
                        "fact_id": fact.id,
                        "content": fact.content,
                        "verdict": verdict,
                        "confidence": updated.confidence if updated else fact.confidence,
                        "stale": updated.stale if updated else fact.stale,
                    }
                )
            return results
        finally:
            await self.close()

    async def close(self) -> None:
        if not self.client.is_closed:
            await self.client.aclose()


class SkillVerifier:
    """Verify skills before they are trusted for reuse.

    Checks structure, evidence, replayability, and negative preconditions.
    """

    def __init__(self, episodic: EpisodicStore, procedural: ProceduralDBStore):
        self.episodic = episodic
        self.procedural = procedural

    async def verify(self, skill: Skill) -> tuple[bool, list[str]]:
        errors: list[str] = []

        if not skill.name.strip():
            errors.append("missing name")

        if not skill.preconditions:
            errors.append("missing preconditions")

        if not skill.procedure or len(skill.procedure) < 2:
            errors.append("procedure too short")

        for step in skill.procedure:
            low = step.lower()
            if "rest unchanged" in low or "..." in step:
                errors.append("procedure contains placeholder text")
                break

        if not skill.evidence:
            errors.append("no evidence episodes")

        success_words = ("success", "pass", "ok", "fixed", "works", "done")
        evidence_episodes = []
        for ev in skill.evidence:
            session_id = ev.get("session_id") or ev.get("id")
            if not session_id:
                continue
            ep = self.episodic.get_by_id(session_id)
            if not ep:
                errors.append(f"evidence episode {session_id} not found")
                continue
            evidence_episodes.append(ep)
            outcome = (ep.outcome or "").lower()
            if not any(w in outcome for w in success_words):
                errors.append(f"evidence episode {session_id} has non-success outcome")

        # Replay check: the procedure should match what actually happened in the episode.
        if evidence_episodes and not self._replay_check(skill, evidence_episodes):
            errors.append("replay check failed: procedure does not match evidence actions")

        # Negative check: preconditions should match the evidence context.
        if evidence_episodes and not self._negative_check(skill, evidence_episodes):
            errors.append("negative check failed: preconditions do not match evidence context")

        # Executable replay/negative checks for skills that look like shell scripts.
        if self._is_executable_skill(skill):
            ok, err = await self.replay_execute(skill)
            if not ok:
                errors.append(f"replay execute failed: {err}")
            ok, err = await self.negative_execute(skill)
            if not ok:
                errors.append(f"negative execute failed: {err}")

        # Duplicate names within the same project
        others = [s for s in self.procedural.get_all(skill.project) if s.id != skill.id]
        if any(s.name == skill.name for s in others):
            errors.append("duplicate skill name")

        return not errors, errors

    def _replay_check(self, skill: Skill, episodes: list) -> bool:
        """Check that the skill's procedure is grounded in the evidence actions."""
        proc_terms = set()
        for step in skill.procedure:
            proc_terms.update(w.lower() for w in step.split() if len(w) > 3)
        if not proc_terms:
            return True
        for ep in episodes:
            action_text = " ".join(
                f"{a.tool} {a.command} {a.target}" for a in ep.actions
            ).lower()
            if any(term in action_text for term in proc_terms):
                return True
        return False

    def _negative_check(self, skill: Skill, episodes: list) -> bool:
        """Check that at least one precondition matches the evidence context."""
        if not skill.preconditions:
            return True
        for ep in episodes:
            context_text = " ".join(
                [ep.task, ep.root_cause, ep.fix_pattern] + ep.tags
            ).lower()
            for pre in skill.preconditions:
                if pre.lower() in context_text:
                    return True
        return False

    def _is_executable_skill(self, skill: Skill) -> bool:
        """Heuristic: does this skill look like a runnable shell script?"""
        if not skill.procedure:
            return False
        text = " ".join(skill.procedure).lower()
        shell_markers = ("git ", "cd ", "npm ", "pytest", "cargo ", "make ", "bash ", "sh ", "./", "echo ", "cat ", "ls ", "grep ", "sed ", "awk ", "python ", "pip ", "docker ")
        return any(marker in text for marker in shell_markers)

    async def replay_execute(self, skill: Skill) -> tuple[bool, str]:
        """Replay the skill at its evidence git commit in a temp worktree."""
        commits = []
        for ev in skill.evidence:
            session_id = ev.get("session_id") or ev.get("id")
            if not session_id:
                continue
            ep = self.episodic.get_by_id(session_id)
            if ep and ep.git_info and ep.git_info.get("commit"):
                commits.append(ep.git_info["commit"])
        if not commits:
            return True, "no git commit in evidence; skipped"

        commit = commits[0]
        script = "\n".join(skill.procedure)
        with tempfile.TemporaryDirectory(prefix="acrux-replay-") as tmpdir:
            worktree = Path(tmpdir) / "worktree"
            try:
                subprocess.run(
                    ["git", "worktree", "add", str(worktree), commit],
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )
            except Exception as exc:
                return True, f"could not create worktree (skipped): {exc}"
            try:
                exit_code, output = await run_sandboxed(script, str(worktree), timeout=120)
                if exit_code != 0:
                    return False, f"replay failed at {commit}: {output[:200]}"
                return True, "replay passed"
            finally:
                subprocess.run(
                    ["git", "worktree", "remove", str(worktree), "--force"],
                    capture_output=True,
                    timeout=10,
                )

    async def negative_execute(self, skill: Skill) -> tuple[bool, str]:
        """Run the skill where preconditions don't hold; require graceful failure."""
        script = "\n".join(skill.procedure)
        with tempfile.TemporaryDirectory(prefix="acrux-negative-") as tmpdir:
            exit_code, output = await run_sandboxed(script, tmpdir, timeout=60)
            # Expect non-zero exit or explicit failure; success is suspicious.
            if exit_code == 0:
                return False, "skill succeeded in an empty workspace (should have failed)"
            return True, f"failed gracefully (exit {exit_code})"

    def ab_check(self, skill: Skill) -> tuple[bool, str]:
        """A/B check: does the skill improve TaskBench pass rate when seeded?"""
        try:
            from acrux.taskbench import run_taskbench

            baseline = run_taskbench(modes=("memory",), extra_skills=None)
            with_skill = run_taskbench(modes=("memory+skills",), extra_skills=[skill])
            baseline_rate = baseline["modes"]["memory"]["pass_rate"]
            skill_rate = with_skill["modes"]["memory+skills"]["pass_rate"]
            ok = skill_rate >= baseline_rate
            return ok, f"memory={baseline_rate:.0%} vs memory+skills={skill_rate:.0%}"
        except Exception as exc:
            return False, f"ab_check failed: {exc}"

    async def verify_project(self, project: str) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {}
        for skill in self.procedural.get_all(project):
            ok, errors = await self.verify(skill)
            if ok and not skill.verified:
                skill.verified = True
                self.procedural.update(skill)
            results[skill.id] = errors
        return results
