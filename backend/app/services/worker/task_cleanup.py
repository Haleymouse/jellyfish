"""生成任务表的保留期清理。

目的：
- `generation_tasks` 的 payload / result 为 JSON 大字段，终态记录只增不减会拖慢
  轮询查询并持续涨库；
- 定期清理超过保留期的终态任务，控制表规模。

安全约束：
- 仅清理 succeeded / failed / cancelled 这类终态任务；
- 保留被 `accepted` 关联引用的任务（代表已采用的产物，需保留溯源）；
- 显式删除被清理任务的非 accepted 关联行，兼容未开启外键级联的后端（如 SQLite）。
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.task import GenerationTask, GenerationTaskStatus
from app.models.task_links import GenerationTaskLink, GenerationTaskLinkStatus

_TERMINAL_STATUSES = (
    GenerationTaskStatus.succeeded,
    GenerationTaskStatus.failed,
    GenerationTaskStatus.cancelled,
)


def cleanup_stale_generation_tasks(
    db: Session,
    *,
    retention_days: int,
    now: datetime | None = None,
    batch_limit: int = 1000,
) -> int:
    """清理超过保留期的终态生成任务，返回删除的任务数。

    参数：
    - retention_days：保留天数；以 finished_at（缺失时回退 updated_at）为基准；
    - now：当前时间（便于测试注入）；
    - batch_limit：单次最多删除的任务数，避免一次删除过多造成长事务。
    """
    if retention_days <= 0:
        return 0

    reference_time = now or datetime.utcnow()
    cutoff = reference_time - timedelta(days=retention_days)

    accepted_task_ids = select(GenerationTaskLink.task_id).where(
        GenerationTaskLink.status == GenerationTaskLinkStatus.accepted
    )

    last_activity = func.coalesce(GenerationTask.finished_at, GenerationTask.updated_at)
    stale_ids_stmt = (
        select(GenerationTask.id)
        .where(
            GenerationTask.status.in_(_TERMINAL_STATUSES),
            last_activity < cutoff,
            GenerationTask.id.notin_(accepted_task_ids),
        )
        .limit(batch_limit)
    )
    stale_ids = [row[0] for row in db.execute(stale_ids_stmt).all()]
    if not stale_ids:
        return 0

    # 被清理任务此时只可能带有非 accepted 关联，显式删除以兼容无级联的后端。
    db.execute(delete(GenerationTaskLink).where(GenerationTaskLink.task_id.in_(stale_ids)))
    db.execute(delete(GenerationTask).where(GenerationTask.id.in_(stale_ids)))
    db.commit()
    return len(stale_ids)
