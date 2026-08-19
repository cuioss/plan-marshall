# code-intelligence-substrate

Plans staged for standalone execution from the `code-intelligence-substrate` epic.

**Theme:** token reduction and the measurement substrate behind it. Context, not generation, carries
almost all of the billing weight, so this epic owns the levers that reduce what enters context and
the instrumentation that makes those reductions verifiable.

Execution contract: `Skill: cloud-plan-lane` (see [`../README.md`](../README.md)).

## The `5xx` fix plans

The plans numbered from `500` are derived from an audit of this epic's landed plans, not from the
orchestrator queue. Each carries a `## Gap coverage` section naming the gap ids it discharges, and
its sequencing against the others in its own Notes — where `540` before `550` is a **preference**
(`550` is order-independent by construction) and `560` last is the one that matters, since it
corrects descriptions of behaviour the other seven change.

[`_audit/summary.md`](_audit/summary.md) is the account of how they came to exist: what was checked,
what the audit found, and what the adversarial pass over the audit changed. That directory holds
records rather than a plan — it carries no `plan.md` and no `report-NN.md`.

⚠ **`_audit/` is the first `_`-prefixed directory inside an epic, and the collect step does not yet
know about it.** [`../cloud-bridge.md`](../cloud-bridge.md) § Path 3 step 1 says *every* directory
under an epic is a plan a run has worked. The bound, which is why this is safe rather than merely
undeclared: step 2 records nothing without a merged PR **and** a `report-NN.md`, and step 6 deletes
only what steps 2–5 corroborated — `_audit/` has neither, so a collector reaches an unhandled case
and stops rather than recording a false landing or deleting anything. Making that exclusion explicit
is a contract change, so it is raised as a proposal in
[`570-cloud-plan-lane-contract-proposals.md`](570-cloud-plan-lane-contract-proposals.md) rather than
asserted here.
