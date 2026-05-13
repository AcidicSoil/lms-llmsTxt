from __future__ import annotations

import json

from lms_llmsTxt.config import AppConfig
from lms_llmsTxt.graph_builder import build_repo_graph
from lms_llmsTxt.graph_dspy_synthesizer import enrich_repo_graph_with_dspy
from lms_llmsTxt.models import RepositoryMaterial
from lms_llmsTxt.repo_digest import build_repo_digest


def _material() -> RepositoryMaterial:
    return RepositoryMaterial(
        repo_url="https://github.com/example/app",
        file_tree="src/contexts/I18nContext.tsx\nsrc/contexts/ShortcutsContext.tsx\nsrc/contexts/ThemeContext.tsx",
        readme_content="# App\n\nA React app with shared UI state contexts.",
        package_files=(
            "=== selected evidence: src/contexts/I18nContext.tsx ===\n"
            "I18nContext stores the active locale and exposes translation helpers so route components render language-specific labels without passing props through every layer.\n\n"
            "=== selected evidence: src/contexts/ShortcutsContext.tsx ===\n"
            "ShortcutsContext registers global keyboard accelerators and cleans them up when views unmount, preventing stale handlers from firing in the wrong screen.\n\n"
            "=== selected evidence: src/contexts/ThemeContext.tsx ===\n"
            "ThemeContext persists light and dark mode preference and synchronizes it with the document root class before components paint."
        ),
        default_branch="main",
        is_private=False,
    )


def test_dspy_graph_enrichment_applies_specific_node_content(monkeypatch):
    material = _material()
    digest = build_repo_digest(material, topic="Example App")
    graph = build_repo_graph(digest)
    target = next(node for node in graph.nodes if node.type != "moc")

    class FakeModule:
        def __call__(self, **kwargs):
            payload = [
                {
                    "id": target.id,
                    "label": "Shared UI State Contexts",
                    "description": "Explains how React context providers centralize locale, keyboard shortcut, and theme state for the app shell.",
                    "content": (
                        "Shared UI State Contexts coordinate cross-cutting interface behavior that many screens need but should not each reimplement. "
                        "The evidence shows locale helpers, keyboard accelerator registration, and theme persistence living together under context providers, so the useful mental model is app-shell state rather than a generic source folder. "
                        "A developer should inspect this concept when a feature changes visible language, global keyboard behavior, or dark-mode rendering because each change can affect unrelated routes.\n\n"
                        "The failure mode is stale shared state: a shortcut handler can fire after its view unmounts, the wrong locale can leak into labels, or the document theme class can update too late and cause flicker. "
                        "Review `I18nContext`, `ShortcutsContext`, and `ThemeContext` together because they each mediate user-facing state outside individual components."
                    ),
                }
            ]
            return type("Prediction", (), {"node_updates_json": json.dumps(payload)})()

    monkeypatch.setattr("lms_llmsTxt.graph_dspy_synthesizer.RepoGraphDSPySynthesizer", lambda: FakeModule())

    enriched = enrich_repo_graph_with_dspy(graph, digest, material, AppConfig(lm_model="test-model"))
    updated = next(node for node in enriched.nodes if node.id == target.id)

    assert updated.label == "Shared UI State Contexts"
    assert "keyboard accelerator" in updated.content
    assert "Explains the role" not in updated.content
    assert "nearby files depend" not in updated.content


def test_dspy_graph_enrichment_calls_model_once_per_node(monkeypatch):
    material = _material()
    digest = build_repo_digest(material, topic="Example App")
    graph = build_repo_graph(digest)
    non_moc_nodes = [node for node in graph.nodes if node.type != "moc"]
    seen_specs: list[list[dict]] = []

    class FakeModule:
        def __call__(self, **kwargs):
            specs = json.loads(kwargs["node_specs_json"])
            seen_specs.append(specs)
            node_id = specs[0]["id"]
            payload = [
                {
                    "id": node_id,
                    "label": f"Specific {node_id}",
                    "description": f"Specific node {node_id} explains a distinct React context responsibility using concrete provider evidence.",
                    "content": (
                        f"Specific {node_id} owns a distinct slice of shared interface state, and this paragraph names that node so the graph cannot reuse a single generic header for every card. "
                        "Its provider evidence points to concrete behavior such as locale helpers, keyboard registration, or document theme synchronization, which makes the relationship useful before editing. "
                        "Developers should compare the cited source excerpt with connected nodes to see whether a UI state change crosses route, shell, or rendering boundaries.\n\n"
                        f"The second {node_id} paragraph explains change risk in unique terms rather than repeating a batched summary. "
                        "Incorrect edits can leak stale handlers, paint the wrong theme, or display labels in the wrong language, so this node needs individual reasoning from the model. "
                        "That per-node synthesis keeps graph descriptions aligned with their own evidence and relationships."
                    ),
                }
            ]
            return type("Prediction", (), {"node_updates_json": json.dumps(payload)})()

    monkeypatch.setattr("lms_llmsTxt.graph_dspy_synthesizer.RepoGraphDSPySynthesizer", lambda: FakeModule())

    enrich_repo_graph_with_dspy(graph, digest, material, AppConfig(lm_model="test-model"))

    assert len(seen_specs) == len(non_moc_nodes)
    assert all(len(specs) == 1 for specs in seen_specs)
    assert {specs[0]["id"] for specs in seen_specs} == {node.id for node in non_moc_nodes}


def test_dspy_graph_enrichment_rejects_generic_node_content(monkeypatch):
    material = _material()
    digest = build_repo_digest(material, topic="Example App")
    graph = build_repo_graph(digest)
    target = next(node for node in graph.nodes if node.type != "moc")

    class FakeModule:
        def __call__(self, **kwargs):
            payload = [
                {
                    "id": target.id,
                    "label": "Src Contexts",
                    "description": "Explains the role Src Contexts plays in the repository and how nearby files depend on that concept.",
                    "content": "Explains the role Src Contexts plays in the repository and how nearby files depend on that concept.",
                }
            ]
            return type("Prediction", (), {"node_updates_json": json.dumps(payload)})()

    monkeypatch.setattr("lms_llmsTxt.graph_dspy_synthesizer.RepoGraphDSPySynthesizer", lambda: FakeModule())

    enriched = enrich_repo_graph_with_dspy(graph, digest, material, AppConfig(lm_model="test-model"))
    updated = next(node for node in enriched.nodes if node.id == target.id)

    assert updated.label == target.label
    assert "nearby files depend on that concept" not in updated.content
