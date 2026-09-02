from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


SUMMARY_TRANSLATIONS = {
    "Accept an asynchronous v3 conversation turn": "接受异步 v3 会话轮次",
    "Cancel a v3 run": "取消 v3 运行",
    "Create a v3 conversation": "创建 v3 会话",
    "Create a v3 memory subject": "创建 v3 记忆主体",
    "Create an immutable v3 agent definition": "创建不可变 v3 智能体定义",
    "Get a v3 agent definition": "获取 v3 智能体定义",
    "Get a v3 memory subject": "获取 v3 记忆主体",
    "Get a v3 run": "获取 v3 运行",
    "Get v3 conversation state": "获取 v3 会话状态",
    "Inspect typed subject memories": "检查类型化主体记忆",
    "Stream normalized v3 run events": "流式读取规范化 v3 运行事件",
    "Check v3 worker process readiness": "检查 v3 工作器进程就绪状态",
    "Compare two chat-memory evaluations": "比较两次聊天记忆评估",
    "Get paired Agent Runtime product parity evidence": "获取成对智能体运行时产品对等性证据",
    "List paired Agent Runtime product parity evaluations": "列出成对智能体运行时产品对等性评估",
    "Record a chat-memory evaluation decision": "记录聊天记忆评估决策",
    "Runtime and control APIs for ADE and local ADE API workflows": "面向 ADE 与本地 ADE API 工作流的运行时与控制 API",
    "Feature-aligned runtime and authoring APIs for Letta Open ADE": "面向 Letta Open ADE 的按功能组织的运行时与创作 API",
    "Archive agent (soft delete)": "归档智能体（软删除）",
    "Archive managed custom tool": "归档受管自定义工具",
    "Archive persona template": "归档 Persona 模板",
    "Archive system prompt template": "归档系统提示词模板",
    "Archive Label Lab JSON schema": "归档 Label Lab JSON Schema",
    "Attach tool to agent": "为智能体挂载工具",
    "Cancel orchestrated test run": "取消编排测试运行",
    "Create managed custom tool": "创建受管自定义工具",
    "Create orchestrated test run": "创建编排测试运行",
    "Create persona template": "创建 Persona 模板",
    "Create system prompt template": "创建系统提示词模板",
    "Create Label Lab JSON schema": "创建 Label Lab JSON Schema",
    "Delete archived agent (hard delete)": "删除已归档智能体（硬删除）",
    "Detach tool from agent": "从智能体卸载工具",
    "Create an Agent Studio agent": "创建 Agent Studio 智能体",
    "Extract football players and teams": "抽取足球球员与球队",
    "Generate a stateless comment for news/comment threads": "生成用于新闻/评论线程的无状态评论",
    "Generate stateless grouped entity extraction for an input article": "为输入文章生成无状态分组实体抽取",
    "Generate with local llama-server": "使用本地 llama-server 生成",
    "Get Agent Studio agent details": "获取 Agent Studio 智能体详情",
    "Get chat-memory evaluation detail": "获取聊天记忆评估详情",
    "Get Label Lab JSON schema": "获取 Label Lab JSON Schema",
    "Get Tool Center managed custom tool": "获取工具中心受管自定义工具",
    "Get orchestrated test run": "获取编排测试运行",
    "Get persona template": "获取 Persona 模板",
    "Get platform capability matrix": "获取平台能力矩阵",
    "Get prompt and persona metadata": "获取提示词与 Persona 元数据",
    "Get prompt/persona revision history timeline": "获取提示词/Persona 修订历史时间线",
    "Get persisted Agent Studio state": "获取 Agent Studio 持久化状态",
    "Get raw prompt messages for an Agent Studio agent": "获取 Agent Studio 智能体的原始提示词消息",
    "Get system prompt template": "获取系统提示词模板",
    "Get unified model-catalog diagnostics": "获取统一模型目录诊断",
    "Invoke a runtime message to validate tool-call behavior": "发送运行时消息以验证工具调用行为",
    "List Agent Studio agents": "列出 Agent Studio 智能体",
    "List chat-memory evaluations": "列出聊天记忆评估",
    "List Label Lab JSON schemas": "列出 Label Lab JSON Schema",
    "List Tool Center entries": "列出工具中心条目",
    "List orchestrated test runs": "列出编排测试运行",
    "List persona templates": "列出 Persona 模板",
    "List system prompt templates": "列出系统提示词模板",
    "List test run artifacts": "列出测试运行产物",
    "List tools for Toolbench discovery": "列出用于 Toolbench 发现的工具",
    "List runtime options for an ADE scenario": "列出 ADE 场景的运行时选项",
    "Purge archived agent (hard delete)": "清除已归档智能体（硬删除）",
    "Purge archived managed custom tool": "清除已归档受管自定义工具",
    "Purge archived persona template": "清除已归档 Persona 模板",
    "Purge archived system prompt template": "清除已归档系统提示词模板",
    "Purge archived Label Lab JSON schema": "清除已归档 Label Lab JSON Schema",
    "Read Index": "读取索引",
    "Read test run artifact content": "读取测试运行产物内容",
    "Restore archived agent": "恢复已归档智能体",
    "Restore archived managed custom tool": "恢复已归档受管自定义工具",
    "Restore archived persona template": "恢复已归档 Persona 模板",
    "Restore archived system prompt template": "恢复已归档系统提示词模板",
    "Restore archived Label Lab JSON schema": "恢复已归档 Label Lab JSON Schema",
    "Send a chat message to a persistent Agent Studio agent": "向持久化 Agent Studio 智能体发送对话消息",
    "Send runtime message with optional overrides": "发送运行时消息（支持可选覆盖参数）",
    "Update core-memory block value": "更新核心记忆块值",
    "Update managed custom tool": "更新受管自定义工具",
    "Update persisted agent model": "更新已持久化智能体模型",
    "Update persisted system prompt": "更新已持久化系统提示词",
    "Update persona template": "更新 Persona 模板",
    "Update system prompt template": "更新系统提示词模板",
    "Update Label Lab JSON schema": "更新 Label Lab JSON Schema",
}

