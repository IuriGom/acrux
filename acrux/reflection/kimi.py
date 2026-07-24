"""Kimi reflection provider using MCP sampling."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.types import SamplingMessage, TextContent

from acrux.models import Episode, Fact, Skill
from acrux.reflection.base import ReflectionProvider

if TYPE_CHECKING:
    from acrux.mcp_server import AcruxMCPServer


class KimiProvider(ReflectionProvider):
    """Reflects by asking the connected MCP client (Kimi Code) via sampling.

    This only works when the acrux is running as an MCP server and a request
    context is active. Calling reflect from the CLI with this provider will
    raise a clear RuntimeError.
    """

    def __init__(self, mcp_server: "AcruxMCPServer | None" = None):
        self.mcp_server = mcp_server

    def _get_server(self) -> "AcruxMCPServer":
        if self.mcp_server is None:
            raise RuntimeError(
                "Kimi reflection can only run inside an active MCP request. "
                "Use 'acrux use-model qwen3:14b' for offline/CLI reflection, "
                "or trigger reflection through Kimi Code."
            )
        return self.mcp_server

    async def _generate(self, prompt: str, max_tokens: int = 1024) -> str:
        server = self._get_server()
        ctx = server.server.request_context
        session = ctx.session
        result = await session.create_message(
            messages=[SamplingMessage(role="user", content=TextContent(type="text", text=prompt))],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        content = result.content
        if isinstance(content, TextContent):
            return content.text
        return ""

    async def reflect_episodes(self, episodes: list[Episode]) -> list[Fact]:
        if not episodes:
            return []
        prompt = self.build_reflection_prompt(episodes)
        response = await self._generate(prompt)
        facts = []
        project = episodes[0].project
        for line in response.split("\n"):
            line = line.strip().lstrip("-").strip()
            if len(line) > 10:
                facts.append(
                    Fact(
                        project=project,
                        content=line,
                        source=episodes[0].session_id,
                        tags=episodes[0].tags,
                    )
                )
        return facts

    async def extract_skills(
        self, episodes: list[Episode], facts: list[Fact], retries: int = 2
    ) -> list[Skill]:
        if not episodes:
            return []
        project = episodes[0].project
        for _ in range(retries + 1):
            prompt = self.build_skill_prompt(episodes, facts)
            response = await self._generate(prompt)
            skill = self._parse_skill_json(response, project)
            if skill:
                return [skill]
        return []

    def _parse_skill_json(self, text: str, project: str) -> Skill | None:
        if "```" in text:
            blocks = text.split("```")
            for block in blocks:
                block = block.strip()
                if block.startswith("json"):
                    block = block[4:].strip()
                if block.startswith("{") and block.endswith("}"):
                    text = block
                    break
        import json

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
            return Skill(
                project=project,
                name=data.get("name", ""),
                preconditions=data.get("preconditions", []),
                procedure=data.get("procedure", []),
                evidence=[],
                verified=False,
            )
        except json.JSONDecodeError:
            return None
