import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services import get_provider

log = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/transcribe")
async def transcribe(ws: WebSocket):
    await ws.accept()
    full = ""
    try:
        async with get_provider() as stt:

            async def reader():
                # Browser -> Gemini. Binary = PCM16 audio, text "stop" = end.
                while True:
                    msg = await ws.receive()
                    if msg.get("bytes"):
                        await stt.send_audio(msg["bytes"])
                    elif msg.get("text") == "stop":
                        await stt.end_audio()
                        return
                    elif msg["type"] == "websocket.disconnect":
                        raise WebSocketDisconnect()

            async def writer():
                # Gemini -> Browser. "final" segments are appended;
                # "interim" is a speculative tail shown until the next final.
                nonlocal full
                async for kind, text in stt.transcripts():
                    if kind == "final":
                        full = (full + " " + text.strip()).strip()
                        shown = full
                    else:
                        shown = (full + " " + text.strip()).strip()
                    await ws.send_text(json.dumps({"type": "partial", "text": shown}))

            r = asyncio.create_task(reader())
            w = asyncio.create_task(writer())
            await r  # wait for the user to stop
            try:  # let trailing transcription arrive
                await asyncio.wait_for(w, timeout=stt.drain_timeout)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        return
    except Exception as e:  # noqa: BLE001
        log.exception("transcription failed")
        await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
    finally:
        try:
            await ws.send_text(json.dumps({"type": "final", "text": full.strip()}))
            await ws.close()
        except Exception:  # noqa: BLE001
            pass
