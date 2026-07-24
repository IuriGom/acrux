#!/usr/bin/env python3
"""Test WebSocket stop functionality."""
import asyncio
import json
import sys
import websockets

CHAT_ID = "test-stop-chat"
WS_URL = f"ws://127.0.0.1:11438/ws/chat/{CHAT_ID}"

async def main():
    print(f"Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL) as ws:
        print("Connected. Sending start message...")
        await ws.send(json.dumps({
            "type": "start",
            "message": "Write a detailed 2000-word essay about the history of computing. Keep going.",
            "model": "qwen3:14b",
            "workspace": "",
            "auto_accept": False,
            "allowed_tools": ["read_file", "list_files"],
            "use_memory": True,
            "loop_mode": False,
        }))

        seen_types = set()
        content_chars = 0
        stop_sent = False
        stopped_received = False
        done_received = False

        try:
            async for raw in ws:
                msg = json.loads(raw)
                t = msg.get("type")
                seen_types.add(t)
                if t == "content":
                    content_chars += len(msg.get("content", ""))
                print(f"  [{t}] {msg.get('content', '')[:80]!r}")

                if content_chars > 200 and not stop_sent:
                    print(f"\n--> Sending stop after {content_chars} chars")
                    await ws.send(json.dumps({"type": "stop"}))
                    stop_sent = True

                if t == "stopped":
                    stopped_received = True
                    print("\n✅ Received 'stopped' message from backend")
                    break
                if t == "done":
                    done_received = True
                    print("\n⚠️ Received 'done' before stop (model finished too fast)")
                    break
                if t == "error":
                    print(f"\n❌ Error: {msg.get('message')}")
                    break
        except asyncio.TimeoutError:
            print("\n❌ Timeout waiting for messages")

        print(f"\nSummary: seen={seen_types}, stop_sent={stop_sent}, stopped={stopped_received}, done={done_received}")
        if stopped_received:
            print("PASS: backend stop protocol works")
            return 0
        else:
            print("FAIL: did not receive stopped message")
            return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
