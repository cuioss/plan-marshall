# Landing Analysis: PLAN-TRUTH-055 — the metrics record cannot represent a re-entered phase

epic: truthful-signals
workstream: WS-01
pr: #1129 — merged as `2586ef00c`

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| #1129 merged as `2586ef00c` | corroborated | `ci pr view` → `state: merged`; `git log origin/main` head |
| Plan archived, worktree removed | corroborated | absent from `manage-status list`; only `-074`'s worktree remains |
| **A live defect escaped into merged main** | **CORROBORATED first-party, and the mechanism is worse than the summary** | see below |

## Deliverable Fidelity vs Spec

All four shipped, and D3 absorbed `-053` as planned.

| Deliverable | Verdict |
|---|---|
| D1 record model — unmeasured columns, renamed verdict, `value_scope` | shipped-as-specified |
| D2 `manage-status` firing history — `firing_count` + `prior_firings` | shipped-as-specified |
| D3 denominators with mandatory sampling points (absorbed `-053`) | shipped-as-specified |
| D4 cross-cutting regression, each test verified RED pre-fix | shipped-as-specified |

### ⭐⭐ The record now represents itself, and that is the proof

Its own final `metrics.md` reports `re_entered_phases: [5-execute]` with `close_count: 2`,
`value_scope: mixed_cumulative_and_last_close`, and a `boundary_monotonicity` warning naming
`6-finalize`. **The loop-back this run actually took is visible in the record rather than flattened.**
`status.json` shows the self-review gate with `firing_count: 4` and `prior_firings: [failed, failed,
done]` — **pre-change that would have read as one clean pass.**

⇒ This retires the epic's standing *"every per-phase figure is RETIRED as evidence"* blocker **at the
mechanism level for future runs**. ⛔ It does **not** retroactively repair the existing corpus — see the
escaped defect, which is precisely why.

## ⛔⛔ THE ESCAPED DEFECT — confirmed first-party, and it is larger than "a floor is wrong"

The report states: *the unmeasured rescue is gated behind a `len(parts) >= 5` floor, so a nine-column
pre-change row still reads as a measured zero.* **Read against merged main, the mechanism is this:**

`analyze-logs.py:597` keeps `if len(parts) < 5: continue` — a floor, correctly widened from the old
strict `!= 5`. The per-column rescue at `:616-621` then marks a column **unmeasured** only when
`index >= len(parts)` (the column is *absent*) or the cell equals the explicit unmeasured token.

⇒ **A nine-column pre-change row has all four cells PRESENT and containing a literal `0`.** `int('0')`
succeeds, so the column is recorded as a **measured zero**. The rescue never fires, because nothing is
missing.

⭐⭐ **And this composes with a finding already folded into `PLAN-TRUTH-045` in the 2026-08-09 drain** —
`provider-…-003` (L3): *"the four per-dispatch context-load columns are declared, wired, and zero on
every row."* ⇒ **The entire pre-change corpus consists of exactly the rows this defect mis-reads.** The
blast-radius claim ("every such row in the archived corpus") is not an estimate; it follows from L3.

⛔ **The deeper shape, and it is this epic's subject exactly**: the fix taught the *reader* to say
*unmeasured*, but the *writer* had already committed `0` to disk. **A three-state vocabulary cannot
recover a distinction the two-state writer already destroyed.** A corpus migration or a
provenance-dated read is required; widening the floor cannot help.

Filed by the plan as epic inbox `-014` (error). **Staged here as `PLAN-TRUTH-077`.**

## Two findings worth the epic's attention

### ⭐⭐⭐ The vacuous-guard archetype recurred INSIDE the fix for it — twice — and this time with a matched negative control

The old guard **stayed green while the defect it names was injected and live.** ⇒ This is no longer an
inferred archetype: it is a guard demonstrated non-firing against its own stated subject, with a control.
**n≥9, and at least three of those instances were introduced by a fix for the class.**

⭐ The control is what makes it publishable. Every prior instance rested on *"the guard did not fire and
we believe the defect was present"*; this one **injected the defect and watched the guard stay green.**

