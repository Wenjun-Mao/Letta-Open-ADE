# Stop Policy

Stop and notify the coordinator immediately when:

- required product or release authority is absent;
- requested work would cross owned write paths;
- a shared resource is held by another owner;
- an irreversible or externally mutating action lacks authorization;
- scope or proof cost materially exceeds the approved bound;
- evidence disproves the planned contract.

Notification remains durable even when urgent: persist the signal and prepare
one identified direct-delivery attempt before calling Steer. A host call is
never authority by itself.

Do not stop merely because work is difficult or a noncritical test is stale.
Diagnose the owning layer, preserve evidence, and continue within authority.
Never weaken a guard, substitute unrelated behavior, clear user state, or
rewrite history solely to make a gate pass.
