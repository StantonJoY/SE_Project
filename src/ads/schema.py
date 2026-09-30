"""素材 JSON Schema（REQ-002：每条素材字段完整且合法）。"""

AD_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "ad_id",
        "title",
        "copy",
        "category",
        "target_tags",
        "scene_restrictions",
        "banned_check",
    ],
    "properties": {
        "ad_id": {"type": "string", "pattern": "^ad_[0-9]+$"},
        "title": {"type": "string", "minLength": 1},
        "copy": {"type": "string", "minLength": 1},
        "category": {"type": "string", "minLength": 1},
        "target_tags": {"type": "array", "items": {"type": "string"}},
        "scene_restrictions": {
            "type": "object",
            "required": ["not_night", "not_campus", "allowed_devices"],
            "properties": {
                "not_night": {"type": "boolean"},
                "not_campus": {"type": "boolean"},
                "allowed_devices": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["mobile", "desktop", "tablet"],
                    },
                },
            },
            "additionalProperties": False,
        },
        "banned_check": {
            "type": "string",
            "enum": ["pending", "checked", "banned"],
        },
    },
    "additionalProperties": False,
}
