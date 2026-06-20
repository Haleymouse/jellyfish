---
title: "数据库迁移（Alembic）"
weight: 8
description: "使用 Alembic 管理 schema 演进，告别手写 SQL 的漂移风险。"
---

后端已接入 **Alembic** 作为 schema 演进工具。配置位于 `backend/alembic.ini` 与
`backend/alembic/`，连接信息从应用 `settings` 读取并自动转为同步驱动，无需在
`alembic.ini` 里硬编码数据库地址。

## 适用范围

- **新增/修改表结构**：统一通过 Alembic 迁移完成，可 `--autogenerate` 对比模型生成。
- **种子数据与历史 SQL**：`backend/sql/*.sql` 仍负责提示词模板等**种子数据**导入，
  这些文件是幂等的（带 `INSERT IGNORE` 与 `information_schema` 守卫），继续保留。

## 基线

`0001_baseline` 迁移以当前 ORM 模型 metadata 创建全部表，作为迁移起点。

- **全新数据库**：
  ```bash
  cd backend
  uv run alembic upgrade head
  ```
- **既有数据库**（此前用 `init_db.py` + `sql/*.sql` 初始化）：标记基线为已应用，
  不重复建表：
  ```bash
  cd backend
  uv run alembic stamp 0001_baseline
  ```

## 日常变更流程

1. 修改 `app/models/` 下的模型。
2. 自动生成迁移：
   ```bash
   cd backend
   uv run alembic revision --autogenerate -m "add xxx column"
   ```
3. **审查生成的迁移文件**（autogenerate 不是万能的，注意类型变更、索引、默认值）。
4. 应用：
   ```bash
   uv run alembic upgrade head
   ```
5. 如涉及接口/类型变更，按既有约定同步 OpenAPI 与前端 generated types。

## 离线生成 SQL

需要把迁移交给 DBA 审阅或在受限环境执行时：

```bash
cd backend
uv run alembic upgrade head --sql > migration.sql
```

## 与测试的关系

测试使用 SQLite，通过 `Base.metadata.create_all` 直接建表，不经过 Alembic，
因此迁移文件不影响现有单测。
