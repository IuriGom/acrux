#!/usr/bin/env python3
import asyncio, json, os, sys, websockets
from pathlib import Path

import yaml

def _load_token() -> str:
    cfg = Path.home() / ".acrux" / "config.yaml"
    if cfg.exists():
        return (yaml.safe_load(cfg.read_text()) or {}).get("brain", {}).get("api_token", "")
    return ""

TOKEN = os.environ.get("ACRUX_TOKEN") or _load_token()

async def main():
    url = f"ws://127.0.0.1:11438/ws/chat/test-memory?token={TOKEN}"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            "type": "start",
            "message": "What is my favorite color?",
            "model": "qwen3:14b",
            "workspace": "/tmp/acrux-test",
            "auto_accept": True,
            "allowed_tools": [],
            "use_memory": True,
            "loop_mode": False,
        }))
        async for raw in ws:
            msg = json.loads(raw)
            t = msg.get("type")
            print(f"[{t}] {msg.get('content', '')[:200]!r} {msg.get('message', '')}")
            if t in ("done", "error"):
                break

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
