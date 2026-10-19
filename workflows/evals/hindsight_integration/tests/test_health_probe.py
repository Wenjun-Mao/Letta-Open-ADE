"""The cheaper probe still requires a successful, bounded HTTP response."""

import socket
from threading import Thread

import pytest

from ..health_probe import probe


@pytest.mark.parametrize(
    "response",
    [
        b"HTTP/1.1 200 OK\r\n",
        b"HTTP/1.0 200 OK\r\n",
        b"HTTP/1.1 503 Closed\r\n",
        b"not HTTP\r\n",
    ],
)
def test_probe_requires_actual_http_200_from_the_health_route(response):
    observed = []
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def serve():
            client, _ = server.accept()
            with client:
                observed.append(client.recv(4096))
                client.sendall(response + b"Content-Length: 0\r\n\r\n")

        task = Thread(target=serve, daemon=True)
        task.start()
        if b" 200 " in response:
            probe(port)
        else:
            with pytest.raises(RuntimeError, match="HTTP 200"):
                probe(port)
        task.join(timeout=2)
        assert not task.is_alive()
        assert observed[0].startswith(b"GET /health HTTP/1.1\r\n")


def test_probe_times_out_instead_of_accepting_a_stalled_health_handler():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with pytest.raises(TimeoutError):
            probe(server.getsockname()[1], timeout=0.01)
