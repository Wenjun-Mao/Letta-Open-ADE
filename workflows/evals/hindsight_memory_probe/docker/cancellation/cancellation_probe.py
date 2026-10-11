"""Build-only dummy RUN: unique observable argv, no providers/models/private inputs."""

import os
import re
import sys
import time

if sys.argv[1] != "ADE_PROBE_BUILDKIT_SENTINEL" or not re.fullmatch(
    "[a-f0-9]{32}", sys.argv[2]
):
    raise SystemExit("invalid_owned_build_sentinel")
print(f"ADE_PROBE_BUILDKIT_SENTINEL token={sys.argv[2]} pid={os.getpid()}", flush=True)
time.sleep(300)
print("owned_build_sentinel_finished_without_cancellation", flush=True)
