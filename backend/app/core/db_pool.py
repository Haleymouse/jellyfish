"""数据库连接池参数构建（同步/异步引擎共用）。

设计：
- SQLite（含测试用 in-memory / 文件库）不使用 QueuePool 的大小相关参数，
  仅启用 pre_ping，避免传入不适用的参数导致报错或行为异常；
- 其余后端（MySQL / PostgreSQL）应用完整池化参数，提升生产稳定性与并发表现。
"""

from __future__ import annotations

from typing import Any

from app.config import settings


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def engine_pool_kwargs(url: str) -> dict[str, Any]:
    """根据数据库 URL 返回适配的连接池参数。

    参数 url 可以是 async 或 sync 形式（如 mysql+aiomysql / mysql+pymysql），
    仅依据方言前缀判断是否为 SQLite。
    """
    if _is_sqlite(url):
        # SQLite 池模型不同，仅保留 pre_ping（对探活无害）。
        return {"pool_pre_ping": settings.db_pool_pre_ping}
    return {
        "pool_pre_ping": settings.db_pool_pre_ping,
        "pool_recycle": settings.db_pool_recycle,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
    }
