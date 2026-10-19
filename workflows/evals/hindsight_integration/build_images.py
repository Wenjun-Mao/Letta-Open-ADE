"""Serial, resource-capped builds from an immutable staged release; no inference."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from .operations import DockerOperations, Lease, check_lease, create_record, resources
from .startup import require_configuration


def build_images(root: Path, environment: Path, *, project_root: Path | None = None):
    lease = Lease.load(root)
    require_configuration(root, environment, lease)
    project_root = project_root or Path(__file__).resolve().parents[3]
    if project_root.name != lease.source_revision:
        raise ValueError("Build only an exact immutable staged release directory")
    values = {}
    for line in environment.read_text().splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in values:
            raise ValueError("Invalid sealed environment entry")
        values[key] = json.loads(value)
    if values["INTEGRATION_SOURCE_REVISION"] != lease.source_revision:
        raise ValueError("Build source differs from activation")
    recipes = [
        ("budget", "docker/build-budget.Dockerfile", None, project_root),
        ("runner", "docker/python.Dockerfile", "runner", project_root),
        ("router", "docker/python.Dockerfile", "router", project_root),
        ("api", "docker/python.Dockerfile", "api", project_root),
        ("web", None, None, project_root / "apps/ade-web"),
    ]
    built = []
    for role, recipe, target, context in recipes:
        require_configuration(root, environment, lease)
        issues = check_lease(
            lease,
            docker=DockerOperations(),
            capacity=resources(lease.disk_path),
            closed=(root / "closed.json").exists(),
        )
        if issues or time.time() + 1230 >= lease.dispatch_deadline:
            raise ValueError("Build does not fit the healthy activation window")
        image = f"ade-hindsight-integration-{role}:{lease.source_revision}"
        dockerfile = (
            project_root / "workflows/evals/hindsight_integration" / recipe
            if recipe
            else context / "Dockerfile"
        )
        command = [
            "timeout",
            "--signal=TERM",
            "--kill-after=30s",
            "1200s",
            "docker",
            "build",
            "--force-rm",
            *(["--no-cache"] if role == "budget" else []),
            "--cpu-period",
            "100000",
            "--cpu-quota",
            "300000",
            "--cpuset-cpus",
            "0-2",
            "--memory",
            "3g",
            "--memory-swap",
            "3g",
            "--platform",
            "linux/arm64",
            "--label",
            f"io.ade.integration.activation={lease.activation_id}",
            "--label",
            f"io.ade.integration.source={lease.source_revision}",
            "--build-arg",
            f"ADE_SOURCE_REVISION={lease.source_revision}",
            "--build-arg",
            f"ADE_SOURCE_FINGERPRINT={values['INTEGRATION_SOURCE_FINGERPRINT']}",
            "--build-arg",
            "NEXT_PUBLIC_ADE_WEB_VERSION=hindsight-stage1",
            "--build-arg",
            f"NEXT_PUBLIC_ADE_WEB_BUILD={lease.source_revision}",
            "-f",
            str(dockerfile),
            "-t",
            image,
            *(["--target", target] if target else []),
            str(context),
        ]
        record_root = root / "builds"
        record_root.mkdir(mode=0o700, exist_ok=True)
        descriptor = os.open(
            record_root / f"{role}.log", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
        )
        with os.fdopen(descriptor, "wb") as log:
            try:
                result = subprocess.run(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=1240,
                    env={**os.environ, "DOCKER_BUILDKIT": "0"},
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                create_record(
                    record_root / f"{role}.failure.json",
                    {
                        "error_type": type(exc).__name__,
                        "source_revision": lease.source_revision,
                        "activation_id": lease.activation_id,
                    },
                )
                raise
        create_record(
            record_root / f"{role}.result.json",
            {
                "source_revision": lease.source_revision,
                "activation_id": lease.activation_id,
                "command": command,
                "returncode": result.returncode,
                "cpu_limit": 3,
                "reserved_cpu": 3,
                "memory_limit_bytes": 3 * 1024**3,
            },
        )
        if result.returncode:
            raise RuntimeError(f"candidate_{role}_build_failed")
        image_id = subprocess.check_output(
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"], text=True
        ).strip()
        built.append({"role": role, "image": image, "image_id": image_id})
        print(f"Built candidate {role}: {image_id}", flush=True)
    create_record(
        root / "images.json",
        {
            "source_revision": lease.source_revision,
            "source_fingerprint": values["INTEGRATION_SOURCE_FINGERPRINT"],
            "activation_id": lease.activation_id,
            "images": built,
        },
    )
    return built


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    args = parser.parse_args()
    build_images(args.root, args.environment)


if __name__ == "__main__":
    main()
