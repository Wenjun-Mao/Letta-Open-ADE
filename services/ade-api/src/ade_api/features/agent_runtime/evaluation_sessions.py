"""Evaluation sessions use the same product lifecycle, not SQL-only erasure."""

from .agent_studio_sessions import PurposeSessionService
from .contracts import CreateAgentStudioSessionRequest
from .session_resources import EVALUATION_PURPOSE, session_identity


class EvaluationSessionService:
    def __init__(self, *, database, definitions, resources):
        self.database, self.resources = database, resources
        self.sessions = PurposeSessionService(
            database=database,
            definitions=definitions,
            purpose=EVALUATION_PURPOSE,
            session_namespace="evaluation",
            allowed_tool_names=frozenset({"search_memory", "get_weather"}),
        )

    async def create(self, request):
        identity = session_identity(
            request.idempotency_key,
            workspace_id=self.database.workspace_id,
            namespace="evaluation",
        )
        return await self.sessions.create(
            CreateAgentStudioSessionRequest(
                idempotency_key=request.idempotency_key,
                title=request.title,
                agent_definition_id=request.agent_definition_id,
                new_definition=None
                if request.agent_definition_id
                else request.definition_request(
                    definition_key=f"evaluation_{identity.session_id.replace('-', '')}"
                ),
                memory_subject_id=request.memory_subject_id,
                new_subject=None
                if request.memory_subject_id
                else request.subject_request(
                    external_key=f"evaluation:{identity.session_id}"
                ),
            )
        )

    async def get_state(self, conversation_id, *, message_limit, before_sequence):
        conversation = await self.resources.get_conversation_state(
            conversation_id,
            required_purpose=EVALUATION_PURPOSE,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )
        session = await self.sessions.get(conversation_id)
        return {
            "conversation": conversation,
            "memory_subject": session["memory_subject"],
            "latest_run": session["latest_run"],
        }
