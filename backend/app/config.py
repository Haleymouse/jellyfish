"""应用配置，从环境变量加载。"""

import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Jellyfish API"
    debug: bool = False

    # API
    api_v1_prefix: str = "/api/v1"

    # 访问鉴权（可选）：
    # - 为空时不启用鉴权，行为与历史一致（向后兼容）；
    # - 配置后，所有 `/api/v1` 接口需携带匹配的令牌，
    #   通过 `Authorization: Bearer <token>` 或 `X-API-Key: <token>` 传入。
    api_auth_token: str | None = None

    # 敏感字段静态加密密钥（可选）：
    # - 为空时供应商 api_key / api_secret 仍按明文存储（向后兼容）；
    # - 配置后，新写入的敏感字段将加密落库，旧明文在下次写入时自动转为密文；
    # - 一旦用于生产数据请勿更换，否则历史密文无法解密。
    field_encryption_key: str | None = None

    # Database
    database_url: str = "sqlite+aiosqlite:///./jellyfish.db"

    # 连接池调优（仅对非 SQLite 后端生效，如 MySQL/PostgreSQL）：
    # - pre_ping 在取用连接前做一次探活，规避 "MySQL server has gone away"；
    # - recycle 回收过期连接，需小于数据库侧 wait_timeout；
    # - size / max_overflow / timeout 控制并发与排队上限。
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = 1800
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Redis / Celery Broker
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    celery_broker_url: str | None = None

    # Celery 健壮性与生成任务保护：
    # - prefetch=1 + acks_late 适配长耗时生成任务，worker 崩溃可重投，避免吞任务；
    # - max_tasks_per_child 周期性回收子进程，规避内存累积；
    # - time_limit / soft_time_limit 为兜底超时（None 表示不额外限制，沿用任务自身超时）；
    # - task_rate_limit 是对外部生成 API 的粗粒度全局节流（如 "60/m"），
    #   留空表示不限制，避免批量提交瞬间打爆收费/限速的供应商接口。
    celery_worker_prefetch_multiplier: int = 1
    celery_task_acks_late: bool = True
    celery_worker_max_tasks_per_child: int = 100
    celery_task_time_limit: int | None = None
    celery_task_soft_time_limit: int | None = None
    celery_task_rate_limit: str | None = None

    # 生成任务表保留期清理（Celery beat 调度）：
    # - enabled 为 False 时不注册周期任务；
    # - retention_days 为保留天数，仅清理超期的终态任务（保留已采用关联的任务）；
    # - interval_seconds 为清理间隔（默认每天）。
    task_cleanup_enabled: bool = True
    task_cleanup_retention_days: int = 7
    task_cleanup_interval_seconds: int = 86400

    # CORS：环境变量中建议使用逗号分隔（更贴近 docker-compose 用法）
    # 也兼容 JSON 数组：'["http://a","http://b"]'
    cors_origins: str = "http://localhost:7788,http://127.0.0.1:7788"

    @property
    def cors_origins_list(self) -> list[str]:
        s = (self.cors_origins or "").strip()
        if not s:
            return []
        if s.startswith("["):
            loaded = json.loads(s)
            if isinstance(loaded, list):
                return [str(x).strip() for x in loaded if str(x).strip()]
            return []
        return [x.strip() for x in s.split(",") if x.strip()]

    # S3 / 对象存储（用于素材文件）
    s3_endpoint_url: str | None = None
    s3_region_name: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket_name: str | None = None
    # 可选：统一前缀，方便按环境/项目隔离，如 "jellyfish/dev"
    s3_base_path: str = ""
    # 可选：对外访问基址（CDN 或自定义域名），为空则使用 S3 自带 URL 或预签名 URL
    s3_public_base_url: str | None = None

    def model_post_init(self, __context: object) -> None:
        if not self.celery_broker_url or not str(self.celery_broker_url).strip():
            password_part = f":{self.redis_password}@" if self.redis_password else ""
            self.celery_broker_url = f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
