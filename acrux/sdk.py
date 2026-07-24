"""Python SDK for the Acrux HTTP API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

from acrux.config import AcruxConfig


class AcruxClient:
    """Small client for talking to a local Acrux backend."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11438",
        token: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token = token or self._load_token()

    def _load_token(self) -> str:
        config_path = Path.home() / ".acrux" / "config.yaml"
        if not config_path.exists():
            return ""
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        acrux = data.get("acrux", {})
        return acrux.get("api_token", "")

    def _headers(self) -> dict[str, str]:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def status(self) -> dict[str, Any]:
        r = httpx.get(f"{self.base_url}/api/acrux/status", headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def remember_fact(
        self,
        project: str,
        content: str,
        source: str = "sdk",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "content": content,
            "source": source,
            "tags": tags or [],
        }
        r = httpx.post(
            f"{self.base_url}/api/memories/facts",
            params={"project": project},
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def recall(self, project: str, query: str, limit: int = 10) -> dict[str, Any]:
        params = {"project": project, "query": query, "limit": limit}
        r = httpx.get(
            f"{self.base_url}/api/search",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def get_context(self, project: str, query: str, limit: int = 8) -> str:
        params = {"project": project, "query": query, "limit": limit}
        r = httpx.get(
            f"{self.base_url}/api/acrux/context",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json().get("context", "")

    def get_skills(self, project: str, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        params = {"project": project, "query": query, "limit": limit}
        r = httpx.get(
            f"{self.base_url}/api/memories/skills",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json().get("skills", [])

    def record_test(
        self,
        project: str,
        test_name: str,
        passed: bool,
        file_path: str | None = None,
        output: str = "",
        duration_ms: int = 0,
        root_cause: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "test_name": test_name,
            "file_path": file_path,
            "passed": passed,
            "output": output,
            "duration_ms": duration_ms,
            "root_cause": root_cause,
        }
        r = httpx.post(
            f"{self.base_url}/api/projects/{project}/tests",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def record_dependency(
        self,
        project: str,
        source_ref: str,
        target_ref: str,
        source_type: str = "file",
        target_type: str = "file",
        dependency_type: str = "depends_on",
    ) -> dict[str, Any]:
        payload = {
            "dependencies": [
                {
                    "source_ref": source_ref,
                    "source_type": source_type,
                    "target_ref": target_ref,
                    "target_type": target_type,
                    "dependency_type": dependency_type,
                }
            ]
        }
        r = httpx.post(
            f"{self.base_url}/api/projects/{project}/dependencies",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def record_review(
        self,
        project: str,
        file_path: str,
        comment: str,
        line_range: str = "",
        reviewer: str = "assistant",
    ) -> dict[str, Any]:
        payload = {
            "file_path": file_path,
            "line_range": line_range,
            "comment": comment,
            "reviewer": reviewer,
        }
        r = httpx.post(
            f"{self.base_url}/api/projects/{project}/reviews",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def reflect(self, project: str = "default", batch_size: int = 10) -> dict[str, Any]:
        r = httpx.post(
            f"{self.base_url}/api/acrux/reflect",
            params={"project": project, "batch_size": batch_size},
            headers=self._headers(),
            timeout=self.timeout * 4,
        )
        r.raise_for_status()
        return r.json()

    def config(self) -> AcruxConfig:
        return AcruxConfig.load()
