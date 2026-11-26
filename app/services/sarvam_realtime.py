import base64
import logging
from collections.abc import AsyncIterator

from ..config import settings
from .stt_base import STTProvider

log = logging.getLogger(__name__)


class SarvamSTT(STTProvider):
    """Sarvam realtime streaming STT (saaras:v4) with true partial transcripts."""

    drain_timeout = 8.0

    def __init__(self, language: str = "hi-IN"):
        self._language = language
        self._cm = None
        self._ws = None

    async def __aenter__(self):
        if not settings.sarvam_api_key:
            raise RuntimeError("SARVAM_API_KEY is not set")
        from sarvamai import AsyncSarvamAI  # imported lazily

        client = AsyncSarvamAI(api_subscription_key=settings.sarvam_api_key)
        self._cm = client.speech_to_text_realtime_streaming.connect(
            language_code=self._language,
            stream_type=settings.sarvam_stream_type,
            mode=settings.sarvam_mode,
            sample_rate="16000",
        )
        self._ws = await self._cm.__aenter__()
        return self

    async def __aexit__(self, *exc):
        if self._cm:
            await self._cm.__aexit__(*exc)

    async def send_audio(self, pcm: bytes) -> None:
        from sarvamai import RealtimeAudioInput

        await self._ws.send_realtime_audio_input(
            RealtimeAudioInput(audio=base64.b64encode(pcm).decode())
        )

    async def end_audio(self) -> None:
        from sarvamai import RealtimeEnd

        await self._ws.send_realtime_end(RealtimeEnd())

    async def transcripts(self) -> AsyncIterator[tuple[str, str]]:
        async for m in self._ws:
            event = getattr(m, "event", None)
            text = (getattr(m, "text", "") or "").strip()
            if event == "transcript.partial" and text:
                yield "interim", text
            elif event == "transcript.final" and text:
                yield "final", text
            elif event == "error":
                log.error("sarvam error: %s %s", getattr(m, "code", ""), getattr(m, "message", ""))
                yield "error", f"{getattr(m, 'code', 'error')}: {getattr(m, 'message', '')}"
                if getattr(m, "is_fatal", False):
                    return
            elif event == "session.end":
                return
