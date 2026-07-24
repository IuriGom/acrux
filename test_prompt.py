#!/usr/bin/env python3
import asyncio, json, sys, websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:11438/ws/chat/test-prompt") as ws:
        await ws.send(json.dumps({
            "type": "start",
            "message": "Hi. Who are you and what can you do in one sentence?",
            "model": "qwen3:14b",
            "workspace": "",
            "auto_accept": False,
            "allowed_tools": [],
            "use_memory": False,
            "loop_mode": False,
        }))
        async for raw in ws:
            msg = json.loads(raw)
            t = msg.get("type")
            print(f"[{t}] {msg.get('content', '')[:200]!r}")
            if t in ("done", "error"):
                break

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
