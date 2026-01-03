from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    LLMSTXT_MCP_ALLOWED_ROOT: Path = Path("./output")
    LLMSTXT_MCP_RESOURCE_MAX_CHARS: int = 100000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
