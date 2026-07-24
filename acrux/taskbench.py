"""TaskBench: end-to-end coding-task benchmark for acrux memory.

Runs a fixed catalog of realistic coding tasks (fix a flaky test, add a
function, refactor, ...) against throwaway workspace fixtures in three
running modes:

- ``no-memory``:      the solver only sees the task prompt.
- ``memory``:         episodic + semantic memory are seeded from past
                      sessions and recalled into the solver context.
- ``memory+skills``:  additionally, verified procedural skills are seeded
                      and recalled.

Each task ships a workspace fixture (temporary files), a prompt, and a
checker that verifies the final state of the workspace (usually by
running the project's tests in a subprocess).

The built-in reference solver is deterministic: it applies the correct
solution when the recalled memory context contains the relevant hint,
otherwise it applies a plausible-but-wrong "naive" fix. The pass-rate
delta between modes therefore measures how much the recalled memory
(and verified skills) actually help. Requires pytest on the interpreter
that runs the checkers.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from acrux.memory.episodic import EpisodicStore
from acrux.memory.procedural_db import ProceduralDBStore
from acrux.memory.semantic import SemanticStore
from acrux.models import Episode, Fact, Skill

MODES = ("no-memory", "memory", "memory+skills")

PROJECT = "taskbench"


@dataclass
class CheckResult:
    passed: bool
    details: str = ""


Checker = Callable[[Path], CheckResult]


@dataclass
class Task:
    id: str
    title: str
    kind: str  # fix-test | add-feature | refactor | fix-bug
    prompt: str
    workspace_files: dict[str, str]
    checker: Checker
    solution_files: dict[str, str] = field(default_factory=dict)
    naive_files: dict[str, str] = field(default_factory=dict)
    memory_query: str = ""
    hint_key: str = ""  # substring the solver must see in context to use solution_files
    episodes: list[Episode] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    skill: Skill | None = None


@dataclass
class Stores:
    episodic: EpisodicStore
    semantic: SemanticStore
    procedural: ProceduralDBStore | None = None


# ---------------------------------------------------------------------------
# Checker helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _pytest_passed(ws: Path, test_file: str) -> tuple[bool, str]:
    res = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", test_file], ws)
    if res.returncode != 0:
        tail = (res.stdout + res.stderr).strip().splitlines()
        return False, f"pytest failed: {tail[-1] if tail else 'unknown'}"
    return True, "tests pass"


def _script_passed(ws: Path, script: str, *args: str) -> tuple[bool, str]:
    res = _run([sys.executable, script, *args], ws)
    if res.returncode != 0:
        return False, f"{script} exited {res.returncode}: {res.stderr.strip()[:120]}"
    return True, res.stdout.strip()


def _inline_passed(ws: Path, code: str) -> tuple[bool, str]:
    res = _run([sys.executable, "-c", code], ws)
    if res.returncode != 0:
        return False, res.stderr.strip().splitlines()[-1][:120]
    return True, "hidden checks pass"


# ---------------------------------------------------------------------------
# Task checkers
# ---------------------------------------------------------------------------


def _check_order_dependent(ws: Path) -> CheckResult:
    ok, msg = _pytest_passed(ws, "test_tracker.py")
    if not ok:
        return CheckResult(False, msg)
    if "skip" in (ws / "test_tracker.py").read_text():
        return CheckResult(False, "test was skipped instead of fixed")
    return CheckResult(True, "both tests pass without skipping")


def _check_pytest_only(test_file: str) -> Checker:
    def _check(ws: Path) -> CheckResult:
        ok, msg = _pytest_passed(ws, test_file)
        return CheckResult(ok, msg)

    return _check


def _check_refactor_duplicate(ws: Path) -> CheckResult:
    ok, msg = _pytest_passed(ws, "test_reports.py")
    if not ok:
        return CheckResult(False, msg)
    src = (ws / "reports.py").read_text()
    if "_totals_by" not in src:
        return CheckResult(False, "no shared helper extracted")
    if src.count("for row in rows") != 1:
        return CheckResult(False, "duplicated loop still present")
    return CheckResult(True, "tests pass and duplication is gone")


_HIDDEN_PAGINATE = """
import sys
sys.path.insert(0, ".")
from paginate import paginate

