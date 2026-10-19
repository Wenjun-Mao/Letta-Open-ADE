"""Normal product orchestration with real SQL and controlled network boundaries."""

import copy
from uuid import uuid4

from sqlalchemy import select, text

from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.deployments import resolve_deployment
from ade_api.features.agent_runtime.persistence.metadata import conversations, runs
from ade_api.features.agent_runtime.router_transport import RouterRequestError
from ade_api.features.agent_runtime.run_service import RunService
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.integrations.hindsight import HindsightError
from ade_api.platform.settings import AdeApiSettings

from .hindsight_native_fake import NativeDeliveryFake
from .hindsight_support import scope


CATALOG = {
    "items": [
        {
            "model_key": "fake::character",
            "source_adapter": "openai_compatible",
            "deployment": {
                "deployment_id": "controlled-character",
                "roles": ["conversation", "compaction"],
                "lifecycle": "candidate",
                "fingerprint": {
                    "sha256": "c" * 64,
                    "context_settings": {
                        "total_tokens": 16384,
                        "max_output_tokens": 1024,
                    },
                },
                "qualification": {
                    "qualified": False,
                    "stale_round_count": 0,
                    "role_results": [
                        {"role": role, "qualified": False}
                        for role in ("conversation", "compaction")
                    ],
                },
            },
        }
    ]
}


class ReadyWorker:
    async def get_health(self):
        return {"worker_ready": True}


class CharacterTransport:
    def __init__(self, db):
        self.db = db
        self.requests = []
        self.fail = False
        self.responses = []
        self.started = None
        self.release = None

    async def catalog(self, **kwargs):
        return copy.deepcopy(CATALOG)

    async def chat_completion(self, payload, **kwargs):
        async with self.db.begin() as connection:
            await connection.execute(text("SET LOCAL lock_timeout = '100ms'"))
            await connection.execute(select(conversations).with_for_update())
            await connection.execute(select(runs).with_for_update())
        self.requests.append(copy.deepcopy(payload))
        if self.started:
            self.started.set()
            await self.release.wait()
        if self.fail:
            raise RouterRequestError("Controlled generation failure", retryable=False)
        if self.responses:
            return self.responses.pop(0)
        if "response_format" in payload:
            return {
                "id": "controlled-summary",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"summary":"Controlled summary of the supplied original prefix."}',
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        return {
            "id": "controlled-reply",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Controlled committed reply",
                    },
                    "finish_reason": "stop",
                }
            ],
        }


class NativeRecallFake(NativeDeliveryFake):
    def __init__(self, db):
        super().__init__(db)
        self.lookups = []
        self.fail_recall = False
        self.recall_started = None
        self.release_recall = None

    async def aclose(self):
        pass

    async def recall(self, bank, payload):
        await self.outside_transaction(bank)
        self.lookups.append((bank, copy.deepcopy(payload)))
        if self.recall_started:
            self.recall_started.set()
            await self.release_recall.wait()
        if self.fail_recall:
            raise HindsightError("hindsight_unavailable")
        return {"results": []}


async def runtime(db):
    settings = AdeApiSettings(
        _env_file=None,
        agent_runtime_mode="development",
        agent_runtime_workspace_key="runtime-sql-" + uuid4().hex,
    )
    database = RuntimeDatabase(db, workspace_key=settings.agent_runtime_workspace_key)
    async with db.begin() as connection:
        await database.ensure_workspace(connection)
        owner = await scope(
            connection,
            workspace_id=database.workspace_id,
            deployments=[
                resolve_deployment(
                    CATALOG,
                    route_alias="fake::character",
                    role=role,
                    mode="development",
                ).as_snapshot()
                for role in ("conversation", "compaction")
            ],
        )
    transport, native = CharacterTransport(db), NativeRecallFake(db)
    service = RunService(
        database=database,
        settings=settings,
        router_transport=transport,
        worker_health=ReadyWorker(),
    )
    worker = AgentRuntimeWorker(
        engine=db, settings=settings, transport=transport, hindsight_client=native
    )
    return owner, service, worker, native, transport
