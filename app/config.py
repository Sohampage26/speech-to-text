from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    sarvam_api_key: str = ""
    sarvam_mode: str = "codemix"  # final transcript style: transcribe|codemix|verbatim|translit
    sarvam_stream_type: str = "fast"  # fast|balanced


settings = Settings()
