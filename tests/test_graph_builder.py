from pathlib import Path

import pytest

from lms_llmsTxt.graph_builder import (
    build_repo_graph,
    emit_graph_files,
    to_force_graph,
    validate_semantic_graph,
)
from lms_llmsTxt.graph_models import RepoGraphNode, RepoSkillGraph
from lms_llmsTxt.repo_digest import RepoDigest


def test_build_repo_graph_from_llms_markdown_uses_sections_and_links():
    from lms_llmsTxt.graph_builder import build_repo_graph_from_llms_markdown

    graph = build_repo_graph_from_llms_markdown(
        """
# Example Project

## Core Runtime
- [Pipeline](https://github.com/acme/repo/blob/main/src/runtime/pipeline.py): coordinates staged generation.
- [Config](src/runtime/config.py): keeps runtime settings together.

## Tests
- [Runtime tests](tests/runtime/test_pipeline.py): validates pipeline behavior.
        """.strip()
    )

    labels = {node.label for node in graph.nodes}
    evidence_paths = {evidence.path for node in graph.nodes for evidence in node.evidence}

    assert graph.topic == "Example Project"
    assert "Core Runtime" in labels
    assert "Tests" in labels
    assert "src/runtime/pipeline.py" in evidence_paths
    assert "tests/runtime/test_pipeline.py" in evidence_paths


def test_graph_builder_emits_expected_files(tmp_path: Path):
    digest = RepoDigest(
        topic="Example Repo",
        architecture_summary="Core services and adapters",
        primary_language="python",
        subsystems=[
            {
                "name": "src/auth",
                "paths": ["src/auth/login.py"],
                "summary": "Authentication subsystem",
                "key_symbols": ["login", "logout"],
            }
        ],
        key_dependencies=["requests"],
        entry_points=["src/main.py"],
        test_coverage_hint="has_tests",
        digest_id="abc123",
    )

    graph = build_repo_graph(digest)
    assert graph.nodes[0].type == "moc"
    assert len(graph.nodes) >= 2
    paths = emit_graph_files(graph, tmp_path)
    assert (tmp_path / "repo.graph.json").exists()
    assert (tmp_path / "repo.force.json").exists()
    assert (tmp_path / "nodes" / "moc.md").exists()
    assert paths["graph_json"].endswith("repo.graph.json")


def test_repo_graph_adds_evidence_backed_topology_and_node_variety():
    digest = RepoDigest(
        topic="Example Repo",
        architecture_summary="CLI, auth, docs, and tests",
        primary_language="python",
        subsystems=[
            {
                "name": "src/auth",
                "paths": ["src/auth/login.py", "src/auth/tokens.py"],
                "summary": "Authentication source code",
                "key_symbols": ["login", "TokenStore"],
            },
            {
                "name": "tests/auth",
                "paths": ["tests/auth/test_login.py"],
                "summary": "Authentication regression coverage",
                "key_symbols": ["test_login", "TokenStore"],
            },
            {
                "name": "docs/auth-guide",
                "paths": ["docs/auth-guide.md"],
                "summary": "Authentication guide and usage pattern",
                "key_symbols": ["login"],
            },
            {
                "name": "cmd/example",
                "paths": ["cmd/example/cli.py"],
                "summary": "CLI entry point",
                "key_symbols": ["main"],
            },
        ],
        key_dependencies=["requests"],
        entry_points=["cmd/example/cli.py"],
        test_coverage_hint="has_tests",
        digest_id="abc123",
    )

    graph = build_repo_graph(digest)
    node_ids = {node.id for node in graph.nodes}
    non_moc_nodes = [node for node in graph.nodes if node.type != "moc"]

    assert graph.nodes[0].type == "moc"
    assert {node.type for node in non_moc_nodes} >= {"concept", "pattern", "gotcha"}
    assert any(node.links for node in non_moc_nodes)
    assert all(target in node_ids for node in graph.nodes for target in node.links)
    assert all("Related traversal" not in node.content for node in non_moc_nodes)
    assert all("This node is grounded in repository paths" not in node.content for node in non_moc_nodes)
    assert all("## Related concepts" not in node.content for node in non_moc_nodes)
    assert all("## Inspect first" not in node.content for node in non_moc_nodes)
    assert all("## Change risk" not in node.content for node in non_moc_nodes)
    assert any("[[" in node.content for node in non_moc_nodes if node.links)


