"""Authoring requires the existing admin role; repairs cannot expose a public web port."""

import copy

import pytest

from ..web_reconfigure import require_web_binding


@pytest.mark.parametrize("damage", [None, "operator", "public", "image", "api"])
def test_web_configuration_uses_server_side_authoring_role_without_weakening_api(
    damage,
):
    config = {
        "services": {
            "ade-web": {
                "image": "owned-web:source",
                "environment": {
                    "ADE_API_ADMIN_KEY": "synthetic-admin",
                    "ADE_API_BASE_URL": "http://ade-api:8000",
                },
                "ports": [
                    {"host_ip": "127.0.0.1", "published": "18020", "target": 3000}
                ],
            }
        }
    }
    config = copy.deepcopy(config)
    web = config["services"]["ade-web"]
    if damage == "operator":
        web["environment"]["ADE_API_ADMIN_KEY"] = "synthetic-operator"
    if damage == "public":
        web["ports"][0]["host_ip"] = "0.0.0.0"
    if damage == "image":
        web["image"] = "unbound-web:latest"
    if damage == "api":
        web["environment"]["ADE_API_BASE_URL"] = "http://incumbent:8000"
    values = {
        "INTEGRATION_ADE_ADMIN_KEY": "synthetic-admin",
        "INTEGRATION_ADE_OPERATOR_KEY": "synthetic-operator",
    }
    if damage:
        with pytest.raises(ValueError, match="authoring_binding"):
            require_web_binding(config, values, {"image": "owned-web:source"})
    else:
        require_web_binding(config, values, {"image": "owned-web:source"})
