"""Daemon that runs the acrux MCP server and scheduled reflection."""

from __future__ import annotations

import asyncio
import signal
from datetime import datetime
from typing import TYPE_CHECKING

from croniter import croniter

from acrux.claude_watcher import ClaudeSessionWatcher
from acrux.config import AcruxConfig
from acrux.kimi_watcher import KimiSessionWatcher
from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.reflection.engine import ReflectionEngine
from acrux.utils import get_logger, setup_logging

if TYPE_CHECKING:
    pass


class AcruxDaemon:
    def __init__(self, config: AcruxConfig):
        self.config = config
        self.stop_event = asyncio.Event()
        self.logger = get_logger()
        self.kimi_watcher = KimiSessionWatcher(config)
        self.claude_watcher = ClaudeSessionWatcher(config)

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._request_stop)

        self.logger.info("Starting acrux daemon (transport=%s)", self.config.mcp.transport)
        server_task = asyncio.create_task(self._run_server())
        scheduler_task = asyncio.create_task(self._run_scheduler())
        app_task = asyncio.create_task(self._run_app_server())
        self.kimi_watcher.start()
        self.claude_watcher.start()
        self.logger.info("Kimi and Claude session watchers started")

        try:
            await self.stop_event.wait()
        finally:
            self.kimi_watcher.stop()
            self.claude_watcher.stop()
            for task in (server_task, scheduler_task, app_task):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self.logger.info("Acrux daemon stopped.")

    def _request_stop(self) -> None:
        self.stop_event.set()

    async def _run_server(self) -> None:
        if self.config.mcp.transport == "http":
            from acrux.http_server import run_http_server

            await run_http_server(self.config)
        else:
            from acrux.mcp_server import AcruxMCPServer

            server = AcruxMCPServer(self.config)
            await server.run()

    async def _run_app_server(self) -> None:
        """Serve the FastAPI app in the same daemon process."""
        import uvicorn

        from acrux.app.main import app

        port = int(getattr(self.config, "app_port", 11438))
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)
        self.logger.info("Starting acrux app server on port %d", port)
        await server.serve()

    async def _run_scheduler(self) -> None:
        if self.config.reflection.provider == "none":
            self.logger.info("Reflection provider is 'none'; scheduler idle.")
            await self.stop_event.wait()
            return

        while not self.stop_event.is_set():
            next_run = self._next_run_time()
            wait_seconds = (next_run - datetime.utcnow()).total_seconds()
            # Wake periodically to check adaptive threshold (at least every 5 minutes).
            check_seconds = min(max(wait_seconds, 0), 300)
            if check_seconds > 0:
                self.logger.info("Next reflection scheduled at %s", next_run.isoformat())
                try:
                    await asyncio.wait_for(self.stop_event.wait(), timeout=check_seconds)
                except asyncio.TimeoutError:
                    pass
            if self.stop_event.is_set():
                break

            cron_due = datetime.utcnow() >= next_run
            threshold_triggered = self._check_adaptive_threshold()
            if cron_due or threshold_triggered:
                await self._run_reflection()

    def _check_adaptive_threshold(self) -> bool:
        threshold = getattr(self.config.reflection, "adaptive_threshold", 10)
        try:
            for project_dir in self.config.projects_dir.iterdir():
                if not project_dir.is_dir() or project_dir.name.startswith("_"):
                    continue
                store = EpisodicStore(project_dir / "episodes.db")
                if store.count_unreflected(project_dir.name) >= threshold:
                    self.logger.info("Adaptive threshold reached for project %s", project_dir.name)
                    return True
        except Exception as exc:
            self.logger.warning("Could not check adaptive threshold: %s", exc)
        return False

    def _next_run_time(self) -> datetime:
        try:
            itr = croniter(self.config.reflection.schedule, datetime.utcnow())
            return itr.get_next(datetime)
        except Exception as exc:
            self.logger.warning(
                "Invalid cron schedule '%s': %s. Falling back to daily at 02:00 UTC.",
                self.config.reflection.schedule,
                exc,
            )
            itr = croniter("0 2 * * *", datetime.utcnow())
            return itr.get_next(datetime)

    async def _run_reflection(self) -> None:
        self.logger.info("Running scheduled reflection")
        try:
            from acrux.verify import SkillVerifier

            for project_dir in self.config.projects_dir.iterdir():
                if not project_dir.is_dir() or project_dir.name.startswith("_"):
                    continue
                episodic = EpisodicStore(project_dir / "episodes.db")
                semantic = SemanticStore(
                    project_dir / "semantic.db", embedder=self.config.create_embedder()
                )
                procedural = ProceduralDBStore(project_dir / "skills.db")
                engine = ReflectionEngine(self.config, episodic, semantic, procedural)
                result = await engine.reflect_project(project_dir.name)
                self.logger.info(
                    "Reflected project %s: +%d facts, +%d skills",
                    project_dir.name,
                    result["facts"],
                    result["skills"],
                )
                verify_results = SkillVerifier(episodic, procedural).verify_project(project_dir.name)
                verified = sum(1 for errs in verify_results.values() if not errs)
                if verified:
                    self.logger.info(
                        "Verified %d skills for project %s", verified, project_dir.name
                    )
                await self._run_reverify(project_dir.name)
        except Exception as exc:
            self.logger.exception("Scheduled reflection failed: %s", exc)

    async def _run_reverify(self, project: str) -> None:
        if self.config.reflection.provider != "ollama":
            return
        self.logger.info("Running scheduled re-verification for %s", project)
        try:
            semantic = SemanticStore(
                self.config.projects_dir / project / "semantic.db",
                embedder=self.config.create_embedder(),
            )
            model = self.config.reflection.routing.get("reflection", self.config.reflection.model)
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Promote pending facts after verification
                pending = semantic.list_pending_facts(project, limit=20)
                for fact in pending:
                    verdict = await self._verify_fact(client, model, fact.content)
                    if verdict == "Yes":
                        semantic.promote_pending_fact(fact.id)
                        self.logger.info("Promoted pending fact %s", fact.id)
                    elif verdict == "No":
                        semantic.reject_pending_fact(fact.id)
                        self.logger.info("Rejected pending fact %s", fact.id)

                # Re-verify low-confidence live facts
                facts = semantic.get_facts_for_reverify(project, limit=10)
                for fact in facts:
                    if not fact.id:
                        continue
                    verdict = await self._verify_fact(client, model, fact.content)
                    if verdict:
                        semantic.record_verification(fact.id, verdict)
                        self.logger.info("Reverified fact %s: %s", fact.id, verdict)
        except Exception as exc:
            self.logger.exception("Scheduled re-verification failed for %s: %s", project, exc)

    async def _verify_fact(self, client, model: str, content: str) -> str | None:
        prompt = (
            "You are a fact-checking assistant. Evaluate whether the following statement "
            "is still true. Answer with exactly one word: Yes, No, or Uncertain.\n\n"
            f"Statement: {content}\n\nVerdict:"
        )
        try:
            r = await client.post(
                f"{self.config.reflection.host}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            return r.json().get("response", "Uncertain").strip().split()[0]
        except Exception as exc:
            self.logger.warning("Fact verification failed: %s", exc)
            return None
        except Exception as exc:
            self.logger.exception("Scheduled re-verification failed for %s: %s", project, exc)


async def run_daemon(config: AcruxConfig) -> None:
    setup_logging(config.log_dir)
    daemon = AcruxDaemon(config)
    await daemon.run()


def main() -> None:
    import asyncio
    import os

    config = AcruxConfig.load()
    if os.environ.get("BRAIN_MCP_TRANSPORT"):
        config.mcp.transport = os.environ["BRAIN_MCP_TRANSPORT"]  # type: ignore[assignment]
    if os.environ.get("BRAIN_MCP_PORT"):
        config.mcp.port = int(os.environ["BRAIN_MCP_PORT"])
    asyncio.run(run_daemon(config))


if __name__ == "__main__":
    main()
