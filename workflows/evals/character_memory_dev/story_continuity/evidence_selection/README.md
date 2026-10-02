# Evidence Selection Investigation

The separately approved [bounded D04 behavioral comparison](behavioral/README.md)
has passed offline manager review under [ADR 0059](../../../../../docs/adr/0059-bounded-d04-behavioral-comparison.md).
Live outcomes remain unrun; the historical measurement below is unchanged.

Current status (2026-10-02): **Offline capacity/rubric diagnostic complete;
implementation and results independently manager-reviewed.** The approved
[offline protocol](OFFLINE_PROTOCOL.md) is frozen at
`62d461d4e2b6939fc8dff2fff9309c1f542f9189`. The [readout](READOUT.md) records
the eight complete packet pairs and source-grounded interpretation. D04's eight
sources fit both unchanged request budgets with full reply reserves. This neither
changes the runtime four-window ceiling nor qualifies generated answers.

The [selector protocol](PROTOCOL.md) remains an unimplemented proposal. The
[original external reports](reports/) and [source-checked assessment](REVIEW_ASSESSMENT.md)
are historical evidence; their then-current status is preserved. The
[continuity plan](../../../../../docs/plans/character-story-continuity.md#model-assisted-evidence-selection)
and [ADR 0058](../../../../../docs/adr/0058-offline-packet-capacity-and-qualifications.md)
own the delivery scope. PC-03/04/05/06/09/10/11 remain unchanged.

## Reproduction And Outputs

Run from the repository root with the existing locked workspace environment:

```sh
PYTHONPATH=. uv run --locked python services/ade-api/tests/agent_runtime/story_offline_capacity.py
uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_story_offline_capacity.py services/ade-api/tests/agent_runtime/test_story_correction_comparison.py services/ade-api/tests/agent_runtime/test_story_packet_comparison.py -q
```

[offline_inputs.py](offline_inputs.py) uses only the standard library. It pins the
protocol bytes and pre-measurement commit, verifies frozen historical inputs,
runtime sources and artifacts, and fixes exactly eight rows. Scope/input drift
fails rather than producing an empty fallback. The separate
[service-test entrypoint](../../../../../services/ade-api/tests/agent_runtime/story_offline_capacity.py)
owns runtime imports. It calls the existing history renderer/binder and request
serializers directly, preserving all included exchanges even on capacity failure.
It does not call admission for the eight-source packet or expose a runtime setting.
The seven ordinary controls must reproduce the historical builder byte-for-byte.

- [offline_capacity.json](offline_capacity.json): freeze/source hashes, unchanged
  capacities/reserves, included counts, source-order/integrity receipts, actual H
  hash, request hashes, headroom/overflow and counterfactual fit status.
- [offline_packets.jsonl](offline_packets.jsonl): eight rows, each retaining the
  complete generation request, ordinary synthetic-reply reviewer request and full
  16,384-character placeholder reviewer request. These are never dispatched.
- [READOUT.md](READOUT.md): capacity findings, exposed non-blind semantic rubric
  witnesses, recommendation and limitations. No aggregate semantic score.

The runner regenerates only these current-slice JSON outputs. Original correction
and packet-comparison artifacts, labels and execution sources remain byte-exact.
No database, external account, provider call, native continuation, new control,
selector/provider runner, deployment or runtime H/count change is authorized here.
