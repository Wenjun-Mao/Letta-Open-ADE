"""Owned-resource/alias safeguards without Docker or provider calls."""

from copy import deepcopy
import json
import socket

import pytest

from .. import native_environment as environment
from ..native_service import install_spark_alias


@pytest.mark.parametrize("change", ["id", "label", "image", "mount"])
def test_retained_or_unowned_container_rejected(monkeypatch, change):
    receipt = {"container_id": "owned-id", "token": "owner-token"}
    inspected = {
        "Id": "owned-id",
        "Config": {
            "Labels": {"ade.pc11.owner": "owner-token"},
            "Image": environment.IMAGE,
        },
        "HostConfig": {"Binds": None},
    }
    other = deepcopy(inspected)
    if change == "id":
        other["Id"] = "retained-id"
    elif change == "label":
        other["Config"]["Labels"]["ade.pc11.owner"] = "another-owner"
    elif change == "image":
        other["Config"]["Image"] = "different-image"
    else:
        other["HostConfig"]["Binds"] = ["/retained:/data"]
    monkeypatch.setattr(environment, "command", lambda *_: json.dumps([other]))
    with pytest.raises(ValueError, match="ownership"):
        environment.owned_container(receipt)


def test_alias_is_process_local_and_does_not_rewrite_other_hosts(monkeypatch):
    calls = []
    monkeypatch.setattr(socket, "getaddrinfo", lambda name, *a, **k: calls.append(name))
    install_spark_alias("192.0.2.5")
    socket.getaddrinfo("dgx-spark", 8001)
    socket.getaddrinfo(b"dgx-spark", 8001)
    socket.getaddrinfo("api.deepseek.com", 443)
    assert calls == ["192.0.2.5", "192.0.2.5", "api.deepseek.com"]


def test_alias_rejects_unconfigured_hostnames():
    with pytest.raises(ValueError):
        install_spark_alias("another-service.invalid")


def test_alias_cannot_change_between_native_launches(tmp_path):
    environment.bind_alias(tmp_path, "192.0.2.5")
    environment.bind_alias(tmp_path, "192.0.2.5")
    with pytest.raises(ValueError, match="changed"):
        environment.bind_alias(tmp_path, "192.0.2.6")
