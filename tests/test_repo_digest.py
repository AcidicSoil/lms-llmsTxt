from lms_llmsTxt.models import RepositoryMaterial
from lms_llmsTxt.repo_digest import build_repo_digest, chunk_repository_material, extract_chunk_capsules, reduce_capsules


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
