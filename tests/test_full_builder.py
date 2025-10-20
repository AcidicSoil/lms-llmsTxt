from __future__ import annotations

import requests

from lmstudiotxt_generator import full_builder


def _curated_link(ref: str = "main") -> str:
    return f"- [Example](https://github.com/owner/repo/blob/{ref}/dir/file.py)"


def test_build_llms_full_prefers_raw(monkeypatch):
    captured = {}

    def fake_fetch_raw(owner, repo, path, ref):
        captured["call"] = (owner, repo, path, ref)
        return b"print('hello world')\n"

    def explode(*args, **kwargs):
        raise AssertionError("gh_get_file should not be used for public repos")

    monkeypatch.setattr(full_builder, "fetch_raw_file", fake_fetch_raw)
    monkeypatch.setattr(full_builder, "gh_get_file", explode)

    output = full_builder.build_llms_full_from_repo(
        _curated_link(),
        prefer_raw=True,
        default_ref="main",
    )

    assert captured["call"] == ("owner", "repo", "dir/file.py", "main")
    assert "print('hello world')" in output


def test_build_llms_full_private_repo_uses_api(monkeypatch):
    def fake_fetch_raw(*args, **kwargs):
        raise AssertionError("fetch_raw_file should not be used for private repos")

    def fake_gh_get(owner, repo, path, ref, token):
        assert token == "token-123"
        assert ref == "main"
        return "file", b"api-content\n"

    monkeypatch.setattr(full_builder, "fetch_raw_file", fake_fetch_raw)
    monkeypatch.setattr(full_builder, "gh_get_file", fake_gh_get)

    output = full_builder.build_llms_full_from_repo(
        _curated_link(),
        prefer_raw=False,
        default_ref="main",
        token="token-123",
    )

    assert "api-content" in output


def test_build_llms_full_403_hint(monkeypatch):
    def fake_fetch_raw(*args, **kwargs):
        raise AssertionError("fetch_raw_file should not be used when prefer_raw=False")

    def fake_gh_get(owner, repo, path, ref, token):
        response = requests.Response()
        response.status_code = 403
        response.reason = "Forbidden"
        http_error = requests.HTTPError("Forbidden")
        http_error.response = response
        raise http_error

    monkeypatch.setattr(full_builder, "fetch_raw_file", fake_fetch_raw)
    monkeypatch.setattr(full_builder, "gh_get_file", fake_gh_get)

    output = full_builder.build_llms_full_from_repo(
        _curated_link(),
        prefer_raw=False,
        default_ref="main",
        token="token-123",
    )

    assert "HTTP 403 Forbidden" in output
    assert "Verify that GITHUB_ACCESS_TOKEN or GH_TOKEN" in output