def test_graph_validation_rejects_repeated_generic_section_template():
    graph = RepoSkillGraph(
        topic="Example Repo",
        nodes=[
            RepoGraphNode(
                id="moc",
                label="Example Repo Map",
                type="moc",
                description="Repository overview",
                content="# Example Repo\n\nA semantic overview of the repository.",
                links=["templated-node"],
            ),
            RepoGraphNode(
                id="templated-node",
                label="Templated Node",
                type="concept",
                description="A node with repeated template sections.",
                content=(
                    "---\n"
                    "title: Templated Node\n"
                    "type: concept\n"
                    "description: A node with repeated template sections.\n"
                    "---\n\n"
                    "# Templated Node\n\n"
                    "## Inspect first\n\n"
                    "This paragraph is long enough to look useful, but the repeated generic heading makes the graph feel templated rather than node-specific.\n\n"
                    "## Related concepts\n\n"
                    "This paragraph is also long enough to pass structure checks, but it keeps the same fixed section title used by every deterministic node.\n\n"
                    "## Change risk\n\n"
                    "This paragraph confirms the validator rejects the repeated header pattern that made generated graph nodes look identical."
                ),
                links=[],
            ),
        ],
    )

    with pytest.raises(ValueError, match="generic graph node section template"):
        validate_semantic_graph(graph)



def test_repo_digest_groups_varied_nested_workspace_shapes_deeply():
    from lms_llmsTxt.models import RepositoryMaterial
    from lms_llmsTxt.repo_digest import build_repo_digest

    material = RepositoryMaterial(
        repo_url="https://github.com/example/workspace",
        file_tree="\n".join(
            [
                "services/api/src/http/routes.py",
                "services/api/src/domain/orders.py",
                "packages/ui/src/components/Button.tsx",
                "packages/ui/src/theme/tokens.ts",
                "crates/engine/src/runtime/mod.rs",
                "tools/converter/source/adapters/claude.ts",
                "plugins/editor/app/commands/register.ts",
                "extensions/vscode/src/activation.ts",
                "examples/quickstart/src/main.py",
            ]
        ),
        readme_content="# Workspace\n\nNested services, packages, crates, tools, plugins, extensions, and examples.",
        package_files="",
        default_branch="main",
        is_private=False,
    )

    digest = build_repo_digest(material, topic="Workspace")
    subsystem_names = {subsystem["name"] for subsystem in digest.subsystems}

    assert "services/api/src/http" in subsystem_names
    assert "services/api/src/domain" in subsystem_names
    assert "packages/ui/src/components" in subsystem_names
    assert "packages/ui/src/theme" in subsystem_names
    assert "crates/engine/src/runtime" in subsystem_names
    assert "tools/converter/source/adapters" in subsystem_names
    assert "plugins/editor/app/commands" in subsystem_names
    assert "extensions/vscode/src/activation.ts" not in subsystem_names
    assert "extensions/vscode/src" in subsystem_names or "extensions/vscode" in subsystem_names
    assert "examples/quickstart/src" in subsystem_names or "examples/quickstart" in subsystem_names



