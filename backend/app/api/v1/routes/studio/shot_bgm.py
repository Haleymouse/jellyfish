"""镜头 BGM 路由：上传、AI 生成、激活、删除。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_manager import DeliveryMode, SqlAlchemyTaskStore, TaskManager
from app.dependencies import get_db
from app.schemas.common import ApiResponse, created_response, empty_response, success_response
from app.schemas.studio.shot_bgm import ShotBgmGenerateRequest, ShotBgmRead, ShotBgmUploadRequest
from app.services.studio.shot_bgm import (
    create_generated_bgm,
    delete_bgm,
    generate_bgm_prompt,
    list_bgms,
    set_active_bgm,
    upload_bgm,
)
from app.tasks.execute_task import enqueue_task_execution

router = APIRouter()


class _CreateOnlyTask:
    async def run(self, *a, **kw):
        return None

    async def status(self):
        return {}

    async def is_done(self):
        return False

    async def get_result(self):
        return None


@router.get(
    "/{shot_detail_id}",
    response_model=ApiResponse[list[ShotBgmRead]],
    summary="获取镜头 BGM 列表",
)
async def list_shot_bgms(
    shot_detail_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ShotBgmRead]]:
    items = await list_bgms(db, shot_detail_id=shot_detail_id)
    return success_response([ShotBgmRead.model_validate(x) for x in items])


@router.post(
    "/{shot_detail_id}/upload",
    response_model=ApiResponse[ShotBgmRead],
    status_code=status.HTTP_201_CREATED,
    summary="上传并关联 BGM 文件",
)
async def upload_shot_bgm(
    shot_detail_id: str,
    body: ShotBgmUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ShotBgmRead]:
    bgm = await upload_bgm(
        db,
        shot_detail_id=shot_detail_id,
        file_id=body.file_id,
        duration_ms=body.duration_ms,
    )
    return created_response(ShotBgmRead.model_validate(bgm))


@router.post(
    "/{shot_detail_id}/generate",
    response_model=ApiResponse[ShotBgmRead],
    status_code=status.HTTP_201_CREATED,
    summary="AI 生成 BGM（Suno）",
)
async def generate_shot_bgm(
    shot_detail_id: str,
    body: ShotBgmGenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ShotBgmRead]:
    prompt = body.prompt
    if not prompt:
        prompt = await generate_bgm_prompt(db, shot_detail_id=shot_detail_id)

    bgm = await create_generated_bgm(
        db,
        shot_detail_id=shot_detail_id,
        file_id=None,
        prompt=prompt,
        duration_ms=body.duration_ms,
        provider_config=body.provider_config,
    )

    run_args = {
        "bgm_id": bgm.id,
        "shot_detail_id": shot_detail_id,
        "prompt": prompt,
        "duration_ms": body.duration_ms,
    }
    if body.provider_config:
        run_args["musicgen_url"] = body.provider_config.get("musicgen_url", "")

    store = SqlAlchemyTaskStore(db)
    tm = TaskManager(store=store, strategies={})
    task_record = await tm.create(
        task=_CreateOnlyTask(),
        mode=DeliveryMode.async_polling,
        task_kind="bgm_generation",
        run_args=run_args,
    )
    await db.commit()
    enqueue_task_execution(task_record.id)

    return created_response(ShotBgmRead.model_validate(bgm))


@router.patch(
    "/{bgm_id}/activate",
    response_model=ApiResponse[ShotBgmRead],
    summary="设为当前激活 BGM",
)
async def activate_shot_bgm(
    bgm_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[ShotBgmRead]:
    bgm = await set_active_bgm(db, bgm_id=bgm_id)
    return success_response(ShotBgmRead.model_validate(bgm))


@router.delete(
    "/{bgm_id}",
    response_model=ApiResponse[None],
    summary="删除 BGM",
)
async def delete_shot_bgm(
    bgm_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[None]:
    await delete_bgm(db, bgm_id=bgm_id)
    return empty_response()
