from typing import Literal, List, Optional
from pydantic import BaseModel, Field

ArtifactName = Literal["llms.txt", "llms-full.txt", "llms-ctx.txt", "llms.json"]

class ArtifactRef(BaseModel):
    name: ArtifactName
    path: str
    size_bytes: int
    hash_sha256: str

class GenerateResult(BaseModel):
    run_id: str
    status: Literal["success", "failed"]
    artifacts: List[ArtifactRef] = Field(default_factory=list)
    error_message: Optional[str] = None

class ReadArtifactResult(BaseModel):
    content: str
    truncated: bool
    total_chars: int