DESCRIPTION_TRANSLATIONS = {
    "ADE-owned Agent Studio runtime APIs.": "ADE 自有 Agent Studio 运行时 API。",
    "Database or matching runtime worker is not ready": "数据库或匹配的运行时工作器尚未就绪",
    "The immutable raw-message prefix represented by a summary version.": "一个摘要版本所代表的不可变原始消息前缀。",
    "Successful Response": "成功响应",
    "Validation Error": "校验错误",
    "Local ADE API": "本地 ADE API",
    "ADE API local": "ADE API 本地服务",
    "Provides versioned API routes for ADE API runtime/control/test orchestration. Designed for backend-first API consumption and ADE Web integration.": "提供用于 ADE API 运行时/控制/测试编排的版本化 API 路由。面向后端优先的 API 调用，并用于 ADE Web 集成。",
    "Provides the versioned Agent Studio, lab, content-center, catalog, and test APIs used by ADE Web, workflows, and first-class developer clients.": "提供 ADE Web、工作流和一等开发者客户端使用的版本化 Agent Studio、实验室、内容中心、目录和测试 API。",
    "Model capabilities, catalog diagnostics, and scenario runtime options.": "模型能力、目录诊断和场景运行时选项。",
    "Persistent-agent creation, inspection, and chat operations.": "持久化智能体的创建、检查与对话操作。",
    "Stateless comment generation using router-visible models.": "使用模型路由器可见模型生成无状态评论。",
    "Stateless grouped entity extraction using Label Lab schemas.": "使用 Label Lab Schema 进行无状态分组实体抽取。",
    "Prompt template and SQLite-backed persona library management.": "提示词模板与 SQLite 后端 Persona 库管理。",
    "File-backed Label Lab JSON schema management.": "基于文件的 Label Lab JSON Schema 管理。",
    "Tool discovery, Tool Center CRUD, and tool attach/detach operations.": "工具发现、工具中心 CRUD，以及工具挂载/卸载操作。",
    "Orchestrated live checks and test-run artifact access.": "编排式实时检查与测试运行产物访问。",
    "Low-level runtime message endpoints with optional overrides.": "支持可选覆盖参数的底层运行时消息端点。",
    "Persistent agent lifecycle and configuration control endpoints.": "持久化智能体生命周期与配置控制端点。",
    "Platform capabilities, model catalog diagnostics, and shared runtime options.": "平台能力、模型目录诊断与共享运行时选项。",
    "Must be `comment` for this endpoint.": "该端点必须使用 `comment`。",
    "News article, comment thread, or source text to comment on.": "需要评论的新闻文章、评论线程或源文本。",
    "Comment Lab prompt key from `/api/v2/model-catalog/options?scenario=comment`.": "来自 `/api/v2/model-catalog/options?scenario=comment` 的 Comment Lab 提示词键。",
    "Comment Lab persona key from `/api/v2/model-catalog/options?scenario=comment`.": "来自 `/api/v2/model-catalog/options?scenario=comment` 的 Comment Lab Persona 键。",
    "Router-scoped model key from `/api/v2/model-catalog/options?scenario=comment`, for example `local_llama_server::gemma4`.": "来自 `/api/v2/model-catalog/options?scenario=comment` 的路由器作用域模型键，例如 `local_llama_server::gemma4`。",
    "Legacy selector kept for backward compatibility. Prefer `model_key`.": "为向后兼容保留的旧选择器。优先使用 `model_key`。",
    "Optional response token budget. Defaults to Comment Lab runtime settings.": "可选响应 Token 预算。默认使用 Comment Lab 运行时设置。",
    "Optional provider timeout in seconds. Use a realistic local-model value such as 120.": "可选供应商超时时间（秒）。本地模型建议使用类似 120 的实际值。",
    "Optional provider retry count for transient failures.": "瞬时失败时的可选供应商重试次数。",
    "Prompt-packing strategy. Defaults to the Comment Lab runtime setting.": "提示词打包策略。默认使用 Comment Lab 运行时设置。",
    "llama.cpp prompt-cache toggle for Comment Lab. Defaults to false and is only sent to llama.cpp-backed sources.": "Comment Lab 的 llama.cpp 提示词缓存开关。默认关闭，并且只发送给 llama.cpp 后端来源。",
    "Optional vLLM/Gemma thinking toggle. When true for supported vLLM sources, ADE sends `chat_template_kwargs.enable_thinking=true`.": "可选 vLLM/Gemma thinking 开关。对支持的 vLLM 来源设为 true 时，ADE 会发送 `chat_template_kwargs.enable_thinking=true`。",
    "Sampling temperature. Defaults to Comment Lab runtime settings.": "采样 temperature。默认使用 Comment Lab 运行时设置。",
    "Nucleus sampling top_p. Defaults to Comment Lab runtime settings.": "核采样 top_p。默认使用 Comment Lab 运行时设置。",
    "Optional top_k sampling value. Defaults to model profile or Comment Lab runtime settings.": "可选 top_k 采样值。默认使用模型 profile 或 Comment Lab 运行时设置。",
    "Must be `label` for this endpoint.": "该端点必须使用 `label`。",
    "Article or text to extract grouped entity lists from.": "用于抽取分组实体列表的文章或文本。",
    "Label Lab prompt key from `/api/v2/model-catalog/options?scenario=label`.": "来自 `/api/v2/model-catalog/options?scenario=label` 的 Label Lab 提示词键。",
    "Label Schema Center key from `/api/v2/model-catalog/options?scenario=label`.": "来自 `/api/v2/model-catalog/options?scenario=label` 的 Label Schema Center 键。",
    "Router-scoped model key from `/api/v2/model-catalog/options?scenario=label`, for example `local_llama_server::gemma4`.": "来自 `/api/v2/model-catalog/options?scenario=label` 的路由器作用域模型键，例如 `local_llama_server::gemma4`。",
    "Optional response token budget. Defaults to Label Lab runtime settings.": "可选响应 Token 预算。默认使用 Label Lab 运行时设置。",
    "Number of structured-output repair attempts after validation failure.": "结构化输出校验失败后的修复重试次数。",
    "Sampling temperature. Defaults to Label Lab runtime settings.": "采样 temperature。默认使用 Label Lab 运行时设置。",
    "Nucleus sampling top_p. Defaults to Label Lab runtime settings.": "核采样 top_p。默认使用 Label Lab 运行时设置。",
    "Optional top_k sampling value. Defaults to model profile or Label Lab runtime settings.": "可选 top_k 采样值。默认使用模型 profile 或 Label Lab 运行时设置。",
    "List existing agents so the UI can pull and inspect prior state.": "列出已有智能体，供 UI 拉取并检查历史状态。",
    "Returns persisted state from Letta backend storage (Postgres/pgvector via Letta API):\n- agent metadata\n- memory blocks\n- attached tools\n- persisted conversation history": "返回 Letta 后端存储（通过 Letta API 访问 Postgres/pgvector）中的持久化状态：\n- 智能体元数据\n- 记忆块\n- 已挂载工具\n- 持久化会话历史",
    "Administrator-only opt-in for raw provider request/reply diagnostics.": "仅管理员可选择启用原始供应商请求/响应诊断信息。",
    "Return the resolved model and content options for one ADE scenario.": "返回一个 ADE 场景解析后的模型与内容选项。",
}

