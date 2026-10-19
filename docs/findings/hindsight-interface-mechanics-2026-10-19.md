# Hindsight Interface Mechanics, 2026-10-19

Domain: Interface. Source: `ab0bd99f6c3d938bda9c925484d6c47c202f6826`.
Scope: [M4](../plans/hindsight-integration.md#m4-complete-agent-studio-and-public-inspection),
PC-02/03/04/07/09/12/14, [ADR 0074](../adr/0074-relationship-memory-inspection.md).

## What Was Exercised

The production-built web client, public product API, normal reply worker and
outbox used owned disposable PostgreSQL with the application role. Native Memory
and Character network boundaries were recording substitutes. Replies explicitly
identified themselves as controlled browser-test output. There was no live
provider inference or Hindsight semantic test.

At the clean source revision above, a headed Chromium run exercised Chinese
input, saved replies, queue updates, original-source inspection, native outage,
page reload and saved-input Retry. The paused input stayed visible with no
assistant apology. Conversation loading and ADE delivery state survived native
inspection failure; the UI explicitly said this was not an empty result.

Restoring the controlled boundary and retrying resumed the same run at attempt
two. Public readback contained two users and two assistants, not a duplicate user
or an extra reply. The same person/character in a fresh chat could inspect the
existing relationship; another character had separate empty delivery/Memory
inspection. Its old relationship results did not remain in view.

The mobile viewport and document both measured 390 pixels after the layout
repair. Desktop and mobile screenshots were inspected. All six retained console
errors after the outage reload were expected HTTP 503s on native Memory/operation
inspection; there were no `/runs/undefined` requests or unrelated console errors.
The earlier preload warning and failed exploratory attempts remain preserved.

## Repairs And Regression Evidence

Browser checking, not the old mocks, exposed the acceptance-receipt/Run mismatch
and mobile intrinsic-width overflow. The client now validates `run_id` and fetches
the actual Run; inspection values wrap locally rather than hiding page overflow.
Paused-input guards, ambiguous same-key retries, independent loading, A-to-B-to-A
responses, source selection races and separate delivery Retry have UI tests.

At this checkpoint, focused backend verification passed 182 checks, including
40 real application-role PostgreSQL cases. The full frontend passed 93 tests,
lint and production build. OpenAPI artifacts are current in English/Chinese.
The SQL/API checks reject mixed relationship IDs, foreign-workspace reads,
forged sources/operations, stale delivery Retry and reader-role mutation. Native
progress is sanitized again on public read, including retained unsafe snapshots.

Private generated evidence is retained under the integration workflow's ignored
`outputs/implementation-20261018/m4-browser-ab0bd99/`, with source-bound receipt,
public state/run/delivery readbacks, snapshots and screenshots. Earlier browser
attempts and the SQL timestamp-tie failure remain separate evidence. The two
loopback servers and dedicated browser were stopped; the disposable SQL fixture
remains for subsequent Stage-1 checks. Existing ADE/trial and OCI services were
not redeployed by this iteration. No GitHub Actions ran.

## Limits

This proves controlled Interface and product-persistence mechanics, not native
Memory extraction, correction, consolidation or semantic reliability. Model-call
telemetry in the fixture describes controlled ADE dispatch, not billed upstream
requests. There is no Character grounding/judgment/fidelity verdict or human
acceptance. It does not prove native restart, paired recovery or release readiness.

M5's complete actual-product capture and six live slots, M6's actual native-product
faults/paired recovery point/closeout, and maintained backend-test reconciliation
remain required. Frozen historical source mismatches were not rebound or waived.
