import json

import httpx
import pytest

from acrux.memory.semantic import SemanticStore
from acrux.models import Fact
from acrux.verify import OllamaFactVerifier


@pytest.mark.asyncio
async def test_verification_bounds_verdicts_and_cleanup():
    requests = []
    responses = [
        httpx.Response(200, json={"response": "yes"}),
        httpx.Response(200, json={"response": "No"}),
        httpx.Response(200, json={"response": "UNCERTAIN"}),
        httpx.Response(200, json={"response": ""}),
        httpx.Response(200, json={"response": "Yes because it works"}),
        httpx.Response(200, json={"response": "maybe"}),
        httpx.Response(500, json={"error": "failed"}),
    ]

    def handler(request):
        requests.append(request)
        if len(requests) == 8:
            raise httpx.ReadTimeout("timed out", request=request)
        return responses[len(requests) - 1]

    verifier = OllamaFactVerifier(
        model="qwen3:8b",
        host="http://localhost:11434",
        transport=httpx.MockTransport(handler),
    )
    assert verifier.client.timeout.connect == 30.0

    verdicts = [await verifier.verify_fact("A stable fact") for _ in range(8)]
    await verifier.close()

    assert verdicts == ["Yes", "No", "Uncertain", None, None, None, None, None]
    assert verifier.client.is_closed
    payload = json.loads(requests[0].content)
    assert payload["model"] == "qwen3:8b"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["keep_alive"] == "30s"
    assert payload["options"] == {"num_ctx": 4096, "num_predict": 8}


@pytest.mark.asyncio
async def test_reverify_project_does_not_mutate_on_malformed_verdict(tmp_path):
    semantic = SemanticStore(tmp_path / "semantic.db", embedder=None)
    first = Fact(project="test", content="First fact remains stable")
    second = Fact(project="test", content="Second fact remains stable")
    await semantic.add(first)
    await semantic.add(second)
    responses = iter(["not-a-verdict", "Yes"])

    def handler(request):
        return httpx.Response(200, json={"response": next(responses)})

    verifier = OllamaFactVerifier(
        model="qwen3:8b",
        host="http://localhost:11434",
        transport=httpx.MockTransport(handler),
    )
    results = await verifier.reverify_project(semantic, "test", limit=2)

    assert results[0]["verdict"] is None
    assert results[1]["verdict"] == "Yes"
    assert semantic.get_by_id(first.id).verified_count == 0
    assert semantic.get_by_id(second.id).verified_count == 1
    assert verifier.client.is_closed
