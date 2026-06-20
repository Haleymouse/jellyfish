"""生成任务保留期清理测试。"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import Base
from app.models.task import GenerationTask, GenerationTaskStatus
from app.models.task_links import GenerationTaskLink, GenerationTaskLinkStatus
from app.services.worker.task_cleanup import cleanup_stale_generation_tasks


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = maker()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_task(
    db: Session,
    *,
    task_id: str,
    status: GenerationTaskStatus,
    finished_at: datetime | None,
) -> GenerationTask:
    task = GenerationTask(
        id=task_id,
        mode="async_polling",
        task_kind="video_generation",
        status=status,
        progress=100,
        payload={"run_args": {}},
        result={"url": "x"},
        error="",
        finished_at=finished_at,
    )
    db.add(task)
    db.commit()
    return task


def test_cleanup_removes_old_terminal_tasks(db: Session) -> None:
    now = datetime(2026, 6, 20, 12, 0, 0)
    _make_task(db, task_id="old", status=GenerationTaskStatus.succeeded, finished_at=now - timedelta(days=30))
    _make_task(db, task_id="recent", status=GenerationTaskStatus.succeeded, finished_at=now - timedelta(days=1))

    removed = cleanup_stale_generation_tasks(db, retention_days=7, now=now)

    assert removed == 1
    assert db.get(GenerationTask, "old") is None
    assert db.get(GenerationTask, "recent") is not None


def test_cleanup_keeps_non_terminal_tasks(db: Session) -> None:
    now = datetime(2026, 6, 20, 12, 0, 0)
    _make_task(db, task_id="running", status=GenerationTaskStatus.running, finished_at=None)

    removed = cleanup_stale_generation_tasks(db, retention_days=7, now=now)

    assert removed == 0
    assert db.get(GenerationTask, "running") is not None


def test_cleanup_preserves_tasks_with_accepted_links(db: Session) -> None:
    now = datetime(2026, 6, 20, 12, 0, 0)
    _make_task(db, task_id="adopted", status=GenerationTaskStatus.succeeded, finished_at=now - timedelta(days=30))
    db.add(
        GenerationTaskLink(
            task_id="adopted",
            resource_type="video",
            relation_type="shot",
            relation_entity_id="shot-1",
            status=GenerationTaskLinkStatus.accepted,
        )
    )
    db.commit()

    removed = cleanup_stale_generation_tasks(db, retention_days=7, now=now)

    assert removed == 0
    assert db.get(GenerationTask, "adopted") is not None


def test_cleanup_removes_task_and_its_non_accepted_links(db: Session) -> None:
    now = datetime(2026, 6, 20, 12, 0, 0)
    _make_task(db, task_id="rejected-old", status=GenerationTaskStatus.failed, finished_at=now - timedelta(days=30))
    db.add(
        GenerationTaskLink(
            task_id="rejected-old",
            resource_type="image",
            relation_type="prop",
            relation_entity_id="prop-1",
            status=GenerationTaskLinkStatus.rejected,
        )
    )
    db.commit()

    removed = cleanup_stale_generation_tasks(db, retention_days=7, now=now)

    assert removed == 1
    assert db.get(GenerationTask, "rejected-old") is None
    assert db.query(GenerationTaskLink).filter_by(task_id="rejected-old").count() == 0
