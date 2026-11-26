from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class STTProvider(ABC):
    """Streaming speech-to-text provider.

    Feed 16 kHz mono PCM16 chunks via `send_audio`; consume
    (kind, text) events from `transcripts()` where kind is
    "interim" (speculative, replaces previous interim) or
    "final" (authoritative segment, append to transcript).
    """

    drain_timeout: float = 5.0  # seconds to wait for trailing text after Stop

    @abstractmethod
    async def __aenter__(self): ...

    @abstractmethod
    async def __aexit__(self, *exc): ...

    @abstractmethod
    async def send_audio(self, pcm: bytes) -> None: ...

    @abstractmethod
    async def end_audio(self) -> None: ...

    @abstractmethod
    def transcripts(self) -> AsyncIterator[tuple[str, str]]: ...