for bad in (0, -1):
    try:
        paginate([1, 2, 3], bad, 2)
    except ValueError:
        pass
    else:
        raise SystemExit(f"page={bad} did not raise ValueError")
print("hidden ok")
"""


def _check_paginate(ws: Path) -> CheckResult:
    ok, msg = _pytest_passed(ws, "test_paginate.py")
    if not ok:
        return CheckResult(False, msg)
    ok, msg = _inline_passed(ws, _HIDDEN_PAGINATE)
    if not ok:
        return CheckResult(False, f"hidden edge case failed: {msg}")
    return CheckResult(True, "1-indexed pagination with ValueError guard")


def _check_config_path(ws: Path) -> CheckResult:
    ok, msg = _script_passed(ws, "app.py")
    if not ok:
        return CheckResult(False, msg)
    if "retries=3" not in msg:
        return CheckResult(False, f"app reads the wrong config (output: {msg!r})")
    return CheckResult(True, "app reads config/app.json (retries=3)")


def _check_cli_flag(ws: Path) -> CheckResult:
    ok, msg = _script_passed(ws, "greet.py", "--name", "bob", "--shout")
    if not ok:
        return CheckResult(False, msg)
    if "HELLO, BOB!" not in msg:
        return CheckResult(False, f"--shout did not uppercase (output: {msg!r})")
    ok, msg = _script_passed(ws, "greet.py", "--name", "bob")
    if not ok or "Hello, bob!" not in msg:
        return CheckResult(False, "default behaviour broken")
    return CheckResult(True, "--shout uppercases, default unchanged")


_HIDDEN_EMAIL = """
import sys
sys.path.insert(0, ".")
from validators import is_valid_email

