# WS-03: The build path records what it actually did

epic: tooling-truthfulness

## Charter

Own the paths where the build/executor machinery leaves evidence that misleads. The change ledger
recorded six failures and no success for a plan whose gate was green, because the `in_process` route
writes no entry — a reader querying it would reasonably conclude the plan shipped ungated. The
executor's self-heal walks the wrong plugin-cache depth, surfaced only because a run happened to
trip it.

⛔ Misleading evidence is worse than missing evidence: it defeats the check rather than merely
failing to answer it. That distinction is this workstream's whole subject.

The workstream closes when every gate route leaves a ledger record of what it ran, and the self-heal
resolves the depth it claims to.