TAG_TRANSLATIONS = {
    "Agent Runtime v3": "智能体运行时 v3",
    "Agent Studio": "智能体工作台",
    "Comment Lab": "评论实验室",
    "Label Lab": "标注实验室",
    "Prompt Center": "提示词中心",
    "Schema Center": "Schema 中心",
    "Tool Center": "工具中心",
    "Test Center": "测试中心",
    "Platform Runtime": "平台运行时",
    "Platform Control": "平台控制",
    "Platform Meta": "平台元数据",
}

TITLE_TRANSLATIONS = {
    "ADE API": "ADE API",
    "Baseline": "基线",
    "Case Keys": "案例键",
    "Compatibility Fingerprint": "兼容性指纹",
    "Configuration Changes": "配置变更",
    "Controls": "控制参数",
    "Checks": "检查项",
    "Cleanup Complete": "清理完成",
    "Comparability Checks": "可比性检查",
    "Completed": "已完成",
    "Inputs Comparable": "输入可比",
    "Legacy Checks": "旧运行时检查",
    "Legacy Completed": "旧运行时已完成",
    "Legacy Creation Indeterminate": "旧运行时创建状态不确定",
    "Native Checks": "原生运行时检查",
    "Native Completed": "原生运行时已完成",
    "Database Ready": "数据库就绪",
    "Freshness Seconds": "新鲜度秒数",
    "Metric Deltas": "指标差值",
    "Note": "备注",
    "Outcome": "结果",
    "Preferred Baseline": "首选基线",
    "Same Configuration": "相同配置",
    "Worker Ready": "工作器就绪",
    "Scenario": "场景",
    "Aliases": "别名",
    "Assistant Replies": "助手回复",
    "Average Elapsed Seconds": "平均耗时秒数",
    "Cleanup Passed Rounds": "清理通过轮数",
    "Deterministic Score": "确定性评分",
    "Elapsed Seconds": "耗时秒数",
    "Pass Rate": "通过率",
    "Passed": "是否通过",
    "Purged": "已清理",
    "Ready": "已就绪",
    "Round": "轮次",
    "Rounds Failed": "失败轮数",
    "Rounds Passed": "通过轮数",
    "Turns": "对话轮次",
    "Deployment": "部署",
    "Deployments": "部署列表",
    "Events Url": "事件 URL",
    "Evidence": "证据",
    "Fingerprint": "指纹",
    "Fingerprint Payload": "指纹载荷",
    "Idempotent Replay": "幂等重放",
    "Lifecycle": "生命周期",
    "Qualifier": "限定符",
    "Quote": "原文摘录",
    "Route Alias": "路由别名",
    "Version": "版本",
    "Agent Id": "智能体 ID",
    "Adapter": "适配器",
    "Allowlist Applied": "已应用允许列表",
    "Allowlist Checked At": "允许列表检查时间",
    "Base Url": "Base URL",
    "Key": "键",
    "Detail": "详情",
    "Description": "描述",
    "Displayed": "已显示",
    "Embeddings": "向量模型",
    "Enabled": "已启用",
    "Enabled For": "启用场景",
    "Exists": "是否存在",
    "Finish Reason": "结束原因",
    "Finished At": "结束时间",
    "Letta Handle": "Letta Handle",
    "Letta Handle Prefix": "Letta Handle 前缀",
    "Letta Catalog Visible": "Letta 目录可见",
    "Line Count": "行数",
    "Location": "位置",
    "Log File": "日志文件",
    "Messages": "消息",
    "Missing Required": "缺失必需能力",
    "Model": "模型",
    "Models": "模型列表",
    "Name": "名称",
    "Output Mode": "输出模式",
    "Output Schema": "输出 Schema",
    "Output Tail": "输出尾部",
    "Provider": "供应商",
    "Profile Applied": "已应用 Profile",
    "Received At": "接收时间",
    "Recorded At": "记录时间",
    "Refresh": "刷新",
    "Repair Retry Count": "修复重试次数",
    "Retry Count": "重试次数",
    "Rounds": "轮数",
    "Judge Enabled": "启用评审模型",
    "Schema": "Schema",
    "Schemas": "Schema 列表",
    "Selected Attempt": "选中尝试",
    "Size Bytes": "字节大小",
    "Sources": "来源列表",
    "Supports Top K": "支持 Top K",
    "Supports Thinking": "支持 Thinking",
    "Started At": "开始时间",
    "Strict Mode": "严格模式",
    "Structured Output Mode": "结构化输出模式",
    "Truncated": "已截断",
    "Usage": "用量",
    "Id": "ID",
    "Content": "内容",
    "Limit": "限制",
    "Items": "条目",
    "Label": "标签",
    "Slug": "Slug",
    "Created At": "创建时间",
    "Archived": "已归档",
    "Run Id": "运行 ID",
    "Embedding": "向量模型",
    "Persona Key": "Persona 键",
    "Prompt Key": "提示词键",
    "Include Archived": "包含已归档",
    "Last Updated At": "最近更新时间",
    "Total": "总数",
    "Input": "输入",
    "Source Type": "来源类型",
    "Tags": "标签",
    "Tool Id": "工具 ID",
    "System": "系统提示词",
    "Updated At": "更新时间",
    "Max Tokens": "最大 Token 数",
    "Task Shape": "任务形态",
    "Temperature": "Temperature",
    "Thinking Default Enabled": "Thinking 默认启用",
    "Timeout Seconds": "超时秒数",
    "Top P": "Top P",
    "Top K": "Top K",
    "Length": "长度",
    "Preview": "预览",
    "Search": "搜索",
    "Field": "字段",
    "Override Model": "覆盖模型",
    "Override System": "覆盖系统提示词",
    "Source Code": "源码",
    "Agent Type": "智能体类型",
    "Context Window Limit": "上下文窗口限制",
    "Last Interaction At": "最近交互时间",
    "Tool Rules": "工具规则",
    "Tools": "工具",
    "Archived At": "归档时间",
    "Kind": "类别",
    "Role": "角色",
    "Status": "状态",
    "Block Label": "记忆块标签",
    "Personas": "Persona 列表",
    "Prompts": "提示词列表",
    "Value": "值",
    "Source": "来源",
    "Managed": "受管",
    "Read Only": "只读",
    "Tool Type": "工具类型",
    "Expected Tool Name": "期望工具名称",
    "Result": "结果",
    "Source Path": "来源路径",
    "Artifact Id": "产物 ID",
    "Run Type": "运行类型",
    "Include Builtin": "包含内置",
    "Message": "消息",
    "Default Requires Approval": "默认需要审批",
    "Enable Parallel Execution": "启用并行执行",
    "Npm Requirements": "NPM 依赖",
    "Pip Requirements": "Pip 依赖",
    "Return Char Limit": "返回字符上限",
    "Include Source": "包含源码",
    "Sequence": "序号",
    "Memory Diff": "记忆差异",
    "ApiAgentListResponse": "智能体列表响应",
    "ApiAgentListItemResponse": "智能体列表条目响应",
    "ApiAgentDetailsResponse": "智能体详情响应",
    "ApiAgentLifecycleResponse": "智能体生命周期响应",
    "ApiAgentPurgeResponse": "智能体清除响应",
    "ApiAgentCreateResponse": "智能体创建响应",
    "AgentCreateRequest": "智能体创建请求",
    "Embedding Config": "向量配置",
    "Llm Config": "LLM 配置",
    "Memory": "记忆",
    "ApiListResponse": "列表响应",
    "ApiPromptPersonaMetadataResponse": "提示词与 Persona 元数据响应",
    "ApiPromptPersonaRevisionListResponse": "提示词与 Persona 修订列表响应",
    "ApiPromptPersonaRevisionResponse": "提示词与 Persona 修订响应",
    "ApiToolListResponse": "工具列表响应",
    "ApiToolResponse": "工具响应",
    "ApiToolTestInvokeRequest": "工具测试调用请求",
    "ApiToolTestInvokeResponse": "工具测试调用响应",
    "ApiTestRunListResponse": "测试运行列表响应",
    "ApiTestRunResponse": "测试运行响应",
    "ApiTestRunArtifactListResponse": "测试运行产物列表响应",
    "ApiTestRunArtifactResponse": "测试运行产物响应",
    "ApiCommentGenerateRequest": "评论生成请求",
    "ApiCommentGenerateResponse": "评论生成响应",
    "ApiCommentConfigResponse": "评论配置响应",
    "CommentTaskShape": "评论任务形态",
    "ApiCapabilitiesResponse": "能力矩阵响应",
    "ValidationError": "校验错误",
    "HTTPValidationError": "HTTP 校验错误",
    "Ok": "成功",
}