assert is_valid_email("name+tag@example.com"), "plus-addressing rejected"
assert is_valid_email("user@mail.example.co.uk"), "multi-part TLD rejected"
assert not is_valid_email("a@b"), "missing TLD accepted"
print("hidden ok")
"""


def _check_email_regex(ws: Path) -> CheckResult:
    ok, msg = _pytest_passed(ws, "test_validators.py")
    if not ok:
        return CheckResult(False, msg)
    ok, msg = _inline_passed(ws, _HIDDEN_EMAIL)
    if not ok:
        return CheckResult(False, f"hidden edge case failed: {msg}")
    return CheckResult(True, "regex covers plus-addressing and multi-part TLDs")


def _check_rename(ws: Path) -> CheckResult:
    import re

    ok, msg = _pytest_passed(ws, "test_calc.py")
    if not ok:
        return CheckResult(False, msg)
    for name in ("calc.py", "test_calc.py", "README.md"):
        if re.search(r"\bcalc\(", (ws / name).read_text()):
            return CheckResult(False, f"stale reference to calc() left in {name}")
    if "calculate_total" not in (ws / "calc.py").read_text():
        return CheckResult(False, "calculate_total not defined")
    return CheckResult(True, "renamed everywhere, tests pass")


def _check_encoding(ws: Path) -> CheckResult:
    ok, msg = _script_passed(ws, "export_report.py")
    if not ok:
        return CheckResult(False, msg)
    src = (ws / "export_report.py").read_text()
    if 'encoding="utf-8"' not in src:
        return CheckResult(False, "open() missing explicit encoding='utf-8'")
    content = (ws / "report.txt").read_text(encoding="utf-8")
    if "café au lait" not in content:
        return CheckResult(False, "non-ASCII content corrupted")
    return CheckResult(True, "utf-8 encoding explicit, content intact")


# ---------------------------------------------------------------------------
# Task catalog
# ---------------------------------------------------------------------------

TASKS: list[Task] = [
    Task(
        id="fix-order-dependent-test",
        title="Fix order-dependent flaky test",
        kind="fix-test",
        prompt=(
            "The test suite in test_tracker.py is flaky: test_starts_empty fails whenever "
            "it runs after another test. Find the root cause and fix it so the suite is "
            "stable. Do not skip or delete the failing test."
        ),
        workspace_files={
            "tracker.py": '''"""In-memory event tracker."""

_events: list[str] = []


def record(event: str) -> None:
    _events.append(event)


def all_events() -> list[str]:
    return list(_events)


def clear() -> None:
    _events.clear()
''',
            "test_tracker.py": '''import tracker


def test_records_event():
    tracker.record("login")
    assert "login" in tracker.all_events()


def test_starts_empty():
    assert tracker.all_events() == []
''',
        },
        naive_files={
            "test_tracker.py": '''import pytest

import tracker


def test_records_event():
    tracker.record("login")
    assert "login" in tracker.all_events()


@pytest.mark.skip(reason="flaky")
def test_starts_empty():
    assert tracker.all_events() == []
''',
        },
        solution_files={
            "test_tracker.py": '''import pytest

import tracker


@pytest.fixture(autouse=True)
def _reset_tracker():
    tracker.clear()
    yield


def test_records_event():
    tracker.record("login")
    assert "login" in tracker.all_events()


def test_starts_empty():
    assert tracker.all_events() == []
''',
        },
        checker=_check_order_dependent,
        memory_query="flaky tracker tests",
        hint_key="autouse",
        episodes=[
            Episode(
                session_id="seed-fix-order-dependent-test",
                task="Fix flaky tracker tests that only fail in CI",
                project=PROJECT,
                outcome="success",
                root_cause="module-level state pollution: tracker._events leaks between tests",
                fix_pattern=(
                    "add an autouse pytest fixture that resets shared state before each test"
                ),
                tags=["pytest", "flaky"],
            )
        ],
    ),
    Task(
        id="add-fibonacci",
        title="Add a fibonacci function",
        kind="add-feature",
        prompt=(
            "Implement fibonacci(n) in math_utils.py so the tests in test_math_utils.py "
            "pass. fib(0) == 0, fib(1) == 1, and negative input must raise ValueError."
        ),
        workspace_files={
            "math_utils.py": '''"""Small math helpers."""


def fibonacci(n: int) -> int:
    """Return the n-th Fibonacci number (fib(0) == 0, fib(1) == 1)."""
    raise NotImplementedError
''',
            "test_math_utils.py": '''import pytest

from math_utils import fibonacci


def test_base_cases():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1


def test_tenth():
    assert fibonacci(10) == 55


def test_negative_raises():
    with pytest.raises(ValueError):
        fibonacci(-1)
''',
        },
        solution_files={
            "math_utils.py": '''"""Small math helpers."""


def fibonacci(n: int) -> int:
    """Return the n-th Fibonacci number (fib(0) == 0, fib(1) == 1)."""
    if n < 0:
        raise ValueError("n must be >= 0")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
''',
        },
        checker=_check_pytest_only("test_math_utils.py"),
    ),
    Task(
        id="refactor-duplicate-logic",
        title="Refactor duplicated report logic",
        kind="refactor",
        prompt=(
            "weekly_totals and monthly_totals in reports.py duplicate the same grouping "
            "loop. Extract a shared helper _totals_by(rows, key) and make both functions "
            "use it. Keep the tests passing."
        ),
        workspace_files={
            "reports.py": '''"""Sales reports."""


def weekly_totals(rows):
    totals = {}
    for row in rows:
        key = row["week"]
        totals[key] = totals.get(key, 0) + row["amount"]
    return totals


def monthly_totals(rows):
    totals = {}
    for row in rows:
        key = row["month"]
        totals[key] = totals.get(key, 0) + row["amount"]
    return totals
''',
            "test_reports.py": '''from reports import monthly_totals, weekly_totals

ROWS = [
    {"week": "w1", "month": "jan", "amount": 10},
    {"week": "w1", "month": "jan", "amount": 5},
    {"week": "w2", "month": "feb", "amount": 7},
]


def test_weekly():
    assert weekly_totals(ROWS) == {"w1": 15, "w2": 7}


def test_monthly():
    assert monthly_totals(ROWS) == {"jan": 15, "feb": 7}
''',
        },
        solution_files={
            "reports.py": '''"""Sales reports."""


def _totals_by(rows, key):
    totals = {}
    for row in rows:
        totals[row[key]] = totals.get(row[key], 0) + row["amount"]
    return totals


def weekly_totals(rows):
    return _totals_by(rows, "week")


def monthly_totals(rows):
    return _totals_by(rows, "month")
''',
        },
        checker=_check_refactor_duplicate,
    ),
    Task(
        id="fix-pagination-off-by-one",
        title="Fix pagination off-by-one",
        kind="fix-bug",
        prompt=(
            "paginate() in paginate.py returns the wrong slice — the tests in "
            "test_paginate.py fail. Fix the implementation so it matches the project's "
            "pagination conventions, including invalid-page handling."
        ),
        workspace_files={
            "paginate.py": '''"""Pagination helper."""


def paginate(items: list, page: int, per_page: int) -> list:
    start = page * per_page
    return items[start : start + per_page]
''',
            "test_paginate.py": '''from paginate import paginate

ITEMS = list(range(1, 26))


def test_first_page():
    assert paginate(ITEMS, 1, 10) == list(range(1, 11))


def test_second_page():
    assert paginate(ITEMS, 2, 10) == list(range(11, 21))


def test_last_partial_page():
    assert paginate(ITEMS, 3, 10) == list(range(21, 26))
''',
        },
        naive_files={
            "paginate.py": '''"""Pagination helper."""


def paginate(items: list, page: int, per_page: int) -> list:
    start = (page - 1) * per_page
    return items[start : start + per_page]
''',
        },
        solution_files={
            "paginate.py": '''"""Pagination helper."""


def paginate(items: list, page: int, per_page: int) -> list:
    if page < 1:
        raise ValueError("page is 1-indexed and must be >= 1")
    start = (page - 1) * per_page
    return items[start : start + per_page]
''',
        },
        checker=_check_paginate,
        memory_query="pagination indexing convention",
        hint_key="valueerror",
        facts=[
            Fact(
                project=PROJECT,
                content=(
                    "Project convention: pagination is 1-indexed and page < 1 must raise "
                    "ValueError (the API treats page=0 as a client error)."
                ),
                source="taskbench",
                tags=["convention", "pagination"],
            )
        ],
    ),
    Task(
        id="fix-config-path",
        title="Fix config path crash",
        kind="fix-bug",
        prompt=(
            "app.py crashes on startup with FileNotFoundError after a config "
            "reorganization. Fix where the app reads its configuration from."
        ),
        workspace_files={
            "settings.json": '{"retries": 0, "legacy": true}\n',
            "config/app.json": '{"retries": 3}\n',
            "app.py": '''"""Demo app that loads its config on startup."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config" / "settings.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def main() -> None:
    cfg = load_config()
    print(f"retries={cfg['retries']}")


