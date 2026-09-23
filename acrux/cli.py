"""acrux CLI — local memory and learning system for coding agents."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click
import yaml

from acrux.config import AcruxConfig, Profile
from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.mcp_server import AcruxMCPServer
from acrux.models import Action, Episode, Skill
from acrux.reflection.engine import ReflectionEngine
from acrux.utils import (
    DAEMON_PID_FILE,
    PidFile,
    format_bytes,
    get_logger,
    get_storage_info,
    git_context,
    list_ollama_models,
    setup_logging,
    tail_log,
    utcnow,
    validate_acrux_data,
)


@click.group()
@click.option("--config-dir", type=click.Path(), help="Override acrux config directory.")
@click.pass_context
def cli(ctx: click.Context, config_dir: str | None) -> None:
    """acrux — local memory and learning system for coding agents."""
    if config_dir:
        os.environ["BRAIN_CONFIG_DIR"] = config_dir
    ctx.ensure_object(dict)
    ctx.obj["config"] = AcruxConfig.load()


@cli.command()
@click.option(
    "--profile",
    type=click.Choice(["minimal", "light", "standard", "workstation"]),
    default="standard",
    help="Resource profile for this machine.",
)
def init(profile: Profile) -> None:
    """Initialize acrux in ~/.acrux."""
    cfg = AcruxConfig.init(profile=profile)
    click.echo(f"Initialized acrux with profile: {cfg.profile}")
    click.echo(f"Config: {cfg.config_path}")
    click.echo(f"Data dir: {cfg.data_dir}")


@cli.command()
@click.argument("key", required=False)
@click.pass_context
def config(ctx: click.Context, key: str | None) -> None:
    """Show or read acrux configuration."""
    cfg = ctx.obj["config"]
    data = cfg.to_dict()
    if key is None:
        click.echo(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))
        return

    # Support nested keys like reflection.model
    parts = key.split(".")
    value: Any = data
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            click.echo(f"Key not found: {key}", err=True)
            sys.exit(1)
    click.echo(value)


@cli.command()
@click.option("--background", is_flag=True, help="Run acrux server in the background.")
@click.option(
    "--mcp",
    "mcp_transport",
    type=click.Choice(["stdio", "http"]),
    default=None,
    help="MCP transport override.",
)
@click.option("--port", type=int, default=None, help="HTTP port override.")
@click.pass_context
def start(
    ctx: click.Context, background: bool, mcp_transport: str | None, port: int | None
) -> None:
    """Start the acrux MCP server."""
    cfg = ctx.obj["config"]
    transport = mcp_transport or cfg.mcp.transport
    port = port or cfg.mcp.port

    if background:
        if transport == "stdio":
            click.echo("Cannot run stdio MCP transport in background. Use --mcp http.", err=True)
            sys.exit(1)
        pid_file = PidFile(DAEMON_PID_FILE)
        if pid_file.is_running():
            click.echo(f"acrux already running (pid {pid_file.read()}).")
            return
        setup_logging(cfg.log_dir)
        env = os.environ.copy()
        env["BRAIN_MCP_TRANSPORT"] = transport
        env["BRAIN_MCP_PORT"] = str(port)
        proc = subprocess.Popen(
            [sys.executable, "-m", "acrux.mcp_server"],
            stdout=open(cfg.log_dir / "acrux.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
        pid_file.write(proc.pid)
        click.echo(f"acrux started in background (pid {proc.pid}, http://localhost:{port}).")
        return

    if transport == "http":
        cfg.mcp.transport = transport
        cfg.mcp.port = port
        setup_logging(cfg.log_dir)
        logger = get_logger()
        logger.info("Starting acrux HTTP MCP server on port %d", cfg.mcp.port)
        from acrux.http_server import run_http_server

        asyncio.run(run_http_server(cfg))
        return

    # Foreground stdio mode: used by Kimi Code as MCP subprocess.
    setup_logging(cfg.log_dir)
    logger = get_logger()
    logger.info("Starting acrux MCP server (transport=%s)", transport)
    server = AcruxMCPServer(cfg)
    asyncio.run(server.run())


@cli.command()
@click.option("--background", is_flag=True, help="Run daemon in the background.")
@click.option(
    "--mcp",
    "mcp_transport",
    type=click.Choice(["stdio", "http"]),
    default=None,
    help="MCP transport override.",
)
@click.option("--port", type=int, default=None, help="HTTP port override.")
@click.pass_context
def daemon(
    ctx: click.Context, background: bool, mcp_transport: str | None, port: int | None
) -> None:
    """Run acrux as a long-running daemon with MCP server + scheduled reflection."""
    cfg = ctx.obj["config"]
    transport = mcp_transport or os.environ.get("BRAIN_MCP_TRANSPORT") or cfg.mcp.transport
    port = port or int(os.environ.get("BRAIN_MCP_PORT") or 0) or cfg.mcp.port

    if background:
        pid_file = PidFile(DAEMON_PID_FILE)
        if pid_file.is_running():
            click.echo(f"acrux already running (pid {pid_file.read()}).")
            return
        setup_logging(cfg.log_dir)
        env = os.environ.copy()
        env["BRAIN_MCP_TRANSPORT"] = transport
        env["BRAIN_MCP_PORT"] = str(port)
        proc = subprocess.Popen(
            [sys.executable, "-m", "acrux.daemon"],
            stdout=open(cfg.log_dir / "acrux.log", "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
        pid_file.write(proc.pid)
        click.echo(f"acrux daemon started in background (pid {proc.pid}).")
        return

    from acrux.daemon import run_daemon

    cfg.mcp.transport = transport  # type: ignore[assignment]
    cfg.mcp.port = port
    asyncio.run(run_daemon(cfg))


@cli.command()
def stop() -> None:
    """Stop a background acrux server."""
    pid_file = PidFile(DAEMON_PID_FILE)
    if not pid_file.is_running():
        click.echo("acrux is not running.")
        return
    pid = pid_file.read()
    if pid_file.stop():
        click.echo(f"Stopped acrux (pid {pid}).")
    else:
        click.echo("acrux was not running.")


@cli.command()
@click.option("--storage", is_flag=True, help="Show storage usage.")
@click.pass_context
def status(ctx: click.Context, storage: bool) -> None:
    """Show acrux status."""
    cfg = ctx.obj["config"]
    pid_file = PidFile(DAEMON_PID_FILE)
    click.echo(f"Profile: {cfg.profile}")
    click.echo(f"Data dir: {cfg.data_dir}")
    click.echo(f"Reflection provider: {cfg.reflection.provider}")
    click.echo(f"Reflection model: {cfg.reflection.model}")
    click.echo(f"MCP transport: {cfg.mcp.transport}")
    click.echo(f"Running: {pid_file.is_running()}")

    projects_dir = cfg.projects_dir
    project_count = (
        sum(1 for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else 0
    )
    click.echo(f"Projects: {project_count}")

    if storage:
        info = get_storage_info(cfg.data_dir)
        click.echo(f"Acrux data: {format_bytes(info.acrux_bytes)} ({info.acrux_gb:.2f} GB)")
        click.echo(f"Disk total: {format_bytes(info.total_bytes)} ({info.total_gb:.2f} GB)")
        click.echo(f"Disk used:  {format_bytes(info.used_bytes)} ({info.used_gb:.2f} GB)")
        click.echo(f"Disk free:  {format_bytes(info.free_bytes)} ({info.free_gb:.2f} GB)")


@cli.command()
@click.argument("model")
@click.pass_context
def use_model(ctx: click.Context, model: str) -> None:
    """Switch reflection model or provider.

    Examples:
        acrux use-model qwen3:14b
        acrux use-model kimi
        acrux use-model none
    """
    cfg = ctx.obj["config"]
    model_lower = model.lower()
    if model_lower in ("kimi", "none"):
        cfg.reflection.provider = model_lower  # type: ignore[assignment]
        cfg.reflection.model = model_lower
    else:
        cfg.reflection.provider = "ollama"
        cfg.reflection.model = model
    cfg.save()
    click.echo(f"Reflection provider set to {cfg.reflection.provider} ({cfg.reflection.model}).")


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["ollama"]),
    default="ollama",
    help="Provider to list models from.",
)
@click.pass_context
def models(ctx: click.Context, provider: str) -> None:
    """List available reflection models."""
    cfg = ctx.obj["config"]
    if provider == "ollama":
        try:
            ollama_models = list_ollama_models(cfg.reflection.host)
        except RuntimeError as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)
        if not ollama_models:
            click.echo("No Ollama models found.")
            return
        for m in ollama_models:
            name = m.get("name") or m.get("model", "unknown")
            size = m.get("size", 0)
            click.echo(f"{name}\t{format_bytes(size)}")
    else:
        click.echo(f"Listing models for provider '{provider}' is not supported yet.")


@cli.command()
@click.option("--project", default=None, help="Project to reflect on.")
@click.option("--batch-size", default=10, help="Episodes per reflection batch.")
@click.pass_context
def reflect(ctx: click.Context, project: str | None, batch_size: int) -> None:
    """Run reflection now to turn episodes into facts and skills."""
    cfg = ctx.obj["config"]
    if cfg.reflection.provider == "none":
        click.echo("Reflection provider is 'none'. Set a model with 'acrux use-model' first.")
        sys.exit(1)

    async def _reflect_project(proj: str) -> dict[str, int]:
        engine = ReflectionEngine(
            cfg,
            EpisodicStore(cfg.projects_dir / proj / "episodes.db"),
            SemanticStore(cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()),
            ProceduralDBStore(cfg.projects_dir / proj / "skills.db"),
        )
        return await engine.reflect_project(proj, batch_size)

    if project:
        results = {project: asyncio.run(_reflect_project(project))}
    else:
        results = {}
        for proj_dir in cfg.projects_dir.iterdir():
            if proj_dir.is_dir() and not proj_dir.name.startswith("_"):
                proj = proj_dir.name
                results[proj] = asyncio.run(_reflect_project(proj))
    for proj, counts in results.items():
        click.echo(f"{proj}: +{counts['facts']} facts, +{counts['skills']} skills")


@cli.command()
@click.option("--older-than", default="30d", help="Prune episodes older than this (e.g. 14d, 90d).")
@click.pass_context
def prune(ctx: click.Context, older_than: str) -> None:
    """Prune old episodes and facts."""
    cfg = ctx.obj["config"]
    days = _parse_duration(older_than)
    if days is None:
        click.echo(f"Invalid duration: {older_than}", err=True)
        sys.exit(1)

    total_episodes = 0
    total_facts = 0
    projects_dir = cfg.projects_dir
    if not projects_dir.exists():
        click.echo("No projects to prune.")
        return

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        episodic = EpisodicStore(project_dir / "episodes.db")
        semantic = SemanticStore(project_dir / "semantic.db", embedder=cfg.create_embedder())
        total_episodes += episodic.prune_old(days)
        total_facts += semantic.prune_old(days)

    click.echo(f"Pruned {total_episodes} episodes and {total_facts} facts older than {days} days.")


def _parse_duration(value: str) -> int | None:
    value = value.strip().lower()
    if value.endswith("d"):
        try:
            return int(value[:-1])
        except ValueError:
            return None
    try:
        return int(value)
    except ValueError:
        return None


@cli.command()
@click.option("--output", "-o", required=True, help="Output YAML file.")
@click.option("--project", default=None, help="Export skills from one project only.")
@click.pass_context
def export_skills(ctx: click.Context, output: str, project: str | None) -> None:
    """Export verified/verified skills to a YAML file."""
    cfg = ctx.obj["config"]
    skills: list[dict[str, Any]] = []

    if project:
        store = ProceduralDBStore(cfg.projects_dir / project / "skills.db")
        skills = store.export_skills()
    else:
        for project_dir in cfg.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            store = ProceduralDBStore(project_dir / "skills.db")
            skills.extend(store.export_skills())
        global_store = ProceduralDBStore(cfg.global_dir / "skills.db")
        skills.extend(global_store.export_skills())

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        yaml.safe_dump(skills, f, default_flow_style=False, sort_keys=False)
    click.echo(f"Exported {len(skills)} skills to {out_path}.")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--project", default=None, help="Import skills into a specific project.")
@click.pass_context
def import_skills(ctx: click.Context, path: str, project: str | None) -> None:
    """Import skills from a YAML file."""
    cfg = ctx.obj["config"]
    with open(path) as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        click.echo("Skills file must contain a YAML list.", err=True)
        sys.exit(1)

    target = cfg.projects_dir / (project or "global") / "skills.db"
    store = ProceduralDBStore(target)
    added = store.import_skills(data)
    click.echo(f"Imported {added} new skills into {target.parent.name}.")


@cli.command()
@click.option("--yes", is_flag=True, help="Skip confirmation.")
@click.pass_context
def reset(ctx: click.Context, yes: bool) -> None:
    """Reset all acrux data (destructive)."""
    cfg = ctx.obj["config"]
    if not yes:
        click.confirm(f"Delete everything in {cfg.data_dir}?", abort=True)
    import shutil

    shutil.rmtree(cfg.data_dir, ignore_errors=True)
    cfg.save()
    click.echo("Acrux data reset. Configuration preserved.")


@cli.command()
@click.option("--lines", default=50, help="Number of log lines to show.")
@click.pass_context
def logs(ctx: click.Context, lines: int) -> None:
    """Show recent acrux logs."""
    cfg = ctx.obj["config"]
    log_path = cfg.log_dir / "acrux.log"
    click.echo(tail_log(log_path, lines))


@cli.command()
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Validate acrux data integrity."""
    cfg = ctx.obj["config"]
    result = validate_acrux_data(cfg.data_dir)
    click.echo(f"Projects checked: {result['checked']}")
    if result["errors"]:
        click.echo("Errors:")
        for err in result["errors"]:
            click.echo(f"  - {err}")
    if result["warnings"]:
        click.echo("Warnings:")
        for warn in result["warnings"]:
            click.echo(f"  - {warn}")
    if result["ok"] and not result["warnings"]:
        click.echo("All checks passed.")
    elif result["ok"]:
        click.echo("Data is usable but has warnings.")
    else:
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--project", required=True, help="Project to ingest into.")
@click.option("--max-files", default=1000, help="Maximum files to ingest.")
@click.pass_context
def ingest_code(ctx: click.Context, path: str, project: str, max_files: int) -> None:
    """Ingest code structure from a file or directory into semantic memory."""
    from acrux.ingest import ingest_directory, ingest_file

    cfg = ctx.obj["config"]
    semantic = SemanticStore(
        cfg.projects_dir / project / "semantic.db", embedder=cfg.create_embedder()
    )
    target = Path(path)
    if target.is_file():
        added = asyncio.run(ingest_file(target, project, semantic))
    else:
        added = asyncio.run(ingest_directory(target, project, semantic, max_files))
    click.echo(f"Ingested {added} facts from {path} into {project}.")


