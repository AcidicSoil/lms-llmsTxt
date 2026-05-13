#!/usr/bin/env python3
"""Generic manifest-vs-artifact delta indexer.

Adapt `extract_key()` and the status-marker path if the target project uses
custom fields or names. This script intentionally has no project-specific terms.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HANDLED_STATUSES = {"captured", "captured_empty", "completed"}


def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = None
        for key in ("data", "items", "projects", "entries"):
            if isinstance(data.get(key), list):
                items = data[key]
                break
        if items is None:
            raise ValueError("manifest object must contain a list field such as data or items")
    else:
        raise ValueError("manifest must be a JSON array or object wrapper")
    return [item if isinstance(item, dict) else {"value": item} for item in items]


def extract_key(item: dict[str, Any]) -> str | None:
    for key in ("id", "url", "key", "item_key", "project_internal_url", "value"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def iter_status_markers(run_roots: list[Path]):
    for root in run_roots:
        for marker in root.glob("artifacts/*/scan_status.json"):
            try:
                yield marker, json.loads(marker.read_text())
            except Exception:
                continue


def main() -> int:
    parser = argparse.ArgumentParser(description="Build missing-item manifest from run artifact status markers.")
    parser.add_argument("run_roots", nargs="+", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--missing-out", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest_items = load_manifest(args.manifest)
    manifest_by_key = {}
    for item in manifest_items:
        key = extract_key(item)
        if key:
            manifest_by_key[key] = item

    handled = {}
    failed = {}
    for marker_path, status in iter_status_markers(args.run_roots):
        key = status.get("item_key")
        state = status.get("status")
        if not key:
            continue
        record = {"status": state, "marker": str(marker_path)}
        if state in HANDLED_STATUSES:
            handled[key] = record
        else:
            failed[key] = record

    missing = [item for key, item in manifest_by_key.items() if key not in handled]
    payload = {
        "schema_version": "1.0.0",
        "artifact_type": "delta-manifest",
        "data": missing,
    }
    args.missing_out.parent.mkdir(parents=True, exist_ok=True)
    args.missing_out.write_text(json.dumps(payload, indent=2) + "\n")

    index = {
        "manifest_count": len(manifest_by_key),
        "handled_count": len([k for k in handled if k in manifest_by_key]),
        "missing_count": len(missing),
        "failed_or_retryable_count": len([k for k in failed if k in manifest_by_key and k not in handled]),
        "handled": handled,
        "failed_or_retryable": failed,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps({k: index[k] for k in ("manifest_count", "handled_count", "missing_count", "failed_or_retryable_count")}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