def test_repo_digest_groups_apps_nested_runtime_domains_deeply():
    from lms_llmsTxt.models import RepositoryMaterial
    from lms_llmsTxt.repo_digest import build_repo_digest

    material = RepositoryMaterial(
        repo_url="https://github.com/example/polyglot",
        file_tree="\n".join(
            [
                "apps/planning-runtime/app/api/main.py",
                "apps/planning-runtime/app/api/routes.py",
                "apps/planning-runtime/app/domain/models.py",
                "apps/planning-runtime/app/orchestration/graph.py",
                "apps/planning-runtime/app/services/planner.py",
                "apps/planning-runtime/app/storage/db.py",
                "apps/toolkit-converter/src/cli/index.ts",
                "apps/toolkit-converter/src/discovery/inventory.ts",
                "apps/toolkit-converter/src/emitters/codex/agent-emitter.ts",
                "apps/toolkit-converter/src/source-adapters/claude-code/skills-parser.ts",
                "apps/toolkit-converter/src/validation/runner.ts",
            ]
        ),
        readme_content="# Polyglot\n\nA planning runtime and toolkit converter workspace.",
        package_files=(
            "=== selected evidence: apps/planning-runtime/app/orchestration/graph.py ===\n"
            "The planning runtime orchestration graph wires nodes and states for policy-driven planning flows.\n\n"
            "=== selected evidence: apps/toolkit-converter/src/source-adapters/claude-code/skills-parser.ts ===\n"
            "The toolkit converter parses Claude Code skills and lowers them into Codex-compatible assets."
        ),
        default_branch="main",
        is_private=False,
    )

    digest = build_repo_digest(material, topic="Polyglot Workspace")
    subsystem_names = {subsystem["name"] for subsystem in digest.subsystems}

    assert "apps/planning-runtime/app/api" in subsystem_names
    assert "apps/planning-runtime/app/domain" in subsystem_names
    assert "apps/planning-runtime/app/orchestration" in subsystem_names
    assert "apps/toolkit-converter/src/cli" in subsystem_names
    assert "apps/toolkit-converter/src/source-adapters" in subsystem_names

    graph = build_repo_graph(digest)
    evidence_paths = {evidence.path for node in graph.nodes for evidence in node.evidence}

    assert "apps/planning-runtime/app/orchestration/graph.py" in evidence_paths
    assert "apps/toolkit-converter/src/source-adapters/claude-code/skills-parser.ts" in evidence_paths



def test_repo_digest_groups_arbitrary_nested_project_roots():
    from lms_llmsTxt.models import RepositoryMaterial
    from lms_llmsTxt.repo_digest import build_repo_digest

    material = RepositoryMaterial(
        repo_url="https://github.com/example/nested",
        file_tree="\n".join(
            [
                "tools/converter/package.json",
                "tools/converter/src/cli/index.ts",
                "tools/converter/src/mapping/mapper.ts",
                "tools/converter/src/validation/runner.ts",
                "workspaces/runtime/pyproject.toml",
                "workspaces/runtime/app/api/main.py",
                "workspaces/runtime/app/domain/models.py",
                "vendor/embedded-engine/Cargo.toml",
                "vendor/embedded-engine/src/scheduler/mod.rs",
                "vendor/embedded-engine/src/storage/lib.rs",
            ]
        ),
        readme_content="# Nested\n\nMultiple nested projects in mixed containers.",
        package_files="",
        default_branch="main",
        is_private=False,
    )

    digest = build_repo_digest(material, topic="Nested Workspace")
    subsystem_names = {subsystem["name"] for subsystem in digest.subsystems}

    assert "tools/converter/src/cli" in subsystem_names
    assert "tools/converter/src/mapping" in subsystem_names
    assert "tools/converter/src/validation" in subsystem_names
    assert "workspaces/runtime/app/api" in subsystem_names
    assert "workspaces/runtime/app/domain" in subsystem_names
    assert "vendor/embedded-engine/src/scheduler" in subsystem_names
    assert "vendor/embedded-engine/src/storage" in subsystem_names



def test_polyglot_graph_selection_keeps_nested_project_roots():
    subsystems = [
        {
            "name": f"src/feature_{index}",
            "paths": [f"src/feature_{index}/module_{part}.py" for part in range(8)],
            "summary": "Large Python feature area",
            "key_symbols": ["run_feature"],
        }
        for index in range(24)
    ]
    subsystems.extend(
        [
            {
                "name": "packages/web",
                "paths": ["packages/web/package.json", "packages/web/src/App.tsx"],
                "summary": "Nested TypeScript web workspace",
                "key_symbols": ["App"],
            },
            {
                "name": "crates/engine",
                "paths": ["crates/engine/Cargo.toml", "crates/engine/src/lib.rs"],
                "summary": "Nested Rust engine crate",
                "key_symbols": ["Engine"],
            },
        ]
    )
    digest = RepoDigest(
        topic="Polyglot Repo",
        architecture_summary="Python core with nested TypeScript and Rust workspaces",
        primary_language="python",
        subsystems=subsystems,
        key_dependencies=[],
        entry_points=[],
        test_coverage_hint="no_tests_detected",
        digest_id="polyglot",
    )

    graph = build_repo_graph(digest)
    labels = {node.label for node in graph.nodes}
    evidence_paths = {evidence.path for node in graph.nodes for evidence in node.evidence}

    assert "Packages Web" in labels
    assert "Crates Engine" in labels
    assert "packages/web/package.json" in evidence_paths
    assert "crates/engine/Cargo.toml" in evidence_paths