if __name__ == "__main__":
    main()
''',
        },
        naive_files={
            "app.py": '''"""Demo app that loads its config on startup."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "settings.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def main() -> None:
    cfg = load_config()
    print(f"retries={cfg['retries']}")


if __name__ == "__main__":
    main()
''',
        },
        solution_files={
            "app.py": '''"""Demo app that loads its config on startup."""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config" / "app.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def main() -> None:
    cfg = load_config()
    print(f"retries={cfg['retries']}")


if __name__ == "__main__":
    main()
''',
        },
        checker=_check_config_path,
        memory_query="app config file location",
        hint_key="config/app.json",
        episodes=[
            Episode(
                session_id="seed-fix-config-path",
                task="Debug app startup crash after config reorganization",
                project=PROJECT,
                outcome="success",
                root_cause=(
                    "app still pointed at the legacy settings.json; the real config "
                    "moved to config/app.json"
                ),
                fix_pattern="read config/app.json and ignore the stale top-level settings.json",
                tags=["config"],
            )
        ],
    ),
    Task(
        id="add-cli-flag",
        title="Add a CLI flag",
        kind="add-feature",
        prompt=(
            "Add a --shout flag to greet.py that uppercases the greeting. Default "
            "behaviour without the flag must stay the same."
        ),
        workspace_files={
            "greet.py": '''"""Greeting CLI."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="world")
    args = parser.parse_args()
    print(f"Hello, {args.name}!")


