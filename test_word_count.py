#!/usr/bin/env python3
"""Test the direct word-count write path end-to-end."""
import asyncio
import json
import pathlib
import sys
import time

import websockets

CHAT_ID = "test-wordcount"
WS_URL = f"ws://127.0.0.1:11438/ws/chat/{CHAT_ID}"
PATH = "/tmp/word_count_test.md"
PROMPT = (
    f"Write 1000 word .md explaining the benefits and flaws of giving an LLM a "
    f"long-term memory acrux. Save it to {PATH}. Be thorough and unbiased."
)


async def main():
    start = time.time()
    async with websockets.connect(WS_URL) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "start",
                    "message": PROMPT,
                    "model": "qwen3:14b",
                    "workspace": "",
                    "auto_accept": False,
                    "allowed_tools": [],
                    "use_memory": False,
                    "loop_mode": False,
                }
            )
        )
        chat_content = []
        final_type = None
        async for raw in ws:
            msg = json.loads(raw)
            t = msg.get("type")
            print(f"  [{t}] {msg.get('content', '')[:120]!r}")
            if t == "content":
                chat_content.append(msg.get("content", ""))
            if t in ("done", "error", "stopped"):
                final_type = t
                break

    elapsed = time.time() - start
    text = pathlib.Path(PATH).read_text(errors="ignore")
    wc = len(text.split())
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"File word count: {wc}")
    print(f"Chat content: {''.join(chat_content)!r}")
    if final_type == "done" and wc >= 900:
        print("PASS: direct word-count path wrote a ~1000-word file")
        return 0
    print(f"FAIL: final={final_type}, words={wc}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
