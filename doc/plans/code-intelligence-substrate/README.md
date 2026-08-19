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
records rather than a plan — it carries **no `plan.md`**, though it does carry a `report-NN.md`.

⛔ **`_audit/` is the first `_`-prefixed directory inside an epic, the collect step does not yet know
about it, and after this PR merges the safety argument no longer holds.**
[`../cloud-bridge.md`](../cloud-bridge.md) § Path 3 step 1 says *every* directory under an epic is a
plan a run has worked. Step 2 needs a merged PR **and** a `report-NN.md` before anything is recorded,
and step 6 deletes only what steps 2–5 corroborated — but `_audit/report-01.md` **exists and names
PR #1304**, so once that PR merges, both halves are satisfied and nothing in Path 3 stops a collector
from treating this directory as a landed plan and deleting it.

While #1304 is open the merged-PR half is unmet, so nothing can be recorded or deleted today. That is
a bound with an expiry, not a standing guarantee, and it is stated here rather than left for a reader
to derive. Closing it needs a guard in `cloud-bridge.md`, which is a change to the governing contract
this run may not self-approve, so it is raised as proposal **P8** in
[`570-cloud-plan-lane-contract-proposals.md`](570-cloud-plan-lane-contract-proposals.md).
⚠ **Until P8 is decided, do not run collect over this epic without checking `_audit/` by hand.**