if __name__ == "__main__":
    main()
''',
        },
        solution_files={
            "greet.py": '''"""Greeting CLI."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="world")
    parser.add_argument("--shout", action="store_true")
    args = parser.parse_args()
    message = f"Hello, {args.name}!"
    if args.shout:
        message = message.upper()
    print(message)


if __name__ == "__main__":
    main()
''',
        },
        checker=_check_cli_flag,
    ),
    Task(
        id="fix-email-regex",
        title="Fix email validation regex",
        kind="fix-bug",
        prompt=(
            "is_valid_email() in validators.py rejects valid addresses — the visible "
            "tests in test_validators.py fail. Fix EMAIL_RE so it validates the "
            "addresses our users actually have."
        ),
        workspace_files={
            "validators.py": '''"""Input validators."""

import re

EMAIL_RE = re.compile(r"^[a-z0-9]+@[a-z0-9]+\\.[a-z]{2,3}$")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))
''',
            "test_validators.py": '''from validators import is_valid_email


def test_simple_valid():
    assert is_valid_email("user@example.com")


def test_missing_at():
    assert not is_valid_email("userexample.com")


def test_subdomain_valid():
    assert is_valid_email("user@mail.example.com")
''',
        },
        naive_files={
            "validators.py": '''"""Input validators."""

import re

EMAIL_RE = re.compile(r"^[a-z0-9]+@([a-z0-9]+\\.)+[a-z]{2,}$")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))
''',
        },
        solution_files={
            "validators.py": '''"""Input validators."""

import re

EMAIL_RE = re.compile(r"^[a-z0-9][a-z0-9._%+-]*@([a-z0-9-]+\\.)+[a-z]{2,}$")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))
''',
        },
        checker=_check_email_regex,
        memory_query="email validation regex",
        hint_key="plus-addressing",
        skill=Skill(
            id="email-regex-checklist",
            project=PROJECT,
            name="email-regex-checklist",
            preconditions=["editing the email validation regex"],
            procedure=[
                "cover plus-addressing (name+tag@example.com)",
                "cover subdomains and multi-part TLDs (user@mail.example.co.uk)",
                "reject addresses without a TLD (a@b)",
                "run both the visible tests and the hidden edge cases",
            ],
            verified=True,
            tags=["regex", "validation"],
        ),
    ),
    Task(
        id="rename-function-everywhere",
        title="Rename function everywhere",
        kind="refactor",
        prompt=(
            "Rename calc() in calc.py to calculate_total(). Update every reference, "
            "including the tests and README.md. Keep the tests passing."
        ),
        workspace_files={
            "calc.py": '''"""Billing calculations."""


def calc(items: list[dict]) -> float:
    """Total price of line items."""
    return sum(i["price"] * i["qty"] for i in items)
''',
            "test_calc.py": '''from calc import calc


def test_total():
    assert calc([{"price": 2.0, "qty": 3}, {"price": 1.5, "qty": 2}]) == 9.0
''',
            "README.md": """# Billing

