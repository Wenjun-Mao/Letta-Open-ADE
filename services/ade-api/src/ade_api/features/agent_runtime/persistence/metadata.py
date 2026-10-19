"""Named ADE persistence tables; migrations remain the schema authority."""

from .metadata_schema import METADATA as METADATA, SCHEMA_NAME as SCHEMA_NAME
from .metadata_delivery import (
    memory_relationships as memory_relationships,
    memory_deliveries as memory_deliveries,
    run_retry_requests as run_retry_requests,
)

from .metadata_products import (
    workspaces as workspaces,
    agent_definitions as agent_definitions,
    agent_definition_versions as agent_definition_versions,
    memory_subjects as memory_subjects,
    conversations as conversations,
)

from .metadata_execution import (
    runs as runs,
    messages as messages,
    run_attempts as run_attempts,
    run_events as run_events,
    outbox as outbox,
    conversation_leases as conversation_leases,
    worker_instances as worker_instances,
)

from .metadata_compaction import (
    conversation_summaries as conversation_summaries,
    summary_sources as summary_sources,
)

from .metadata_native_history import (
    memory_entities as memory_entities,
    agent_studio_reset_receipts as agent_studio_reset_receipts,
    memory_actions as memory_actions,
    memory_facts as memory_facts,
    memory_revisions as memory_revisions,
    memory_revision_predecessors as memory_revision_predecessors,
    memory_revision_sources as memory_revision_sources,
    memory_embeddings as memory_embeddings,
)


ALL_TABLES = tuple(METADATA.tables.values())
