import logging

import pytest

from acrux.config import AcruxConfig
from acrux.daemon import AcruxDaemon
from acrux.memory.journal import IncompleteBatchError, MutationBatch, MutationJournal
from acrux.memory.locks import ProjectLockError, project_write_lock


def test_before_image_is_durable_before_data_mutation(tmp_path):
    journal = MutationJournal(tmp_path)
    batch_id = journal.begin("test")
    sequence = journal.record_before(
        batch_id,
        tmp_path / "semantic.db",
        "facts",
        "id",
        42,
        {"id": 42, "content": "before"},
    )

    incomplete = journal.incomplete()
    assert len(incomplete) == 1
    assert incomplete[0].id == batch_id
    assert incomplete[0].last_sequence == 1

    journal.record_after(sequence, {"id": 42, "content": "after"})
    journal.complete(batch_id)

    assert journal.incomplete() == []
    assert journal.latest().id == batch_id
    assert journal.latest().completed is True


def test_incomplete_batch_warning_and_lock_exclusion(tmp_path):
    journal = MutationJournal(tmp_path)
    with pytest.raises(RuntimeError, match="simulated crash"):
        with MutationBatch(tmp_path, "reflection") as batch:
            journal.record_before(
                batch.id,
                tmp_path / "episodes.db",
                "episodes",
                "session_id",
                "episode-1",
                None,
            )
            raise RuntimeError("simulated crash")

    incomplete = journal.incomplete()
    assert len(incomplete) == 1
    with pytest.raises(IncompleteBatchError) as error:
        with MutationBatch(tmp_path, "next-reflection"):
            pass
    assert f"acrux undo {incomplete[0].id} --project {tmp_path.name}" in str(error.value)

    first_lock = project_write_lock(tmp_path)
    first_lock.__enter__()
    try:
        second_lock = project_write_lock(tmp_path)
        with pytest.raises(ProjectLockError):
            second_lock.__enter__()
    finally:
        first_lock.__exit__(None, None, None)

    with project_write_lock(tmp_path):
        pass


def test_daemon_startup_warns_with_recovery_command(tmp_path, caplog):
    project_dir = tmp_path / "projects" / "demo"
    journal = MutationJournal(project_dir)
    batch_id = journal.begin("reflection")
    journal.record_before(
        batch_id,
        project_dir / "episodes.db",
        "episodes",
        "session_id",
        "episode-1",
        None,
    )
    daemon = AcruxDaemon(AcruxConfig(data_dir=tmp_path))

    with caplog.at_level(logging.WARNING, logger="acrux"):
        daemon._warn_incomplete_batches()

    assert batch_id in caplog.text
    assert f"acrux undo {batch_id} --project demo" in caplog.text
