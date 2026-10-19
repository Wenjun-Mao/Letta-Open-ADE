"""Temporary candidate-only HTTP faults. Idle forwarding never changes input bytes."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import secrets
import time
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
import httpx
from pydantic import BaseModel, ConfigDict, Field

from .operations import Lease, create_record
from .startup import require_supervision


class FaultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    conversation_id: UUID
    target: Literal["router_chat", "memory_retain"]
    mode: Literal[
        "fail_before_send", "hold_before_send", "hold_after_response", "lose_ack"
    ]
    hold_seconds: int = Field(default=240, ge=1, le=300)


@dataclass
class Rule:
    request: FaultRequest
    matched: bool = False
    released: asyncio.Event = field(default_factory=asyncio.Event)
    outcome: dict = field(default_factory=dict)

    def status(self):
        return {
            **self.request.model_dump(mode="json"),
            "matched": self.matched,
            "released": self.released.is_set(),
            "outcome": self.outcome,
        }


@dataclass(frozen=True)
class ProxyConfig:
    activation_root: Path
    record_root: Path
    control_key: str

    def fence(self):
        try:
            lease = Lease.load(self.activation_root)
            now = time.time()
            if (
                self.activation_root / "closed.json"
            ).exists() or now >= lease.dispatch_deadline:
                raise HTTPException(503, "Candidate activation is closed")
            require_supervision(self.activation_root, lease, now=now)
        except (ValueError, OSError) as exc:
            raise HTTPException(503, "Candidate supervision is unavailable") from exc
        return lease


def create_app(
    config: ProxyConfig, *, client: httpx.AsyncClient | None = None
) -> FastAPI:
    if not config.control_key:
        raise ValueError("A private fault-control credential is required")
    config.record_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if config.record_root.is_symlink() or config.record_root.stat().st_mode & 0o077:
        raise ValueError("Fault records require a private directory")
    rules: dict[str, Rule] = {}

    @asynccontextmanager
    async def lifespan(app):
        app.state.upstream = client or httpx.AsyncClient(timeout=180)
        try:
            yield
        finally:
            if client is None:
                await app.state.upstream.aclose()

    app = FastAPI(lifespan=lifespan)
    if client is not None:
        app.state.upstream = client

    def auth(value):
        if not secrets.compare_digest(value or "", "Bearer " + config.control_key):
            raise HTTPException(401, "Invalid fault-control credential")

    def record(rule: Rule, stage: str, **value):
        lease = config.fence()
        create_record(
            config.record_root / f"{time.time_ns()}-{uuid4().hex}.json",
            {
                "activation_id": lease.activation_id,
                "source_revision": lease.source_revision,
                "fault_id": str(rule.request.id),
                "stage": stage,
                "time": time.time(),
                **value,
            },
        )

    @app.get("/health")
    def health():
        config.fence()
        return {"status": "ok"}

    @app.post("/control/rules")
    async def arm(
        request: FaultRequest, authorization: str | None = Header(default=None)
    ):
        auth(authorization)
        config.fence()
        identity = str(request.id)
        if identity in rules:
            if rules[identity].request != request:
                raise HTTPException(409, "Fault identity already has a different plan")
            return rules[identity].status()
        if any(
            not rule.matched
            and rule.request.conversation_id == request.conversation_id
            and rule.request.target == request.target
            for rule in rules.values()
        ):
            raise HTTPException(
                409, "An unconsumed fault already targets this conversation"
            )
        rules[identity] = Rule(request)
        record(rules[identity], "armed", plan=request.model_dump(mode="json"))
        return rules[identity].status()

    @app.get("/control/rules/{identity}")
    async def status(identity: UUID, authorization: str | None = Header(default=None)):
        auth(authorization)
        if str(identity) not in rules:
            raise HTTPException(404, "Fault identity not found")
        return rules[str(identity)].status()

    @app.post("/control/rules/{identity}/release")
    async def release(identity: UUID, authorization: str | None = Header(default=None)):
        auth(authorization)
        config.fence()
        if str(identity) not in rules:
            raise HTTPException(404, "Fault identity not found")
        rule = rules[str(identity)]
        rule.released.set()
        record(rule, "released")
        return rule.status()

    async def wait(rule, request):
        deadline = time.monotonic() + rule.request.hold_seconds
        while not rule.released.is_set():
            config.fence()
            if await request.is_disconnected():
                raise HTTPException(499, "Injected hold caller disconnected")
            if time.monotonic() >= deadline:
                raise HTTPException(503, "Bounded injected hold expired")
            try:
                await asyncio.wait_for(rule.released.wait(), timeout=0.5)
            except TimeoutError:
                pass
        config.fence()
        if await request.is_disconnected():
            raise HTTPException(499, "Injected hold caller disconnected before release")

    @app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "PATCH"])
    async def forward(service: str, path: str, request: Request):
        config.fence()
        if service not in {"router", "hindsight"}:
            raise HTTPException(404, "Unknown candidate upstream")
        raw = await request.body()
        target, conversation, operation = None, None, None
        if (
            request.method == "POST"
            and service == "router"
            and path == "v1/chat/completions"
        ):
            target, conversation = (
                "router_chat",
                request.headers.get("x-ade-conversation-id"),
            )
        if (
            request.method == "POST"
            and service == "hindsight"
            and path.endswith("/memories")
        ):
            body = await request.json()
            items = body.get("items", [])
            if len(items) == 1 and isinstance(items[0].get("metadata"), dict):
                target = "memory_retain"
                conversation = items[0]["metadata"].get("conversation_id")
                try:
                    operation = str(UUID(body.get("operation_id", "")))
                except (ValueError, TypeError, AttributeError):
                    target = None
        rule = next(
            (
                rule
                for rule in rules.values()
                if not rule.matched
                and rule.request.target == target
                and str(rule.request.conversation_id) == conversation
            ),
            None,
        )
        if rule:
            rule.matched = True
            rule.outcome = {
                "operation_id": operation,
                "request_sha256": hashlib.sha256(raw).hexdigest(),
            }
            record(rule, "matched", **rule.outcome)
            if rule.request.mode == "fail_before_send":
                return JSONResponse(
                    {"error": {"code": "injected_candidate_failure"}}, status_code=400
                )
            if rule.request.mode == "hold_before_send":
                await wait(rule, request)
        config.fence()
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() in {"authorization", "content-type", "accept"}
            or key.lower().startswith("x-ade-")
        }
        base = (
            "http://model-router:8010"
            if service == "router"
            else "http://hindsight:8888"
        )
        try:
            upstream = await app.state.upstream.request(
                request.method,
                base + "/" + path,
                content=raw,
                params=request.url.query,
                headers=headers,
            )
        except httpx.HTTPError:
            if rule:
                record(rule, "upstream_transport_failed")
            return JSONResponse(
                {"error": {"code": "candidate_upstream_unavailable"}}, status_code=502
            )
        if rule:
            rule.outcome.update(
                {
                    "upstream_status": upstream.status_code,
                    "router_request_id": upstream.headers.get(
                        "X-Model-Router-Request-Id"
                    ),
                }
            )
            record(rule, "upstream_received", **rule.outcome)
            if rule.request.mode == "hold_after_response":
                await wait(rule, request)
            if rule.request.mode == "lose_ack":
                return JSONResponse(
                    {"error": {"code": "injected_lost_acknowledgement"}},
                    status_code=503,
                )
        return Response(
            upstream.content,
            status_code=upstream.status_code,
            headers={
                key: value
                for key, value in upstream.headers.items()
                if key.lower()
                not in {
                    "content-length",
                    "content-encoding",
                    "transfer-encoding",
                    "connection",
                }
            },
        )

    return app


def main():
    import uvicorn

    config = ProxyConfig(
        Path(os.environ["ADE_INTEGRATION_ACTIVATION_ROOT"]),
        Path(os.environ["ADE_INTEGRATION_FAULT_ROOT"]),
        os.environ["ADE_INTEGRATION_FAULT_KEY"],
    )
    uvicorn.run(create_app(config), host="0.0.0.0", port=8020, access_log=False)


if __name__ == "__main__":
    main()
