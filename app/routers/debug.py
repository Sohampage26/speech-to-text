"""TEMPORARY diagnostics. Remove before final submission."""
from importlib.metadata import version

from fastapi import APIRouter
from google import genai

from ..config import settings

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/models")
def models():
    client = genai.Client(api_key=settings.gemini_api_key)
    out = []
    for m in client.models.list():
        actions = list(getattr(m, "supported_actions", None) or [])
        if "bidiGenerateContent" in actions or "live" in m.name or "transcribe" in m.name:
            out.append({"name": m.name, "actions": actions})
    return {
        "configured_model": settings.gemini_model,
        "sdk_version": version("google-genai"),
        "live_capable_models": out,
    }