### ⛔⛔ The required bot cannot be HEAD-bound BY CONSTRUCTION — this is the mechanism behind five consecutive plans

Across three review rounds: **`pr-agent` (required) produced one finding, which was rejected.
`coderabbit` (optional) produced all nine substantive ones — including catching this plan's own fix
regression.**

> **`pr-agent`'s `issue_comment`-only publish shape means the merge barrier can never HEAD-bind it.**

⇒ **This is not five unlucky runs — it is a structural property.** #1122, #1123, #1125, #1132, #1131 and
now #1129 all show the required bot satisfying quorum while producing nothing bindable, and the reason
is that its publish channel carries no HEAD association the barrier can check. ⭐ **A required bot that
cannot be bound to a HEAD is a quorum member that cannot be verified — the quorum is decorative for that
member.** ⇒ Routed to `review-apparatus`; this is the sixth consecutive observation and the first with a
named mechanism.

## Metrics

8h38m worked / **31h41m wall** / 7.5M dispatched tokens / **134.4M billing-weighted**. Both budget
anchors tripped `error` — ⚠ **on a figure the report itself labels a floor**, so the overrun is at least
that large and its true size is unstated. ⭐ Recorded as the honest form: an anchor tripped against a
lower bound tells you the direction, not the magnitude.

## Routing and Merge Behavior

Two deviations, **each recorded in the decision log by the plan** — both accepted:

- **Enqueued without the unconditional pre-merge rebase** (operator call; the merge queue re-tests
  anyway). ✅ Sound: the queue is the authority on mergeability.
- **Scoped `module-tests` substituted for whole-tree** after the build daemon's adaptive budget **timed
  out twice**. ⚠ **A timeout status, not a red test** — correctly distinguished. ⭐ This is the third
  independent report of the build-daemon adaptive-budget timeout (with `-070`'s `d0cd33`, where
  whole-tree `module-tests` at 642 s exceeded its learned timeout while the **superset** `verify`
  completed in 215–537 s). **The subset times out and the superset does not** — that is now n≥3 and
  still unowned.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = `1129`; `landing` = `landings/PLAN-TRUTH-055.md`;
      `plan_marshall_plan_id` = `metrics-record-cannot-represent-re-entered-phase`
- [x] `PLAN-TRUTH-077` staged for the escaped defect
- [x] the CIS obligation, the misrouted `-010`, and the required-bot mechanism recorded as Open Defects
- [ ] the plan's 14 inbox messages — left queued; `-074` is still at 6-finalize

## Follow-Ups

1. ⛔ **The CIS obligation is UNCONFIRMED, not discharged.** `inbox list` returns `count: 0` for
   `code-intelligence-substrate`, and **archived messages are not enumerated**, so that zero **cannot
   distinguish "emitted and drained" from "never emitted."** ⭐⭐ **This is the which-zero-is-this defect
   inside the tool this epic uses to prove its own drains** — and this orchestrator has been quoting
   `count: 0, inbox_state: present` as evidence of a clean drain all session. For *our own* epic that
   reading holds (we archived the messages ourselves and hold the receipts); **for a sibling's queue it
   does not.** ⇒ Two CIS plans wait on the `-055` vocabulary and the hand-off is **not** provably
   delivered. `inbox -013` carries the reconciliation steps. **Confirm against the archive, not the
   count.**
2. ⛔ **Inbox `-010` is misrouted BY CONSTRUCTION** — a `review-apparatus` finding that had to ride this
   epic's inbox because **a plan can only write its OWN epic's inbox** (`inbox write` derives the path
   from the plan's epic). ⇒ **There is no plan→sibling-epic channel**, so every cross-epic finding a plan
   produces must transit an orchestrator by hand. That is a structural gap, not a routing mistake by the
   plan — and it is the fourth time this drain-cycle that an orchestrator has had to relay one.
3. **The build-daemon adaptive-budget timeout** is now n≥3 and unowned.