TITLE_TOKEN_TRANSLATIONS = {
    "accept": "接受",
    "accepted": "已接受",
    "after": "变更后",
    "agent": "智能体",
    "agents": "智能体",
    "api": "API",
    "approval": "审批",
    "archive": "归档",
    "archived": "已归档",
    "adapter": "适配器",
    "artifact": "产物",
    "artifacts": "产物",
    "attach": "挂载",
    "attached": "已挂载",
    "arguments": "参数",
    "attempt": "尝试",
    "at": "时间",
    "available": "可用",
    "before": "变更前",
    "behavior": "行为",
    "baseline": "基线",
    "block": "块",
    "blocks": "记忆块",
    "body": "正文",
    "boundary": "边界",
    "build": "构建",
    "by": "按",
    "call": "调用",
    "calls": "调用",
    "cancel": "取消",
    "cancellation": "取消",
    "capability": "能力",
    "capabilities": "能力",
    "candidate": "候选",
    "captured": "已捕获",
    "catalog": "目录",
    "cache": "缓存",
    "center": "中心",
    "char": "字符",
    "chat": "对话",
    "code": "源码",
    "comment": "评论",
    "commenting": "评论",
    "command": "命令",
    "compatible": "兼容",
    "config": "配置",
    "content": "内容",
    "cleanup": "清理",
    "completed": "已完成",
    "context": "上下文",
    "control": "控制",
    "conversation": "会话",
    "count": "计数",
    "core": "核心",
    "counts": "计数",
    "create": "创建",
    "created": "创建",
    "changed": "已变更",
    "checked": "已检查",
    "comparison": "比较",
    "compatibility": "兼容性",
    "configuration": "配置",
    "custom": "自定义",
    "default": "默认",
    "defaults": "默认值",
    "definition": "定义",
    "decision": "决策",
    "delta": "变化",
    "diagnostics": "诊断",
    "description": "描述",
    "detach": "卸载",
    "deployment": "部署",
    "digests": "摘要值",
    "details": "详情",
    "detail": "详情",
    "display": "显示",
    "dev": "开发",
    "dirty": "脏状态",
    "e2e": "E2E",
    "embedding": "向量模型",
    "enable": "启用",
    "enabled": "已启用",
    "end": "结束",
    "entries": "条目",
    "entry": "条目",
    "entity": "实体",
    "error": "错误",
    "errors": "错误",
    "event": "事件",
    "evidence": "证据",
    "evaluation": "评估",
    "expected": "期望",
    "exit": "退出",
    "execution": "执行",
    "external": "外部",
    "extra": "额外",
    "field": "字段",
    "fact": "事实",
    "facts": "事实",
    "failure": "失败",
    "fingerprint": "指纹",
    "filtered": "过滤后",
    "final": "最终",
    "fixture": "测试数据集",
    "forbidden": "禁止",
    "generate": "生成",
    "generated": "已生成",
    "idempotency": "幂等性",
    "get": "获取",
    "hard": "硬",
    "health": "健康状态",
    "heartbeat": "心跳",
    "history": "历史",
    "hit": "命中",
    "http": "HTTP",
    "human": "Human",
    "id": "ID",
    "identity": "身份",
    "ids": "ID",
    "include": "包含",
    "index": "索引",
    "input": "输入",
    "initial": "初始",
    "interaction": "交互",
    "invoke": "调用",
    "is": "是否",
    "item": "条目",
    "items": "条目",
    "judge": "评审模型",
    "key": "键",
    "kind": "类别",
    "lab": "实验室",
    "label": "标签",
    "legacy": "旧运行时",
    "labeling": "标注",
    "last": "最近",
    "latest": "最新",
    "length": "长度",
    "limit": "上限",
    "lines": "行",
    "list": "列表",
    "llama": "llama",
    "managed": "受管",
    "matched": "匹配",
    "matching": "匹配",
    "matrix": "矩阵",
    "max": "最大",
    "memory": "记忆",
    "matches": "匹配",
    "memories": "记忆",
    "message": "消息",
    "messages": "消息",
    "metadata": "元数据",
    "metrics": "指标",
    "model": "模型",
    "name": "名称",
    "native": "原生运行时",
    "normalized": "规范化",
    "names": "名称",
    "news": "新闻",
    "npm": "NPM",
    "ok": "成功",
    "openapi": "OpenAPI",
    "option": "选项",
    "options": "选项",
    "operation": "操作",
    "override": "覆盖",
    "orchestrated": "编排",
    "parallel": "并行",
    "passed": "通过",
    "params": "参数",
    "patch": "补丁",
    "path": "路径",
    "per": "每",
    "persona": "Persona",
    "parity": "对等性",
    "personas": "Persona 列表",
    "persistent": "持久化",
    "persisted": "已持久化",
    "pip": "Pip",
    "platform": "平台",
    "policy": "策略",
    "predecessor": "前驱",
    "preview": "预览",
    "previous": "上一个",
    "prompt": "提示词",
    "prompts": "提示词列表",
    "provider": "供应商",
    "preflight": "预检",
    "provenance": "来源证明",
    "profile": "Profile",
    "purge": "清除",
    "purged": "已清理",
    "qualification": "资格",
    "raw": "原始",
    "read": "读取",
    "record": "记录",
    "request": "请求",
    "requested": "请求的",
    "requires": "需要",
    "response": "响应",
    "restore": "恢复",
    "result": "结果",
    "ready": "就绪",
    "reply": "回复",
    "return": "返回",
    "revision": "修订",
    "revisions": "修订",
    "reviewer": "评审器",
    "role": "角色",
    "round": "轮次",
    "rounds": "轮次",
    "rules": "规则",
    "run": "运行",
    "runtime": "运行时",
    "scenario": "场景",
    "schema": "Schema",
    "sampling": "采样",
    "sdk": "SDK",
    "search": "搜索",
    "send": "发送",
    "session": "会话",
    "sequence": "序号",
    "sha": "SHA",
    "slug": "Slug",
    "soft": "软",
    "source": "来源",
    "spec": "规格",
    "snapshot": "快照",
    "start": "开始",
    "state": "状态",
    "steps": "步骤",
    "stateless": "无状态",
    "status": "状态",
    "substrings": "子字符串",
    "subject": "主体",
    "summary": "摘要",
    "system": "系统",
    "studio": "工作台",
    "tag": "标签",
    "tags": "标签",
    "task": "任务",
    "template": "模板",
    "test": "测试",
    "threads": "线程",
    "this": "本轮",
    "thinking": "Thinking",
    "through": "截止",
    "timeline": "时间线",
    "timeout": "超时",
    "to": "到",
    "token": "Token",
    "tool": "工具",
    "turns": "轮次",
    "tools": "工具",
    "total": "总数",
    "turn": "轮次",
    "type": "类型",
    "update": "更新",
    "updated": "更新",
    "upstream": "上游",
    "user": "用户",
    "validation": "校验",
    "value": "值",
    "version": "版本",
    "via": "通过",
    "was": "是否已",
    "worker": "工作器",
    "write": "写入",
}

