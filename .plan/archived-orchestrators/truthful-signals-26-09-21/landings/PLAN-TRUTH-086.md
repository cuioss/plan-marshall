# Landing Analysis: PLAN-TRUTH-086 — manage-config seeding, effort presets, steward upgrade flow

epic: truthful-signals
workstream: WS-01
pr: #1351 — merged, `b4e8a2364`

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth — a pasted claim is a lead, never a fact.

## ⛔ This landing had NO `kind: landing` message

The plan filed **10 messages, all `candidate-lesson`**. `emit-landing` produced no landing envelope, so:

- there is **no `landing-facts` block** and `inbox landing-check` had nothing to run against;
- the PR number, merge state, deliverable counts and step outcomes came from the **operator paste and
  git**, not from a machine-readable fact;
- `landings_incomplete` is not the right field for this — the landing is **absent**, not incomplete,
  and the drain's own vocabulary has no term for it.

⚠ Both prior drains (`-094` #1343, `-087` #1340) emitted `complete: true` landings. This one did not.
Recorded as **D-086-a**.

## Identity reconciliation

| | Value |
|---|---|
| Queue slug | `manage-config-seeding-effort-presets-and-steward-upgrade-flow` |
| Live plan id | `config-seeding-effort-presets-steward-upgrade` |
| Row status before this drain | **`staged`** — never `launched`, never `running` |

⚠ The row went **`staged` → `shipped` in one step.** The orchestrator emitted the command
(`auto_emit: false`), the operator launched it without confirming back, so no `launched` transition
was ever recorded — correct under the emit≠running invariant, and it still leaves the ledger with no
record that the plan was ever in flight. Recorded as **D-086-b**.

## Corroboration

PR body carries no `Orchestrated plan — epic … spec PLAN-TRUTH-086` line, so identity was established
by surface overlap rather than by declaration:

| Measure | Value |
|---|---|
| declared Expected Surface | 36 paths |
| merged in `b4e8a2364` | 62 files |
| declared **and** merged | **29** |
| declared, never merged | 7 |
| merged, never declared | 33 |
| recall | **29/36 = 80.6%** |

29 of 36 is decisive for identity. ⇒ Third consecutive landing where the declared surface is wrong in
both directions (`-094` 3-of-6 unused, `-087` ~26 undeclared, `-086` 7 unused / 33 undeclared) — the
population `PLAN-TRUTH-113` D0 needs is now three plans deep and all three point the same way.

## Deliverables

10/10 per the paste. Not independently verified deliverable-by-deliverable — there is no landing
payload to check against, and the PR body enumerates changes rather than deliverables.

Two are reported to have **validated themselves in production during finalize**, which is worth
keeping: D10's staleness guard let `sync.py` run under bare `python3`, and D3's fail-closed reconcile
saw real counts, found the daemon busy, and **deferred instead of draining a live build** — the same
defer this epic recorded as `D-087-f` one landing earlier, now behaving correctly by design rather
than by accident.

## The self-reported orchestration failures

The plan reported **six interventions**, five of one kind and one worse. Recorded because the sixth
is this epic's own theme turned on the runner:

> *"I reported the merge as blocked on your approval — plausible, evidenced (two `enqueued: true`
> returns, 25 minutes of `pr_open`, queue rule confirmed active), and false. `ci pr auto-merge`
> merged it on the first attempt, and that verb was in a `--help` listing I had printed two tool
> calls earlier."*

⭐ **First-party corroboration from this orchestrator, independently and twice.** During the `-094`
and `-087` drains I hit the same wall and recorded it before seeing this message: `ci pr merge-queue`
returns `enqueued: true` whose `enqueue_corroboration` reads *"merge_queue rule active on branch"* —
a statement about the **branch rule**, never about **this PR's membership**. Two observers, two runs,
same false signal. ⇒ candidate-lesson `-002` says exactly this; it is not a lead, it is confirmed.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` → `#1351`
- [x] row `landing` → `landings/PLAN-TRUTH-086.md`
- [x] row `plan_marshall_plan_id` → `config-seeding-effort-presets-steward-upgrade`
- [x] 10 candidate-lessons dispositioned and archived
- [x] D-086-a / D-086-b recorded

## Follow-Ups

Routed, not re-derived: `-002` → merge-queue corroboration (confirmed, promote);
`-003` → `-097` (dispatch); `-004` + `-006` → `-098` (footprint, Arm 1 is the squash tier verbatim);
`-007` → `-101` (documented invocations); `-005` / `-009` → already tracked (R5 / R7);
`-008` → stale-cache reference contract; `-001` + `-010` → the stopping-short lessons.
