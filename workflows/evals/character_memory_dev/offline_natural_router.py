"""Loopback fake Model Router for the isolated natural-memory browser journey.

Every response is scripted. This server makes no outbound provider request and
does not establish model extraction, compaction, or reply quality.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count


def _catalog() -> dict:
    items = []
    for index, (role, alias, window) in enumerate(
        (
            ("conversation", "fake::conversation", 8192),
            ("reviewer", "fake::reviewer", 8192),
            ("retriever", "fake::retriever", 8192),
        ),
        start=1,
    ):
        items.append(
            {
                "model_key": alias,
                "source_adapter": "synthetic",
                "deployment": {
                    "deployment_id": f"synthetic-browser-{role}",
                    "roles": [role],
                    "lifecycle": "candidate",
                    "fingerprint": {
                        "sha256": str(index) * 64,
                        "context_settings": {
                            "total_tokens": window,
                            "max_output_tokens": 512,
                            "reviewer_repair_count": 0,
                        },
                        "sampling_settings": {"dimensions": 3},
                    },
                    "qualification": {"role_results": []},
                },
            }
        )
    return {"items": items}


class FakeRouterHandler(BaseHTTPRequestHandler):
    request_ids = count(1)

    def _send(self, payload: dict, *, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/router/model-catalog":
            self._send(_catalog())
        else:
            self._send({"error": "unknown fake route"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 1_000_000:
            self._send({"error": "invalid fake request size"}, status=400)
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except ValueError:
            self._send({"error": "invalid JSON"}, status=400)
            return
        if self.path == "/v1/embeddings":
            self._send(
                {
                    "data": [
                        {"index": index, "embedding": [1.0, 0.0, 0.0]}
                        for index, _ in enumerate(payload.get("input", []))
                    ]
                }
            )
            return
        if self.path != "/v1/chat/completions":
            self._send({"error": "unknown fake route"}, status=404)
            return
        if payload.get("model") == "fake::conversation":
            content = "I hear you live in Toronto."
        elif payload.get("model") == "fake::reviewer":
            packet = json.loads(payload["messages"][1]["content"])
            current = packet["current_user_message"]
            if "I live in Toronto" in current["content"]:
                decision = {
                    "proposals": [
                        {
                            "claim_id": "browser-residence",
                            "operation": "add",
                            "fact_type": "person.current_location",
                            "value": "Toronto",
                            "evidence_quote": "I live in Toronto",
                            "sources": [
                                {
                                    "message_id": current["id"],
                                    "quote": "I live in Toronto",
                                    "role": "user_assertion",
                                }
                            ],
                        }
                    ],
                    "claim_dispositions": [
                        {
                            "claim_id": "browser-residence",
                            "outcome": "allow",
                            "reason": "supported",
                        }
                    ],
                }
            else:
                decision = {"proposals": [], "claim_dispositions": []}
            content = json.dumps(decision, ensure_ascii=False)
        else:
            self._send({"error": "unknown fake model"}, status=400)
            return
        self._send(
            {
                "id": f"fake-browser-{next(self.request_ids)}",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": content},
                    }
                ],
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8130)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), FakeRouterHandler).serve_forever()


if __name__ == "__main__":
    main()