@cli.command()
@click.option("--project", default=None, help="Project to heal (default: all).")
@click.option("--dry-run", is_flag=True, help="Show what would be done without changing anything.")
@click.pass_context
def heal(ctx: click.Context, project: str | None, dry_run: bool) -> None:
    """Self-heal memory: merge duplicates, decay stale facts, re-verify low-confidence items."""
    cfg = ctx.obj["config"]
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]
    if not projects:
        click.echo("No projects found.")
        return

    for proj in projects:
        semantic = SemanticStore(
            cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()
        )
        click.echo(f"\nHealing project: {proj}")

        # 1. Merge duplicate facts
        duplicates = semantic.get_duplicate_facts(proj, limit=1000)
        merged = 0
        for dup in duplicates:
            with sqlite3.connect(semantic.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT id, timestamp FROM facts WHERE project = ? AND content = ? ORDER BY timestamp DESC",
                    (proj, dup["content"]),
                ).fetchall()
            if len(rows) <= 1:
                continue
            delete_ids = [r["id"] for r in rows[1:]]
            if not dry_run:
                for fact_id in delete_ids:
                    semantic.delete_by_id(fact_id)
            merged += len(delete_ids)
        if dry_run:
            click.echo(f"  Duplicates that would be merged: {merged}")
        else:
            click.echo(f"  Duplicates merged: {merged}")

        # 2. Compute decay scores
        if not dry_run:
            updated = semantic.compute_decay_scores(proj)
            click.echo(f"  Decay scores updated: {updated}")

        # 3. Archive stale facts (decay >= 0.8) and delete very stale (>= 0.95)
        stale = semantic.list_stale_facts(proj, threshold=0.8, limit=10000)
        archived = 0
        deleted = 0
        for fact in stale:
            if fact.decay_score >= 0.95:
                if not dry_run:
                    semantic.delete_by_id(fact.id)
                deleted += 1
            else:
                if not dry_run:
                    fact.stale = True
                    with sqlite3.connect(semantic.db_path) as conn:
                        conn.execute("UPDATE facts SET stale = 1 WHERE id = ?", (fact.id,))
                        conn.commit()
                archived += 1
        if dry_run:
            click.echo(f"  Stale facts that would be archived: {archived}, deleted: {deleted}")
        else:
            click.echo(f"  Stale facts archived: {archived}, deleted: {deleted}")

        # 4. Re-verify low-confidence facts
        low_conf = [
            f for f in semantic.get_facts_for_reverify(proj, limit=20) if f.confidence < 0.3
        ]
        if not low_conf:
            click.echo("  No low-confidence facts to re-verify")
            continue
        if cfg.reflection.provider != "ollama":
            click.echo("  Reflection provider is not ollama; skipping re-verification")
            continue
        import httpx

        model = cfg.reflection.routing.get("reflection", cfg.reflection.model)
        reverified = 0
        for fact in low_conf:
            prompt = (
                "You are a fact-checking assistant. Evaluate whether the following statement "
                "is still true. Answer with exactly one word: Yes, No, or Uncertain.\n\n"
                f"Statement: {fact.content}\n\nVerdict:"
            )
            if dry_run:
                click.echo(f"  [dry-run] would reverify fact {fact.id}: {fact.content[:60]}...")
                continue
            try:
                r = httpx.post(
                    f"{cfg.reflection.host}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=60.0,
                )
                r.raise_for_status()
                verdict = r.json().get("response", "Uncertain").strip().split()[0]
            except Exception as e:
                click.echo(f"  Reverify failed for fact {fact.id}: {e}")
                continue
            semantic.record_verification(fact.id, verdict)
            reverified += 1
        click.echo(f"  Low-confidence facts re-verified: {reverified}")


