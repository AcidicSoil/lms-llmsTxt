from lms_llmsTxt.models import RepositoryMaterial
from lms_llmsTxt.repo_digest import (
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

    reduced = apply_evidence_plan(material, plan)
    assert reduced.file_tree.splitlines() == plan.selected_paths


def test_suggested_evidence_limit_shrinks_under_budget_pressure():
    assert suggested_evidence_limit(estimated_prompt_tokens=500, available_tokens=1000) == 80
    assert suggested_evidence_limit(estimated_prompt_tokens=4000, available_tokens=1000) < 80
    assert suggested_evidence_limit(estimated_prompt_tokens=4000, available_tokens=1000) >= 20
