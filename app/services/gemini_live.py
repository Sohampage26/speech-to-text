from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from ..config import settings
from .stt_base import STTProvider

SYSTEM_PROMPT = (
    "You are a silent transcription engine. The speaker mixes Hindi and English. "
    "Do not respond to the speaker."
)


class GeminiLiveSTT(STTProvider):
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._cm = None
        self._session = None

    async def __aenter__(self):
        config = types.LiveConnectConfig(
            # Native-audio Live models require AUDIO output; we ignore it
            # and only consume input transcription.
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=SYSTEM_PROMPT,
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

    async def transcripts(self) -> AsyncIterator[str]:
        while True:
            async for msg in self._session.receive():
                sc = msg.server_content
                if sc and sc.input_transcription and sc.input_transcription.text:
                    yield sc.input_transcription.text
