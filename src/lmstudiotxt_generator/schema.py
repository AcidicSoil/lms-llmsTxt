from __future__ import annotations

LLMS_JSON_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "llmsTxtDocument",
    "type": "object",
    "required": ["project", "remember", "sections"],
    "properties": {
        "project": {
            "type": "object",
            "required": ["name", "summary"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "summary": {"type": "string", "minLength": 1},
            },
        },
        "remember": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
        "sections": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["title", "links"],
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "url", "note"],
                            "properties": {
                                "title": {"type": "string"},
                                "url": {"type": "string", "format": "uri"},
                                "note": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}


__all__ = ["LLMS_JSON_SCHEMA"]
