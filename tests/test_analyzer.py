from __future__ import annotations

from lmstudiotxt_generator import analyzer


def test_build_dynamic_buckets_uses_default_branch_and_filters_dead_links(monkeypatch):
    recorded = []

    def fake_construct(repo_url, path, ref=None, style="blob"):
        recorded.append((repo_url, path, ref, style))
        return f"https://example.com/{ref or 'none'}/{path}"

    monkeypatch.setattr(analyzer, "construct_github_file_url", fake_construct)
    monkeypatch.setattr(analyzer, "_url_alive", lambda url: "keep" in url)

    file_tree = "docs/keep.md\nREADME.md\ntrash/missing.md"
    buckets = analyzer.build_dynamic_buckets(
        "https://github.com/example/repo",
        file_tree,
        default_ref="custom-branch",
        validate_urls=True,
    )

    # Only the URL containing 'keep' should remain after validation.
    assert any("keep.md" in url for _, items in buckets for _, url, _ in items)
    assert all("missing.md" not in url for _, items in buckets for _, url, _ in items)
    # construct_raw_url should receive the explicit default branch.
    assert all(ref == "custom-branch" for _, _, ref, _ in recorded if ref is not None)
