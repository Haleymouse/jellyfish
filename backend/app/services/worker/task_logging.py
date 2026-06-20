"""统一任务事件日志。"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


def log_task_event(task_kind: str, task_id: str, event: str, **fields: Any) -> None:
    extras = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    suffix = f" {extras}" if extras else ""
    logger.info("task_event kind=%s task_id=%s event=%s%s", task_kind, task_id, event, suffix)

    # 同步上报 Prometheus 指标（失败不影响主流程）。
    try:
        from app.core.metrics import record_task_event

        elapsed = fields.get("elapsed_ms")
        record_task_event(
            task_kind,
            event,
            elapsed_ms=int(elapsed) if elapsed is not None else None,
        )
    except Exception:  # noqa: BLE001 - 指标上报不应阻断任务
        logger.debug("failed to record task metric", exc_info=True)


def log_task_failure(task_kind: str, task_id: str, error: str) -> None:
    logger.exception("task_event kind=%s task_id=%s event=failed error=%s", task_kind, task_id, error)
