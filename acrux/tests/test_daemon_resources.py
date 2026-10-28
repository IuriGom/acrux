import asyncio
import json

import httpx
import pytest

from acrux.config import AcruxConfig, ReflectionConfig
from acrux.daemon import AcruxDaemon
from acrux.memory.episodic import EpisodicStore
from acrux.models import Episode
from acrux.reflection.ollama import OllamaProvider


def _config(tmp_path):
    return AcruxConfig(
        data_dir=tmp_path,
        reflection=ReflectionConfig(provider="ollama", model="qwen3:8b"),
    )


def _seed_project(tmp_path, name, pending):
    project_dir = tmp_path / "projects" / name
    store = EpisodicStore(project_dir / "episodes.db")
    store.add(
        Episode(
            session_id=f"{name}-1",
            task="task",
            project=name,
            outcome="success",
            compacted=not pending,
        )
    )


def _patch_engine(monkeypatch, daemon, tmp_path, instances, reflect_impl=None):
    semantic_projects = []
    embedder_projects = []

    class FakeSemantic:
        def __init__(self, db_path, embedder=None):
            semantic_projects.append(db_path.parent.name)
            self.embedder = embedder

    class FakeProcedural:
        def __init__(self, db_path):
            pass

    class FakeEngine:
        def __init__(self, config, episodic, semantic, procedural):
            self.project = episodic.db_path.parent.name
            self.semantic = semantic
            self.closed = 0
            instances.append(self)

        async def reflect_project(self, project):
            if reflect_impl is not None:
                return await reflect_impl(project)
            return {"facts": 0, "skills": 0}

        async def close(self):
            self.closed += 1
            if self.semantic.embedder is not None:
                await self.semantic.embedder.close()

    class FakeEmbedder:
        def __init__(self):
            self.closed = 0

        async def close(self):
            self.closed += 1

    embedders = []

    def create_embedder():
        embedder_projects.append("created")
        embedder = FakeEmbedder()
        embedders.append(embedder)
        return embedder

    monkeypatch.setattr("acrux.daemon.SemanticStore", FakeSemantic)
    monkeypatch.setattr("acrux.daemon.ProceduralDBStore", FakeProcedural)
    monkeypatch.setattr("acrux.daemon.ReflectionEngine", FakeEngine)
    monkeypatch.setattr(daemon.config, "create_embedder", create_embedder)
    return semantic_projects, embedder_projects, embedders


@pytest.mark.asyncio
async def test_idle_projects_make_no_ollama_or_expensive_store_calls(tmp_path, monkeypatch):
    _seed_project(tmp_path, "idle", pending=False)
    _seed_project(tmp_path, "pending", pending=True)
    daemon = AcruxDaemon(_config(tmp_path))
    instances = []
    semantic_projects, embedder_calls, _ = _patch_engine(
        monkeypatch, daemon, tmp_path, instances
    )

    async def no_reverify(project):
        return None

    monkeypatch.setattr(daemon, "_run_reverify", no_reverify)
    await daemon._run_reflection()

    assert semantic_projects == ["pending"]
    assert len(embedder_calls) == 1
    assert [engine.project for engine in instances] == ["pending"]
    assert [engine.closed for engine in instances] == [1]


@pytest.mark.asyncio
async def test_scheduler_never_reverifies(tmp_path, monkeypatch):
    _seed_project(tmp_path, "pending", pending=True)
    daemon = AcruxDaemon(_config(tmp_path))
    instances = []
    _patch_engine(monkeypatch, daemon, tmp_path, instances)

    verifier_calls = []
    reverify_calls = []

    class ForbiddenVerifier:
        def __init__(self, *args):
            verifier_calls.append(args)

    async def forbidden_reverify(project):
        reverify_calls.append(project)

    monkeypatch.setattr("acrux.verify.SkillVerifier", ForbiddenVerifier)
    monkeypatch.setattr(daemon, "_run_reverify", forbidden_reverify)

    await daemon._run_reflection()
    assert len(instances) == 1
    assert verifier_calls == []
    assert reverify_calls == []


@pytest.mark.asyncio
async def test_overlapping_full_run_is_skipped_and_clients_close(tmp_path, monkeypatch):
    _seed_project(tmp_path, "pending", pending=True)
    daemon = AcruxDaemon(_config(tmp_path))
    instances = []
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked_reflection(project):
        started.set()
        await release.wait()
        return {"facts": 0, "skills": 0}

    _, _, embedders = _patch_engine(
        monkeypatch, daemon, tmp_path, instances, blocked_reflection
    )

    first = asyncio.create_task(daemon._run_reflection())
    await asyncio.wait_for(started.wait(), timeout=1)
    second = asyncio.create_task(daemon._run_reflection())
    await asyncio.wait_for(second, timeout=1)
    assert len(instances) == 1

    release.set()
    await asyncio.wait_for(first, timeout=1)
    assert instances[0].closed == 1
    assert [embedder.closed for embedder in embedders] == [1]


@pytest.mark.asyncio
async def test_ollama_reflection_uses_bounded_keep_alive():
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"response": "[]"})

    provider = OllamaProvider()
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        assert await provider._generate("prompt") == "[]"
    finally:
        await provider.close()

    assert captured["keep_alive"] == "30s"
    assert captured["think"] is False
    assert captured["options"]["num_ctx"] == 16384
    assert captured["options"]["num_predict"] == 1024
