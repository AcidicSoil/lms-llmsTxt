import argparse
import logging
import sys
from pathlib import Path
from textwrap import dedent

from .config import AppConfig
from .pipeline import run_generation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lmstxt",
        description="Generate llms.txt artifacts for a GitHub repository using LM Studio.",
    )
    parser.add_argument("repo", help="GitHub repository URL (https://github.com/<owner>/<repo>)")
    parser.add_argument(
        "--model",
        help="LM Studio model identifier (overrides LMSTUDIO_MODEL).",
    )
    parser.add_argument(
        "--api-base",
        help="LM Studio API base URL (overrides LMSTUDIO_BASE_URL).",
    )
    parser.add_argument(
        "--api-key",
        help="LM Studio API key (overrides LMSTUDIO_API_KEY).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where artifacts will be written (default: OUTPUT_DIR or ./artifacts).",
    )
    parser.add_argument(
        "--link-style",
        choices=["blob", "raw"],
        help="Style of GitHub file links to generate (default: blob).",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Append a UTC timestamp comment to generated files.",
    )
    parser.add_argument(
        "--no-ctx",
        action="store_true",
        help="Skip generating llms-ctx.txt even if ENABLE_CTX is set.",
    )
    parser.add_argument(
        "--cache-lm",
        action="store_true",
        help="Enable DSPy's LM cache (useful for repeated experiments).",
    )
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        help="Maximum context tokens budget for prompt construction.",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Reserved output token budget.",
    )
    parser.add_argument(
        "--context-headroom",
        type=float,
        help="Headroom ratio reserved from context window (e.g. 0.15).",
    )
    parser.add_argument(
        "--generate-graph",
        action="store_true",
        help="Generate repository graph artifacts (repo.graph.json, repo.force.json, nodes/*.md).",
    )
    parser.add_argument(
        "--graph-only",
        action="store_true",
        help="Skip llms-full generation and only produce llms.txt (+ optional graph artifacts).",
    )
    parser.add_argument(
        "--enable-session-memory",
        action="store_true",
        help="Record append-only generation events for LCM-style session memory.",
    )
    parser.add_argument(
        "--verbose-budget",
        action="store_true",
        help="Log context budget and retry reductions.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)

    config = AppConfig()
    if args.model:
        config.lm_model = args.model
    if args.api_base:
        config.lm_api_base = str(args.api_base)
    if args.api_key:
        config.lm_api_key = args.api_key
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.link_style:
        config.link_style = args.link_style
    if args.no_ctx:
        config.enable_ctx = False
    if args.max_context_tokens is not None:
        config.max_context_tokens = args.max_context_tokens
    if args.max_output_tokens is not None:
        config.max_output_tokens = args.max_output_tokens
    if args.context_headroom is not None:
        config.context_headroom_ratio = args.context_headroom
    if args.generate_graph:
        config.enable_repo_graph = True
    if args.enable_session_memory:
        config.enable_session_memory = True

    try:
        artifacts = run_generation(
            repo_url=args.repo,
            config=config,
            stamp=bool(args.stamp),
            cache_lm=bool(args.cache_lm),
            generate_graph=bool(args.generate_graph),
            graph_only=bool(args.graph_only),
            verbose_budget=bool(args.verbose_budget),
            enable_session_memory=bool(args.enable_session_memory),
        )
    except Exception as exc:
        parser.error(str(exc))
        return 2

    summary = dedent(
        f"""\
        Artifacts written:
          - {artifacts.llms_txt_path}
          - {artifacts.llms_full_path}
        """
    ).rstrip()

    if artifacts.ctx_path:
        summary += f"\n  - {artifacts.ctx_path}"
    if artifacts.json_path:
        summary += f"\n  - {artifacts.json_path}"
    if artifacts.graph_json_path:
        summary += f"\n  - {artifacts.graph_json_path}"
    if artifacts.force_graph_path:
        summary += f"\n  - {artifacts.force_graph_path}"
    if artifacts.graph_nodes_dir:
        summary += f"\n  - {artifacts.graph_nodes_dir}"
    if artifacts.used_fallback:
        summary += "\n(note) LM call failed; fallback JSON/schema output was used."

    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
