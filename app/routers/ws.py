import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services import get_provider
from ..services.languages import DEFAULT_LANGUAGE, LANGUAGES

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/languages")
def languages():
    return {
        "default": DEFAULT_LANGUAGE,
        "items": [{"code": c, "label": l} for c, l in LANGUAGES.items()],
    }


@router.websocket("/ws/transcribe")
async def transcribe(ws: WebSocket, lang: str = DEFAULT_LANGUAGE):
    await ws.accept()
    if lang not in LANGUAGES:
        lang = DEFAULT_LANGUAGE
    full = ""
    tasks: list[asyncio.Task] = []
    try:
        async with get_provider(lang) as stt:

            async def reader():
                # Browser -> provider. Binary = PCM16 audio, text "stop" = end.
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.disconnect":
                        raise WebSocketDisconnect()
                    if msg.get("bytes"):
                        await stt.send_audio(msg["bytes"])
                    elif msg.get("text") == "stop":
                        await stt.end_audio()
                        return

            async def writer():
                # Provider -> browser. "final" segments are appended;
                # "interim" is a speculative tail shown until the next final.
                nonlocal full
                async for kind, text in stt.transcripts():
                    if kind == "error":
                        await ws.send_text(json.dumps({"type": "error", "message": text}))
                        continue
                    if kind == "final":
                        full = (full + " " + text).strip()
                        shown = full
                    else:
                        shown = (full + " " + text).strip()
                    await ws.send_text(json.dumps({"type": "partial", "text": shown}))

            r = asyncio.create_task(reader())
            w = asyncio.create_task(writer())
            tasks = [r, w]
            done, _ = await asyncio.wait({r, w}, return_when=asyncio.FIRST_COMPLETED)
            if r in done:
                r.result()  # user pressed Stop (or raise on disconnect)
                try:  # let trailing transcription arrive
                    await asyncio.wait_for(w, timeout=stt.drain_timeout)
                except asyncio.TimeoutError:
                    pass
            else:
                w.result()  # provider ended first: raise its error, if any
    except WebSocketDisconnect:
        return
    except Exception as e:  # noqa: BLE001
        log.exception("transcription failed")
        try:
            await ws.send_text(json.dumps({"type": "error", "message": f"{type(e).__name__}: {e}"[:300]}))
        except Exception:  # noqa: BLE001
            pass
    finally:
        for t in tasks:
            t.cancel()
        try:
            await ws.send_text(json.dumps({"type": "final", "text": full.strip()}))
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
