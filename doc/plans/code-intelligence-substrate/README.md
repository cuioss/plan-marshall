# code-intelligence-substrate

Plans staged for standalone execution from the `code-intelligence-substrate` epic.

**Theme:** token reduction and the measurement substrate behind it. Context, not generation, carries
almost all of the billing weight, so this epic owns the levers that reduce what enters context and
the instrumentation that makes those reductions verifiable.

Execution contract: `Skill: cloud-plan-lane` (see [`../README.md`](../README.md)).

## The `5xx` fix plans

The plans numbered from `500` are derived from an audit of this epic's landed plans, not from the
orchestrator queue. Each carries a `## Gap coverage` section naming the gap ids it discharges, and
the sequencing constraints between them are recorded in their own Notes — `540` before `550`, and
`560` last.

[`_audit/summary.md`](_audit/summary.md) is the account of how they came to exist: what was checked,
what the audit found, and what the adversarial pass over the audit changed. That directory is a
record, not a plan — it carries no `plan.md` and is not a collect target.
