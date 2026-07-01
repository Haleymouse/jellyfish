"""BGM 生成任务 runner：对接本地 MusicGen 服务，下载音频存 S3，更新 ShotBgm。"""

from __future__ import annotations

import logging

from app.core.db import async_session_maker
from app.core.task_manager import SqlAlchemyTaskStore
from app.core.task_manager.types import TaskStatus
from app.core.tasks.bgm_generation_tasks import (
    BgmGenerationInput,
    BgmGenerationResult,
    LocalBgmGenerationTask,
)
from app.core.integrations.suno.music import LocalMusicGenConfig
from app.models.studio_shots import ShotBgm
from app.utils.files import create_file_from_url_or_b64
from app.services.worker.task_logging import log_task_event, log_task_failure

logger = logging.getLogger(__name__)


async def run_bgm_generation_task(
    task_id: str,
    run_args: dict,
) -> None:
    async with async_session_maker() as session:
        try:
            store = SqlAlchemyTaskStore(session)
            await store.set_status(task_id, TaskStatus.running)
            await store.set_progress(task_id, 5)
            await session.commit()
            log_task_event("bgm_generation", task_id, "running")

            bgm_id = str(run_args.get("bgm_id") or "")
            shot_detail_id = str(run_args.get("shot_detail_id") or "")
            prompt = str(run_args.get("prompt") or "")

            musicgen_url = run_args.get("musicgen_url") or "http://host.docker.internal:8100"
            cfg = LocalMusicGenConfig(base_url=musicgen_url)

            input_ = BgmGenerationInput(
                prompt=prompt,
                duration_ms=int(run_args.get("duration_ms", 10000)),
                shot_detail_id=shot_detail_id,
                bgm_id=bgm_id,
            )

            await store.set_progress(task_id, 10)
            await session.commit()
            log_task_event("bgm_generation", task_id, "generating_music")

            task = LocalBgmGenerationTask(musicgen_config=cfg, input_=input_)
            result: BgmGenerationResult = await task.run()

            if result.status != "succeeded" or not result.audio_url:
                raise RuntimeError(result.error or "BGM generation failed")

            await store.set_progress(task_id, 70)
            await session.commit()
            log_task_event("bgm_generation", task_id, "downloading_audio")

            file_obj = await create_file_from_url_or_b64(
                session,
                url_or_b64=result.audio_url,
                filename=f"bgm-{bgm_id[:8]}.wav",
                content_type="audio/wav",
            )

            await store.set_progress(task_id, 90)
            await session.commit()

            if bgm_id:
                bgm = await session.get(ShotBgm, bgm_id)
                if bgm:
                    bgm.file_id = file_obj.id
                    bgm.duration_ms = result.duration_ms or bgm.duration_ms
                    bgm.provider_config = {"provider": "local-musicgen"}

            result_payload = {
                "audio_url": result.audio_url,
                "file_id": file_obj.id,
                "duration_ms": result.duration_ms,
            }
            await store.set_result(task_id, result_payload)
            await store.set_progress(task_id, 100)
            await store.set_status(task_id, TaskStatus.succeeded)
            await session.commit()
            log_task_event("bgm_generation", task_id, "succeeded")

        except Exception as exc:
            await session.rollback()
            async with async_session_maker() as s2:
                store2 = SqlAlchemyTaskStore(s2)
                await store2.set_error(task_id, str(exc))
                await store2.set_status(task_id, TaskStatus.failed)
                await s2.commit()
            log_task_failure("bgm_generation", task_id, str(exc))
