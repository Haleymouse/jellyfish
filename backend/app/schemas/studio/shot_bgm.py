"""镜头 BGM 相关 schemas。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.types import BgmSource


class ShotBgmRead(BaseModel):
    """BGM 读取响应。"""

    id: str = Field(..., description="BGM ID")
    shot_detail_id: str = Field(..., description="所属镜头细节 ID")
    source: BgmSource = Field(..., description="来源类型：upload / generated")
    file_id: str | None = Field(None, description="关联的音频文件 ID")
    prompt: str = Field("", description="生成时使用的提示词")
    duration_ms: int = Field(0, description="音频时长（毫秒）")
    is_active: bool = Field(False, description="是否为当前激活的 BGM")
    provider_config: dict[str, Any] | None = Field(None, description="供应商/模型配置")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class ShotBgmUploadRequest(BaseModel):
    """上传 BGM 请求体。"""

    file_id: str = Field(..., description="已上传的音频文件 ID（files.id）")
    duration_ms: int = Field(0, ge=0, description="音频时长（毫秒），前端可选传入")


class ShotBgmGenerateRequest(BaseModel):
    """AI 生成 BGM 请求体。"""

    prompt: str | None = Field(None, description="自定义提示词（为空时自动从 mood_tags + atmosphere 生成）")
    duration_ms: int = Field(30000, ge=1000, le=300000, description="期望生成的音频时长（毫秒）")
    provider_config: dict[str, Any] | None = Field(None, description="指定供应商/模型配置（可选）")
