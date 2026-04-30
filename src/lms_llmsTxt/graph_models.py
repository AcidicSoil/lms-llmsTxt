from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

GraphNodeType = Literal["moc", "concept", "pattern", "gotcha"]


class GraphNodeEvidence(BaseModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None
    artifact_ref: str | None = None
    excerpt: str | None = None


class GraphEdge(BaseModel):
    target_id: str
    relation: str = "relates_to"
    prose: str | None = None


class RepoGraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    description: str
    content: str
    links: list[str] = Field(default_factory=list)
    evidence: list[GraphNodeEvidence] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RepoSkillGraph(BaseModel):
    topic: str
    nodes: list[RepoGraphNode]
    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ForceGraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    val: float = 1.0


class ForceGraphLink(BaseModel):
    source: str
    target: str


class ForceGraphData(BaseModel):
    nodes: list[ForceGraphNode]
    links: list[ForceGraphLink]
