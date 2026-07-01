"""音乐生成 HTTP 适配器（支持本地 MusicGen + AIML API）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# 本地 MusicGen 适配器
# ============================================================

@dataclass(frozen=True, slots=True)
class LocalMusicGenConfig:
    base_url: str = "http://host.docker.internal:8100"


@dataclass
class LocalMusicGenResult:
    status: str
    audio_url: str | None = None
    duration_s: float = 0
    error: str | None = None


class LocalMusicGenAdapter:
    """对接本地 MusicGen FastAPI 服务（异步模式：POST 提交 + GET 轮询）。"""

    async def generate(
        self,
        *,
        cfg: LocalMusicGenConfig,
        prompt: str,
        duration_s: int = 10,
        timeout_s: float = 1800.0,
        poll_interval_s: float = 15.0,
    ) -> LocalMusicGenResult:
        import asyncio
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx is required") from e

        base_url = cfg.base_url.rstrip("/")

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{base_url}/generate",
                json={"prompt": prompt, "duration_s": duration_s},
            )
            r.raise_for_status()
            data: dict[str, Any] = r.json()

        task_id = data.get("id", "")
        if not task_id:
            return LocalMusicGenResult(status="failed", error=f"No task_id returned: {data}")

        elapsed = 0.0
        while elapsed < timeout_s:
            await asyncio.sleep(poll_interval_s)
            elapsed += poll_interval_s

            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(f"{base_url}/status/{task_id}")
                r.raise_for_status()
                status_data: dict[str, Any] = r.json()

            status = status_data.get("status", "")

            if status == "completed":
                audio_path = status_data.get("audio_url", "")
                full_url = f"{base_url}{audio_path}" if audio_path.startswith("/") else audio_path
                return LocalMusicGenResult(
                    status="completed",
                    audio_url=full_url,
                    duration_s=status_data.get("duration_s", 0),
                )

            if status == "failed":
                return LocalMusicGenResult(
                    status="failed",
                    error=status_data.get("error", "Generation failed"),
                )

            logger.debug("MusicGen poll: status=%s elapsed=%.0fs", status, elapsed)

        return LocalMusicGenResult(status="failed", error=f"Timeout after {timeout_s}s")


# ============================================================
# AIML API (Stable Audio) 适配器（备用）
# ============================================================

DEFAULT_AIML_BASE_URL = "https://api.aimlapi.com"


@dataclass(frozen=True, slots=True)
class AimlAudioConfig:
    api_key: str
    base_url: str = DEFAULT_AIML_BASE_URL
    model: str = "stable-audio"


@dataclass(frozen=True, slots=True)
class AimlAudioGenerateRequest:
    prompt: str
    seconds_total: int = 30
    steps: int = 100
    model: str = "stable-audio"


@dataclass
class AimlAudioResult:
    generation_id: str
    status: str
    audio_url: str | None = None
    error: str | None = None


class AimlAudioApiAdapter:
    """AIML API (Stable Audio) HTTP 适配器。"""

    async def create_generation(
        self,
        *,
        cfg: AimlAudioConfig,
        request: AimlAudioGenerateRequest,
        timeout_s: float = 30.0,
    ) -> str:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx is required for AIML API integration") from e

        base_url = cfg.base_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }

        body: dict[str, Any] = {
            "model": request.model,
            "prompt": request.prompt,
            "seconds_total": request.seconds_total,
            "steps": request.steps,
        }

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(f"{base_url}/v2/generate/audio", headers=headers, json=body)
            r.raise_for_status()
            data: dict[str, Any] = r.json()

        generation_id = data.get("id", "")
        if not generation_id:
            raise RuntimeError(f"AIML API create missing id: {data!r}")

        return generation_id

    async def get_generation_status(
        self,
        *,
        cfg: AimlAudioConfig,
        generation_id: str,
        timeout_s: float = 30.0,
    ) -> AimlAudioResult:
        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx is required for AIML API integration") from e

        base_url = cfg.base_url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.get(
                f"{base_url}/v2/generate/audio",
                headers=headers,
                params={"generation_id": generation_id},
            )
            r.raise_for_status()
            data: dict[str, Any] = r.json()

        status = data.get("status", "unknown")
        audio_url = None
        error = None

        audio_file = data.get("audio_file")
        if isinstance(audio_file, dict):
            audio_url = audio_file.get("url")

        error_data = data.get("error")
        if isinstance(error_data, dict):
            error = error_data.get("message", str(error_data))

        return AimlAudioResult(
            generation_id=generation_id,
            status=status,
            audio_url=audio_url,
            error=error,
        )
