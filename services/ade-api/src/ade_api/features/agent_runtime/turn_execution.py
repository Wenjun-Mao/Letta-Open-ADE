"""Execute a Hindsight-backed reply without a second ADE memory engine."""

from __future__ import annotations

import time

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.integrations.hindsight import HindsightClient
from ade_api.platform.settings import AdeApiSettings

from .compaction import plan_compaction
from .compaction_executor import CompactionExecutor
from .context import context_budget_from_deployment
from .deployments import definition_deployment, validate_definition_execution
from .errors import RuntimeValidationError
from .evaluation_tools import evaluation_tool_registry
from .executor import ConversationExecutor, curated_tools
from .hindsight_context import build_hindsight_context, validate_input
from .memory_banks import MemoryBankAccess
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .persistence.memory_relationships import MemoryRelationshipRepository
from .persistence.workspaces import WorkspaceRepository
from .provider_tracing import AttemptTrace
from .release_policy import release_validation_kwargs
from .router_transport import RouterTransport
from .turn_deployment import deployment_adapter, max_model_requests
from .turn_recall import TurnRecall
from .turn_result import AttemptResult
from .turn_sources import relationship_for, require_hindsight_definition


class TurnExecution:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        transport: RouterTransport,
        settings: AdeApiSettings,
        hindsight_client: HindsightClient,
    ) -> None:
        self.engine = engine
        self.transport = transport
        self.settings = settings
        self.client = hindsight_client

    async def execute(
        self, run: dict, *, deadline: float, trace: AttemptTrace
    ) -> AttemptResult:
        # SQL snapshots end before any native or provider HTTP request.
        async with self.engine.connect() as connection:
            conversations = ConversationRepository(connection)
            conversation = await conversations.get(str(run["conversation_id"]))
            if str(conversation["workspace_id"]) != str(run["workspace_id"]):
                raise RuntimeValidationError("Run is outside its conversation")
            workspace = await WorkspaceRepository(connection).get(
                str(run["workspace_id"])
            )
            if workspace["memory_backend"] != "hindsight":
                raise RuntimeValidationError(
                    "Retained native workspaces cannot execute in this runtime"
                )
            subject = await MemoryRepository(connection).get_subject(
                str(conversation["memory_subject_id"])
            )
            if conversation["archived_at"] or subject["archived_at"]:
                raise RuntimeValidationError(
                    "Archived relationships cannot execute replies"
                )
            if int(conversation["version"]) != int(
                run["accepted_conversation_version"]
            ):
                raise RuntimeValidationError("Saved reply conversation changed")
            definition = await DefinitionVersionRepository(connection).get(
                str(conversation["agent_definition_version_id"])
            )
            require_hindsight_definition(definition)
            scope = relationship_for(conversation, definition)
            relationship = await MemoryRelationshipRepository(connection).get(
                scope.bank_id, workspace_id=scope.workspace_id
            )
            messages = await conversations.list_messages(str(conversation["id"]))
            summary = await conversations.latest_summary(str(conversation["id"]))
        users = [
            row
            for row in messages
            if row["role"] == "user" and str(row.get("run_id")) == str(run["id"])
        ]
        if len(users) != 1:
            raise RuntimeValidationError("Run has no unique immutable accepted input")
        current_user = users[0]
        trace.identity.update(
            {
                "subject_id": scope.subject_id,
                "character_root_id": scope.character_root_id,
            }
        )
        trace.record_private(
            "context.sources",
            {
                "bank_id": scope.bank_id,
                "bank_configuration_sha256": relationship["configuration_sha256"],
                "definition_version_id": str(definition["id"]),
                "definition_root_id": scope.character_root_id,
                "current_user_message_id": str(current_user["id"]),
                "message_ids": [str(row["id"]) for row in messages],
                "summary": summary,
            },
        )

        # Pending delivery is deliberately not an admission barrier. Every attempt
        # (including saved-input Retry) still performs this required lookup.
        recall = TurnRecall(
            banks=MemoryBankAccess(
                engine=self.engine, client=self.client, workspace_id=scope.workspace_id
            ),
            client=self.client,
            bank_id=scope.bank_id,
            deadline=deadline,
            trace=trace,
        )
        memories = await recall.lookup(current_user["content"])
        catalog = await trace.transport(self.transport, stage="catalog").catalog(
            timeout_seconds=min(
                _remaining(deadline), self.settings.model_discovery_timeout_seconds
            )
        )
        validate_definition_execution(
            definition,
            catalog,
            mode=self.settings.agent_runtime_mode,
            **release_validation_kwargs(self.settings.agent_runtime_mode),
        )
        deployment = definition_deployment(definition, "conversation")
        compaction_deployment = definition_deployment(definition, "compaction")
        adapter = deployment_adapter(catalog, deployment)
        budget = context_budget_from_deployment(deployment)
        compaction_budget = context_budget_from_deployment(compaction_deployment)
        validate_input(definition, current_user["content"], budget)
        compaction = None
        plan = plan_compaction(
            messages=messages,
            current_user_message_id=str(current_user["id"]),
            summary=summary,
            recent_token_budget=budget.recent_tokens,
            compaction_input_token_budget=compaction_budget.input_limit,
        )
        if plan is not None:
            trace.record_private(
                "compaction.sources",
                {
                    "source_message_ids": list(plan.source_message_ids),
                    "through_sequence": plan.through_sequence,
                },
            )
            compaction = await CompactionExecutor(
                trace.transport(
                    self.transport,
                    stage="compaction",
                    model_fingerprint=str(compaction_deployment["fingerprint"]),
                ),
                provider_adapter=deployment_adapter(catalog, compaction_deployment),
            ).compact(
                model_key=str(compaction_deployment["route_alias"]),
                model_fingerprint=str(compaction_deployment["fingerprint"]),
                plan=plan,
                timeout_seconds=_remaining(deadline),
                max_output_tokens=compaction_budget.max_output_tokens,
                summary_token_budget=budget.summary_tokens,
                input_token_limit=compaction_budget.input_limit,
            )
            summary = {
                "through_sequence": plan.through_sequence,
                "content": compaction.content,
            }
            trace.record_private(
                "compaction.completed",
                {
                    "content": compaction.content,
                    "content_sha256": compaction.content_sha256,
                    "input_sha256": compaction.input_sha256,
                    "source_message_ids": list(plan.source_message_ids),
                    "model_fingerprint": compaction.model_fingerprint,
                    "provider_request_id": compaction.provider_request_id,
                },
            )
        tools = curated_tools(
            tuple(definition["tool_names"]),
            search_memory=recall.search,
            additional_tools=evaluation_tool_registry()
            if conversation.get("purpose") == "evaluation"
            else None,
        )
        context = build_hindsight_context(
            definition=definition,
            messages=messages,
            current_user=current_user,
            summary=summary,
            memories=memories,
            budget=budget,
            tools=tools,
            provider_adapter=adapter,
            model_key=str(deployment["route_alias"]),
        )
        trace.record_private(
            "context.composed",
            {
                "messages": context.messages,
                "components": context.components,
                "omitted_message_ids": context.omitted_message_ids,
                "automatic_memory_ids": context.retrieved_fact_ids,
            },
        )
        result = await ConversationExecutor(
            trace.transport(
                self.transport,
                stage="conversation",
                model_fingerprint=str(deployment["fingerprint"]),
            ),
            provider_adapter=adapter,
        ).execute(
            model_key=str(deployment["route_alias"]),
            messages=context.messages,
            timeout_seconds=_remaining(deadline),
            max_output_tokens=budget.max_output_tokens,
            tools=tools,
            max_model_requests=max_model_requests(deployment),
            input_token_limit=budget.input_limit,
        )
        return AttemptResult(
            assistant_text=result.assistant_text,
            context=context,
            executor=result,
            compaction=compaction,
            memory_lookups=tuple(recall.observations),
        )


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("whole runtime attempt timed out")
    return remaining