TOKEN_SPLIT_PATTERN = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+")
ASCII_LETTER_PATTERN = re.compile(r"[A-Za-z]")


def _contains_ascii_letters(value: str) -> bool:
    return bool(ASCII_LETTER_PATTERN.search(value))


def _split_title_tokens(value: str) -> list[str]:
    chunks = re.split(r"[\s_\-/]+", value.strip())
    tokens: list[str] = []

    for chunk in chunks:
        if not chunk:
            continue

        if chunk.isupper() and len(chunk) > 1:
            tokens.append(chunk)
            continue

        camel_tokens = TOKEN_SPLIT_PATTERN.findall(chunk)
        if camel_tokens:
            tokens.extend(camel_tokens)
        else:
            tokens.append(chunk)

    return tokens


def _translate_title_value(
    value: str,
    missing_titles: set[str],
    unknown_title_tokens: set[str],
) -> str:
    if value in TITLE_TRANSLATIONS:
        return TITLE_TRANSLATIONS[value]

    if not _contains_ascii_letters(value):
        return value

    tokens = _split_title_tokens(value)
    if not tokens:
        missing_titles.add(value)
        return value

    translated_tokens: list[str] = []
    unknown_tokens: list[str] = []

    for token in tokens:
        translated = TITLE_TOKEN_TRANSLATIONS.get(token.lower())
        if translated:
            translated_tokens.append(translated)
        else:
            translated_tokens.append(token)
            unknown_tokens.append(token)

    translated_value = " ".join(translated_tokens)
    if translated_value != value:
        for token in unknown_tokens:
            if _contains_ascii_letters(token):
                unknown_title_tokens.add(token)
        return translated_value

    missing_titles.add(value)
    return value


