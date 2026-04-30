from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import re
from collections.abc import Callable, Iterable

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


@dataclass(slots=True)
class EvidencePlan:
    selected_paths: list[str]
    dropped_paths: list[str]
    selected_reasons: dict[str, str] = field(default_factory=dict)
    candidate_count: int = 0
    max_paths: int = 0
    selected_count: int = 0
    dropped_count: int = 0
    budget_reason: str = "within-limit"
    fetched_paths: list[str] = field(default_factory=list)
    fetch_skipped: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EvidenceFetchLimits:
    max_fetches: int = 8
    max_bytes_per_fetch: int = 8_000
    max_total_bytes: int = 24_000
    max_path_depth: int = 8


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


def _path_priority(path: str, repo_digest: RepoDigest) -> tuple[float, str]:
    lower = path.lower()
    depth_penalty = lower.count("/") * 0.1
    score = max(0.0, 10.0 - depth_penalty)
    reasons: list[str] = []

    if lower in {"readme.md", "readme.rst", "readme.txt"}:
        score += 120
        reasons.append("root-readme")
    if path in repo_digest.entry_points:
        score += 110
        reasons.append("entry-point")
    if any(token in lower for token in ("docs/", "guide", "tutorial", "example", "quickstart", "getting-started")):
        score += 60
        reasons.append("documentation")
    if lower.endswith(("pyproject.toml", "package.json", "requirements.txt", "package-lock.json", "pnpm-lock.yaml")):
        score += 55
        reasons.append("dependency-manifest")
    if lower.endswith(("/cli.py", "/app.py", "/main.py", "/__main__.py", "/index.ts", "/index.js")) or lower in {
        "cli.py",
        "app.py",
        "main.py",
        "__main__.py",
        "index.ts",
        "index.js",
    } or any(token in lower for token in ("/cmd/", "/bin/")):
        score += 50
        reasons.append("runtime-entry")
    if repo_digest.test_coverage_hint == "has_tests" and ("/test" in lower or lower.startswith("tests/") or "test_" in lower):
        score += 10
        reasons.append("tests")

    for subsystem in repo_digest.subsystems[:8]:
        subsystem_name = str(subsystem.get("name", "")).strip("/")
        if not subsystem_name or "/" not in subsystem_name:
            continue
        if "." in subsystem_name.rsplit("/", 1)[-1]:
            continue
        if path == subsystem_name or path.startswith(f"{subsystem_name}/"):
            score += 35
            reasons.append(f"subsystem:{subsystem_name}")
            break

    if _language_from_path(path) == repo_digest.primary_language:
        score += 10
        reasons.append(f"primary-language:{repo_digest.primary_language}")

    return score, ", ".join(reasons) or "fallback-ranking"


def plan_evidence_paths(
    material: RepositoryMaterial,
    repo_digest: RepoDigest,
    *,
    max_paths: int,
) -> EvidencePlan:
    paths = sorted({path.strip() for path in material.file_tree.splitlines() if path.strip()})
    candidate_count = len(paths)
    if not paths or len(paths) <= max_paths:
        return EvidencePlan(
            selected_paths=paths,
            dropped_paths=[],
            candidate_count=candidate_count,
            max_paths=max_paths,
            selected_count=candidate_count,
            dropped_count=0,
            budget_reason="within-limit",
        )

    ranked: list[tuple[float, str, str]] = []
    for path in paths:
        score, reason = _path_priority(path, repo_digest)
        ranked.append((score, path, reason))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = ranked[:max_paths]
    dropped = ranked[max_paths:]
    return EvidencePlan(
        selected_paths=[path for _, path, _ in selected],
        dropped_paths=[path for _, path, _ in dropped],
        selected_reasons={path: reason for _, path, reason in selected},
        candidate_count=candidate_count,
        max_paths=max_paths,
        selected_count=len(selected),
        dropped_count=len(dropped),
        budget_reason="candidate-count-exceeds-limit",
    )


def apply_evidence_plan(
    material: RepositoryMaterial,
    plan: EvidencePlan,
    *,
    fetch_content: Callable[[str], str | None] | None = None,
    limits: EvidenceFetchLimits = EvidenceFetchLimits(),
) -> RepositoryMaterial:
    selected_tree = "\n".join(plan.selected_paths)
    package_files = material.package_files

    if fetch_content is not None and limits.max_fetches > 0 and limits.max_total_bytes > 0:
        fetched_blocks: list[str] = []
        total_bytes = 0
        for path in plan.selected_paths[: limits.max_fetches]:
            if path.count("/") > limits.max_path_depth:
                plan.fetch_skipped.append({"path": path, "reason": "depth-limited"})
                continue

            content = fetch_content(path)
            if not content:
                plan.fetch_skipped.append({"path": path, "reason": "empty-or-unavailable"})
                continue

            encoded = content.encode("utf-8", "replace")
            if total_bytes >= limits.max_total_bytes:
                plan.fetch_skipped.append({"path": path, "reason": "total-byte-limit"})
                continue

            remaining = limits.max_total_bytes - total_bytes
            capped = encoded[: min(limits.max_bytes_per_fetch, remaining)].decode("utf-8", "replace")
            total_bytes += len(capped.encode("utf-8"))
            plan.fetched_paths.append(path)
            fetched_blocks.append(f"=== selected evidence: {path} ===\n{capped}")

        if fetched_blocks:
            package_files = "\n\n".join(part for part in [package_files, *fetched_blocks] if part)

    return RepositoryMaterial(
        repo_url=material.repo_url,
        file_tree=selected_tree,
        readme_content=material.readme_content,
        package_files=package_files,
        default_branch=material.default_branch,
        is_private=material.is_private,
    )


def suggested_evidence_limit(estimated_prompt_tokens: int, available_tokens: int) -> int:
    if available_tokens <= 0:
        return 20
    pressure = estimated_prompt_tokens / available_tokens
    if pressure <= 1:
        return 80
    scaled = max(20, int(80 / math.ceil(pressure)))
    return min(80, scaled)


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
        if lower.endswith(("/main.py", "/__main__.py", "/index.ts", "/index.js", "/cli.py", "/app.py")) or lower in {
            "main.py",
            "__main__.py",
            "index.ts",
            "index.js",
            "cli.py",
            "app.py",
        } or any(token in lower for token in ("/cmd/", "/bin/")):
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
