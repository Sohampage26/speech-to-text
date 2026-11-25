from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    gemini_api_key: str
    # "chunked" (standard Gemini API) or "live" (Gemini Live API)
    stt_provider: str = "chunked"
    gemini_stt_model: str = "gemini-3.8-flash"  # used by "chunked"
    # comma-separated models tried in order if the primary is overloaded/unavailable
    gemini_stt_fallbacks: str = "gemini-3.7-flash,gemini-3.5-flash"
    gemini_model: str = "gemini-3.5-transcribe-live"  # used by "live"


settings = Settings()
