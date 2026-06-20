"""baseline schema

把当前 ORM 模型定义的全部表作为迁移基线。

适配两种场景：
- 全新数据库：`alembic upgrade head` 依据当前 metadata 创建所有表；
- 既有数据库（此前用 create_all + sql/*.sql 初始化）：执行
  `alembic stamp 0001_baseline` 标记基线为已应用，后续变更再走 autogenerate。

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-20
"""

from typing import Sequence, Union

from alembic import op

from app.core.db import Base

# 导入模型，确保 metadata 完整。
import app.models.llm  # noqa: F401
import app.models.studio  # noqa: F401
import app.models.task  # noqa: F401
import app.models.task_links  # noqa: F401

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """按当前模型 metadata 创建全部表。"""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """删除全部表（基线回滚）。"""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
