# Natural-memory checkpoint 6: development iteration 1

Status: stopped after two of three targeted native mutation cells. This is a
separate diagnostic from the immutable first campaign and is not A/B evidence.
Source revision `59478b4b5dc1857ce693f23b197ac80fc05abc13`; source
fingerprint `89ad1fc86f7f7c71b76306cb31d77e9c1ab89cd93ef136788118dd7a8523de95`.
The reviewer instruction and schema hashes were
`6d90f5cb9b4d7903d50e9ba4732907e34a122b4b583983f55c436940867f4a60`
and `4c7ff4f9813e6ff9f1ec70072e6a0c942b9fcec7125094406b58168bd22f4067`.

## Observations

`mutation-preference-add::native` committed one `person.preference` with value
`早上喝咖啡`, implicit subject binding, a current-user evidence span, one assistant
message, and one new revision. This is visible improvement over the initial
campaign's atomic rejection of the same source turn.

`mutation-scoped-addition::native` reached the reviewer with the same frozen
1,024-token output reserve, `thinking.enabled`, and `reasoning_effort=high`.
The response had `finish_reason=length`, `completion_tokens=1024`, and empty
visible content. No decision parsed; the run was atomically rejected with no
assistant message or revision. The retained raw capture redacts private
reasoning. The correction probe and all remaining frozen cells were unrun.
The iteration used four DeepSeek requests and four Qwen embedding requests,
each completed once. There was no retry, repair, or reroll.

The request's visible reviewer input estimate was 3,030, below the frozen
6,759 limit. [DeepSeek's Chat Completions documentation](https://api-docs.deepseek.com/api/create-chat-completion/)
states that `max_tokens` limits generated completion and `length` marks a token
or context limit; [thinking-mode documentation](https://api-docs.deepseek.com/guides/thinking_mode/)
states that reasoning precedes visible content. The captured empty content,
exact 1,024 completion use, and finish reason support an output-envelope
diagnosis, while the private reasoning token count remains unavailable.

## Retained evidence

Mode-restricted artifacts remain under
`data/runtime/natural-c6-iter1-01a0d41f-output/`. The manifest SHA-256 is
`1ee5927c7efa54dba3ab7fa057627aef2fc2de1e4076ba4b0e2bcc44d6dbe03c`;
the first and second attempt SHA-256 values are
`4c216d34fd14f3b65efc7cfd79880101ed0eb5adc0c783e0f4138b4b93795d5d`
and `327b77c6f09684716a2234e521040c6ca3f23fadef45244e7c7488a94f9a4b17`.
The ledger SHA-256 is
`7b54cc30f46f04db1baf4f20156ab047d3f2f4906eb6036a5e27a44872363212`.
The scoped router was stopped after the diagnostic.
