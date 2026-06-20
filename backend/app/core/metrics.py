"""Prometheus 指标。

目标：用最小成本暴露任务执行的可观测信号（成功/失败率、时长分布），
便于定位"生成卡住/批量失败"类问题。指标基数受控：
- task_kind 为有限的任务类型；
- event 为有限的生命周期事件（started/succeeded/failed/cancelled）。
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

# 使用独立 registry，避免与第三方库默认指标互相干扰。
registry = CollectorRegistry()

task_events_total = Counter(
    "jellyfish_task_events_total",
    "任务生命周期事件计数",
    labelnames=("task_kind", "event"),
    registry=registry,
)

task_duration_seconds = Histogram(
    "jellyfish_task_duration_seconds",
    "任务从开始到终态的耗时（秒）",
    labelnames=("task_kind", "event"),
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600, 1800),
    registry=registry,
)

# 写入终态时长的事件集合。
_TERMINAL_EVENTS = {"succeeded", "failed", "cancelled"}


def record_task_event(task_kind: str, event: str, *, elapsed_ms: int | None = None) -> None:
    """记录一次任务事件；终态事件附带耗时直方图。"""
    task_events_total.labels(task_kind=task_kind, event=event).inc()
    if event in _TERMINAL_EVENTS and elapsed_ms is not None:
        task_duration_seconds.labels(task_kind=task_kind, event=event).observe(elapsed_ms / 1000.0)


def render_latest() -> bytes:
    """渲染 Prometheus 文本格式指标。"""
    return generate_latest(registry)
