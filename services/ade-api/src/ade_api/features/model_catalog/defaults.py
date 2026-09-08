from __future__ import annotations

from ade_api.platform.contracts import ScenarioType

PROVIDER_MODEL_OPTION_OVERRIDES: dict[str, dict[str, str]] = {
    "gemma-4-31b-it": {
        "label": "Gemma 4 31B IT",
        "description": "Local model discovered from Unsloth Studio.",
    },
    "gemma4": {
        "label": "Gemma 4 (llama-server)",
        "description": "Local GGUF model served by llama-server with JSON schema support.",
    },
    "qwen3.5-27b": {
        "label": "Qwen 3.5 27B",
        "description": "Recommended default for local development.",
    },
    "qwen/qwen3.5-35b-a3b": {
        "label": "Qwen 3.5 35B A3B",
        "description": "Higher quality but heavier VRAM usage.",
    },
    "doubao-seed-1-8-251228": {
        "label": "Doubao Seed 1.8 (ARK)",
        "description": "OpenAI-compatible ARK provider model.",
    },
}

PROVIDER_MODEL_OPTION_PRIORITY = {
    key: index for index, key in enumerate(PROVIDER_MODEL_OPTION_OVERRIDES)
}

DEFAULT_MODEL = ""
DEFAULT_CHAT_PROMPT_KEY = "chat_v20260516"
DEFAULT_CHAT_PERSONA_KEY = "chat_linxiaotang"
DEFAULT_COMMENT_PROMPT_KEY = "comment_v20260418"
DEFAULT_COMMENT_PERSONA_KEY = "comment_linxiaotang"
DEFAULT_LABEL_PROMPT_KEY = "label_generic_entities_v1"
SCENARIO_DEFAULTS: dict[ScenarioType, dict[str, str]] = {
    "chat": {
        "prompt_key": DEFAULT_CHAT_PROMPT_KEY,
        "persona_key": DEFAULT_CHAT_PERSONA_KEY,
    },
    "comment": {
        "prompt_key": DEFAULT_COMMENT_PROMPT_KEY,
        "persona_key": DEFAULT_COMMENT_PERSONA_KEY,
    },
    "label": {
        "prompt_key": DEFAULT_LABEL_PROMPT_KEY,
        "persona_key": "",
    },
}
