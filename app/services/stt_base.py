from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class STTProvider(ABC):
    """Streaming speech-to-text provider.

    Feed 16 kHz mono PCM16 chunks via `send_audio`; consume text deltas
    from `transcripts()`.
    """

    @abstractmethod
    async def __aenter__(self): ...

    @abstractmethod
    async def __aexit__(self, *exc): ...

    @abstractmethod
    async def send_audio(self, pcm: bytes) -> None: ...

    @abstractmethod
    async def end_audio(self) -> None: ...

    @abstractmethod
    def transcripts(self) -> AsyncIterator[str]: ...
