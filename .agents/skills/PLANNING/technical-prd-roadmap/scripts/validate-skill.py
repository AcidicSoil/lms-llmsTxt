#!/usr/bin/env python3
"""Lightweight validation for the technical-prd-roadmap skill bundle."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    skill = ROOT / "SKILL.md"
    if not skill.exists():
        fail("SKILL.md missing")

    text = skill.read_text(encoding="utf-8")
    if "name: technical-prd-roadmap" not in text:
        fail("frontmatter name missing or incorrect")
    if "description:" not in text or "WHEN:" not in text:
        fail("description must include WHEN triggers")

    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    missing = []
    for link in links:
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = (ROOT / link).resolve()
        if not str(target).startswith(str(ROOT.resolve())):
            missing.append(f"escapes skill root: {link}")
        elif not target.exists() or target.is_dir():
            missing.append(link)
    if missing:
        fail("bad links: " + ", ".join(missing))

    required = [
        "templates/base-prd-template.txt",
        "templates/rpg-prd-template.txt",
        "references/prd-generation-workflow.md",
        "references/rpg-method/README.md",
        "references/task-master-handoff.md",
        "references/checklists/prd-quality-checklist.md",
    ]
    for rel in required:
        if not (ROOT / rel).exists():
            fail(f"missing required file: {rel}")

    print("OK: skill bundle structure is valid")


if __name__ == "__main__":
    main()