@cli.command()
@click.option("--project", default=None, help="Project to verify (default: all).")
@click.option("--execute", is_flag=True, help="Run skill procedures in a sandbox.")
@click.option("--workspace", default=".", help="Workspace to execute skills in.")
@click.pass_context
def verify_skills(ctx: click.Context, project: str | None, execute: bool, workspace: str) -> None:
    """Run the skill verification playground."""
    from acrux.sandbox import run_sandboxed
    from acrux.verify import SkillVerifier

    cfg = ctx.obj["config"]
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]
    if not projects:
        click.echo("No projects found.")
        return

    for proj in projects:
        episodic = EpisodicStore(cfg.projects_dir / proj / "episodes.db")
        procedural = ProceduralDBStore(cfg.projects_dir / proj / "skills.db")
        verifier = SkillVerifier(episodic, procedural)

        # Verify live skills
        live_results = asyncio.run(verifier.verify_project(proj))
        live_verified = sum(1 for errs in live_results.values() if not errs)
        live_failed = len(live_results) - live_verified
        click.echo(f"{proj}: {live_verified} live verified, {live_failed} live failed")
        for skill_id, errors in live_results.items():
            if errors:
                click.echo(f"  live {skill_id}: {', '.join(errors)}")

        # Verify pending skills and promote the ones that pass
        pending = procedural.list_pending(proj)
        promoted = 0
        still_pending = 0
        for skill in pending:
            ok, errors = asyncio.run(verifier.verify(skill))
            if ok:
                if execute:
                    script = "\n".join(skill.procedure)
                    exit_code, output = asyncio.run(run_sandboxed(script, workspace, timeout=120))
                    skill.evidence.append(
                        {"success": exit_code == 0, "output": output, "sandboxed": True}
                    )
                    if exit_code != 0:
                        still_pending += 1
                        click.echo(f"  pending {skill.id}: sandbox execution failed ({exit_code})")
                        continue
                skill.verified = True
                procedural.add(skill)
                procedural.reject_pending(skill.id)
                promoted += 1
            else:
                still_pending += 1
                click.echo(f"  pending {skill.id}: {', '.join(errors)}")
        if promoted or still_pending:
            click.echo(f"{proj}: {promoted} promoted, {still_pending} still pending")


