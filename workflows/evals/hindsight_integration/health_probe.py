"""Bounded loopback HTTP readiness check without importing a TLS client stack."""

import socket


def probe(port: int = 8020, *, timeout: float = 2) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(("127.0.0.1", port))
        client.sendall(
            b"GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
        )
        with client.makefile("rb") as response:
            status = response.readline(256).split(b" ", 2)
        if (
            len(status) != 3
            or status[0] not in {b"HTTP/1.0", b"HTTP/1.1"}
            or status[1] != b"200"
        ):
            raise RuntimeError("Candidate loopback health did not return HTTP 200")


if __name__ == "__main__":
    probe()
