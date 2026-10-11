"""P1 executable in pinned full Hindsight image. Actual providers + local fake HTTP."""

import asyncio
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PREFIX = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "


class FakeHTTP(BaseHTTPRequestHandler):
    requests = []
    fail_embeddings = False
    fail_chat = False

    def log_message(self, *_):
        pass

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append((self.path, payload))
        embedding = self.path.endswith("/embeddings")
        failure = self.fail_embeddings if embedding else self.fail_chat
        if embedding:
            body = {
                "object": "list",
                "data": [
                    {"object": "embedding", "index": i, "embedding": [0.0] * 1024}
                    for i, _ in enumerate(payload["input"])
                ],
                "usage": {"prompt_tokens": 1, "total_tokens": 1},
                "model": payload["model"],
            }
        else:
            body = {
                "id": "fake",
                "object": "chat.completion",
                "created": 1,
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": '{"text":"好"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            }
        data = json.dumps(
            {"error": {"message": "synthetic"}} if failure else body
        ).encode()
        self.send_response(500 if failure else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


async def qualify(base):
    from hindsight_api.config import get_config, clear_config_cache
    from hindsight_api.engine.embeddings import create_embeddings_from_env
    from hindsight_api.engine.providers.openai_compatible_llm import OpenAICompatibleLLM
    from pydantic import BaseModel

    class ResponseSchema(BaseModel):
        text: str

    # Use factory, not hand-built embedding class: catches global retry setting being ignored.
    os.environ.update(
        {
            "HINDSIGHT_API_EMBEDDINGS_PROVIDER": "openai",
            "HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY": "synthetic",
            "HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL": base,
            "HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
            "HINDSIGHT_API_EMBEDDINGS_MAX_RETRIES": "0",
            "HINDSIGHT_API_EMBEDDINGS_QUERY_PREFIX": PREFIX,
            "HINDSIGHT_API_EMBEDDINGS_PASSAGE_PREFIX": "",
        }
    )
    clear_config_cache()
    config = get_config()
    assert config.embeddings_max_retries == 0
    embeddings = create_embeddings_from_env()
    await embeddings.initialize()
    assert FakeHTTP.requests[-1][1]["input"] == ["test"]
    assert embeddings.dimension == 1024
    await embeddings.encode_query(["中文问题"])
    assert FakeHTTP.requests[-1][1]["input"] == [PREFIX + "中文问题"]
    await embeddings.encode_documents(["中文原文"])
    assert FakeHTTP.requests[-1][1]["input"] == ["中文原文"]
    before = len(FakeHTTP.requests)
    FakeHTTP.fail_embeddings = True
    try:
        await embeddings.encode_query(["失败重试"])
    except Exception:
        pass
    else:
        raise AssertionError("expected SDK failure")
    assert len(FakeHTTP.requests) - before == 4, (
        "actual SDK default is 3 retries / 4 attempts"
    )
    FakeHTTP.fail_embeddings = False
    # Inspect timeout from real provider's SDK, accounting for concurrency wrapper.
    inner = getattr(embeddings, "_inner", embeddings)
    client = inner._loop_client()
    assert client.max_retries == 3 and client.timeout.read == 600
    llm = OpenAICompatibleLLM(
        provider="openai",
        api_key="synthetic",
        base_url=base,
        model="deepseek::deepseek-flash",
        timeout=10,
        extra_body={"thinking": {"type": "disabled"}},
    )
    await llm.call(
        [{"role": "user", "content": "请提取 JSON"}],
        response_format=ResponseSchema,
        strict_schema=False,
        max_completion_tokens=128,
        max_retries=0,
    )
    request = FakeHTTP.requests[-1][1]
    assert request["response_format"] == {"type": "json_object"}
    assert request["thinking"] == {"type": "disabled"}
    assert "json_schema" not in json.dumps(request)
    assert any("text" in str(m["content"]) for m in request["messages"]), (
        "schema must be in prompt"
    )
    before = len(FakeHTTP.requests)
    FakeHTTP.fail_chat = True
    try:
        await llm.call(
            [{"role": "user", "content": "JSON"}],
            response_format=ResponseSchema,
            strict_schema=False,
            max_completion_tokens=128,
            max_retries=0,
        )
    except Exception:
        pass
    else:
        raise AssertionError("expected LLM failure")
    assert len(FakeHTTP.requests) - before == 1, "zero extra LLM attempts"
    before = len(FakeHTTP.requests)
    try:
        await llm.verify_connection()
    except Exception:
        pass
    else:
        raise AssertionError("expected startup verification failure")
    assert len(FakeHTTP.requests) - before == 3, (
        "startup verification hardcodes two extra LLM attempts"
    )
    await llm.cleanup()
    await client.close()
    print(
        "pinned_image_provider_qualification_passed; embeddings_attempts=4; SDK_read_timeout=600"
    )


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeHTTP)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        asyncio.run(
            asyncio.wait_for(
                qualify(f"http://127.0.0.1:{server.server_port}/v1"), timeout=90
            )
        )
    finally:
        server.shutdown()
