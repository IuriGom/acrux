"""MCP server for acrux."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from acrux.config import AcruxConfig
from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Action, Episode, Fact
from acrux.utils import git_context, prune_if_needed


class AcruxMCPServer:
    def __init__(self, config: AcruxConfig):
        self.config = config
        self.server = Server("acrux")
        self._setup_tools()

    def _setup_tools(self) -> None:
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="acrux_remember_session",
                    description="Store a completed coding session trace.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "task": {"type": "string"},
                            "project": {"type": "string"},
                            "context": {"type": "object"},
                            "actions": {"type": "array"},
                            "outcome": {"type": "string"},
                            "root_cause": {"type": "string"},
                            "fix_pattern": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "source": {
                                "type": "string",
                                "description": "Origin of the session, e.g. 'kimi' or 'user'",
                            },
                            "corrected": {"type": "boolean"},
                        },
                        "required": ["session_id", "task", "project"],
                    },
                ),
                Tool(
                    name="acrux_recall",
                    description="Recall relevant memories for a task.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "default": 10},
                        },
                        "required": ["project", "query"],
                    },
                ),
                Tool(
                    name="acrux_context",
                    description="Get a ready-to-inject memory context block for a task.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "default": 8},
                        },
                        "required": ["project", "query"],
                    },
                ),
                Tool(
                    name="acrux_remember_fact",
                    description="Store a semantic fact about a project.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "content": {"type": "string"},
                            "source": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["project", "content"],
                    },
                ),
                Tool(
                    name="acrux_get_skills",
                    description="Get procedural skills relevant to a task.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "default": 5},
                        },
                        "required": ["project", "query"],
                    },
                ),
                Tool(
                    name="acrux_user_correction",
                    description="Record a high-priority user correction.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "task": {"type": "string"},
                            "correction": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["project", "task", "correction"],
                    },
                ),
                Tool(
                    name="acrux_reflect",
                    description="Run reflection now to extract facts and skills from recent episodes.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "batch_size": {"type": "integer", "default": 10},
                        },
                    },
                ),
                Tool(
                    name="acrux_record_test",
                    description="Record a test result for a project.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "test_name": {"type": "string"},
                            "file_path": {"type": "string"},
                            "passed": {"type": "boolean"},
                            "output": {"type": "string"},
                            "duration_ms": {"type": "integer"},
                            "root_cause": {"type": "string"},
                        },
                        "required": ["project", "test_name", "passed"],
                    },
                ),
                Tool(
                    name="acrux_record_dependency",
                    description="Record a dependency between project artifacts.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "source_ref": {"type": "string"},
                            "source_type": {"type": "string"},
                            "target_ref": {"type": "string"},
                            "target_type": {"type": "string"},
                            "dependency_type": {"type": "string"},
                        },
                        "required": ["project", "source_ref", "target_ref"],
                    },
                ),
                Tool(
                    name="acrux_record_review",
                    description="Record a code review comment.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "file_path": {"type": "string"},
                            "line_range": {"type": "string"},
                            "comment": {"type": "string"},
                            "reviewer": {"type": "string"},
                        },
                        "required": ["project", "file_path", "comment"],
                    },
                ),
                Tool(
                    name="acrux_record_outcome",
                    description="Record whether injected memories helped a task outcome.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string"},
                            "memory_ids": {"type": "array", "items": {"type": "string"}},
                            "success": {"type": "boolean"},
                        },
                        "required": ["project", "memory_ids", "success"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            return await self._handle_tool(name, arguments)

    async def _handle_tool(self, name: str, arguments: dict) -> list[TextContent]:
        project = arguments.get("project", "default")
        project_dir = self.config.projects_dir / project
        project_dir.mkdir(parents=True, exist_ok=True)

        git_info = git_context(Path.cwd())

        def attach_git(obj: Fact | Episode) -> None:
            if not obj.git_info:
                obj.git_info = git_info

        # Enforce storage budget before adding new data
        if name in ("acrux_remember_session", "acrux_remember_fact", "acrux_user_correction"):
            limit = self.config.storage_limit_bytes
            if limit > 0:
                removed = prune_if_needed(
                    self.config.data_dir, limit, self.config.retention.episodes_days
                )
                if removed:
                    logger = logging.getLogger("acrux")
                    logger.info("Storage budget enforcement removed %d old records", removed)

        episodic = EpisodicStore(project_dir / "episodes.db")
        semantic = SemanticStore(
            project_dir / "semantic.db", embedder=self.config.create_embedder()
        )
        procedural = ProceduralDBStore(project_dir / "skills.db")

        if name == "acrux_remember_session":
            source = arguments.get("source", "kimi").strip() or "kimi"
            episode = Episode(
                session_id=arguments.get("session_id", ""),
                task=arguments.get("task", ""),
                project=project,
                context=arguments.get("context", {}),
                actions=[Action.from_dict(a) for a in arguments.get("actions", [])],
                outcome=arguments.get("outcome", ""),
                root_cause=arguments.get("root_cause", ""),
                fix_pattern=arguments.get("fix_pattern", ""),
                tags=arguments.get("tags", []),
                corrected=arguments.get("corrected", False),
                source=source,
            )
            attach_git(episode)
            episodic.add(episode)
            return [TextContent(type="text", text=f"Stored episode {episode.session_id}")]

        if name == "acrux_recall":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 10)
            k = max(1, limit // 2)
            episodes = episodic.search(project, query, k)
            facts = await semantic.search(project, query, k)
            skills = procedural.search(project, query, k)
            result = {
                "episodes": [e.to_dict() for e in episodes],
                "facts": [f.to_dict() for f in facts],
                "skills": [s.to_dict() for s in skills],
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "acrux_context":
            from acrux.retrieval import recall_context

            query = arguments.get("query", "")
            limit = arguments.get("limit", 8)
            stores = SimpleNamespace(semantic=semantic, episodic=episodic, procedural=procedural)
            context = await recall_context(
                stores,
                lambda p: ProceduralDBStore(self.config.projects_dir / p / "skills.db")
                if p != "global"
                else procedural,
                project,
                query,
                limit,
            )
            return [TextContent(type="text", text=context or "No relevant memories.")]

        if name == "acrux_remember_fact":
            fact = Fact(
                project=project,
                content=arguments.get("content", ""),
                source=arguments.get("source", ""),
                tags=arguments.get("tags", []),
            )
            attach_git(fact)
            await semantic.add(fact)
            return [TextContent(type="text", text="Fact stored.")]

        if name == "acrux_get_skills":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 5)
            skills = procedural.search(project, query, limit)
            return [
                TextContent(type="text", text=json.dumps([s.to_dict() for s in skills], indent=2))
            ]

        if name == "acrux_user_correction":
            episode = Episode(
                session_id=f"correction-{arguments.get('task', '')}",
                task=arguments.get("task", ""),
                project=project,
                outcome="user_correction",
                root_cause=arguments.get("correction", ""),
                tags=arguments.get("tags", []),
                corrected=True,
                source="user_correction",
            )
            attach_git(episode)
            episodic.add(episode)
            fact = Fact(
                project=project,
                content=arguments.get("correction", ""),
                source="user_correction",
                tags=arguments.get("tags", []),
            )
            attach_git(fact)
            await semantic.add(fact)
            return [TextContent(type="text", text="Correction recorded.")]

        if name == "acrux_reflect":
            from acrux.reflection.engine import ReflectionEngine

            batch_size = arguments.get("batch_size", 10)
            engine = ReflectionEngine(
                self.config,
                episodic,
                semantic,
                procedural,
                mcp_server=self,
            )
            if project:
                result = await engine.reflect_project(project, batch_size)
                return [TextContent(type="text", text=json.dumps(result))]
            results = await engine.reflect_all(batch_size)
            return [TextContent(type="text", text=json.dumps(results, indent=2))]

        if name == "acrux_record_test":
            test_id = semantic.add_test_result(
                project,
                {
                    "test_name": arguments.get("test_name", ""),
                    "file_path": arguments.get("file_path"),
                    "passed": bool(arguments.get("passed", False)),
                    "output": arguments.get("output", ""),
                    "duration_ms": int(arguments.get("duration_ms", 0)),
                    "root_cause": arguments.get("root_cause"),
                },
            )
            return [TextContent(type="text", text=f"Recorded test {test_id}")]

        if name == "acrux_record_dependency":
            count = semantic.add_dependencies(
                project,
                [
                    {
                        "source_ref": arguments.get("source_ref", ""),
                        "source_type": arguments.get("source_type", "file"),
                        "target_ref": arguments.get("target_ref", ""),
                        "target_type": arguments.get("target_type", "file"),
                        "dependency_type": arguments.get("dependency_type", "depends_on"),
                    }
                ],
            )
            return [TextContent(type="text", text=f"Recorded {count} dependency")]

        if name == "acrux_record_review":
            review_id = semantic.add_review(
                project,
                {
                    "file_path": arguments.get("file_path", ""),
                    "line_range": arguments.get("line_range", ""),
                    "comment": arguments.get("comment", ""),
                    "reviewer": arguments.get("reviewer", "assistant"),
                },
            )
            return [TextContent(type="text", text=f"Recorded review {review_id}")]

        if name == "acrux_record_outcome":
            memory_ids = arguments.get("memory_ids", [])
            success = bool(arguments.get("success", True))
            updated = 0
            for mid in memory_ids:
                try:
                    if mid.startswith("fact:"):
                        semantic.record_outcome(int(mid.split(":", 1)[1]), success)
                        updated += 1
                    elif mid.startswith("skill:"):
                        procedural.update_success(mid.split(":", 1)[1], success)
                        updated += 1
                except Exception:
                    pass
            return [TextContent(type="text", text=f"Recorded outcome for {updated} memories")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    import asyncio
    import os

    config = AcruxConfig.load()
    if os.environ.get("BRAIN_MCP_TRANSPORT"):
        config.mcp.transport = os.environ["BRAIN_MCP_TRANSPORT"]  # type: ignore[assignment]
    if os.environ.get("BRAIN_MCP_PORT"):
        config.mcp.port = int(os.environ["BRAIN_MCP_PORT"])

    if config.mcp.transport == "http":
        from acrux.http_server import run_http_server

        asyncio.run(run_http_server(config))
    else:
        server = AcruxMCPServer(config)
        asyncio.run(server.run())


if __name__ == "__main__":
    main()
