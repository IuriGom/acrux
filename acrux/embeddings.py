"""Embedding generation and similarity helpers."""

from __future__ import annotations

import math

import httpx


class OllamaEmbedder:
    def __init__(
        self,
        model: str = "nomic-embed-text:latest",
        host: str = "http://localhost:11434",
        ram_target_mb: int = 1024,
        dim: int | None = None,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.client = httpx.AsyncClient(timeout=60.0)
        self.ram_target_mb = ram_target_mb
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        from acrux.utils import available_ram_mb, set_degraded

        threshold = max(self.ram_target_mb // 2, 300)
        avail = available_ram_mb()
        if avail < threshold:
            set_degraded(
                f"Low RAM: {avail} MB available (threshold {threshold} MB); skipping embedding"
            )
            raise RuntimeError(f"Low RAM ({avail} MB); embedding skipped")

        url = f"{self.host}/api/embeddings"
        payload = {"model": self.model, "prompt": text}
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        if "embedding" not in data:
            raise RuntimeError(f"Model {self.model} does not support embeddings")
        return data["embedding"]

    async def close(self) -> None:
        await self.client.aclose()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]
