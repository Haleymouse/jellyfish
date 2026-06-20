"""维护类周期任务（由 Celery beat 调度）。"""

from __future__ import annotations

import logging

from app.config import settings
from app.core.celery_app import celery_app
from app.core.db_sync import sync_session_maker
from app.services.worker.task_cleanup import cleanup_stale_generation_tasks

logger = logging.getLogger(__name__)


@celery_app.task(name="task.cleanup_generation_tasks")
def cleanup_generation_tasks() -> int:
    """周期清理超过保留期的终态生成任务，返回删除数量。"""
    with sync_session_maker() as db:
        deleted = cleanup_stale_generation_tasks(
            db,
            retention_days=settings.task_cleanup_retention_days,
        )
    if deleted:
        logger.info("cleanup_generation_tasks removed %d stale tasks", deleted)
    return deleted
