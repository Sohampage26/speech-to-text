import asyncio
import io
import logging
import wave
from array import array
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from ..config import settings
from .stt_base import STTProvider

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHUNK_SECONDS = 4
CHUNK_BYTES = SAMPLE_RATE * 2 * CHUNK_SECONDS
MIN_FLUSH_BYTES = int(SAMPLE_RATE * 2 * 0.4)
SILENCE_LEVEL = 80  # mean |sample| below this is treated as silence

PROMPT = (
    "Transcribe this audio exactly as spoken. The speaker may mix Hindi and English. "
    "Write Hindi words in Devanagari and English words in Latin script. "
    "Output only the transcript text, nothing else. If there is no speech, output nothing."
)


def _is_silent(pcm: bytes) -> bool:
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    if not samples:
        return True
    return sum(abs(s) for s in samples) / len(samples) < SILENCE_LEVEL


def _to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


class GeminiChunkedSTT(STTProvider):
    """Near-real-time STT using the standard Gemini API (no Live API needed).

    Buffers audio into ~4 s chunks and transcribes them in order.
    """

    drain_timeout = 20.0  # allow the last chunk to finish after Stop

    async def __aenter__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._buf = bytearray()
        self._in: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._out: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()
        self._worker = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, *exc):
        self._worker.cancel()

    async def _run(self):
        try:
            while (chunk := await self._in.get()) is not None:
                if _is_silent(chunk):
                    log.info("chunk skipped (silence)")
                    continue
                try:
                    text = await self._transcribe(chunk)
                    log.info("chunk transcribed: %d chars", len(text))
                except Exception as e:  # noqa: BLE001
                    log.exception("gemini transcription call failed")
                    await self._out.put(("error", f"{type(e).__name__}: {str(e)[:250]}"))
                    continue
                if text:
                    await self._out.put(("final", text))
        finally:
            await self._out.put(None)

    async def _transcribe(self, pcm: bytes) -> str:
        resp = await self._client.aio.models.generate_content(
            model=settings.gemini_stt_model,
            contents=[PROMPT, types.Part.from_bytes(data=_to_wav(pcm), mime_type="audio/wav")],
        )
        return (resp.text or "").strip()

    async def send_audio(self, pcm: bytes) -> None:
        self._buf.extend(pcm)
        while len(self._buf) >= CHUNK_BYTES:
            await self._in.put(bytes(self._buf[:CHUNK_BYTES]))
            del self._buf[:CHUNK_BYTES]

    async def end_audio(self) -> None:
        if len(self._buf) >= MIN_FLUSH_BYTES:
            await self._in.put(bytes(self._buf))
        self._buf.clear()
        await self._in.put(None)

    async def transcripts(self) -> AsyncIterator[tuple[str, str]]:
        while (item := await self._out.get()) is not None:
            yield item
