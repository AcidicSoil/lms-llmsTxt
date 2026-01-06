## Checklist: rename the distribution in `pyproject.toml`

Current state: your distribution name is `lmstudio-lmstxt-generator`, and you expose two CLI commands via `[project.scripts]`: `lmstxt` and `lmstxt-mcp`.

* [ ] **Pick the new distribution name** (the thing users `pip install ...`, and what shows up on PyPI). This is `[project].name` per PEP 621. ([Python Enhancement Proposals (PEPs)][1])

  * [ ] Prefer something short and aligned with how users run it (e.g., aligned with `lmstxt-mcp` or `lmstxt`) to reduce “package name vs command name” confusion.

* [ ] **Validate name rules + normalization behavior before you commit**

  * [ ] Ensure it matches allowed characters/format for the `name` field. ([Python Packaging][2])
  * [ ] Check normalization/collision risk: comparisons normalize case and treat runs of `.`, `-`, `_` equivalently (important for “too similar”/conflicts). ([Python Packaging][3])
  * [ ] Confirm availability on PyPI (and that it doesn’t trigger the “too similar” filter). ([Python Packaging][3])

* [ ] **Change the distribution name**

  * [ ] Update `pyproject.toml` → `[project].name = "<new-name>"`.
  * [ ] Keep it **static** (PEP 621 requires `name` not be dynamic). ([Python Packaging][2])

* [ ] **Decide whether to rename CLI commands**

  * [ ] Review `[project.scripts]` keys (they are the actual installed command names). ([Python Packaging][4])
  * [ ] If you want command names to change, update:

    * the **script key** (command name)
    * and/or the module:function target if you also rename Python packages/modules
       ([Python Packaging][4])

* [ ] **Decide whether to rename import package/module names**

  * [ ] If you **only** want easier install/discovery: you can change `[project].name` without renaming `src/` packages (distribution name and import name can differ).
  * [ ] If you want full consistency: rename modules under `src/` and update imports + script entry points accordingly. ([Python Packaging][4])

* [ ] **If you already published the old name to PyPI: plan a proper rename migration**

  * [ ] You generally can’t “rename” a project as an owner; the typical approach is: publish under the new name, then ship a final release under the old name that points users to the new one (and can depend on it). ([Discussions on Python.org][5])

* [ ] **Update docs + discovery surfaces**

  * [ ] README install/run snippets (pip/pipx/uvx), and any references to the old distribution name. ([Python Packaging][2])
  * [ ] Repo badges, examples, and any “copy-paste” commands.

* [ ] **Update release automation**

  * [ ] Any CI/CD “publish to PyPI” config that references the project name (Trusted Publisher, workflow environment variables, release scripts). ([Python Enhancement Proposals (PEPs)][1])

* [ ] **Verify locally**

  * [ ] Build: `python -m build`
  * [ ] Install the wheel in a clean venv and run:

    * `lmstxt --help`
    * `lmstxt-mcp`
      (ensures metadata + entry points are correct). ([Python Packaging][4])

[1]: https://peps.python.org/pep-0621/?utm_source=chatgpt.com "PEP 621 – Storing project metadata in pyproject.toml"
[2]: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/?utm_source=chatgpt.com "Writing your pyproject.toml - Python Packaging User Guide"
[3]: https://packaging.python.org/en/latest/specifications/name-normalization/?utm_source=chatgpt.com "Names and normalization"
[4]: https://packaging.python.org/specifications/entry-points/?utm_source=chatgpt.com "Entry points specification"
[5]: https://discuss.python.org/t/how-can-we-petition-for-removal-of-a-defunct-unmaintained-project-in-pypi/91836?utm_source=chatgpt.com "How can we petition for removal of a defunct/unmaintained ..."
