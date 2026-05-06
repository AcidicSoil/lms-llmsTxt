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


def test_generate_graph_short_flag_sets_generate_graph():
    from lms_llmsTxt.cli import build_parser

    args = build_parser().parse_args([
        "https://github.com/example/repo",
        "-g",
    ])

    assert args.generate_graph is True


def test_graph_safeguard_flags_parse():
    from lms_llmsTxt.cli import build_parser

    args = build_parser().parse_args([
        "https://github.com/example/repo",
        "-g",
        "--semantic-graph-mode",
        "fast",
        "--semantic-graph-timeout-seconds",
        "30",
        "--semantic-graph-max-output-tokens",
        "1024",
        "--lm-unload-timeout-seconds",
        "5",
        "--lm-ttl-seconds",
        "600",
        "--lm-context-length",
        "8192",
    ])

    assert args.generate_graph is True
    assert args.semantic_graph_mode == "fast"
    assert args.semantic_graph_timeout_seconds == 30
    assert args.semantic_graph_max_output_tokens == 1024
    assert args.lm_unload_timeout_seconds == 5
    assert args.lm_ttl_seconds == 600
    assert args.lm_context_length == 8192


def test_semantic_graph_short_flag_parse():
    from lms_llmsTxt.cli import build_parser

    args = build_parser().parse_args([
        "https://github.com/example/repo",
        "-g",
        "--semantic-graph",
    ])

    assert args.generate_graph is True
    assert args.semantic_graph is True


def test_semantic_graph_defaults_are_safe_without_env(tmp_path, monkeypatch):
    from lms_llmsTxt.config import AppConfig

    monkeypatch.delenv("SEMANTIC_GRAPH_MODE", raising=False)
    monkeypatch.delenv("SEMANTIC_GRAPH_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("SEMANTIC_GRAPH_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.chdir(tmp_path)

    config = AppConfig()

    assert config.semantic_graph_mode == "off"
    assert config.semantic_graph_timeout_seconds == 30
    assert config.semantic_graph_max_output_tokens == 768


def test_graph_synthesis_alias_parses_semantic_mode():
    from lms_llmsTxt.cli import build_parser

    args = build_parser().parse_args([
        "https://github.com/example/repo",
        "-g",
        "--graph-synthesis",
        "fast",
    ])

    assert args.generate_graph is True
    assert args.semantic_graph_mode == "fast"