Use `calc(items)` to compute the total of line items.
""",
        },
        solution_files={
            "calc.py": '''"""Billing calculations."""


def calculate_total(items: list[dict]) -> float:
    """Total price of line items."""
    return sum(i["price"] * i["qty"] for i in items)
''',
            "test_calc.py": '''from calc import calculate_total


def test_total():
    assert calculate_total([{"price": 2.0, "qty": 3}, {"price": 1.5, "qty": 2}]) == 9.0
''',
            "README.md": """# Billing

Use `calculate_total(items)` to compute the total of line items.
""",
        },
        checker=_check_rename,
    ),
    Task(
        id="fix-file-encoding",
        title="Fix file encoding",
        kind="fix-bug",
        prompt=(
            "export_report.py writes a report containing non-ASCII text. Make the "
            "export robust and cross-platform, following the project's file-encoding "
            "conventions."
        ),
        workspace_files={
            "export_report.py": '''"""Export a small text report."""

from pathlib import Path


def export_report(path: Path, lines: list[str]) -> None:
    with open(path, "w") as f:
        for line in lines:
            f.write(line + "\\n")


def main() -> None:
    export_report(Path("report.txt"), ["Summary", "café au lait", "naïve"])
    print("done")


if __name__ == "__main__":
    main()
''',
        },
        naive_files={
            "export_report.py": '''"""Export a small text report."""

from pathlib import Path


def export_report(path: Path, lines: list[str]) -> None:
    with open(path, "w", errors="ignore") as f:
        for line in lines:
            f.write(line + "\\n")


def main() -> None:
    export_report(Path("report.txt"), ["Summary", "café au lait", "naïve"])
    print("done")


if __name__ == "__main__":
    main()
''',
        },
        solution_files={
            "export_report.py": '''"""Export a small text report."""

from pathlib import Path


def export_report(path: Path, lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\\n")


def main() -> None:
    export_report(Path("report.txt"), ["Summary", "café au lait", "naïve"])
    print("done")


if __name__ == "__main__":
    main()
''',
        },
        checker=_check_encoding,
        memory_query="file encoding convention",
        hint_key="utf-8",
        facts=[
            Fact(
                project=PROJECT,
                content=(
                    "Project convention: always pass encoding='utf-8' to open() because "
                    "CI runs on Windows where the default encoding is not UTF-8."
                ),
                source="taskbench",
                tags=["convention", "encoding"],
            )
        ],
    ),
    Task(
        id="fix-mutable-default",
        title="Fix mutable default argument",
        kind="fix-bug",
        prompt=(
            "collect() in collector.py leaks items between calls — test_collector.py "
            "fails. Fix the bug."
        ),
        workspace_files={
            "collector.py": '''"""Item collector."""


def collect(item: str, bucket: list[str] = []) -> list[str]:
    bucket.append(item)
    return bucket
''',
            "test_collector.py": '''from collector import collect


def test_independent_calls():
    first = collect("a")
    second = collect("b")
    assert first == ["a"]
    assert second == ["b"]
''',
        },
        solution_files={
            "collector.py": '''"""Item collector."""


def collect(item: str, bucket: list[str] | None = None) -> list[str]:
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
''',
        },
        checker=_check_pytest_only("test_collector.py"),
    ),
]

_TASKS_BY_ID = {t.id: t for t in TASKS}


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def setup_workspace(task: Task, path: Path) -> Path:
    """Materialize a task's workspace fixture under ``path``."""
    path = Path(path)
    for rel, content in task.workspace_files.items():
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return path


def _seed_stores(data_dir: Path, mode: str, extra_skills: list[Skill] | None = None) -> Stores | None:
    """Create fresh memory stores seeded with the catalog's past sessions."""
    if mode == "no-memory":
        return None
    stores = Stores(
        episodic=EpisodicStore(data_dir / "episodes.db"),
        semantic=SemanticStore(data_dir / "semantic.db", embedder=None),
        procedural=ProceduralDBStore(data_dir / "skills.db") if mode == "memory+skills" else None,
    )
    for task in TASKS:
        for episode in task.episodes:
            stores.episodic.add(episode)
        for fact in task.facts:
            asyncio.run(stores.semantic.add(fact))
        if stores.procedural is not None and task.skill is not None:
            stores.procedural.add(task.skill)
    if stores.procedural is not None and extra_skills:
        for skill in extra_skills:
            stores.procedural.add(skill)
    return stores


