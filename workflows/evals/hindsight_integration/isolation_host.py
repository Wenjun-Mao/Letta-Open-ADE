"""A second, same-image API binds a fresh workspace only for negative access checks."""

import json
import re

from .operations import OWNER_LABEL, PROJECT_LABEL, SOURCE_LABEL, create_record
from .provision import _private_text
from .runtime_assets import seed_runtime_assets


class IsolationAPI:
    def __init__(self, controls):
        self.controls = controls
        self.name = controls.lease.project + "-" + controls.output.name + "-api"
        if not re.fullmatch(r"[a-z0-9-]{1,120}", self.name):
            raise ValueError("isolation_api_name_invalid")
        self.identity = None

    def start(self):
        control = self.controls
        control.fence()
        api = control.current("ade-api")
        network = control.lease.project + "_default"
        if list(api["networks"]) != [network]:
            raise ValueError("isolation_api_network_not_owned")
        running = [
            row
            for row in control.docker.owned(control.lease)
            if row["state"] in {"running", "restarting", "paused"}
        ]
        # Inspect each exact owned container, including the running evaluator.
        quotas = [
            int(
                control.docker._run(
                    [
                        "inspect",
                        "--format",
                        "{{.HostConfig.NanoCpus}}",
                        row["id"],
                    ]
                ).strip()
            )
            for row in running
        ]
        cpu = sum(quotas)
        if (
            not quotas
            or any(value <= 0 for value in quotas)
            or cpu + 100_000_000 > 3_000_000_000
        ):
            raise ValueError("isolation_api_cpu_reserve_unproven")
        config = json.loads(
            control.docker._run(
                [
                    "inspect",
                    "--format",
                    "{{json .Config}}",
                    api["id"],
                ]
            )
        )
        values = dict(item.split("=", 1) for item in config["Env"])
        workspace = control.workspace + "-" + control.output.name + "-isolation"
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,120}", workspace):
            raise ValueError("isolation_api_workspace_invalid")
        values["ADE_API_AGENT_RUNTIME_WORKSPACE_KEY"] = workspace
        if any(
            "\n" in key + value or "\r" in key + value for key, value in values.items()
        ):
            raise ValueError("isolation_api_environment_not_single_line")
        private_env = control.environment.with_name(
            control.environment.stem + "-" + control.output.name + "-api.env"
        )
        _private_text(
            private_env, "".join(f"{key}={value}\n" for key, value in values.items())
        )
        base = control.output / "secondary-api"
        base.mkdir(mode=0o700)
        product = control.root.parents[2] / "releases" / control.lease.source_revision
        seed = seed_runtime_assets(base, product / "content")
        observations = base / "product-observations"
        observations.mkdir(mode=0o700)
        runtime = base / "runtime-data"
        if any(
            row["name"].lstrip("/") == self.name
            for row in control.docker.owned(control.lease)
        ):
            raise ValueError("isolation_api_name_already_owned")
        command = [
            "create",
            "--name",
            self.name,
            "--restart",
            "no",
            "--cpus",
            "0.1",
            "--memory",
            "512m",
            "--user",
            config["User"],
            "--network",
            network,
            "--network-alias",
            "ade-isolation-api",
            "--env-file",
            str(private_env),
        ]
        labels = {
            OWNER_LABEL: control.lease.activation_id,
            PROJECT_LABEL: control.lease.project,
            SOURCE_LABEL: control.lease.source_revision,
            "com.docker.compose.service": "ade-isolation-api",
        }
        for key, value in labels.items():
            command.extend(["--label", key + "=" + value])
        for source, target, readonly in (
            (runtime, "/runtime", False),
            (runtime / "content", "/app/content", False),
            (observations, "/product-observations", True),
        ):
            command.extend(
                [
                    "--mount",
                    f"type=bind,src={source},dst={target}"
                    + (",readonly" if readonly else ""),
                ]
            )
        command.append(api["image"])
        self.identity = control.docker._run(command).strip()
        control.docker._run(["start", self.identity])
        receipt = {
            "container_id": self.identity,
            "image_id": api["image"],
            "workspace_key": workspace,
            "network": network,
            "cpu_limit": 0.1,
            "total_candidate_cpu_limit": (cpu + 100_000_000) / 1e9,
            "public_ports": [],
            "seed_sha256": seed["sha256"],
            "product_revision": control.lease.source_revision,
        }
        create_record(control.output / "secondary-api-start.json", receipt)
        return receipt

    def stop(self):
        if self.identity is not None:
            rows = [
                row
                for row in self.controls.docker.owned(self.controls.lease)
                if row["id"] == self.identity and row["name"].lstrip("/") == self.name
            ]
            if len(rows) != 1:
                raise ValueError("isolation_api_owned_identity_missing")
            if rows[0]["state"] in {"running", "paused", "restarting"}:
                self.controls.docker.stop(self.identity)
            return {"container_id": self.identity, "stopped": True}
        return {"not_started": True}
