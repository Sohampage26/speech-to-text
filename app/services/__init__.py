from .sarvam_realtime import SarvamSTT
from .stt_base import STTProvider


def get_provider(language: str = "hi-IN") -> STTProvider:
    """Single place to swap the STT backend (anything implementing STTProvider)."""
    return SarvamSTT(language)
