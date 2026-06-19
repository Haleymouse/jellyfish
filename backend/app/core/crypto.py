"""敏感字段加密工具。

设计目标与取舍：
- 为数据库中的敏感字段（如供应商 api_key / api_secret）提供"静态加密"能力，
  避免明文落库；
- 完全向后兼容：未配置加密密钥时行为与历史一致（明文存取），
  已存在的明文值也能继续读取（解密时按非密文原样返回）；
- 通过加密前缀 `enc::` 区分密文与历史明文，便于平滑迁移：
  配置密钥后，旧明文值在下一次写入时自动转为密文。

注意：
- `FIELD_ENCRYPTION_KEY` 可使用任意字符串，内部会派生为 Fernet 所需的 32 字节密钥；
- 一旦用于生产数据，请勿更换该密钥，否则历史密文将无法解密。
"""

from __future__ import annotations

import base64
import hashlib

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.config import settings

# 密文统一前缀；用于区分"已加密值"与"历史明文值"。
ENC_PREFIX = "enc::"


def _build_fernet():
    """根据配置的密钥构建 Fernet 实例；未配置时返回 None（表示不启用加密）。"""
    raw_key = (settings.field_encryption_key or "").strip()
    if not raw_key:
        return None
    try:
        from cryptography.fernet import Fernet
    except ImportError:  # pragma: no cover - 依赖缺失时退回明文，保证可用性
        return None
    # 将任意长度的人类可读密钥派生为 Fernet 要求的 urlsafe base64 32 字节密钥。
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str | None) -> str | None:
    """加密敏感字符串。

    - 未配置密钥、空串或已是密文时，原样返回（幂等、向后兼容）。
    - 返回值带 `enc::` 前缀，便于读取侧识别。
    """
    if value is None or value == "":
        return value
    if value.startswith(ENC_PREFIX):
        return value
    fernet = _build_fernet()
    if fernet is None:
        return value
    token = fernet.encrypt(value.encode("utf-8")).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_secret(value: str | None) -> str | None:
    """解密敏感字符串。

    - 非密文（无 `enc::` 前缀）的历史明文原样返回。
    - 解密失败（如密钥变更）时退回原值，避免业务直接崩溃。
    """
    if value is None or not value.startswith(ENC_PREFIX):
        return value
    fernet = _build_fernet()
    if fernet is None:
        return value
    try:
        from cryptography.fernet import InvalidToken

        return fernet.decrypt(value[len(ENC_PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):  # pragma: no cover - 密钥不匹配等异常
        return value


class EncryptedString(TypeDecorator):
    """透明加密的字符串列类型。

    在写入数据库前自动加密、读取后自动解密，使上层业务无需感知加密细节。
    底层仍为 String，因此不改变表结构（仅存储内容由明文变为密文）。
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:  # noqa: ANN001
        return encrypt_secret(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:  # noqa: ANN001
        return decrypt_secret(value)