def test_force_graph_uses_deduped_valid_edges_and_degree_sizing():
    digest = RepoDigest(
        topic="Example Repo",
        architecture_summary="Auth and tests",
        primary_language="python",
        subsystems=[
            {
                "name": "src/auth",
                "paths": ["src/auth/login.py"],
                "summary": "Authentication source code",
                "key_symbols": ["login"],
            },
            {
                "name": "tests/auth",
                "paths": ["tests/auth/test_login.py"],
                "summary": "Authentication tests",
                "key_symbols": ["login"],
            },
        ],
        key_dependencies=[],
        entry_points=[],
        test_coverage_hint="has_tests",
        digest_id="abc123",
    )

    graph = build_repo_graph(digest)
    force = to_force_graph(graph)
    edge_keys = {tuple(sorted((link.source, link.target))) for link in force.links}
    node_values = {node.id: node.val for node in force.nodes}

    assert len(force.links) == len(edge_keys)
    assert any(key == ("src-auth", "tests-auth") for key in edge_keys)
    assert node_values["src-auth"] > 1.5
    assert node_values["tests-auth"] > 1.5


def test_semantic_graph_validation_rejects_provenance_boilerplate():
    graph = RepoSkillGraph(
        topic="Example Repo",
        nodes=[
            RepoGraphNode(
                id="moc",
                label="Example Repo Map",
                type="moc",
                description="Repository overview",
                content="# Example Repo\n\nA semantic overview of the repository.",
                links=["bad-node"],
            ),
            RepoGraphNode(
                id="bad-node",
                label="Bad Node",
                type="concept",
                description="This node is grounded in repository paths.",
                content=(
                    "---\n"
                    "title: Bad Node\n"
                    "type: concept\n"
                    "description: Bad node\n"
                    "---\n\n"
                    "# Bad Node\n\n"
                    "This node is grounded in repository paths that indicate a concept role.\n\n"
                    "Another paragraph that would otherwise be long enough to pass structure validation."
                ),
                links=[],
            ),
        ],
    )

    with pytest.raises(ValueError, match="provenance boilerplate"):
        validate_semantic_graph(graph)


def test_repo_digest_uses_selected_evidence_content_for_graph_summaries():
    from lms_llmsTxt.models import RepositoryMaterial
    from lms_llmsTxt.repo_digest import build_repo_digest

    material = RepositoryMaterial(
        repo_url="https://github.com/example/repo",
        file_tree="docs/knowledge-base.md\ndocs/api-reference.md",
        readme_content="# Example\n\nA docs repo.",
        package_files=(
            "=== selected evidence: docs/knowledge-base.md ===\n"
            "Knowledge base integration connects local models to user-owned corpora. "
            "It explains retrieval, grounding, and answer workflows.\n\n"
            "=== selected evidence: docs/api-reference.md ===\n"
            "The API reference documents concrete methods, arguments, return shapes, "
            "and integration boundaries for SDK users."
        ),
        default_branch="main",
        is_private=False,
    )

    digest = build_repo_digest(material, topic="Docs")
    summaries = {subsystem["name"]: subsystem["summary"] for subsystem in digest.subsystems}

    assert "Knowledge base integration connects local models" in summaries["docs/knowledge-base.md"]
    assert "concrete methods" in summaries["docs/api-reference.md"]

    graph = build_repo_graph(digest)
    non_moc_content = "\n".join(node.content for node in graph.nodes if node.type != "moc")
    assert "Knowledge base integration connects local models" in non_moc_content
    assert "concrete methods" in non_moc_content
    assert "This area groups the behavior" not in non_moc_content
