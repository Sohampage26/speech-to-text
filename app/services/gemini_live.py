from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from ..config import settings
from .stt_base import STTProvider


class GeminiLiveSTT(STTProvider):
    """Gemini Live transcription (gemini-3.5-transcribe-live)."""

    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._cm = None
        self._session = None

    async def __aenter__(self):
        config = types.LiveConnectConfig(
            response_modalities=["TEXT"],
            input_audio_transcription=types.AudioTranscriptionConfig(
                language_codes=[],  # auto-detect, handles Hindi/English code-switching
            ),
        )
        self._cm = self._client.aio.live.connect(model=settings.gemini_model, config=config)
        self._session = await self._cm.__aenter__()
        return self

    async def __aexit__(self, *exc):
        if self._cm:
            await self._cm.__aexit__(*exc)

    async def send_audio(self, pcm: bytes) -> None:
        await self._session.send_realtime_input(
            audio=types.Blob(data=pcm, mime_type="audio/pcm;rate=16000")
        )

    async def end_audio(self) -> None:
        await self._session.send_realtime_input(audio_stream_end=True)

    async def transcripts(self) -> AsyncIterator[tuple[str, str]]:
        while True:
            async for msg in self._session.receive():
                sc = msg.server_content
                if not sc:
                    continue
                if sc.interim_input_transcription and sc.interim_input_transcription.text:
                    yield "interim", sc.interim_input_transcription.text
                if sc.input_transcription and sc.input_transcription.text:
                    yield "final", sc.input_transcription.text
