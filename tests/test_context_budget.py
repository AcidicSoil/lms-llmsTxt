from types import SimpleNamespace

from lms_llmsTxt.context_budget import BudgetDecision, build_context_budget, validate_budget
from lms_llmsTxt.models import RepositoryMaterial


def _config(max_context=1000, output=200, headroom=0.1):
    return SimpleNamespace(
        max_context_tokens=max_context,
        max_output_tokens=output,
        context_headroom_ratio=headroom,
        max_file_tree_lines=200,
        max_readme_chars=10000,
        max_package_chars=10000,
    )


def test_budget_approved_for_small_payload():
    material = RepositoryMaterial(
        repo_url="x",
        file_tree="a.py\nb.py",
        readme_content="small",
        package_files="pkg",
        default_branch="main",
        is_private=False,
    )
    budget = build_context_budget(_config(), material)
    assert budget.decision == BudgetDecision.APPROVED
    assert budget.available_tokens == 700


def test_validate_budget_states():
    material = RepositoryMaterial(
        repo_url="x",
        file_tree="\n".join([f"f{i}.py" for i in range(1000)]),
        readme_content="x" * 10000,
        package_files="y" * 10000,
        default_branch="main",
        is_private=False,
    )
    budget = build_context_budget(_config(max_context=1200, output=100, headroom=0.1), material)
    assert validate_budget(budget) in (BudgetDecision.NEEDS_COMPACTION, BudgetDecision.REJECTED)