@cli.command()
@click.option("--project", default=None, help="Project to review (default: all).")
@click.option("--promote", default=None, type=int, help="Promote a pending fact by ID.")
@click.option("--reject", default=None, type=int, help="Reject a pending fact by ID.")
@click.pass_context
def review_facts(ctx: click.Context, project: str | None, promote: int | None, reject: int | None) -> None:
    """List or manage pending facts produced by reflection."""
    cfg = ctx.obj["config"]
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]
    if not projects:
        click.echo("No projects found.")
        return

    for proj in projects:
        semantic = SemanticStore(
            cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()
        )
        if promote is not None:
            if semantic.promote_pending_fact(promote):
                click.echo(f"Promoted fact {promote} in {proj}")
            else:
                click.echo(f"Pending fact not found: {promote}")
            continue
        if reject is not None:
            if semantic.reject_pending_fact(reject):
                click.echo(f"Rejected fact {reject} in {proj}")
            else:
                click.echo(f"Pending fact not found: {reject}")
            continue
        pending = semantic.list_pending_facts(proj)
        if not pending:
            click.echo(f"{proj}: no pending facts")
            continue
        click.echo(f"{proj}: {len(pending)} pending facts")
        for fact in pending:
            click.echo(f"  [{fact.id}] {fact.content[:80]} (confidence {fact.confidence:.2f})")


@cli.command()
@click.option("--project", default=None, help="Project to review (default: all).")
@click.option("--promote", default=None, help="Promote a pending skill by ID.")
@click.option("--reject", default=None, help="Reject a pending skill by ID.")
@click.pass_context
def review(ctx: click.Context, project: str | None, promote: str | None, reject: str | None) -> None:
    """List or manage pending skills produced by reflection."""
    cfg = ctx.obj["config"]
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]
    if not projects:
        click.echo("No projects found.")
        return

    for proj in projects:
        procedural = ProceduralDBStore(cfg.projects_dir / proj / "skills.db")
        if promote:
            if procedural.promote_pending(promote):
                click.echo(f"Promoted {promote} in {proj}")
            else:
                click.echo(f"Pending skill not found: {promote}")
            continue
        if reject:
            if procedural.reject_pending(reject):
                click.echo(f"Rejected {reject} in {proj}")
            else:
                click.echo(f"Pending skill not found: {reject}")
            continue
        pending = procedural.list_pending(proj)
        if not pending:
            click.echo(f"{proj}: no pending skills")
            continue
        click.echo(f"{proj}: {len(pending)} pending skills")
        for skill in pending:
            click.echo(f"  [{skill.id}] {skill.name} (evidence: {len(skill.evidence)})")
            click.echo(f"    preconditions: {', '.join(skill.preconditions[:3])}")
            click.echo(f"    procedure: {len(skill.procedure)} steps")


