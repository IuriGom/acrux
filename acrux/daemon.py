"""Daemon that runs the acrux MCP server and scheduled reflection."""

from __future__ import annotations

import asyncio
import os
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
from acrux.utils import DAEMON_PID_FILE, PidFile, get_logger, setup_logging, utcnow

if TYPE_CHECKING:
    pass


class AcruxDaemon:
    def __init__(self, config: AcruxConfig):
        self.config = config
        self.stop_event = asyncio.Event()
        self.logger = get_logger()
        self.kimi_watcher = KimiSessionWatcher(config)
        self.claude_watcher = ClaudeSessionWatcher(config)
        self._reflection_running = False
        self._active_reflection_projects: set[str] = set()

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._request_stop)

        pid_file = PidFile(DAEMON_PID_FILE)
        pid_file.write(os.getpid())
        self.logger.info("Starting acrux daemon (transport=%s)", self.config.mcp.transport)
        self._warn_incomplete_batches()
        server_task = asyncio.create_task(self._run_server())
        scheduler_task = asyncio.create_task(self._run_scheduler())
        # NOTE: the daemon deliberately does NOT serve the app API (port 11438).
        # The Acrux app spawns and owns its own backend; two owners of the port
        # made them kill each other.
        self.kimi_watcher.start()
        self.claude_watcher.start()
        self.logger.info("Kimi and Claude session watchers started")

        try:
            await self.stop_event.wait()
        finally:
            self.kimi_watcher.stop()
            self.claude_watcher.stop()
            for task in (server_task, scheduler_task):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            pid_file.clear()
            self.logger.info("Acrux daemon stopped.")

    def _request_stop(self) -> None:
        self.stop_event.set()

    def _warn_incomplete_batches(self) -> None:
        from acrux.memory.journal import MutationJournal

        if not self.config.projects_dir.exists():
            return
        for project_dir in self.config.projects_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith("_"):
                continue
            for batch in MutationJournal(project_dir).incomplete():
                self.logger.warning(
                    "Incomplete mutation batch %s for %s (created %s, last sequence %d); "
                    "new mutations paused. Recover with: acrux undo %s --project %s",
                    batch.id,
                    batch.project,
                    batch.created_at,
                    batch.last_sequence,
                    batch.id,
                    batch.project,
                )

    async def _run_server(self) -> None:
        if self.config.mcp.transport == "http":
            from acrux.http_server import run_http_server

            await run_http_server(self.config)
        else:
            from acrux.mcp_server import AcruxMCPServer

            server = AcruxMCPServer(self.config)
            await server.run()

    async def _run_scheduler(self) -> None:
        if self.config.reflection.provider == "none":
            self.logger.info("Reflection provider is 'none'; scheduler idle.")
            await self.stop_event.wait()
            return

        while not self.stop_event.is_set():
            next_run = self._next_run_time()
            wait_seconds = (next_run - utcnow()).total_seconds()
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

            cron_due = utcnow() >= next_run
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
            itr = croniter(self.config.reflection.schedule, utcnow())
            return itr.get_next(datetime)
        except Exception as exc:
            self.logger.warning(
                "Invalid cron schedule '%s': %s. Falling back to daily at 02:00 UTC.",
                self.config.reflection.schedule,
                exc,
            )
            itr = croniter("0 2 * * *", utcnow())
            return itr.get_next(datetime)

    def _eligible_projects(self) -> list[str]:
        if not self.config.projects_dir.exists():
            return []
        eligible = []
        for project_dir in self.config.projects_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith("_"):
                continue
            episodic = EpisodicStore(project_dir / "episodes.db")
            if episodic.count_unreflected(project_dir.name) > 0:
                eligible.append(project_dir.name)
        return eligible

    async def _run_reflection(self) -> None:
        if self._reflection_running:
            self.logger.info("Scheduled reflection already running; skipping overlapping run")
            return
        self._reflection_running = True
        self.logger.info("Running scheduled reflection")
        try:
            for project in self._eligible_projects():
                if project in self._active_reflection_projects:
                    self.logger.info("Reflection already running for %s; skipping", project)
                    continue
                self._active_reflection_projects.add(project)
                project_dir = self.config.projects_dir / project
                try:
                    episodic = EpisodicStore(project_dir / "episodes.db")
                    semantic = SemanticStore(
                        project_dir / "semantic.db", embedder=self.config.create_embedder()
                    )
                    procedural = ProceduralDBStore(project_dir / "skills.db")
                    engine = ReflectionEngine(self.config, episodic, semantic, procedural)
                    try:
                        result = await engine.reflect_project(project)
                        self.logger.info(
                            "Reflected project %s: +%d facts, +%d skills",
                            project,
                            result["facts"],
                            result["skills"],
                        )
                    finally:
                        await engine.close()
                except Exception as exc:
                    self.logger.exception("Scheduled reflection failed for %s: %s", project, exc)
                finally:
                    self._active_reflection_projects.discard(project)
        finally:
            self._reflection_running = False

    async def _run_reverify(self, project: str) -> None:
        if self.config.reflection.provider != "ollama":
            return
        from acrux.verify import OllamaFactVerifier

        self.logger.info("Running explicit re-verification for %s", project)
        semantic = SemanticStore(
            self.config.projects_dir / project / "semantic.db", embedder=None
        )
        model = self.config.reflection.routing.get("reflection", self.config.reflection.model)
        verifier = OllamaFactVerifier(model, self.config.reflection.host)
        results = await verifier.reverify_project(semantic, project, limit=10)
        for result in results:
            if result["verdict"]:
                self.logger.info(
                    "Reverified fact %s: %s", result["fact_id"], result["verdict"]
                )


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
