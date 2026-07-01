"""镜头 BGM 服务：CRUD + 提示词构建。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.studio_shots import ShotBgm, ShotDetail
from app.models.types import BgmSource
from app.services.common import entity_not_found, get_or_404


async def list_bgms(
    db: AsyncSession,
    *,
    shot_detail_id: str,
) -> list[ShotBgm]:
    """列出指定镜头的所有 BGM 记录。"""
    stmt = (
        select(ShotBgm)
        .where(ShotBgm.shot_detail_id == shot_detail_id)
        .order_by(ShotBgm.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upload_bgm(
    db: AsyncSession,
    *,
    shot_detail_id: str,
    file_id: str,
    duration_ms: int = 0,
) -> ShotBgm:
    """创建一条上传来源的 BGM 记录。"""
    await get_or_404(db, ShotDetail, shot_detail_id, detail=entity_not_found("ShotDetail"))
    bgm = ShotBgm(
        id=str(uuid.uuid4()),
        shot_detail_id=shot_detail_id,
        source=BgmSource.upload,
        file_id=file_id,
        prompt="",
        duration_ms=duration_ms,
        is_active=False,
    )
    db.add(bgm)
    await db.flush()
    await db.refresh(bgm)
    return bgm


async def generate_bgm_prompt(
    db: AsyncSession,
    *,
    shot_detail_id: str,
) -> str:
    """根据镜头的 mood_tags + atmosphere 构建音乐生成提示词。"""
    detail = await get_or_404(db, ShotDetail, shot_detail_id, detail=entity_not_found("ShotDetail"))
    parts: list[str] = []
    if detail.mood_tags:
        parts.append(f"Mood: {', '.join(detail.mood_tags)}")
    if detail.atmosphere:
        parts.append(f"Atmosphere: {detail.atmosphere}")
    if not parts:
        parts.append("Cinematic background music")
    return ". ".join(parts)


async def create_generated_bgm(
    db: AsyncSession,
    *,
    shot_detail_id: str,
    file_id: str | None,
    prompt: str,
    duration_ms: int = 0,
    provider_config: dict[str, Any] | None = None,
) -> ShotBgm:
    """创建一条 AI 生成来源的 BGM 记录。"""
    await get_or_404(db, ShotDetail, shot_detail_id, detail=entity_not_found("ShotDetail"))
    bgm = ShotBgm(
        id=str(uuid.uuid4()),
        shot_detail_id=shot_detail_id,
        source=BgmSource.generated,
        file_id=file_id,
        prompt=prompt,
        duration_ms=duration_ms,
        is_active=False,
        provider_config=provider_config,
    )
    db.add(bgm)
    await db.flush()
    await db.refresh(bgm)
    return bgm


async def set_active_bgm(
    db: AsyncSession,
    *,
    bgm_id: str,
) -> ShotBgm:
    """将指定 BGM 设为激活状态，同时取消同镜头其他 BGM 的激活。"""
    bgm = await get_or_404(db, ShotBgm, bgm_id, detail=entity_not_found("ShotBgm"))
    # 先取消同镜头所有 BGM 的激活
    await db.execute(
        update(ShotBgm)
        .where(ShotBgm.shot_detail_id == bgm.shot_detail_id)
        .values(is_active=False)
    )
    # 再激活目标
    bgm.is_active = True
    await db.flush()
    await db.refresh(bgm)
    return bgm


async def delete_bgm(
    db: AsyncSession,
    *,
    bgm_id: str,
) -> None:
    """删除指定 BGM 记录。"""
    bgm = await db.get(ShotBgm, bgm_id)
    if bgm is None:
        return
    await db.delete(bgm)
    await db.flush()
