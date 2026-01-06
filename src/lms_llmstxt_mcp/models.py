from datetime import datetime, timezone
from typing import Literal, List, Optional
from pydantic import BaseModel, Field

ArtifactName = Literal["llms.txt", "llms-full.txt", "llms-ctx.txt", "llms.json"]
RunStatus = Literal["pending", "processing", "completed", "failed"]

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ArtifactRef(BaseModel):
    name: ArtifactName
    path: str
    size_bytes: int
    hash_sha256: str

class RunRecord(BaseModel):
    run_id: str
    status: RunStatus
    artifacts: List[ArtifactRef] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

class GenerateResult(RunRecord):
    """Legacy name preserved for compatibility with existing tool outputs."""

class ReadArtifactResult(BaseModel):
    content: str
    truncated: bool
    total_chars: int

class ArtifactMetadata(BaseModel):
    filename: str
    size_bytes: int
    last_modified: datetime
    uri: str