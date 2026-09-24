"""Local alias contract for the one-shot factual diagnostic host."""

import socket

from workflows.evals.character_memory_dev.natural_factual_live import (
    install_spark_alias,
)


def test_spark_alias_accepts_sync_and_async_dns_forms(monkeypatch):
    resolved = []

    def fake_getaddrinfo(name, *args, **kwargs):
        resolved.append(name)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    install_spark_alias("192.0.2.5")

    socket.getaddrinfo("dgx-spark", 8001)
    socket.getaddrinfo(b"dgx-spark", 8001)
    socket.getaddrinfo("example.com", 443)

    assert resolved == ["192.0.2.5", "192.0.2.5", "example.com"]
