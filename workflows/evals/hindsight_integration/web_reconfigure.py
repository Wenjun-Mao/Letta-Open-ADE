"""Apply only the corrected private web credential binding to an exact owned image."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

from .native_faults import healthy_lease
from .operations import DockerOperations, Lease, create_record, stop_owned
from .paired_backup import owned_service
from .startup import require_configuration


def require_web_binding(configuration, values, image):
    service = configuration["services"]["ade-web"]
    environment = service["environment"]
    if not (
        service["image"] == image["image"]
        and environment["ADE_API_ADMIN_KEY"] == values["INTEGRATION_ADE_ADMIN_KEY"]
        and environment["ADE_API_ADMIN_KEY"] != values["INTEGRATION_ADE_OPERATOR_KEY"]
        and environment["ADE_API_BASE_URL"] == "http://ade-api:8000"
        and {
            (row["host_ip"], str(row["published"]), row["target"])
            for row in service["ports"]
        }
        == {("127.0.0.1", "18020", 3000)}
    ):
        raise ValueError("owned_web_authoring_binding_invalid")


def reconfigure(root, environment, output, *, controller_revision):
    source = Path(__file__).resolve().parents[3]
    if (
        not re.fullmatch(r"[a-f0-9]{40}", controller_revision)
        or source.name != controller_revision
    ):
        raise ValueError("Use a staged committed web controller")
    root, output = root.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(root / "evidence"):
        raise ValueError("Use a new owned web configuration receipt directory")
    lease, docker = Lease.load(root), DockerOperations()
    healthy_lease(root, lease, docker)
    require_configuration(root, environment, lease)
    if time.time() + 300 >= lease.dispatch_deadline:
        raise ValueError("Web reconfiguration cannot fit the dispatch window")
    before = owned_service(docker, lease, "ade-web")
    images = json.loads((root / "images.json").read_bytes())
    web_images = [row for row in images["images"] if row["role"] == "web"]
    if (
        images["source_revision"] != lease.source_revision
        or images["activation_id"] != lease.activation_id
        or len(web_images) != 1
        or before["image"] != web_images[0]["image_id"]
    ):
        raise ValueError("owned_web_image_receipt_mismatch")
    if (
        docker._run(
            ["image", "inspect", web_images[0]["image"], "--format", "{{.Id}}"]
        ).strip()
        != before["image"]
    ):
        raise ValueError("owned_web_image_tag_changed")
    values = dict(
        shlex.split(line)[0].split("=", 1)
        for line in environment.read_text().splitlines()
        if line and not line.startswith("#")
    )
    compose = Path(__file__).with_name("compose.yaml")
    command = [
        "docker",
        "compose",
        "--env-file",
        str(environment),
        "-f",
        str(compose),
        "--profile",
        "product",
    ]
    resolved = subprocess.run(
        [*command, "config", "--format", "json"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    require_web_binding(json.loads(resolved.stdout), values, web_images[0])
    create_record(
        output / "plan.json",
        {
            "product_image_revision": lease.source_revision,
            "configuration_controller_revision": controller_revision,
            "compose_sha256": hashlib.sha256(compose.read_bytes()).hexdigest(),
            "activation_id": lease.activation_id,
            "before": before,
            "credential_role": "admin_authoring_server_side_only",
            "unchanged": [
                "product_image",
                "api_roles",
                "sealed_environment",
                "api",
                "worker",
                "both_databases",
            ],
        },
    )
    try:
        with (output / "compose.log").open("x") as log:
            (output / "compose.log").chmod(0o600)
            subprocess.run(
                [
                    *command,
                    "up",
                    "-d",
                    "--no-deps",
                    "--force-recreate",
                    "--no-build",
                    "--pull",
                    "never",
                    "ade-web",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=180,
                check=True,
            )
        healthy_lease(root, lease, docker)
        require_configuration(root, environment, lease)
        after = owned_service(docker, lease, "ade-web")
        actual = dict(
            item.split("=", 1)
            for item in json.loads(
                docker._run(
                    [
                        "inspect",
                        "--format",
                        "{{json .Config.Env}}",
                        after["id"],
                    ]
                )
            )
        )
        if (
            after["image"] != before["image"]
            or after["state"] != "running"
            or actual["ADE_API_ADMIN_KEY"] != values["INTEGRATION_ADE_ADMIN_KEY"]
        ):
            raise ValueError("owned_web_reconfiguration_not_applied")
        create_record(
            output / "outcome.json",
            {"status": "passed", "after": after, "browser_verification": "pending"},
        )
    except Exception as exc:
        create_record(output / "failure.json", {"error_type": type(exc).__name__})
        stop_owned(
            lease, docker=docker, root=root, reason="owned_web_reconfiguration_failed"
        )
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--controller-revision", required=True)
    args = parser.parse_args()
    reconfigure(
        args.root,
        args.environment,
        args.out,
        controller_revision=args.controller_revision,
    )


if __name__ == "__main__":
    main()
