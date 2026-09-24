# Revision-5 offline reviewer contract cases

Status: frozen before implementation, 2026-09-24. These are complete allowed
memory deltas for mechanical fixtures; semantic equivalents require explicit
review. `∅` means no fact, entity, embedding, revision or generation change.
Every row keeps unrelated facts, identities and scopes unchanged. A rejected
attempt commits no assistant reply or memory mutation.

| Exchange / starting state | Permitted complete delta | Forbidden extra change |
| --- | --- | --- |
| Current `I prefer coffee in the morning`; no prior fact | Add one subject `person.preference` scoped to morning coffee | Broad all-day coffee, entity selection |
| Earlier user `One of my dogs is a Husky`; assistant `Rocky or Roxy?`; current `Roxy` | Add one Roxy breed assertion, with current resolution anchor and earlier-user antecedent | Breed from assistant alone, Rocky mutation |
| Assistant alone `Is Roxy a Husky?`; current `Roxy` | ∅, defer unresolved | Any breed write under direct, resolve-user or endorse-assistant mode |
| One assistant proposition `Is Roxy a Husky?`; current `Yes` | Add one Roxy breed with current endorsement and assistant referent | Any other inferred pet property |
| Two assistant propositions; current `Yes` | ∅, defer ambiguous assent | Either proposition chosen arbitrarily |
| Earlier user `One dog might be a Husky`; assistant asks which; current `Roxy` | ∅, retain uncertainty | Definite breed |
| Earlier user `Don't save that Husky claim`; assistant asks which; current `Roxy` | ∅, retain no-save | Breed write |
| Earlier user withdraws Husky claim; assistant asks which; current `Roxy` | ∅, retain withdrawal | Breed write |
| Current self-contained `Yes, Roxy is a Husky` | One Roxy breed add when identity is established | Bare-yes ambiguity applied to explicit assertion |
| Earlier user `Remove one drink preference`; assistant `Coffee or tea?`; current `The morning-coffee one`; morning coffee and evening tea exist | Forget morning coffee only | Forget tea, merely end coffee, recreate coffee |
| Assistant `Shall I remove saved morning coffee?`; current `Yes, please` | Forget morning coffee only | End it or remove other preference |
| Assistant `Is morning coffee no longer your preference?`; current `Yes` | End morning coffee only | Forget its history |
| Current `The morning-coffee one` with no removal request; same state | ∅, defer | End or forget coffee |
| Current `I prefer coffee in the morning. Don't save that. I now live in Toronto` | Add Toronto residence only | Coffee write; broad no-save veto of Toronto |
| Current `早上我喜欢咖啡，别保存这个。我现在住多伦多。` | Add Toronto residence only | Coffee write |
| Same no-save text with both coffee and Toronto writes proposed | Reject entire attempt | Silently drop coffee to rescue Toronto |
| Existing morning coffee; current `I prefer tea in the evening` | Add independent evening tea only | Replace or end morning coffee |
| Existing morning coffee v1; current `Actually, morning tea instead` | Revise coffee target to morning tea v2 | New all-day tea; modify evening scope |
| Current `What is my dog's name?`; existing active `pet.name=Roxy`; candidate `Rocky` | Grounded conflict, reject with zero writes | Fabricated user assertion of Roxy |
| Same query; candidate `Roxy. What else is new?` | ∅; reply allowed | False conflict over unrelated question |
| `{}` / absent decisions / null / truncated JSON | Reject entire attempt | Interpret as no-change |
| `{"decisions":[]}` | ∅; checked candidate allowed | Generation advance |
| Target handle from other subject or stale version | Reject entire attempt | Remap to matching current fact |
| Permuted source ordering with current resolution and earlier antecedent | Same bound anchor and provenance | Authority chosen by list position |

All successful rows require zero unlisted revisions, entities and mutation
embeddings. Read-only query embeddings, when retrieval requests them, are reported
separately. These fixtures demonstrate bindings and deltas, not universal language
entailment or live reviewer reliability.
