"""Alembic 运行环境。

要点：
- 连接信息从应用配置(settings)读取，并复用 db_sync 的同步驱动转换，
  迁移始终走同步引擎(pymysql / sqlite)，避免在迁移期引入 async 复杂度；
- target_metadata 绑定到 Base.metadata，确保导入全部模型后可用 autogenerate；
- 连接池参数复用应用侧设置，保持一致。
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.config import settings
from app.core.db import Base
from app.core.db_pool import engine_pool_kwargs
from app.core.db_sync import _to_sync_database_url

# 导入所有模型，使其注册到 Base.metadata（autogenerate 依赖）。
import app.models.llm  # noqa: F401,E402
import app.models.studio  # noqa: F401,E402
import app.models.task  # noqa: F401,E402
import app.models.task_links  # noqa: F401,E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_url() -> str:
    return _to_sync_database_url(settings.database_url)


def run_migrations_offline() -> None:
    """离线模式：仅生成 SQL，不连接数据库。"""
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：建立同步连接并执行迁移。"""
    sync_url = _sync_url()
    engine = create_engine(sync_url, future=True, **engine_pool_kwargs(sync_url))
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
