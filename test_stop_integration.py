#!/usr/bin/env python3
"""Integration test: Acrux backend + mock Ollama stop behavior."""
import asyncio
import httpx
import json
import subprocess
import sys
import time
import websockets
from pathlib import Path

ROOT = Path(__file__).parent

MOCK_OLLAMA_PORT = 11499
BRAIN_PORT = 11438
CHAT_ID = "test-stop-mock"

async def wait_for_server(url: str, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        await asyncio.sleep(0.2)
    return False

async def main():
    # Start mock Ollama
    mock_proc = subprocess.Popen(
        [sys.executable, str(ROOT / "test_mock_ollama.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Start Acrux backend
    acrux_env = {"OLLAMA_HOST": f"http://127.0.0.1:{MOCK_OLLAMA_PORT}"}
    acrux_env.update({k: v for k, v in __import__("os").environ.items()})
    acrux_proc = subprocess.Popen(
        [str(ROOT / ".venv" / "bin" / "uvicorn"), "acrux.app.main:app", "--host", "127.0.0.1", "--port", str(BRAIN_PORT), "--log-level", "warning"],
        cwd=str(ROOT),
        env=acrux_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        ok1 = await wait_for_server(f"http://127.0.0.1:{MOCK_OLLAMA_PORT}/api/tags")
        ok2 = await wait_for_server(f"http://127.0.0.1:{BRAIN_PORT}/api/acrux/status")
        if not (ok1 and ok2):
            print("Servers did not start")
            return 1

        print("Servers up. Connecting websocket...")
        async with websockets.connect(f"ws://127.0.0.1:{BRAIN_PORT}/ws/chat/{CHAT_ID}") as ws:
            await ws.send(json.dumps({
                "type": "start",
                "message": "Say a lot of words",
                "model": "mock:latest",
                "workspace": "",
                "auto_accept": False,
                "allowed_tools": ["read_file"],
                "use_memory": True,
                "loop_mode": False,
            }))

            seen_types = set()
            content_count = 0
            stop_sent = False
            stopped_received = False
            error_received = None

            try:
                async for raw in ws:
                    msg = json.loads(raw)
                    t = msg.get("type")
                    seen_types.add(t)
                    if t == "content":
                        content_count += 1
                    if content_count >= 5 and not stop_sent:
                        print(f"Sending stop after {content_count} content chunks")
                        await ws.send(json.dumps({"type": "stop"}))
                        stop_sent = True
                    if t == "stopped":
                        stopped_received = True
                        print("✅ Received stopped")
                        break
                    if t == "error":
                        error_received = msg.get("message")
                        print(f"❌ Error: {error_received}")
                        break
            except asyncio.TimeoutError:
                pass

            print(f"seen={seen_types}, stop_sent={stop_sent}, stopped={stopped_received}")
            if stopped_received:
                print("PASS")
                return 0
            else:
                print("FAIL")
                return 1
    finally:
        acrux_proc.terminate()
        mock_proc.terminate()
        try:
            acrux_proc.wait(timeout=5)
        except Exception:
            acrux_proc.kill()
        try:
            mock_proc.wait(timeout=5)
        except Exception:
            mock_proc.kill()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
