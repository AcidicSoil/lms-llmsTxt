from __future__ import annotations

from dataclasses import fields

from lms_llmsTxt import cli
from lms_llmsTxt.fallback import fallback_llms_payload, fallback_markdown_from_payload
from lms_llmsTxt.models import GenerationArtifacts
from lms_llmsTxt.rlm_evaluation import ExplorationLimits


def test_generation_artifacts_contract_retains_expected_fields() -> None:
    field_names = [field.name for field in fields(GenerationArtifacts)]

    assert field_names == [
        "llms_txt_path",
        "llms_full_path",
        "ctx_path",
        "json_path",
        "graph_json_path",
        "force_graph_path",
        "graph_nodes_dir",
        "trace_path",
        "used_fallback",
        "fallback_reason",
    ]


def test_cli_contract_exposes_existing_flags_without_rlm_rollout_flag() -> None:
    parser = cli.build_parser()
    help_text = parser.format_help()

    for flag in (
        "--output-dir",
        "--model",
        "--generate-graph",
        "--graph-only",
        "--enable-session-memory",
        "--ui",
        "--ui-no-open",
    ):
        assert flag in help_text

    assert "--rlm" not in help_text
    assert "--recursive-language-model" not in help_text


def test_fallback_payload_and_markdown_contract_remain_separate_from_rlm_scaffold() -> None:
    payload = fallback_llms_payload(
        repo_name="Example Repo",
        repo_url="https://github.com/acme/example",
        file_tree="README.md\nsrc/example.py",
        readme_content="# Example Repo\n\nA useful package.",
        default_branch="main",
    )
    markdown = fallback_markdown_from_payload("Example Repo", payload)

    assert payload["schema"]["title"] == "llmsTxtDocument"
    assert payload["project"]["name"] == "Example Repo"
    assert "<!-- Generated via fallback path (no LM). -->" in markdown
    assert "RLM" not in markdown


def test_optional_rlm_scaffold_is_not_wired_into_cli_or_fallback_contracts() -> None:
    limits = ExplorationLimits(max_depth=2, max_files=3, max_total_chars=10_000)

    assert limits.max_depth == 2
    assert cli.build_parser().prog == "lmstxt"
    assert GenerationArtifacts(llms_txt_path="out/llms.txt").used_fallback is False
