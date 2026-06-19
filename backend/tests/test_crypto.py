"""敏感字段加密工具与可选鉴权中间件测试。"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

import app.config as app_config
import app.core.crypto as crypto


def _reload_with_key(monkeypatch: pytest.MonkeyPatch, key: str | None) -> None:
    """以指定加密密钥重载配置，使 crypto 读取到的 settings 同步更新。"""
    monkeypatch.setattr(app_config.settings, "field_encryption_key", key, raising=False)


def test_encrypt_roundtrip_when_key_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_with_key(monkeypatch, "unit-test-key")
    token = crypto.encrypt_secret("sk-secret-123")
    assert token.startswith(crypto.ENC_PREFIX)
    assert token != "sk-secret-123"
    assert crypto.decrypt_secret(token) == "sk-secret-123"


def test_encrypt_is_idempotent_on_ciphertext(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_with_key(monkeypatch, "unit-test-key")
    token = crypto.encrypt_secret("sk-secret-123")
    assert crypto.encrypt_secret(token) == token


def test_empty_and_none_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    _reload_with_key(monkeypatch, "unit-test-key")
    assert crypto.encrypt_secret("") == ""
    assert crypto.encrypt_secret(None) is None
    assert crypto.decrypt_secret(None) is None


def test_legacy_plaintext_is_readable(monkeypatch: pytest.MonkeyPatch) -> None:
    """历史明文（无 enc:: 前缀）应原样返回，保证平滑迁移。"""
    _reload_with_key(monkeypatch, "unit-test-key")
    assert crypto.decrypt_secret("legacy-plaintext") == "legacy-plaintext"


def test_no_key_keeps_plaintext(monkeypatch: pytest.MonkeyPatch) -> None:
    """未配置密钥时行为与历史一致：明文存取。"""
    _reload_with_key(monkeypatch, None)
    assert crypto.encrypt_secret("sk-secret-123") == "sk-secret-123"
    assert crypto.decrypt_secret("sk-secret-123") == "sk-secret-123"


def test_auth_guard_enforced_when_token_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """配置 api_auth_token 后，受保护接口需携带匹配令牌。"""
    import app.main as main

    monkeypatch.setattr(main.settings, "api_auth_token", "topsecret", raising=False)
    # 放行后的接口会触达真实 DB（测试环境无表），令 500 以响应形式返回，
    # 这样仍可断言"鉴权是否拦截"（401 vs 非 401）。
    client = TestClient(main.app, raise_server_exceptions=False)

    # 健康检查始终放行
    assert client.get("/health").status_code == 200

    # 受保护接口：缺少令牌 -> 401
    missing = client.get("/api/v1/llm/providers")
    assert missing.status_code == 401
    assert missing.json()["code"] == 401

    # 受保护接口：携带正确令牌 -> 放行（不再是 401）
    with_bearer = client.get(
        "/api/v1/llm/providers", headers={"Authorization": "Bearer topsecret"}
    )
    assert with_bearer.status_code != 401

    with_api_key = client.get("/api/v1/llm/providers", headers={"X-API-Key": "topsecret"})
    assert with_api_key.status_code != 401


def test_auth_guard_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """未配置令牌时不启用鉴权，保持向后兼容。"""
    import app.main as main

    monkeypatch.setattr(main.settings, "api_auth_token", None, raising=False)
    client = TestClient(main.app, raise_server_exceptions=False)
    assert client.get("/api/v1/llm/providers").status_code != 401
