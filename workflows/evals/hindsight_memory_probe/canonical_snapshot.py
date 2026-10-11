"""Whitelist and SQL contract for canonical PostgreSQL table snapshots."""

from __future__ import annotations

SNAPSHOT_TABLES = (
    "banks", "documents", "chunks", "memory_units", "invalidated_memory_units",
    "observation_history", "entities", "unit_entities",
    "entity_cooccurrences", "memory_links",
)


def table_query(table: str) -> str:
    """Return ordered JSON rows, with no output row for an empty table."""
    if table not in SNAPSHOT_TABLES:
        raise RuntimeError("canonical_snapshot_table_not_allowed")
    return (f"SELECT to_jsonb(t)::text FROM public.{table} AS t "
            "ORDER BY to_jsonb(t)::text")