@cli.command()
@click.option("--project", default=None, help="Project to show the improvement curve for (default: all).")
@click.option("--days", default=30, help="Number of days to include.")
@click.pass_context
def curve(ctx: click.Context, project: str | None, days: int) -> None:
    """Show the improvement curve: how memory quality changes over time."""
    cfg = ctx.obj["config"]
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]
    if not projects:
        click.echo("No projects found.")
        return

    cutoff = (utcnow() - timedelta(days=days)).isoformat()
    for proj in projects:
        semantic = SemanticStore(
            cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()
        )
        metrics = semantic.get_metrics(proj, limit=1000)
        if not metrics:
            click.echo(f"\n{proj}: no metrics yet")
            continue
        click.echo(f"\n{proj} improvement curve (last {days} days):")
        # Group by day and metric
        by_day: dict[str, dict[str, list[float]]] = {}
        for m in metrics:
            day = m["timestamp"][:10]
            if day < cutoff[:10]:
                continue
            by_day.setdefault(day, {}).setdefault(m["metric"], []).append(m["value"])
        for day in sorted(by_day):
            parts = []
            for metric, values in sorted(by_day[day].items()):
                avg = sum(values) / len(values)
                parts.append(f"{metric}={avg:.1f}")
            click.echo(f"  {day}: {', '.join(parts)}")
        # Show verification pass rate if available
        procedural = ProceduralDBStore(cfg.projects_dir / proj / "skills.db")
        skills = procedural.get_all(proj)
        if skills:
            verified = sum(1 for s in skills if s.verified)
            click.echo(f"  Skills verified: {verified}/{len(skills)} ({verified/len(skills):.1%})")


@cli.command()
@click.option("--project", default=None, help="Project to show metrics for (default: all).")
@click.option("--metric", default=None, help="Specific metric to show.")
@click.pass_context
def metrics(ctx: click.Context, project: str | None, metric: str | None) -> None:
    """Show observability metrics for the Acrux."""
    cfg = ctx.obj["config"]
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]
    if not projects:
        click.echo("No projects found.")
        return

    for proj in projects:
        semantic = SemanticStore(
            cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()
        )
        click.echo(f"\nMetrics for {proj}:")
        if metric:
            summary = semantic.get_metric_summary(proj, metric)
            click.echo(
                f"  {metric}: count={summary['count']}, avg={summary['avg']:.3f}, "
                f"min={summary['min']:.3f}, max={summary['max']:.3f}"
            )
        else:
            rows = semantic.get_metrics(proj, limit=50)
            if not rows:
                click.echo("  No metrics recorded yet.")
                continue
            by_metric: dict[str, list[float]] = {}
            for r in rows:
                by_metric.setdefault(r["metric"], []).append(r["value"])
            for m, values in sorted(by_metric.items()):
                click.echo(
                    f"  {m}: count={len(values)}, avg={sum(values)/len(values):.3f}, "
                    f"min={min(values):.3f}, max={max(values):.3f}"
                )


@cli.command()
@click.option("--project", default=None, help="Project to benchmark (default: all).")
@click.option("--k", default=10, help="Top-k to measure recall at.")
@click.option("--limit", default=50, help="Number of facts to test per project.")
@click.pass_context
def recall_bench(ctx: click.Context, project: str | None, k: int, limit: int) -> None:
    """Measure how well the Acrux recalls its own facts."""
    cfg = ctx.obj["config"]
    if project:
        projects = [project]
    else:
        projects = [
            p.name
            for p in cfg.projects_dir.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        ]
    if not projects:
        click.echo("No projects found.")
        return

    async def _score(proj: str) -> dict[str, float]:
        semantic = SemanticStore(
            cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()
        )
        facts = semantic.list_facts(proj, limit=limit)
        if not facts:
            return {"n": 0, "recall_at_1": 0.0, "recall_at_5": 0.0, "recall_at_k": 0.0}
        hits1 = hits5 = hitsk = 0
        for fact in facts:
            query = fact.content[:300]
            results = await semantic.search(proj, query, k)
            ids = [f.id for f in results]
            if fact.id in ids:
                idx = ids.index(fact.id)
                if idx == 0:
                    hits1 += 1
                if idx < 5:
                    hits5 += 1
                hitsk += 1
        total = len(facts)
        return {
            "n": total,
            "recall_at_1": hits1 / total,
            "recall_at_5": hits5 / total,
            "recall_at_k": hitsk / total,
        }

    for proj in projects:
        metrics = asyncio.run(_score(proj))
        if metrics["n"] == 0:
            click.echo(f"{proj}: no facts to test")
            continue
        click.echo(
            f"{proj}: recall@1 {metrics['recall_at_1']:.1%}, "
            f"recall@5 {metrics['recall_at_5']:.1%}, "
            f"recall@{k} {metrics['recall_at_k']:.1%} "
            f"(n={metrics['n']})"
        )


@cli.command()
@click.option("--project", default=None, help="Project to benchmark (default: all).")
@click.option("--k", default=10, help="Top-k to measure recall at.")
@click.option("--limit", default=50, help="Number of facts/skills to test per project.")
@click.option("--out", default=None, help="Output directory (default: ~/.acrux/benchmarks).")
@click.pass_context
def bench(ctx: click.Context, project: str | None, k: int, limit: int, out: str | None) -> None:
    """Run the public Acrux benchmark suite and save the report."""
    from acrux.bench import run_benchmark, save_report

    cfg = ctx.obj["config"]
    report = asyncio.run(run_benchmark(cfg, project, k, limit))
    out_dir = Path(out) if out else Path.home() / ".acrux" / "benchmarks"
    path = save_report(report, out_dir)

    click.echo(f"Benchmark saved to {path}")
    overall = report["overall"]
    click.echo(
        f"Facts:  recall@1 {overall['fact_recall_at_1']:.1%}, "
        f"recall@5 {overall['fact_recall_at_5']:.1%}, "
        f"recall@{k} {overall[f'fact_recall_at_{k}']:.1%}"
    )
    click.echo(
        f"Skills: recall@1 {overall['skill_recall_at_1']:.1%}, "
        f"recall@5 {overall['skill_recall_at_5']:.1%}, "
        f"recall@{k} {overall[f'skill_recall_at_{k}']:.1%}"
    )


@cli.command()
@click.option("--project", required=True, help="Project to export verified skills from.")
@click.argument("output", type=click.Path())
@click.pass_context
def registry_export(ctx: click.Context, project: str, output: str) -> None:
    """Export verified skills as a signed registry package."""
    from acrux.registry import export_package

    cfg = ctx.obj["config"]
    procedural = ProceduralDBStore(cfg.projects_dir / project / "skills.db")
    skills = [s for s in procedural.get_all(project) if s.verified]
    if not skills:
        click.echo(f"No verified skills in project {project}.")
        return
    export_package(skills, Path(output))
    click.echo(f"Exported {len(skills)} verified skills to {output}.")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--project", default=None, help="Target project (default: use package project).")
