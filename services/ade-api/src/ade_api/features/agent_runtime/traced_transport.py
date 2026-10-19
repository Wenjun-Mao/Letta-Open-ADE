"""One-attempt lifecycle tracing and correlation for every model continuation."""

import asyncio
import re
from dataclasses import dataclass
from typing import Any

from .router_correlation import correlate_request


@dataclass(frozen=True)
class TracedRouterTransport:
    transport: Any
    trace: Any
    stage: str
    model_fingerprint: str | None = None

    async def catalog(self, *, timeout_seconds=10.0):
        return await self._invoke(
            operation="catalog",
            payload=None,
            timeout_seconds=timeout_seconds,
            call=lambda: self.transport.catalog(timeout_seconds=timeout_seconds),
        )

    async def chat_completion(self, payload, *, timeout_seconds):
        return await self._invoke(
            operation="chat_completion",
            payload=payload,
            timeout_seconds=timeout_seconds,
            call=lambda: self.transport.chat_completion(
                payload, timeout_seconds=timeout_seconds
            ),
        )

    async def embeddings(self, payload, *, timeout_seconds):
        return await self._invoke(
            operation="embeddings",
            payload=payload,
            timeout_seconds=timeout_seconds,
            call=lambda: self.transport.embeddings(
                payload, timeout_seconds=timeout_seconds
            ),
        )

    async def _invoke(self, *, operation, payload, timeout_seconds, call):
        started = None
        try:
            started = self.trace._start(
                operation=operation,
                stage=self.stage,
                model_key=payload.get("model")
                if payload and isinstance(payload.get("model"), str)
                else None,
                model_fingerprint=self.model_fingerprint,
                timeout_seconds=timeout_seconds,
            )
        except Exception:
            # Capture cannot veto the product operation; qualification fails on gaps.
            self.trace.observation_incomplete = True
        metadata = {
            **self.trace.identity,
            "observation_role": self.stage,
            "observation_phase": "reply",
            **({"request_id": started[0]} if started else {}),
        }
        with correlate_request(metadata) as correlation:
            if started:
                self.trace.record_private(
                    "model_request.started",
                    {
                        "request_id": started[0],
                        "operation": operation,
                        "stage": self.stage,
                        "request_number": started[1],
                        "model_fingerprint": self.model_fingerprint,
                        "payload": payload,
                    },
                )
            try:
                response = await call()
            except BaseException as exc:
                if started:
                    try:
                        args = dict(
                            request_id=started[0],
                            operation=operation,
                            stage=self.stage,
                            request_number=started[1],
                            started_at=started[2],
                        )
                        if isinstance(exc, asyncio.CancelledError):
                            self.trace._cancel(**args)
                        elif isinstance(exc, Exception):
                            self.trace._fail(
                                **args,
                                exc=exc,
                                router_request_id=correlation.router_request_id,
                            )
                        self.trace.record_private(
                            "model_request.finished",
                            {
                                "request_id": started[0],
                                "status": "failed",
                                "error_type": type(exc).__name__,
                                "router_request_id": correlation.router_request_id,
                            },
                        )
                    except Exception:
                        self.trace.observation_incomplete = True
                raise
            if started:
                try:
                    self.trace._complete(
                        request_id=started[0],
                        operation=operation,
                        stage=self.stage,
                        request_number=started[1],
                        response=response,
                        started_at=started[2],
                        router_request_id=correlation.router_request_id,
                    )
                    self.trace.record_private(
                        "model_request.finished",
                        {
                            "request_id": started[0],
                            "status": "received",
                            "provider_request_id": response.get("id")
                            if isinstance(response.get("id"), str)
                            and re.fullmatch(
                                r"[A-Za-z0-9._:-]{1,256}", response["id"].strip()
                            )
                            else None,
                            "router_request_id": correlation.router_request_id,
                        },
                    )
                except Exception:
                    self.trace.observation_incomplete = True
            return response
