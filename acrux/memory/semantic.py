"""Semantic memory store backed by SQLite with optional vector search.

The store is split into focused mixins that share a single SQLite
database per store (WAL enabled in ``_init_db``):

- ``acrux.memory.facts``: fact CRUD, confidence, decay, versioning,
  pending facts, metrics
- ``acrux.memory.graph``: relationships, trees, clusters, inheritance layers
- ``acrux.memory.artifacts``: tests, reviews, dependencies, file summaries,
  watcher state (plus chat pins and project system prompts)
- ``acrux.memory.health``: health checks and storage checksums

``SemanticStore`` is a thin facade composing them so existing callers
(``from acrux.memory.semantic import SemanticStore``) keep working.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from acrux.memory.artifacts import ArtifactsStoreMixin
from acrux.memory.facts import FactStoreMixin
from acrux.memory.graph import GraphStoreMixin
from acrux.memory.health import HealthStoreMixin

try:
    from acrux.vector_sqlite import SqliteVecIndex as VectorIndex
except Exception:  # pragma: no cover - fallback when sqlite-vec is unavailable
    from acrux.vector_index import VectorIndex

if TYPE_CHECKING:
    from acrux.embeddings import OllamaEmbedder

# Schema version, bumped by future migrations (stored in PRAGMA user_version).
SCHEMA_VERSION = 1


class SemanticStore(
    FactStoreMixin,
    GraphStoreMixin,
    ArtifactsStoreMixin,
    HealthStoreMixin,
):
    def __init__(
        self,
        db_path: Path,
        embedder: "OllamaEmbedder | None" = None,
        vector_index: VectorIndex | None = None,
    ):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder
        self.dim = getattr(embedder, "dim", None)
        self._init_db()
        if vector_index is None:
            index_path = self.db_path.with_suffix(self.db_path.suffix + ".vec")
            enabled = self.dim is not None and self.dim > 0
            vector_index = VectorIndex.load_or_init(index_path, self.dim, enabled=enabled)
        self.vector_index = vector_index
        self._rebuild_vector_index()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection to this store's single SQLite database.

        WAL mode is persistent at the database level (enabled in
        ``_init_db``), so it applies to every connection returned here.
        """
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    content TEXT,
                    source TEXT,
                    tags TEXT,
                    timestamp TEXT,
                    recall_count INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0,
                    verified_count INTEGER DEFAULT 0,
                    contradicted_count INTEGER DEFAULT 0,
                    stale INTEGER DEFAULT 0,
                    git_info TEXT,
                    parent_id INTEGER NULL,
                    version_group_id INTEGER NULL,
                    is_current INTEGER DEFAULT 1,
                    fact_type TEXT DEFAULT 'positive',
                    cluster_id INTEGER NULL,
                    inheritance_mode TEXT DEFAULT 'none',
                    decay_score REAL DEFAULT 0,
                    last_recalled_at TEXT NULL,
                    checksum TEXT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                    content,
                    content='facts',
                    content_rowid='id'
                )
                """
            )
            self._migrate_columns(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fact_embeddings (
                    fact_id INTEGER PRIMARY KEY,
                    content_hash TEXT,
                    vector TEXT,
                    FOREIGN KEY (fact_id) REFERENCES facts(id) ON DELETE CASCADE
                )
                """
            )
            # New schema tables
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fact_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact_id INTEGER NOT NULL,
                    content TEXT,
                    tags TEXT,
                    edited_at TEXT,
                    edited_by TEXT,
                    FOREIGN KEY (fact_id) REFERENCES facts(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clusters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    label TEXT NULL,
                    centroid_vector TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_layers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    base_project TEXT NOT NULL,
                    layer_order INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fact_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    source_fact_id INTEGER NOT NULL,
                    target_fact_id INTEGER NOT NULL,
                    relation_type TEXT DEFAULT 'related',
                    strength REAL DEFAULT 0.5
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    source_ref TEXT,
                    source_type TEXT,
                    target_ref TEXT,
                    target_type TEXT,
                    dependency_type TEXT,
                    detected_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS code_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    file_path TEXT,
                    line_range TEXT,
                    comment TEXT,
                    resolution TEXT NULL,
                    reviewer TEXT,
                    timestamp TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    test_name TEXT,
                    file_path TEXT NULL,
                    passed INTEGER,
                    output TEXT,
                    duration_ms INTEGER,
                    root_cause TEXT NULL,
                    run_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    path TEXT,
                    summary TEXT,
                    content_hash TEXT,
                    last_modified TEXT,
                    indexed_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_watcher_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    path TEXT,
                    last_seen_mtime TEXT,
                    last_seen_hash TEXT,
                    last_diff TEXT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NULL,
                    check_type TEXT,
                    severity TEXT,
                    message TEXT,
                    created_at TEXT,
                    resolved_at TEXT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_pins (
                    chat_id TEXT,
                    message_id TEXT,
                    created_at TEXT,
                    PRIMARY KEY (chat_id, message_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_system_prompts (
                    project TEXT PRIMARY KEY,
                    prompt_text TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS storage_checksums (
                    file_path TEXT PRIMARY KEY,
                    checksum TEXT,
                    checked_at TEXT
                )
                """
            )
            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_project ON facts(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_tags ON facts(tags)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_timestamp ON facts(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fact_stale ON facts(stale)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_fact_hash ON fact_embeddings(content_hash)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_parent ON facts(parent_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_facts_version_group ON facts(version_group_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_cluster ON facts(cluster_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_decay ON facts(decay_score)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_fact_versions_fact ON fact_versions(fact_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_clusters_project ON clusters(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_layers_project ON project_layers(project)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rel_source ON fact_relationships(source_fact_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rel_target ON fact_relationships(target_fact_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_project ON dependencies(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_source ON dependencies(source_ref)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_target ON dependencies(target_ref)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_project ON code_reviews(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_file ON code_reviews(file_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tests_project ON test_results(project)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_summaries_project ON file_summaries(project)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_path ON file_summaries(path)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_watcher_project ON workspace_watcher_state(project)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_health_project ON health_checks(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_health_type ON health_checks(check_type)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_health_resolved ON health_checks(resolved_at)"
            )
            # Keep PRAGMA user_version for future migrations: only raise it,
            # never downgrade a database already migrated to a newer version.
            current_version = conn.execute("PRAGMA user_version").fetchone()[0]
            if current_version < SCHEMA_VERSION:
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        columns = [r[1] for r in conn.execute("PRAGMA table_info(facts)").fetchall()]
        migrations = {
            "recall_count": "ALTER TABLE facts ADD COLUMN recall_count INTEGER DEFAULT 0",
            "confidence": "ALTER TABLE facts ADD COLUMN confidence REAL DEFAULT 0",
            "verified_count": "ALTER TABLE facts ADD COLUMN verified_count INTEGER DEFAULT 0",
            "contradicted_count": "ALTER TABLE facts ADD COLUMN contradicted_count INTEGER DEFAULT 0",
            "stale": "ALTER TABLE facts ADD COLUMN stale INTEGER DEFAULT 0",
            "git_info": "ALTER TABLE facts ADD COLUMN git_info TEXT",
            "parent_id": "ALTER TABLE facts ADD COLUMN parent_id INTEGER NULL",
            "version_group_id": "ALTER TABLE facts ADD COLUMN version_group_id INTEGER NULL",
            "is_current": "ALTER TABLE facts ADD COLUMN is_current INTEGER DEFAULT 1",
            "fact_type": "ALTER TABLE facts ADD COLUMN fact_type TEXT DEFAULT 'positive'",
            "cluster_id": "ALTER TABLE facts ADD COLUMN cluster_id INTEGER NULL",
            "inheritance_mode": "ALTER TABLE facts ADD COLUMN inheritance_mode TEXT DEFAULT 'none'",
            "decay_score": "ALTER TABLE facts ADD COLUMN decay_score REAL DEFAULT 0",
            "last_recalled_at": "ALTER TABLE facts ADD COLUMN last_recalled_at TEXT NULL",
            "checksum": "ALTER TABLE facts ADD COLUMN checksum TEXT NULL",
        }
        for column, sql in migrations.items():
            if column not in columns:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass

        columns_emb = [r[1] for r in conn.execute("PRAGMA table_info(fact_embeddings)").fetchall()]
        if "content_hash" not in columns_emb:
            try:
                conn.execute("ALTER TABLE fact_embeddings ADD COLUMN content_hash TEXT")
            except sqlite3.OperationalError:
                pass

    def _rebuild_vector_index(self) -> None:
        """Load existing embeddings into the in-memory vector index."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT fact_id, vector FROM fact_embeddings WHERE vector IS NOT NULL"
            ).fetchall()
        for row in rows:
            try:
                vector = json.loads(row["vector"])
                self.vector_index.load_vector(row["fact_id"], vector)
            except Exception:
                continue
        if not self.vector_index.loaded_from_disk:
            self.vector_index.rebuild_hnsw()
