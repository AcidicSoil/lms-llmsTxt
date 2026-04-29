from lms_llmsTxt.models import RepositoryMaterial
from lms_llmsTxt.repo_digest import (
    EvidenceFetchLimits,
    apply_evidence_plan,
    build_repo_digest,
    chunk_repository_material,
    extract_chunk_capsules,
    plan_evidence_paths,
    reduce_capsules,
    suggested_evidence_limit,
)


def test_digest_pipeline_is_stable():
    material = RepositoryMaterial(
        repo_url="https://github.com/example/repo",
        file_tree="src/main.py\nsrc/auth/login.py\ntests/test_auth.py\nREADME.md",
        readme_content="# Repo\n\nSample",
        package_files="import requests\nfrom pydantic import BaseModel",
        default_branch="main",
        is_private=False,
    )
    digest1 = build_repo_digest(material, topic="Repo")
    digest2 = build_repo_digest(material, topic="Repo")
    assert digest1.digest_id == digest2.digest_id
    assert digest1.subsystems == digest2.subsystems


def test_extract_capsules_and_reduce_empty():
    material = RepositoryMaterial(
        repo_url="x",
        file_tree="",
        readme_content="",
        package_files="",
        default_branch="main",
        is_private=False,
    )
    chunks = chunk_repository_material(material)
    capsules = extract_chunk_capsules(chunks)
    digest = reduce_capsules(capsules, topic="Empty")
    assert digest.topic == "Empty"


def test_plan_evidence_paths_prioritizes_docs_and_entry_points():
    material = RepositoryMaterial(
        repo_url="https://github.com/example/repo",
        file_tree=(
            "README.md\n"
            "docs/getting-started.md\n"
            "src/cli.py\n"
            "src/internal/worker.py\n"
            "tests/test_cli.py\n"
            "notes/todo.txt"
        ),
        readme_content="# Repo\n\nSample",
        package_files="[project]\nname='repo'",
        default_branch="main",
        is_private=False,
    )
    digest = build_repo_digest(material, topic="Repo")
    plan = plan_evidence_paths(material, digest, max_paths=3)

    assert "README.md" in plan.selected_paths
    assert "docs/getting-started.md" in plan.selected_paths
    assert "src/cli.py" in plan.selected_paths
    assert "src/internal/worker.py" in plan.dropped_paths
    assert plan.candidate_count == 6
    assert plan.max_paths == 3
    assert plan.selected_count == 3
    assert plan.dropped_count == 3
    assert plan.budget_reason == "candidate-count-exceeds-limit"

    reduced = apply_evidence_plan(material, plan)
    assert reduced.file_tree.splitlines() == plan.selected_paths


def test_apply_evidence_plan_fetches_selected_content_with_limits():
    material = RepositoryMaterial(
        repo_url="https://github.com/example/repo",
        file_tree="README.md\ndocs/guide.md\nsrc/cli.py",
        readme_content="# Repo\n\nSample",
        package_files="[project]\nname='repo'",
        default_branch="main",
        is_private=False,
    )
    digest = build_repo_digest(material, topic="Repo")
    plan = plan_evidence_paths(material, digest, max_paths=3)

    fetched = []

    def fetch_content(path: str) -> str | None:
        fetched.append(path)
        return f"content for {path}" * 20

    reduced = apply_evidence_plan(
        material,
        plan,
        fetch_content=fetch_content,
        limits=EvidenceFetchLimits(max_fetches=2, max_bytes_per_fetch=32, max_total_bytes=48),
    )

    assert fetched == plan.selected_paths[:2]
    assert plan.fetched_paths == plan.selected_paths[:2]
    assert "=== selected evidence:" in reduced.package_files
    assert plan.selected_paths[0] in reduced.package_files
    assert len(reduced.package_files.encode("utf-8")) < len(material.package_files.encode("utf-8")) + 300


def test_plan_evidence_paths_records_within_limit_budget_metadata():
    material = RepositoryMaterial(
        repo_url="https://github.com/example/repo",
        file_tree="README.md\nsrc/cli.py",
        readme_content="# Repo\n\nSample",
        package_files="[project]\nname='repo'",
        default_branch="main",
        is_private=False,
    )
    digest = build_repo_digest(material, topic="Repo")
    plan = plan_evidence_paths(material, digest, max_paths=10)

    assert plan.selected_paths == ["README.md", "src/cli.py"]
    assert plan.dropped_paths == []
    assert plan.candidate_count == 2
    assert plan.max_paths == 10
    assert plan.selected_count == 2
    assert plan.dropped_count == 0
    assert plan.budget_reason == "within-limit"


def test_suggested_evidence_limit_shrinks_under_budget_pressure():
    assert suggested_evidence_limit(estimated_prompt_tokens=500, available_tokens=1000) == 80
    assert suggested_evidence_limit(estimated_prompt_tokens=4000, available_tokens=1000) < 80
    assert suggested_evidence_limit(estimated_prompt_tokens=4000, available_tokens=1000) >= 20