def _translate_document_fields(
    node: Any,
    missing_summaries: set[str],
    missing_descriptions: set[str],
    missing_titles: set[str],
    unknown_title_tokens: set[str],
) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "summary" and isinstance(value, str):
                if not _contains_ascii_letters(value):
                    continue

                translated = SUMMARY_TRANSLATIONS.get(value)
                if translated is None:
                    missing_summaries.add(value)
                else:
                    node[key] = translated
                continue

            if key == "description" and isinstance(value, str):
                if not _contains_ascii_letters(value):
                    continue

                translated = DESCRIPTION_TRANSLATIONS.get(value)
                if translated is None:
                    missing_descriptions.add(value)
                else:
                    node[key] = translated
                continue

            if key == "title" and isinstance(value, str):
                node[key] = _translate_title_value(
                    value, missing_titles, unknown_title_tokens
                )
                continue

            _translate_document_fields(
                value,
                missing_summaries,
                missing_descriptions,
                missing_titles,
                unknown_title_tokens,
            )
    elif isinstance(node, list):
        for item in node:
            _translate_document_fields(
                item,
                missing_summaries,
                missing_descriptions,
                missing_titles,
                unknown_title_tokens,
            )


def _apply_top_level_translations(openapi_payload: dict[str, Any]) -> None:
    info = openapi_payload.get("info")
    if isinstance(info, dict):
        if isinstance(info.get("title"), str):
            info["title"] = "ADE API"
        if isinstance(info.get("summary"), str):
            info["summary"] = "面向 ADE 与本地 ADE API 工作流的运行时与控制 API"
        if isinstance(info.get("description"), str):
            info["description"] = (
                "提供用于 ADE API 运行时/控制/测试编排的版本化 API 路由。"
                "面向后端优先的 API 调用，并用于 ADE Web 集成。"
            )

    servers = openapi_payload.get("servers")
    if isinstance(servers, list):
        for server in servers:
            if isinstance(server, dict) and isinstance(server.get("description"), str):
                if server["description"] == "ADE API local":
                    server["description"] = "ADE API 本地服务"


