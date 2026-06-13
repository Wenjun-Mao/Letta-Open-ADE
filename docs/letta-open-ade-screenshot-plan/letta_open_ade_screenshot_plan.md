# Letta Open ADE Screenshot Plan

This document collects screenshots for five ADE workspace surfaces: schema-first labeling, editable schemas and prompts, model routing, and persistent agent work. Agent Studio uses two screenshots because one image cannot clearly show both memory layers and the tool interface.

## 1. Label Lab — Schema-Driven Label Generation Result

![Label Lab schema-driven result](label-lab-result.png)

Label Lab turns an article into structured labels using a selected prompt, schema, and model. In this example, the football entity schema constrains the result into validated groups such as players and teams, making the output easier to inspect, compare, and reuse downstream.

## 2. Schema Center — Schema Editing / Schema List

![Schema Center schema editor](schema-center.png)

Schema Center manages Label Lab JSON schemas as workspace assets. The schema list shows active templates, while the editor exposes metadata and JSON Schema content so schema-driven extraction rules can be reviewed and updated without touching application code.

## 3. Prompt Center — Prompt Editing / Prompt List

![Prompt Center prompt editor](prompt-center.png)

Prompt Center manages system prompts and persona templates. Older prompt baselines remain selectable for comparison, while the editor gives a direct workspace view into the active prompt content, description, and lifecycle status.

## 4. Model Router / Model Options — Local + Cloud Model Choices

![Model router model options](model-router-options.png)

The model router centralizes model availability across local servers, DGX Spark vLLM, and cloud providers. ADE modules use this catalog to expose scenario-appropriate choices for Agent Studio, Comment Lab, Label Lab, and related tooling; served model names are provider handles and may be aliases for the checkpoint behind the endpoint.

## 5. Agent Studio — Persistent Memory / Tool Interface

![Agent Studio persistent memory layers](agent-studio-memory-layers.png)

Agent Studio works with persistent Letta agents rather than one-off chat completions. The main workspace brings together model, prompt, persona, runtime controls, execution trace review, and persistent memory inspection; the memory panel shows durable `human` and `persona` layers with direct edit affordances.

![Agent Studio tool attachment and probe panel](agent-studio-tools-panel.png)

The tools panel shows the agent-facing tool surface: attached memory/search tools, attach/detach controls for optional tools, and the Tool Probe workflow used to test whether an agent chooses the expected tool path.