def _recall_context(task: Task, mode: str, stores: Stores | None) -> list[str]:
    """Recall memory relevant to the task through the real store search paths."""
    if stores is None or not task.memory_query:
        return []
    context: list[str] = []
    for ep in stores.episodic.search(PROJECT, task.memory_query, limit=20):
        context.append(
            f"Past episode '{ep.task}': root cause: {ep.root_cause}; fix: {ep.fix_pattern}"
        )
    facts = asyncio.run(stores.semantic.search(PROJECT, task.memory_query, 20))
    for fact in facts:
        context.append(f"Remembered fact: {fact.content}")
    if stores.procedural is not None:
        for skill in stores.procedural.search(PROJECT, task.memory_query, limit=20):
            if skill.verified:
                steps = "; ".join(skill.procedure)
                context.append(f"Verified skill '{skill.name}': {steps}")
    return context


def _solve(task: Task, workspace: Path, context: list[str]) -> bool:
    """Reference solver: apply the guided or naive file set. Returns True if guided."""
    ctx_text = "\n".join(context).lower()
    guided = bool(task.hint_key) and task.hint_key.lower() in ctx_text
    files = task.solution_files if guided else (task.naive_files or task.solution_files)
    for rel, content in files.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return guided


def _record_episode(stores: Stores, task: Task, mode: str, passed: bool) -> None:
    stores.episodic.add(
        Episode(
            session_id=f"taskbench-{mode}-{task.id}",
            task=f"taskbench: {task.title}",
            project=PROJECT,
            outcome="success" if passed else "error",
            tags=["taskbench", mode],
        )
    )


def run_task(
    task: Task,
    mode: str,
    stores: Stores | None,
    keep_workspaces: bool = False,
    work_root: Path | None = None,
) -> dict:
    """Run one task in one mode and return a JSON-serializable result."""
    start = time.time()
    if work_root is not None:
        workspace = Path(work_root) / f"{mode}-{task.id}"
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        workspace = Path(tempfile.mkdtemp(prefix=f"taskbench-{mode}-{task.id}-"))
    try:
        setup_workspace(task, workspace)
        context = _recall_context(task, mode, stores)
        guided = _solve(task, workspace, context)
        check = task.checker(workspace)
        if stores is not None:
            _record_episode(stores, task, mode, check.passed)
        return {
            "task_id": task.id,
            "title": task.title,
            "passed": check.passed,
            "details": check.details,
            "guided": guided,
            "recalled": len(context),
            "workspace": str(workspace),
            "duration_s": round(time.time() - start, 2),
        }
    finally:
        if not keep_workspaces:
            shutil.rmtree(workspace, ignore_errors=True)


def run_taskbench(
    modes: list[str] | tuple[str, ...] | None = None,
    keep_workspaces: bool = False,
    work_root: Path | None = None,
    extra_skills: list[Skill] | None = None,
) -> dict:
    """Run the full catalog in each mode and return pass rates per mode."""
    report: dict = {"modes": {}}
    for mode in modes or MODES:
        if mode not in MODES:
            raise ValueError(f"unknown mode: {mode}")
        data_dir = Path(tempfile.mkdtemp(prefix=f"acrux-taskbench-{mode}-"))
        try:
            stores = _seed_stores(data_dir, mode, extra_skills)
            results = [
                run_task(task, mode, stores, keep_workspaces, work_root) for task in TASKS
            ]
            passed = sum(1 for r in results if r["passed"])
            report["modes"][mode] = {
                "passed": passed,
                "total": len(results),
                "pass_rate": passed / len(results) if results else 0.0,
                "tasks": results,
            }
        finally:
            shutil.rmtree(data_dir, ignore_errors=True)
    return report
