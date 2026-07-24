"""Sandboxed execution helpers."""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path


async def run_sandboxed(script: str, workspace: str, timeout: int = 120) -> tuple[int, str]:
    """Run a script inside a restricted sandbox.

    Uses macOS `sandbox-exec` when available. Denies network access and
    restricts writes to a temporary directory. Falls back to a timed shell
    execution when sandbox-exec is unavailable.
    """
    sandbox_exec = shutil.which("sandbox-exec")
    if sandbox_exec:
        with tempfile.TemporaryDirectory(prefix="acrux-skill-") as tmpdir:
            script_path = Path(tmpdir) / "run.sh"
            script_path.write_text(script)
            script_path.chmod(0o755)
            profile = (
                "(version 1)\n"
                "(deny default)\n"
                "(allow process*)\n"
                "(allow file-read*)\n"
                f'(allow file-write* (subpath "{tmpdir}"))\n'
                "(allow sysctl-read)\n"
                "(deny network*)\n"
            )
            proc = await asyncio.create_subprocess_exec(
                sandbox_exec,
                "-p",
                profile,
                "/bin/bash",
                str(script_path),
                cwd=workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return proc.returncode or 0, stdout.decode(errors="replace")[:50_000]
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return 124, f"Skill verification timed out after {timeout}s"

    # Linux: use Docker if available for a network-less, read-only sandbox.
    docker = shutil.which("docker")
    if docker:
        with tempfile.TemporaryDirectory(prefix="acrux-skill-") as tmpdir:
            script_path = Path(tmpdir) / "run.sh"
            script_path.write_text(script)
            script_path.chmod(0o755)
            cmd = [
                docker,
                "run",
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "-v",
                f"{tmpdir}:/work:ro",
                "-w",
                "/work",
                "bash:5",
                "bash",
                "run.sh",
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return proc.returncode or 0, stdout.decode(errors="replace")[:50_000]
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return 124, f"Skill verification timed out after {timeout}s"

    proc = await asyncio.create_subprocess_shell(
        script,
        cwd=workspace,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode(errors="replace")[:50_000]
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, f"Skill verification timed out after {timeout}s"
