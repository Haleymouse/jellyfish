"""本地 MusicGen 推理服务（FastAPI + 后台生成）。

使用 facebook/musicgen-small (300M)，CPU 推理。
启动: python server.py
端口: 8100

异步模式：POST /generate 立即返回 task_id，后台线程执行推理，
         GET /status/{task_id} 查询状态，完成后返回 audio_url。
"""

from __future__ import annotations

import os
import time
import uuid
import logging
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict

import torch
import torchaudio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("/tmp/musicgen_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = os.environ.get("MUSICGEN_MODEL", "facebook/musicgen-small")

model = None
processor = None
tasks: Dict[str, dict] = {}
gen_lock = threading.Lock()


def load_model():
    global model, processor
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    logger.info("Loading MusicGen model: %s (CPU)...", MODEL_NAME)
    start = time.time()
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    model = MusicgenForConditionalGeneration.from_pretrained(MODEL_NAME)
    logger.info("Model loaded in %.1fs", time.time() - start)


def _generate_worker(task_id: str, prompt: str, duration_s: int):
    """后台线程：执行推理。"""
    try:
        tasks[task_id]["status"] = "generating"
        logger.info("Generating: id=%s prompt=%r duration=%ds", task_id, prompt, duration_s)
        start = time.time()

        with gen_lock:
            inputs = processor(text=[prompt], padding=True, return_tensors="pt")
            max_new_tokens = int(duration_s * 50)

            with torch.no_grad():
                audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

        audio = audio_values[0].cpu()
        if audio.dim() == 1:
            audio = audio.unsqueeze(0)

        sample_rate = model.config.audio_encoder.sampling_rate
        actual_duration = audio.shape[-1] / sample_rate

        out_path = OUTPUT_DIR / f"{task_id}.wav"
        torchaudio.save(str(out_path), audio, sample_rate)

        elapsed = time.time() - start
        logger.info("Generated: id=%s duration=%.1fs elapsed=%.1fs", task_id, actual_duration, elapsed)

        tasks[task_id].update({
            "status": "completed",
            "duration_s": actual_duration,
            "audio_url": f"/audio/{task_id}.wav",
            "elapsed_s": round(elapsed, 1),
        })
    except Exception as exc:
        logger.exception("Generation failed: %s", task_id)
        tasks[task_id].update({
            "status": "failed",
            "error": str(exc),
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()
    yield


app = FastAPI(title="MusicGen Local Service", lifespan=lifespan)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="音乐风格/氛围描述")
    duration_s: int = Field(default=5, ge=1, le=10, description="生成时长（秒），最大10")


class TaskResponse(BaseModel):
    id: str
    status: str
    duration_s: float = 0
    audio_url: str = ""
    elapsed_s: float = 0
    error: str = ""


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME, "device": "cpu", "pending": sum(1 for t in tasks.values() if t["status"] in ("queued", "generating"))}


@app.post("/generate", response_model=TaskResponse)
def generate_music(req: GenerateRequest):
    if model is None:
        raise HTTPException(503, "Model not loaded")

    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "queued", "duration_s": 0, "audio_url": "", "elapsed_s": 0, "error": ""}

    thread = threading.Thread(target=_generate_worker, args=(task_id, req.prompt, req.duration_s), daemon=True)
    thread.start()

    return TaskResponse(id=task_id, status="queued")


@app.get("/status/{task_id}", response_model=TaskResponse)
def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Task not found")
    t = tasks[task_id]
    return TaskResponse(
        id=task_id,
        status=t["status"],
        duration_s=t.get("duration_s", 0),
        audio_url=t.get("audio_url", ""),
        elapsed_s=t.get("elapsed_s", 0),
        error=t.get("error", ""),
    )


@app.get("/audio/{filename}")
def get_audio(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Audio not found")
    return FileResponse(path, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
