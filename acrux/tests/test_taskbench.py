"""Tests for the TaskBench harness."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from acrux.cli import cli
from acrux.taskbench import MODES, TASKS, Task, run_taskbench, setup_workspace

GATED_TASKS = {
    "fix-order-dependent-test",
    "fix-pagination-off-by-one",
    "fix-config-path",
    "fix-email-regex",
    "fix-file-encoding",
}


def test_catalog_has_ten_tasks() -> None:
    assert len(TASKS) == 10
    ids = [t.id for t in TASKS]
    assert len(set(ids)) == 10
    kinds = {t.kind for t in TASKS}
    assert {"fix-test", "add-feature", "refactor", "fix-bug"} <= kinds
    for task in TASKS:
        assert task.prompt, task.id
        assert task.workspace_files, task.id
        assert task.solution_files, task.id


def test_memory_gated_tasks_carry_seeds() -> None:
    for task in TASKS:
        if task.id in GATED_TASKS:
            assert task.memory_query, task.id
            assert task.hint_key, task.id
            assert task.naive_files, task.id
            assert task.episodes or task.facts or task.skill, task.id


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_checker_fails_on_pristine_workspace(task: Task, tmp_path: Path) -> None:
    ws = setup_workspace(task, tmp_path / task.id)
    result = task.checker(ws)
    assert not result.passed, f"checker passes without any solve for {task.id}"


def test_no_memory_mode_pass_rate() -> None:
    report = run_taskbench(modes=["no-memory"])
    summary = report["modes"]["no-memory"]
    assert summary["total"] == 10
    # Only the 5 non-gated tasks pass without memory.
    assert summary["pass_rate"] == pytest.approx(0.5)
    by_id = {t["task_id"]: t for t in summary["tasks"]}
    for task_id in GATED_TASKS:
        assert by_id[task_id]["passed"] is False, task_id
        assert by_id[task_id]["guided"] is False, task_id
        assert by_id[task_id]["recalled"] == 0, task_id


def test_memory_mode_pass_rate() -> None:
    report = run_taskbench(modes=["memory"])
    summary = report["modes"]["memory"]
    assert summary["total"] == 10
    # Episode/fact-gated tasks now pass; the skill-gated regex task still fails.
    assert summary["pass_rate"] == pytest.approx(0.9)
    by_id = {t["task_id"]: t for t in summary["tasks"]}
    assert by_id["fix-email-regex"]["passed"] is False
    assert by_id["fix-email-regex"]["guided"] is False
    for task_id in GATED_TASKS - {"fix-email-regex"}:
        assert by_id[task_id]["passed"] is True, task_id
        assert by_id[task_id]["guided"] is True, task_id
        assert by_id[task_id]["recalled"] > 0, task_id


def test_memory_skills_mode_all_pass() -> None:
    report = run_taskbench(modes=["memory+skills"])
    summary = report["modes"]["memory+skills"]
    assert summary["total"] == 10
    assert summary["pass_rate"] == 1.0
    by_id = {t["task_id"]: t for t in summary["tasks"]}
    assert by_id["fix-email-regex"]["passed"] is True
    assert by_id["fix-email-regex"]["guided"] is True


def test_cli_taskbench_reports_pass_rates() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["taskbench", "--mode", "memory+skills"])
    assert result.exit_code == 0, result.output
    assert "pass rate 100%" in result.output
    assert "fix-email-regex" in result.output


def test_cli_taskbench_json() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["taskbench", "--mode", "no-memory", "--json"])
    assert result.exit_code == 0, result.output
    import json

    report = json.loads(result.output)
    assert report["modes"]["no-memory"]["total"] == 10


def test_modes_constant() -> None:
    assert MODES == ("no-memory", "memory", "memory+skills")
