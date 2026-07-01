"""BGM 生成任务：对接本地 MusicGen 服务。

本地 MusicGen 服务运行在 localhost:8100，同步返回结果（无需轮询）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.integrations.suno.music import LocalMusicGenAdapter, LocalMusicGenConfig

logger = logging.getLogger(__name__)

__all__ = [
    "BgmGenerationInput",
    "BgmGenerationResult",
    "LocalBgmGenerationTask",
    "BgmGenerationTask",
]


@dataclass(frozen=True, slots=True)
class BgmGenerationInput:
    prompt: str
    duration_ms: int = 30000
    shot_detail_id: str = ""
    bgm_id: str = ""


@dataclass(frozen=True, slots=True)
class BgmGenerationResult:
    status: str  # "succeeded" | "failed"
    audio_url: str | None = None
    provider_task_id: str | None = None
    error: str | None = None
    duration_ms: int = 0


class LocalBgmGenerationTask:
    """本地 MusicGen BGM 生成（同步调用，无需轮询）。"""

    def __init__(
        self,
        *,
        musicgen_config: LocalMusicGenConfig,
        input_: BgmGenerationInput,
        adapter: LocalMusicGenAdapter | None = None,
    ) -> None:
        self._cfg = musicgen_config
        self._input = input_
        self._adapter = adapter or LocalMusicGenAdapter()

    async def run(self) -> BgmGenerationResult:
        try:
            duration_s = min(max(self._input.duration_ms // 1000, 1), 30)

            result = await self._adapter.generate(
                cfg=self._cfg,
                prompt=self._input.prompt,
                duration_s=duration_s,
                timeout_s=300.0,
            )

            if result.status == "completed" and result.audio_url:
                return BgmGenerationResult(
                    status="succeeded",
                    audio_url=result.audio_url,
                    duration_ms=int(result.duration_s * 1000),
                )

            return BgmGenerationResult(
                status="failed",
                error=result.error or "MusicGen generation failed",
            )

        except Exception as exc:
            return BgmGenerationResult(
                status="failed",
                error=str(exc),
            )


BgmGenerationTask = LocalBgmGenerationTask
