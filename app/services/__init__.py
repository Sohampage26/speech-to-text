from ..config import settings
from .stt_base import STTProvider


def get_provider() -> STTProvider:
    if settings.stt_provider == "live":
        from .gemini_live import GeminiLiveSTT
        return GeminiLiveSTT()
    from .gemini_chunked import GeminiChunkedSTT
    return GeminiChunkedSTT()
