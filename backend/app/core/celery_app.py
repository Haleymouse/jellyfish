"""Celery 应用实例。

最小落地原则：
- 仅把 Celery 当作执行层与 broker 客户端；
- 任务状态/结果真相仍然回写 GenerationTask；
- 第一阶段不依赖 Celery result backend。
"""

from celery import Celery
from celery.signals import worker_process_init

from app.config import settings
from app.core.db import reset_db_runtime


celery_app = Celery(
    "jellyfish",
    broker=settings.celery_broker_url,
    include=["app.tasks.execute_task", "app.tasks.maintenance"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    timezone="Asia/Shanghai",
    enable_utc=False,
    # 健壮性：长耗时生成任务公平分发 + 崩溃可重投 + 周期回收子进程
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    task_acks_late=settings.celery_task_acks_late,
    task_reject_on_worker_lost=settings.celery_task_acks_late,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    # broker 重连（兼容 Celery 6 弃用项）
    broker_connection_retry_on_startup=True,
)

# 兜底超时（None 表示不额外限制，沿用任务自身的 timeout_seconds）。
if settings.celery_task_time_limit:
    celery_app.conf.task_time_limit = settings.celery_task_time_limit
if settings.celery_task_soft_time_limit:
    celery_app.conf.task_soft_time_limit = settings.celery_task_soft_time_limit

# 对外部生成 API 的粗粒度全局节流：仅在配置后生效，保护收费/限速的供应商接口。
if settings.celery_task_rate_limit:
    celery_app.conf.task_annotations = {
        "task.execute": {"rate_limit": settings.celery_task_rate_limit},
    }

# 生成任务表保留期清理：注册 beat 周期任务（需以 beat 调度，如 worker -B）。
if settings.task_cleanup_enabled:
    celery_app.conf.beat_schedule = {
        "cleanup-generation-tasks": {
            "task": "task.cleanup_generation_tasks",
            "schedule": float(settings.task_cleanup_interval_seconds),
        },
    }


@worker_process_init.connect
def _reset_async_db_runtime(**_: object) -> None:
    """Celery prefork 子进程启动后，重建 async DB 运行时。"""

    reset_db_runtime()
