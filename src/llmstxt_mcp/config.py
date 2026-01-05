from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    LLMSTXT_MCP_ALLOWED_ROOT: Path = Path("./artifacts")
    LLMSTXT_MCP_RESOURCE_MAX_CHARS: int = 100000
    LLMSTXT_MCP_RUN_TTL_SECONDS: int = 60 * 60 * 24
    LLMSTXT_MCP_RUN_CLEANUP_INTERVAL_SECONDS: int = 300
    LLMSTXT_MCP_RUN_MAX: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()