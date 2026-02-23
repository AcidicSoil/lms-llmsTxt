from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Iterable

from .models import RepositoryMaterial


@dataclass(slots=True)
class RepoChunk:
    path: str
    content: str
    start_line: int = 1
    end_line: int = 1


@dataclass(slots=True)
class ChunkCapsule:
    chunk_id: str
    path: str
    chunk_type: str
    summary: str
    key_symbols: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RepoDigest:
    topic: str
    architecture_summary: str
    primary_language: str
    subsystems: list[dict]
    key_dependencies: list[str]
    entry_points: list[str]
    test_coverage_hint: str
    digest_id: str


def _language_from_path(path: str) -> str:
    if path.endswith(".py"):
        return "python"
    if path.endswith(".ts") or path.endswith(".tsx"):
        return "typescript"
    if path.endswith(".js"):
        return "javascript"
    if path.endswith(".rs"):
        return "rust"
    return "unknown"


def _chunk_type(path: str) -> str:
    low = path.lower()
    if "/test" in low or "test_" in low or low.endswith("_test.py"):
        return "test"
    if low.endswith((".md", ".rst", ".txt")):
        return "doc"
    if low.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")):
        return "config"
    return "code"


def _extract_symbols(content: str) -> list[str]:
    symbols = set(re.findall(r"(?:def|class|function|const|let|var|pub\\s+fn)\\s+([A-Za-z_][A-Za-z0-9_]*)", content))
    return sorted(symbols)[:10]


def _extract_dependencies(content: str) -> list[str]:
    deps = set(re.findall(r"(?:import|from|require|use)\\s+([A-Za-z0-9_./:@-]+)", content))
    return sorted(deps)[:20]


def _summarize(content: str, max_chars: int = 180) -> str:
    flat = " ".join(line.strip() for line in content.splitlines() if line.strip())
    if len(flat) <= max_chars:
        return flat
    return flat[:max_chars] + "..."


def chunk_repository_material(material: RepositoryMaterial) -> list[RepoChunk]:
    chunks: list[RepoChunk] = []
    for path in sorted(p for p in material.file_tree.splitlines() if p.strip()):
        chunks.append(RepoChunk(path=path, content=path, start_line=1, end_line=1))
    if material.readme_content:
        end_line = max(1, material.readme_content.count("\n") + 1)
        chunks.append(RepoChunk(path="README.md", content=material.readme_content, end_line=end_line))
    if material.package_files:
        end_line = max(1, material.package_files.count("\n") + 1)
        chunks.append(RepoChunk(path="package_files.txt", content=material.package_files, end_line=end_line))
    return chunks


def extract_chunk_capsules(chunks: Iterable[RepoChunk]) -> list[ChunkCapsule]:
    capsules: list[ChunkCapsule] = []
    for chunk in chunks:
        raw_id = f"{chunk.path}:{chunk.start_line}:{chunk.end_line}"
        capsule = ChunkCapsule(
            chunk_id=hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16],
            path=chunk.path,
            chunk_type=_chunk_type(chunk.path),
            summary=_summarize(chunk.content),
            key_symbols=_extract_symbols(chunk.content),
            dependencies=_extract_dependencies(chunk.content),
        )
        capsules.append(capsule)
    return capsules


def reduce_capsules(capsules: list[ChunkCapsule], topic: str = "Repository") -> RepoDigest:
    if not capsules:
        return RepoDigest(
            topic=topic,
            architecture_summary="No repository content available.",
            primary_language="unknown",
            subsystems=[],
            key_dependencies=[],
            entry_points=[],
            test_coverage_hint="no_tests_detected",
            digest_id="empty",
        )

    by_subsystem: dict[str, list[ChunkCapsule]] = {}
    lang_counter: dict[str, int] = {}
    all_deps: set[str] = set()
    entry_points: list[str] = []

    for cap in capsules:
        parts = cap.path.split("/")
        subsystem = "/".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "root")
        by_subsystem.setdefault(subsystem, []).append(cap)

        lang = _language_from_path(cap.path)
        lang_counter[lang] = lang_counter.get(lang, 0) + 1

        all_deps.update(cap.dependencies)

        lower = cap.path.lower()
        if any(token in lower for token in ("main.py", "__main__.py", "index.ts", "index.js", "cli.py", "/cmd/", "/bin/", "app.py")):
            entry_points.append(cap.path)

    primary_language = max(lang_counter.items(), key=lambda kv: kv[1])[0] if lang_counter else "unknown"

    subsystems: list[dict] = []
    for name, values in sorted(by_subsystem.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        paths = sorted({v.path for v in values})[:20]
        symbols = sorted({s for v in values for s in v.key_symbols})[:20]
        summary = _summarize(" ".join(v.summary for v in values), max_chars=280)
        subsystems.append({"name": name, "paths": paths, "summary": summary, "key_symbols": symbols})

    test_hint = "has_tests" if any(c.chunk_type == "test" for c in capsules) else "no_tests_detected"
    architecture_summary = _summarize(
        " ".join(f"{sub['name']}: {sub['summary']}" for sub in subsystems[:5]),
        max_chars=500,
    )

    digest_key = "|".join(sorted(c.chunk_id for c in capsules))
    digest_id = hashlib.sha256(digest_key.encode("utf-8")).hexdigest()[:16]

    return RepoDigest(
        topic=topic,
        architecture_summary=architecture_summary,
        primary_language=primary_language,
        subsystems=subsystems,
        key_dependencies=sorted(all_deps)[:40],
        entry_points=sorted(set(entry_points))[:20],
        test_coverage_hint=test_hint,
        digest_id=digest_id,
    )


def build_repo_digest(material: RepositoryMaterial, topic: str = "Repository") -> RepoDigest:
    chunks = chunk_repository_material(material)
    capsules = extract_chunk_capsules(chunks)
    return reduce_capsules(capsules, topic=topic)