def _apply_tag_translations(openapi_payload: dict[str, Any]) -> None:
    tags = openapi_payload.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and isinstance(tag.get("name"), str):
                tag["name"] = TAG_TRANSLATIONS.get(tag["name"], tag["name"])

    paths = openapi_payload.get("paths")
    if not isinstance(paths, dict):
        return

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            operation_tags = operation.get("tags")
            if not isinstance(operation_tags, list):
                continue
            operation["tags"] = [
                TAG_TRANSLATIONS.get(tag, tag) if isinstance(tag, str) else tag
                for tag in operation_tags
            ]


def _write_missing_report(
    report_path: Path,
    missing_summaries: set[str],
    missing_descriptions: set[str],
    missing_titles: set[str],
    unknown_title_tokens: set[str],
) -> None:
    payload = {
        "missing_summaries": sorted(missing_summaries),
        "missing_descriptions": sorted(missing_descriptions),
        "missing_titles": sorted(missing_titles),
        "unknown_title_tokens": sorted(unknown_title_tokens),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_canonical_json(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate manually curated Chinese OpenAPI artifact."
    )
    parser.add_argument(
        "--source",
        default="docs/openapi/ade-api-openapi.json",
        help="Source English OpenAPI artifact path.",
    )
    parser.add_argument(
        "--target",
        default="docs/openapi/ade-api-openapi-zh.json",
        help="Target Chinese OpenAPI artifact path.",
    )
    parser.add_argument(
        "--frontend-target",
        default="apps/ade-web/public/openapi/ade-api-openapi-zh.json",
        help="Frontend copy path for Chinese OpenAPI artifact.",
    )
    parser.add_argument(
        "--missing-report",
        default="docs/openapi/zh_openapi_missing_terms.json",
        help="Path to write untranslated term report for incremental curation.",
    )
    parser.add_argument(
        "--no-missing-report",
        action="store_true",
        help="Disable writing missing-term report.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    source_path = (project_root / args.source).resolve()
    target_path = (project_root / args.target).resolve()
    frontend_target_path = (project_root / args.frontend_target).resolve()
    missing_report_path = (project_root / args.missing_report).resolve()

    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Expected OpenAPI root object.")

    missing_summaries: set[str] = set()
    missing_descriptions: set[str] = set()
    missing_titles: set[str] = set()
    unknown_title_tokens: set[str] = set()

    _translate_document_fields(
        payload,
        missing_summaries,
        missing_descriptions,
        missing_titles,
        unknown_title_tokens,
    )
    _apply_top_level_translations(payload)
    _apply_tag_translations(payload)

    rendered = _canonical_json(payload)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    frontend_target_path.parent.mkdir(parents=True, exist_ok=True)

    target_path.write_text(rendered, encoding="utf-8")
    frontend_target_path.write_text(rendered, encoding="utf-8")

    print(f"[OK] Wrote Chinese OpenAPI artifact: {target_path}")
    print(f"[OK] Synced frontend Chinese OpenAPI artifact: {frontend_target_path}")
    if not args.no_missing_report:
        _write_missing_report(
            missing_report_path,
            missing_summaries,
            missing_descriptions,
            missing_titles,
            unknown_title_tokens,
        )
        print(f"[OK] Wrote missing-term report: {missing_report_path}")
        print(
            "[INFO] missing terms "
            f"summaries={len(missing_summaries)} "
            f"descriptions={len(missing_descriptions)} "
            f"titles={len(missing_titles)} "
            f"unknown_title_tokens={len(unknown_title_tokens)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
