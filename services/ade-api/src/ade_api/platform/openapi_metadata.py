from __future__ import annotations

TAG_AGENT_STUDIO = "Agent Studio"
TAG_COMMENT_LAB = "Comment Lab"
TAG_LABEL_LAB = "Label Lab"
TAG_MODEL_CATALOG = "Model Catalog"
TAG_PROMPT_CENTER = "Prompt Center"
TAG_SCHEMA_CENTER = "Schema Center"
TAG_TOOL_CENTER = "Tool Center"
TAG_TEST_CENTER = "Test Center"
TAG_AGENT_RUNTIME_V3 = "Agent Runtime v3 Preview"

OPENAPI_TAGS = [
    {
        "name": TAG_AGENT_STUDIO,
        "description": "Persistent-agent creation, inspection, and chat operations.",
    },
    {
        "name": TAG_COMMENT_LAB,
        "description": "Stateless comment generation using router-visible models.",
    },
    {
        "name": TAG_LABEL_LAB,
        "description": "Stateless grouped entity extraction using Label Lab schemas.",
    },
    {
        "name": TAG_PROMPT_CENTER,
        "description": "Prompt template and SQLite-backed persona library management.",
    },
    {
        "name": TAG_SCHEMA_CENTER,
        "description": "File-backed Label Lab JSON schema management.",
    },
    {
        "name": TAG_TOOL_CENTER,
        "description": "Tool discovery, Tool Center CRUD, and tool attach/detach operations.",
    },
    {
        "name": TAG_TEST_CENTER,
        "description": "Orchestrated live checks and test-run artifact access.",
    },
    {
        "name": TAG_MODEL_CATALOG,
        "description": "Model capabilities, catalog diagnostics, and scenario runtime options.",
    },
    {
        "name": TAG_AGENT_RUNTIME_V3,
        "description": "Disabled-by-default ADE-owned agent runtime preview APIs.",
    },
]
