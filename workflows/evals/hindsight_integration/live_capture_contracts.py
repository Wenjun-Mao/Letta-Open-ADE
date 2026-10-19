"""Versioned source-linked sidecars; setup requests never masquerade as probes."""

from typing import Literal

from pydantic import Field

from .models import Record, Text, Digest, Identifier, Positive


class FileReference(Record):
    path: Text
    file_sha256: Digest


class PhaseReference(FileReference):
    phase: Literal["setup", "probe"]
    run_id: Text


class ProductSlotManifest(Record):
    schema_version: Literal[1] = 1
    case_id: Identifier
    repeat: Positive
    actor_sha256: Digest
    source: dict[str, str]
    scope: dict[str, str]
    source_conversation_id: Text
    probe_conversation_id: Text
    collections: list[PhaseReference]
    readbacks: FileReference
    journals: list[FileReference]


class ProductCollection(Record):
    schema_version: Literal[1]
    phase_group: Literal["setup", "probe", "diagnostic"]
    phase_run_id: Text
    run: dict
    export: dict
    state: dict
    events: list[dict]
    wires: list[dict]
    scope: dict[str, str]
    source: dict[str, str]
    expected_input: Text
    fresh_probe: bool


class ProductReadbacks(Record):
    source_session: dict
    probe_session: dict
    source_initial_state: dict
    probe_initial_state: dict
    source_initial_memories: dict
    probe_initial_memories: dict
    source_initial_deliveries: dict
    deliveries: dict
    operations: dict
    memories: dict
    source_state: dict
    source_documents: list[dict]


class HttpJournal(Record):
    schema_version: Literal[1]
    requests: int = Field(ge=0)
    files: list[FileReference]