@click.pass_context
def registry_install(ctx: click.Context, path: str, project: str | None) -> None:
    """Install a signed registry package."""
    from acrux.registry import load_package

    cfg = ctx.obj["config"]
    try:
        skills = load_package(Path(path))
    except ValueError as e:
        click.echo(f"Invalid registry package: {e}", err=True)
        sys.exit(1)
    target_project = project or "global"
    procedural = ProceduralDBStore(cfg.projects_dir / target_project / "skills.db")
    for skill in skills:
        skill.project = target_project
    added = procedural.import_skills([s.to_dict() for s in skills])
    click.echo(f"Installed {added} skills into {target_project}.")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.pass_context
def registry_list(ctx: click.Context, path: str) -> None:
    """List skills in a registry package."""
    from acrux.registry import list_package

    try:
        skills = list_package(Path(path))
    except Exception as e:
        click.echo(f"Could not read package: {e}", err=True)
        sys.exit(1)
    for s in skills:
        click.echo(
            f"- {s['name']} (project={s['project']}, verified={s['verified']}, evidence={s['evidence_count']})"
        )


@cli.command()
@click.option(
    "--packages-dir",
    type=click.Path(),
    default=None,
    help="Directory with exported packages (default: ~/.acrux/packages).",
)
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help="Index file to write (default: ~/.acrux/registry-index.json).",
)
@click.pass_context
def registry_index(ctx: click.Context, packages_dir: str | None, output: str | None) -> None:
    """Generate/update the public registry index JSON."""
    from acrux.registry_hosting import build_index, default_index_path, default_packages_dir

    pkg_dir = Path(packages_dir) if packages_dir else default_packages_dir()
    index_path = Path(output) if output else default_index_path()
    try:
        entries = build_index(pkg_dir, index_path)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    click.echo(f"Indexed {len(entries)} package(s) from {pkg_dir} -> {index_path}")
    for e in entries:
        click.echo(f"- {e['name']} {e['version']} ({e['path']})")


@cli.command()
@click.argument("index_url")
@click.option(
    "--packages-dir",
    type=click.Path(),
    default=None,
    help="Directory with exported packages (default: ~/.acrux/packages).",
)
@click.option(
    "--index",
    "index_path",
    type=click.Path(),
    default=None,
    help="Index file to write (default: ~/.acrux/registry-index.json).",
)
@click.option("--dry-run", is_flag=True, help="Only log what would be pushed (no HTTP).")
@click.pass_context
def registry_push(
    ctx: click.Context,
    index_url: str,
    packages_dir: str | None,
    index_path: str | None,
    dry_run: bool,
) -> None:
    """Push the local registry index and packages to an index URL."""
    import httpx

    from acrux.registry_hosting import (
        RegistryClient,
        build_index,
        default_index_path,
        default_packages_dir,
        package_url,
    )

    pkg_dir = Path(packages_dir) if packages_dir else default_packages_dir()
    idx_path = Path(index_path) if index_path else default_index_path()
    try:
        entries = build_index(pkg_dir, idx_path)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)
    if dry_run:
        click.echo(f"[dry-run] would PUT index ({len(entries)} package(s)) to {index_url}")
        for e in entries:
            click.echo(f"[dry-run] would PUT package {e['name']} to {package_url(index_url, e)}")
        return
    try:
        with RegistryClient(index_url) as client:
            summary = client.push(idx_path)
    except httpx.HTTPError as e:
        click.echo(f"Push failed: {e}", err=True)
        sys.exit(1)
    click.echo(f"Pushed index to {summary['index_url']} ({len(summary['pushed'])} package(s)).")
    for name in summary["pushed"]:
        click.echo(f"- pushed {name}")
    for name in summary["skipped"]:
        click.echo(f"- skipped {name} (package file missing)")


