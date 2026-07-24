#!/usr/bin/env python3
import asyncio, json, sys, websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:11438/ws/chat/test-web") as ws:
        await ws.send(json.dumps({
            "type": "start",
            "message": "What is the current latest stable version of Python? Search the web and tell me the version and the source URL.",
            "model": "qwen3:14b",
            "workspace": "",
            "auto_accept": True,
            "allowed_tools": ["web_search", "web_fetch"],
            "use_memory": False,
            "loop_mode": False,
        }))
        async for raw in ws:
            msg = json.loads(raw)
            t = msg.get("type")
            print(f"[{t}] {msg.get('content', '')[:200]!r} {msg.get('name', '')} {msg.get('arguments', '')}")
            if t in ("done", "error"):
                break

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
