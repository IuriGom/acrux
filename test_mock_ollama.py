#!/usr/bin/env python3
"""Mock Ollama server to test Acrux backend stop/timeout behavior."""
import asyncio
import json
import sys
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    stream = data.get("stream", False)
    model = data.get("model", "mock")

    async def event_generator():
        # Stream 100 chunks slowly (0.2s between each)
        for i in range(100):
            chunk = {
                "model": model,
                "created_at": "2026-07-14T00:00:00Z",
                "message": {"role": "assistant", "content": f"word{i} "},
                "done": False,
            }
            yield json.dumps(chunk) + "\n"
            await asyncio.sleep(0.2)
        # Final chunk
        yield json.dumps({"model": model, "message": {"role": "assistant", "content": ""}, "done": True}) + "\n"

    if stream:
        return StreamingResponse(event_generator(), media_type="application/x-ndjson")
    else:
        await asyncio.sleep(20)  # simulate slow non-streaming
        return {
            "model": model,
            "message": {"role": "assistant", "content": "non-streaming response"},
            "done": True,
        }

@app.get("/api/tags")
async def tags():
    return {"models": [{"name": "mock:latest", "size": 1000}]}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=11499)
