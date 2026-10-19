# ADR 0082: Candidate Web Authoring Credential

Status: Accepted for the isolated Stage-1 workflow, 2026-10-19.

## Problem

The native browser check received 403 on prompt/persona template reads. The
candidate Compose file deliberately passed an operator key under the web server's
`ADE_API_ADMIN_KEY` name, but Prompt Center and immutable definition authoring
require the existing admin role. The earlier controlled browser fixture used its
admin key, so it did not exercise this deployment mismatch. Native safety/API
checks do not qualify the complete browser configuration (PC-04/08/12/14).

## Decision

Use the activation's generated admin authoring key only inside the loopback-bound
web server, matching its existing authoring responsibilities. Keep normal actor
and evaluator calls on their operator/reader credentials. Do not weaken API role
checks, put credentials into browser code or URLs, expose a public web port or
change global credentials. This is the trusted local authoring UI, not a new
multi-user authentication design.

For an already active candidate, an explicit finite controller may recreate only
its web service at the same inspected image, using the unchanged sealed private
environment and the corrected committed Compose binding. Record image source and
configuration-controller source/hash separately. No build, pull, API/worker/database
restart or sealed-source relabel is implied. Failure closes owned resources;
the actual browser journey must still be repeated. A source/config receipt is not
browser acceptance or production deployment.

## Guardrails

Compose and repair-controller tests reject operator-as-admin, wrong images,
foreign API targets and public ports. Preserve the first browser's 403 evidence.
The existing admin API requirements remain unchanged. A future externally exposed
or multi-user UI needs its own authorization design, not reuse of this local key.
