"""TEMPORARY diagnostics. Remove before final submission."""
import asyncio
from importlib.metadata import version

from fastapi import APIRouter
from google import genai
from google.genai import types

from ..config import settings

router = APIRouter(prefix="/debug", tags=["debug"])

CANDIDATES = [
    settings.gemini_model,
    "gemini-3.5-transcribe-live",
    "gemini-3.8-live",
    "gemini-3.1-flash-live-preview",
    "gemini-2.5-flash-native-audio-preview-12-2025",
    "gemini-live-2.5-flash-preview",
]


async def _try(client, model: str) -> dict:
    try:
        cfg = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )
        if "transcribe" in model:
            cfg = types.LiveConnectConfig(
                response_modalities=["TEXT"],
                input_audio_transcription=types.AudioTranscriptionConfig(language_codes=[]),
            )
        async with asyncio.timeout(10):
            async with client.aio.live.connect(model=model, config=cfg):
                return {"model": model, "connect": "OK"}
    except Exception as e:  # noqa: BLE001
        return {"model": model, "connect": "FAILED", "error": f"{type(e).__name__}: {str(e)[:200]}"}


@router.get("/models")
async def models():
    client = genai.Client(api_key=settings.gemini_api_key)
    names = []
    try:
        async for m in await client.aio.models.list():
            names.append(m.name)
    except Exception as e:  # noqa: BLE001
        names = [f"list failed: {type(e).__name__}: {str(e)[:200]}"]
    seen, results = set(), []
    for m in CANDIDATES:
        if m not in seen:
            seen.add(m)
            results.append(await _try(client, m))
    return {
        "sdk_version": version("google-genai"),
        "connect_tests": results,
        "model_count": len(names),
        "all_models": sorted(names),
    }
