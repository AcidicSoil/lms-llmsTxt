from lms_llmsTxt.github import is_default_ignored_repo_path


def test_default_ignored_repo_paths_exclude_agent_skill_trees() -> None:
    assert is_default_ignored_repo_path(".agents/skills/python/SKILL.md") is True
    assert is_default_ignored_repo_path(".serena/memories/project.md") is True
    assert is_default_ignored_repo_path("src/lms_llmsTxt/cli.py") is False
