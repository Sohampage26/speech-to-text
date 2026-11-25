from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    gemini_api_key: str
    # "chunked" (standard Gemini API) or "live" (Gemini Live API)
    stt_provider: str = "chunked"
    gemini_stt_model: str = "gemini-2.5-flash"  # used by "chunked"
    gemini_model: str = "gemini-3.5-transcribe-live"  # used by "live"


settings = Settings()
