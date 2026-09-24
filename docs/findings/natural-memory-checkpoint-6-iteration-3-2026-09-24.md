# Natural-memory checkpoint 6: development iteration 3

Status: stopped at the first of three targeted native mutation cells. This was
the third and final authorized repair/live-test iteration, separately versioned
from the immutable original campaign and not frozen A/B evidence. Source
revision `a0ce57265cd990bbe2da654b37132c3dc129c5f6`; source fingerprint
`b2a6a8c5f9e27923806bb504dbb84ebe275478a249a0c08d4b3add93dc573ccf`.
The reviewer instruction hash was
`072d0fa006199fe5b9d770952c2a5939d0ce11a5e01e5cfd136bbd31e862c0fe`;
schema hash remained
`4c7ff4f9813e6ff9f1ec70072e6a0c942b9fcec7125094406b58168bd22f4067`.
The separate output diagnostic kept reviewer input limit 6,759 and
`max_tokens: 4096`, with the same pinned DeepSeek/Qwen routes, high thinking,
and no repair or retry.

## Measured result and diagnosis

The first cell again used `我早上喜欢喝咖啡。`. Conversation and reviewer calls
both completed. The reviewer returned a complete JSON proposal with
`finish_reason=stop`, 354 completion tokens, `person.preference`, drink,
`早上喝咖啡`, and current-user evidence. It also selected the subject UUID
in `entity_ref`. Replaying the exact proposal against the typed parser
reproduced `RuntimeValidationError: subject-kind add cannot select an entity`.
The run was atomically rejected: no fact, revision, or assistant reply was
committed; memory generation remained 1. The other two diagnostic cells and
29 of the frozen schedule's 30 cells were unrun. The ledger recorded two
DeepSeek generation and one Qwen embedding requests, all completed once.
There was no privacy, isolation, or atomicity breach.

This is a recurrence of the original campaign's subject-binding failure,
although iteration 2 successfully committed the same cell with the same
subject rule. The iteration-3 instruction change concerned source authority;
it did not remove the explicit subject-binding rule. The observation is
therefore evidence that prose plus a typed rejection does not reliably elicit
valid proposals on this route, not evidence that the authority clarification
caused this particular field choice. The strict parser prevented an invalid
write. No fourth repair or provider run is planned. See the prepared
[consultation packet](natural-memory-consultation/checkpoint-6-live-diagnostic-brief.md)
for the decision questions.

## Retained evidence

Mode-restricted artifacts are under
`data/runtime/natural-c6-iter3-01a0d421-output/`; DB
`ade_m2_memory_test_01a0d421`. Manifest SHA-256:
`07f700db5597b6b829cfd29c3565f0d9f85d8d535115255f15a9759a57909355`.
Attempt SHA-256:
`4731ab4c1d7ea4bef76c12873fe62b38c4217d3569e2f6915efbd3f685f636fc`.
Reviewer raw capture SHA-256:
`3f4c47ad8597fab792dca819bcd71ba854d01595da4b3a523a39fa72bd37978c`.
Ledger SHA-256:
`76d6fce68a4d4823619d38e0705c63615077b7cfe0206af81f8c711662044b17`.
The isolated router was stopped after the attempt.
