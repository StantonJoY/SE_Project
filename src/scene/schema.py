"""场景输入 JSON Schema（REQ-003）。"""

SCENE_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["time_slot", "device"],
    "properties": {
        "time_slot": {
            "type": "string",
            "enum": ["morning", "afternoon", "evening", "night"],
        },
        "device": {
            "type": "string",
            "enum": ["mobile", "desktop", "tablet"],
        },
        "user_tags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}
