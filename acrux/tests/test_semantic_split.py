"""Tests for the W6 SemanticStore split into mixin modules."""

import sqlite3
from pathlib import Path

from acrux.memory.artifacts import ArtifactsStoreMixin
from acrux.memory.facts import FactStoreMixin
from acrux.memory.graph import GraphStoreMixin
from acrux.memory.health import HealthStoreMixin
from acrux.memory.semantic import SCHEMA_VERSION, SemanticStore


def test_facade_composes_all_mixins():
    assert issubclass(SemanticStore, FactStoreMixin)
    assert issubclass(SemanticStore, GraphStoreMixin)
    assert issubclass(SemanticStore, ArtifactsStoreMixin)
    assert issubclass(SemanticStore, HealthStoreMixin)


def test_methods_live_in_expected_modules():
    # facts.py
    assert SemanticStore.add.__module__ == "acrux.memory.facts"
    assert SemanticStore.update_fact.__module__ == "acrux.memory.facts"
    assert SemanticStore.record_verification.__module__ == "acrux.memory.facts"
    assert SemanticStore.compute_decay_scores.__module__ == "acrux.memory.facts"
    assert SemanticStore.add_pending_fact.__module__ == "acrux.memory.facts"
    assert SemanticStore.record_metric.__module__ == "acrux.memory.facts"
    # graph.py
    assert SemanticStore.link_facts.__module__ == "acrux.memory.graph"
    assert SemanticStore.get_tree.__module__ == "acrux.memory.graph"
    assert SemanticStore.cluster_facts.__module__ == "acrux.memory.graph"
    assert SemanticStore.add_project_layer.__module__ == "acrux.memory.graph"
    # artifacts.py
    assert SemanticStore.add_test_result.__module__ == "acrux.memory.artifacts"
    assert SemanticStore.add_review.__module__ == "acrux.memory.artifacts"
    assert SemanticStore.add_dependencies.__module__ == "acrux.memory.artifacts"
    assert SemanticStore.add_file_summary.__module__ == "acrux.memory.artifacts"
    assert SemanticStore.set_watcher_state.__module__ == "acrux.memory.artifacts"
    # health.py
    assert SemanticStore.add_health_check.__module__ == "acrux.memory.health"
    assert SemanticStore.set_storage_checksum.__module__ == "acrux.memory.health"
    # facade keeps init/schema/vector glue
    assert SemanticStore._init_db.__module__ == "acrux.memory.semantic"
    assert SemanticStore._connect.__module__ == "acrux.memory.semantic"


def test_single_database_wal_and_user_version(tmp_path: Path):
    store = SemanticStore(tmp_path / "semantic.db")
    assert store.db_path == tmp_path / "semantic.db"
    with store._connect() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    # Reopening an existing DB must not downgrade user_version.
    with sqlite3.connect(store.db_path) as conn:
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    SemanticStore(tmp_path / "semantic.db")
    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION + 1


def test_mixins_share_one_database(tmp_path: Path):
    """Writes through one mixin are visible through the others (same DB file)."""
    store = SemanticStore(tmp_path / "semantic.db")
    store.add_health_check(
        {"project": "p", "check_type": "split", "severity": "low", "message": "ok"}
    )
    store.set_watcher_state("p", "x.py", "mtime", "hash")
    with store._connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"facts", "health_checks", "workspace_watcher_state", "clusters"} <= tables
    assert len(store.get_health_checks(project="p")) == 1
    assert len(store.get_watcher_state("p")) == 1