@cli.command()
@click.argument("index_url")
@click.option(
    "--package",
    "selected",
    multiple=True,
    help="Install only these packages (repeatable; default: all).",
)
@click.option("--project", default="global", help="Target project for installed skills.")
@click.option(
    "--packages-dir",
    type=click.Path(),
    default=None,
    help="Where to download packages (default: ~/.acrux/packages).",
)
@click.pass_context
def registry_pull(
    ctx: click.Context,
    index_url: str,
    selected: tuple[str, ...],
    project: str,
    packages_dir: str | None,
) -> None:
    """Download a registry index and install selected packages."""
    import httpx

    from acrux.registry import load_package
    from acrux.registry_hosting import RegistryClient, default_packages_dir

    cfg = ctx.obj["config"]
    dest_dir = Path(packages_dir) if packages_dir else default_packages_dir()
    try:
        with RegistryClient(index_url) as client:
            entries = client.pull_index()
            if selected:
                wanted = set(selected)
                known = {str(e.get("name", "")) for e in entries}
                missing = wanted - known
                if missing:
                    click.echo(f"Package(s) not in index: {', '.join(sorted(missing))}", err=True)
                    sys.exit(1)
                entries = [e for e in entries if str(e.get("name", "")) in wanted]
            if not entries:
                click.echo("No packages to install.")
                return
            paths = [client.download_package(e, dest_dir) for e in entries]
    except httpx.HTTPError as e:
        click.echo(f"Pull failed: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    procedural = ProceduralDBStore(cfg.projects_dir / project / "skills.db")
    for path in paths:
        try:
            skills = load_package(path)
        except ValueError as e:
            click.echo(f"Invalid registry package {path}: {e}", err=True)
            sys.exit(1)
        for skill in skills:
            skill.project = project
        added = procedural.import_skills([s.to_dict() for s in skills])
        click.echo(f"Installed {added} skills from {path.name} into {project}.")


@cli.command()
@click.option(
    "--agent",
    type=click.Choice(["kimi", "claude", "cursor", "codex", "gemini"]),
    required=True,
    help="Agent to install the Acrux MCP server for.",
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="MCP transport to configure.",
)
@click.option("--migrate", is_flag=True, help="Migrate old brain_* MCP config to acrux_*.")
@click.pass_context
def install_mcp(ctx: click.Context, agent: str, transport: str, migrate: bool) -> None:
    """Install the Acrux MCP server config for a coding agent."""
    cfg = ctx.obj["config"]
    paths = {
        "kimi": Path.home() / ".kimi-code" / "mcp.json",
        "claude": Path.home() / ".claude.json",
        "cursor": Path.home() / ".cursor" / "mcp.json",
        "codex": Path.home() / ".codex" / "mcp.json",
        "gemini": Path.home() / ".gemini" / "mcp.json",
    }
    path = paths[agent]
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = str(Path(sys.executable).parent / "acrux")
    if transport == "stdio":
        entry = {"command": cmd, "args": ["start"], "enabled": True}
    else:
        port = cfg.mcp.port
        token = cfg.api_token or cfg.ensure_token()
        entry = {
            "url": f"http://127.0.0.1:{port}/sse",
            "headers": {"Authorization": f"Bearer {token}"},
            "enabled": True,
        }
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except Exception:
            data = {}
    servers = data.setdefault("mcpServers", {})

    if migrate:
        # Remove/rename old brain server entries
        for old_name in ("brain", "brain-server", "brain-mcp"):
            if old_name in servers:
                del servers[old_name]
        # Migrate any brain command paths
        for name, server in list(servers.items()):
            command = server.get("command", "")
            if command.endswith("/brain"):
                server["command"] = str(Path(command).parent / "acrux")
            if name == "brain":
                servers["acrux"] = server
                del servers[name]

    servers["acrux"] = entry
    path.write_text(json.dumps(data, indent=2))
    if transport == "stdio":
        click.echo(f"Installed acrux MCP for {agent} at {path}")
        click.echo(f"  command: {cmd} start")
    else:
        click.echo(f"Installed acrux MCP for {agent} at {path}")
        click.echo(f"  url: {entry['url']}")


@cli.command()
@click.option("--project", default="demo", help="Demo project name.")
@click.pass_context
def demo(ctx: click.Context, project: str) -> None:
    """Run a three-session demo showing Acrux learning and recalling a fix."""
    cfg = ctx.obj["config"]
    project_dir = cfg.projects_dir / project
    project_dir.mkdir(parents=True, exist_ok=True)

    semantic = SemanticStore(project_dir / "semantic.db", embedder=cfg.create_embedder())
    episodic = EpisodicStore(project_dir / "episodes.db")
    procedural = ProceduralDBStore(project_dir / "skills.db")

    click.echo("=== Acrux demo ===")
    click.echo("Session 1: agent fixes a bug and stores the episode.")

    episode = Episode(
        session_id="demo-session-1",
        task="Fix race condition in token refresh",
        project=project,
        outcome="success",
        root_cause="token refresh raced with concurrent requests",
        fix_pattern="serialize token access with a lock",
        tags=["demo", "rust", "auth"],
        source="demo",
    )
    episodic.add(episode)

    skill = Skill(
        project=project,
        name="fix_token_refresh_race",
        preconditions=["language:rust", "symptom:token refresh race"],
        procedure=[
            "Identify shared token state",
            "Add a mutex or channel to serialize access",
            "Run the concurrent test in a loop to verify",
        ],
        evidence=[{"session_id": "demo-session-1"}],
        verified=True,
        tags=["demo"],
    )
    procedural.add(skill)

    click.echo("Session 2: memory is recalled for a similar task.")
    query = "How do I fix a token refresh race condition?"
    facts = asyncio.run(semantic.search(project, query, 3))
    episodes = episodic.search(project, query, 3)
    skills = procedural.search(project, query, 3)

    if facts:
        click.echo("  Facts:")
        for f in facts:
            click.echo(f"    [memory:fact:{f.id}] {f.content}")
    if episodes:
        click.echo("  Episodes:")
        for e in episodes:
            click.echo(f"    [memory:episode:{e.session_id}] {e.task}: {e.fix_pattern}")
    if skills:
        click.echo("  Skills:")
        for s in skills:
            click.echo(f"    [memory:skill:{s.id}] {s.name} ({len(s.procedure)} steps)")

    click.echo("Session 3: a fresh session start carries the verified skill.")
    context_lines = []
    if skills:
        context_lines.append("[Procedural memory]")
        for s in skills:
            context_lines.append(f"- [memory:skill:{s.id}] {s.name}: {' -> '.join(s.procedure[:3])}")
    click.echo("\nInjected context:")
    click.echo("\n".join(context_lines) if context_lines else "  (none)")
    click.echo("\nDemo complete. Acrux learned a fix and recalled it in a later session.")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--kind", type=click.Choice(["episode", "fact", "skill"]), required=True)
@click.pass_context
def validate_spec(ctx: click.Context, path: str, kind: str) -> None:
    """Validate a JSON file against the Acrux spec."""
    from acrux.spec import validate

    data = json.loads(Path(path).read_text())
    errors = validate(data, kind)
    if errors:
        for e in errors:
            click.echo(f"  - {e}")
        sys.exit(1)
    click.echo("Valid.")


@cli.command()
@click.argument("project")
@click.option("--apply", is_flag=True, help="Copy verified skills/facts to global.")
@click.pass_context
def transfer_report(ctx: click.Context, project: str, apply: bool) -> None:
    """Show what a project learned that others should inherit."""
    cfg = ctx.obj["config"]
    procedural = ProceduralDBStore(cfg.projects_dir / project / "skills.db")
    semantic = SemanticStore(
        cfg.projects_dir / project / "semantic.db", embedder=cfg.create_embedder()
    )
    global_procedural = ProceduralDBStore(cfg.global_dir / "skills.db")
    global_semantic = SemanticStore(cfg.global_dir / "facts.db", embedder=cfg.create_embedder())

    skills = [s for s in procedural.get_all(project) if s.verified]
    facts = semantic.list_facts(project, limit=1000)
    global_skill_names = {s.name for s in global_procedural.get_all("global")}
    global_fact_contents = {f.content for f in global_semantic.list_facts("global", limit=10000)}

    transferable_skills = [s for s in skills if s.name not in global_skill_names]
    transferable_facts = [f for f in facts if f.content not in global_fact_contents]

    click.echo(f"Transfer report for {project}:")
    click.echo(f"  Verified skills: {len(skills)} ({len(transferable_skills)} transferable)")
    for s in transferable_skills[:20]:
        click.echo(f"    - {s.name} (success {s.success_rate:.0%})")
    click.echo(f"  Facts: {len(facts)} ({len(transferable_facts)} transferable)")
    for f in transferable_facts[:10]:
        click.echo(f"    - {f.content[:70]}")

    if apply:
        for s in transferable_skills:
            s.project = "global"
            global_procedural.add(s)
        click.echo(f"Copied {len(transferable_skills)} skills to global.")
        # Facts are not copied automatically to avoid duplication; use review.


@cli.command()
@click.option("--min-projects", default=3, help="Minimum projects a pattern must appear in.")
@click.option("--apply", is_flag=True, help="Promote patterns to global.")
@click.pass_context
def mine_patterns(ctx: click.Context, min_projects: int, apply: bool) -> None:
    """Find skills/facts appearing in multiple projects and promote to global."""
    cfg = ctx.obj["config"]
    projects = [
        p.name
        for p in cfg.projects_dir.iterdir()
        if p.is_dir() and not p.name.startswith("_")
    ]
    skill_counts: dict[str, list[str]] = {}
    fact_counts: dict[str, list[str]] = {}
    for proj in projects:
        procedural = ProceduralDBStore(cfg.projects_dir / proj / "skills.db")
        for skill in procedural.get_all(proj):
            skill_counts.setdefault(skill.name, []).append(proj)
        semantic = SemanticStore(
            cfg.projects_dir / proj / "semantic.db", embedder=cfg.create_embedder()
        )
        for fact in semantic.list_facts(proj, limit=1000):
            fact_counts.setdefault(fact.content, []).append(proj)

    common_skills = {name: projs for name, projs in skill_counts.items() if len(set(projs)) >= min_projects}
    common_facts = {content: projs for content, projs in fact_counts.items() if len(set(projs)) >= min_projects}

    click.echo(f"Patterns in {min_projects}+ projects:")
    click.echo(f"  Skills: {len(common_skills)}")
    for name, projs in sorted(common_skills.items())[:20]:
        click.echo(f"    - {name} ({', '.join(sorted(set(projs)))})")
    click.echo(f"  Facts: {len(common_facts)}")
    for content, projs in sorted(common_facts.items())[:10]:
        click.echo(f"    - {content[:70]} ({', '.join(sorted(set(projs)))})")

    if apply:
        global_procedural = ProceduralDBStore(cfg.global_dir / "skills.db")
        global_semantic = SemanticStore(cfg.global_dir / "facts.db", embedder=cfg.create_embedder())
        promoted = 0
        for name in common_skills:
            for proj in projects:
                procedural = ProceduralDBStore(cfg.projects_dir / proj / "skills.db")
                skill = next((s for s in procedural.get_all(proj) if s.name == name), None)
                if skill:
                    skill.project = "global"
                    global_procedural.add(skill)
                    promoted += 1
                    break
        click.echo(f"Promoted {promoted} skills to global.")


@cli.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--project", default="default", help="Project to record the session under.")
@click.option("--task", default=None, help="Task description (default: the command itself).")
@click.pass_context
def wrap(ctx: click.Context, command: tuple[str, ...], project: str, task: str | None) -> None:
    """Run a command and record it as an episode for learning."""
    cfg = ctx.obj["config"]
    task = task or " ".join(command)
    git_before = git_context(Path.cwd())
    start = time.time()
    proc = subprocess.run(command, capture_output=True, text=True)
    duration = time.time() - start
    outcome = "success" if proc.returncode == 0 else f"error (exit {proc.returncode})"
    actions = [
        Action(
            tool="run_command",
            command=" ".join(command),
            result=outcome,
            diff="",
        )
    ]
    episode = Episode(
        session_id=f"wrap-{int(start)}",
        task=task,
        project=project,
        context={"git_before": git_before, "duration_s": round(duration, 2)},
        actions=actions,
        outcome=outcome,
        root_cause="",
        fix_pattern="",
        tags=["wrapped"],
        source="acrux_wrap",
    )
    episodic = EpisodicStore(cfg.projects_dir / project / "episodes.db")
    episodic.add(episode)
    click.echo(f"Recorded wrapped session (exit {proc.returncode})")
    if proc.stdout:
        click.echo(proc.stdout)
    if proc.stderr:
        click.echo(proc.stderr, err=True)
    sys.exit(proc.returncode)


@cli.command()
@click.option(
    "--mode",
    type=click.Choice(["no-memory", "memory", "memory+skills", "all"]),
    default="all",
    help="Running mode (default: all three).",
)
@click.option("--json", "as_json", is_flag=True, help="Print the raw JSON report.")
@click.option("--keep-workspaces", is_flag=True, help="Keep task workspaces on disk.")
@click.pass_context
def taskbench(ctx: click.Context, mode: str, as_json: bool, keep_workspaces: bool) -> None:
    """Run the TaskBench coding-task harness and report pass rates."""
    from acrux.taskbench import MODES, run_taskbench

    modes = list(MODES) if mode == "all" else [mode]
    report = run_taskbench(modes=modes, keep_workspaces=keep_workspaces)
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return
    for m in modes:
        summary = report["modes"][m]
        click.echo(
            f"{m}: pass rate {summary['pass_rate']:.0%} "
            f"({summary['passed']}/{summary['total']})"
        )
        for t in summary["tasks"]:
            mark = "PASS" if t["passed"] else "FAIL"
            hint = "guided" if t["guided"] else "naive"
            click.echo(
                f"  [{mark}] {t['task_id']} ({hint}, recalled={t['recalled']}) — {t['details']}"
            )


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
