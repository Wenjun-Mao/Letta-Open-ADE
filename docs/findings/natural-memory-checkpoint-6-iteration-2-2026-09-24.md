# Natural-memory checkpoint 6: development iteration 2

Status: stopped after three of three targeted native mutation cells. This is a
separate 4,096-token reviewer-output diagnostic, not frozen A/B evidence.
Source revision `11f86b56230998083fc6be487818823f6d8be788`; source
fingerprint `7ef41ef3ecb3305b39ad6c7936622a66eb96aaf1293b653742c947744d7e16c7`.
The reviewer instruction and schema hashes were
`6d90f5cb9b4d7903d50e9ba4732907e34a122b4b583983f55c436940867f4a60`
and `4c7ff4f9813e6ff9f1ec70072e6a0c942b9fcec7125094406b58168bd22f4067`.
The input limit remained 6,759; the only planned request-envelope change was
`max_tokens: 4096` for the reviewer. The frozen cases/matrix hashes remained
`abd244c17c5f2e6fe90f9a32bc50e1bb262d233f0dad62db4f682d65b615dcc3`
and `188148ea73facc1e2fbecd795d2172e5cb659e489ff792b42dcc0db704a356d8`.

## Observations

The morning coffee and evening flower tea cells both passed exact native
readback. The first committed `早上喝咖啡` with current-user provenance. The
second retained the independent morning coffee assertion and committed
`晚上一般更喜欢花茶` as a separate active preference. The scoped tea reviewer
finished with `stop` at 2,613 completion tokens, resolving iteration 1's
1,024-token `length`/empty-content failure. Neither cell used a retry.

The correction cell's reviewer finished with `stop` at 604 completion tokens
and proposed `revise` of the exact Rocky `pet.name` fact at version 1, with
reason `correct` and value `Roxy`. It cited the current correction and an
older user message (`我家狗叫 Rocky。`) as `user_assertion` sources. The native
source binder requires each `user_assertion`/`user_endorsement` to bind the
current user message; replay of the captured decision produced
`RuntimeValidationError: Write authority must cite the current user`. The
candidate reply remained uncommitted, no revision was added, and readback
still showed active Rocky. The current user's exact correction and the supplied
target fact already support Roxy without the old citation. This is an
instruction/authority contract mismatch; accepting old user authority or
silently dropping the invalid citation would weaken provenance.

Three of the frozen schedule's 30 cells were probed; 27 remained unrun.
Six DeepSeek generation and seven Qwen embedding requests completed. There
were no hidden retries or reviewer repairs. The isolated router was stopped.

## Retained evidence

Mode-restricted artifacts are under
`data/runtime/natural-c6-iter2-01a0d420-output/`; DB
`ade_m2_memory_test_01a0d420`. Manifest SHA-256:
`be7a572afeec307bd6df5fa8f23c30a7446f18ba5cc01ebc1d1227a6a63c6747`.
Attempt SHA-256 values in cell order:
`63703ef021c9c9e3b9ad59def22d6bdcc90cc0ef5402cd674774f09a59f4cf1a`,
`be6859a61fb7c08574df1ce1875835bd16c8b66e578ee149687e5c92b3b01b26`,
`b5f7b710ba9d5cecfb3b444022e8cf4c6f1c83a7740efdc6fb029fe06ecc41e0`.
Correction reviewer raw capture SHA-256:
`f6ac346a9613c1a0d18e252e6bec3d457b980c041de951c96e299ab58954fed8`.
Ledger SHA-256:
`c1531adf927266e0a92c35e9a6715b7a25c0043ed6ce8ed70c7f2a8ce7e6b8b7`.
