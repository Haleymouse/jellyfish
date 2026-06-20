"""Prometheus 指标与 /metrics 端点测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.metrics import record_task_event, render_latest
from app.main import app
from app.services.worker.task_logging import log_task_event


def test_record_task_event_increments_counter() -> None:
    record_task_event("video_generation", "succeeded", elapsed_ms=1500)
    output = render_latest().decode("utf-8")
    assert "jellyfish_task_events_total" in output
    assert 'task_kind="video_generation"' in output
    assert "jellyfish_task_duration_seconds" in output


def test_log_task_event_reports_metric() -> None:
    log_task_event("image_generation", "task-1", "failed", elapsed_ms=2000, error="boom")
    output = render_latest().decode("utf-8")
    assert 'event="failed"' in output
    assert 'task_kind="image_generation"' in output


def test_metrics_endpoint_serves_prometheus_text() -> None:
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "jellyfish_task_events_total" in resp.text
