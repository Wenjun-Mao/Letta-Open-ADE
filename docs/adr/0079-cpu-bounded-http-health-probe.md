# ADR 0079: CPU-Bounded HTTP Health Probe

Status: Accepted for the isolated workflow, 2026-10-19.

## Problem And Evidence

With the authored-asset repair, the actual API started successfully. Full-stack
startup still failed because fault-proxy's health command exceeded Docker's
three-second process timeout repeatedly. The handler was listening, and Docker
retained thirteen failed checks. The candidate closed safely without product
dialogue. This is an operational probe defect, not Memory/Character quality.

A separate finite, network-disabled diagnostic used the exact runner image,
0.1 CPU and 128 MiB RAM. Fresh Python subprocess imports took 2.893 seconds for
`urllib.request` versus 0.845 seconds for `socket`. The former spends almost the
entire process deadline importing an unnecessary TLS/client stack before HTTP.
Private source-bound logs retain the measurement and failed activation health.

## Decision

Use a small standard-library socket probe against the fixed loopback `/health`
route. It sends the same HTTP GET, reads a bounded status line and requires an
actual HTTP 200. Connection/read timeouts remain two seconds; Docker's overall
three-second health timeout and failure threshold are not relaxed. The server's
health handler still checks the lease and fresh source-bound supervision.

No inference, native readiness, lease, CPU reserve or product contract is bypassed.
Tests cover both supported HTTP versions, 503, invalid responses and a stalled
handler. The next fresh activation must demonstrate the actual CPU-bounded probe
and full startup; import measurements alone are not that proof. Retain all failed
activations and provider observations, with no six-slot or quality claim.

## Rejected Alternatives

Removing health checks, increasing resources at baseline services' expense,
relying on an open TCP port and inflating timeouts without identifying the cost
were rejected. A new client dependency is unnecessary for one loopback HTTP check.
