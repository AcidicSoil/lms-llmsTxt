# Release Runbook

## Prerequisites

1. **PyPI Account**: You must have an account on [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org).
2. **Permissions**: Ensure you are a maintainer on the PyPI project `lmstudio-llmstxt-generator`.
3. **Trusted Publishing**: The project uses GitHub Actions OIDC. Ensure the GitHub Environment `pypi` is configured in repository settings.

## Versioning

The project uses **dynamic versioning** (`setuptools_scm`).
**Do not** edit `pyproject.toml` to bump versions. The version is derived automatically from Git tags.

## Production Release

1. **Tagging**: Create and push a tag starting with `v`.
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```
2. **Workflow**: The `Release` workflow will automatically build and publish to PyPI.

## TestPyPI Release (Manual)

To test a release candidate:

1. **Tag**: Push a dev tag (optional, but recommended for clean versions).
   ```bash
   git tag v0.1.2.dev1
   git push origin v0.1.2.dev1
   ```
2. **Trigger**:
   - Go to [Actions -> Publish to TestPyPI](https://github.com/lmstudio-ai/lms-llmsTxt/actions/workflows/publish-testpypi.yml).
   - Run workflow using the tag (e.g., `v0.1.2.dev1`) or branch.