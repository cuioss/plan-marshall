# Landing Analysis: PLAN-TRUTH-102 — A dual-homed hook install renders identically to a healthy one

epic: truthful-signals
workstream: WS-01
pr: #1384 (merged via merge queue as `19453cb1b`)

> Written by `analyze` after corroborating against ground truth. Source: operator paste, cross-checked
> against `ci pr view --pr-number 1384`, `git log origin/main`, the archived plan directory, and the
> plan's own `landing` message `-015`.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| Merged as #1384 | **corroborated** | `ci pr view` → `state: merged` |
| Landing commit `19453cb1b` | **corroborated, three ways** | PR's `merge_commit_sha`, `git log origin/main`, and the facts block's `landing_commit` all agree |
| Merged via the queue | **corroborated** | facts `merge_mechanism=merge_queue` |
| 2/2 deliverables | **corroborated** | facts `deliverables_total=2` / `deliverables_done=2` |
| 4.2M tokens / 4h22m worked | **corroborated** | facts `total_tokens=4171248`, `total_worked_seconds=15745` |
| Plan archived, worktree removed | **corroborated** | `archived-plans/2026-09-03-dual-homed-hook-install-renders-identically` exists; plan absent from `manage-status list` |
| "23/23 finalize steps done" | ⚠ **corroborated with a caveat** | see § The 23/23 caveat |

⭐ **No `merge_commit_sha` mis-stamp.** The R148 hazard (a landing stamped with another plan's commit,
n=2 across two epics, and reachable only at N>1) was checked explicitly: all three independent sources
name the same sha. **N>1 was live during this run, so the check was not redundant.**

## ⭐⭐ The landing message is COMPLETE — the #1349 regression did not recur

`inbox landing-check` → **`complete: true`, `missing_keys[0]`**. Every required fact key is supplied,
plus the optional `total_wall_seconds`, `total_billing_weighted`, `merge_mechanism` and
`landing_commit`.

⇒ **This closes a live watch.** PLAN-PR-024's landing (#1349) returned `complete: false` with **all 8
required keys missing** — a prose-only landing, recorded there as a *regression* against PLAN-PR-034's
complete one. **The emitter is working again**, and this is the first post-#1349 evidence of it. ⚠ Two
data points either side of a gap is not a fixed defect: record the recovery, keep the watch.

### ⚠ The 23/23 caveat — a disagreement by construction, not a defect

The operator report says **23/23 done**; the facts block says `archive-plan:pending`. Both are correct:
`emit-landing` runs *before* `archive-plan`, so **a landing's `steps` list can never report its own
archive step as done.** ⇒ A consumer reading `steps` for completeness will always see exactly one
pending entry on a healthy run. ⛔ Do not "fix" this by re-emitting after archive — the landing must be
written before the plan directory moves. **Record it so no future drain reads that one pending step as
an incomplete finalize.**

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|---|---|---|
| 1. Detect the dual-homed install, render as a named non-fatal state | shipped-as-specified | `_dual_homed_labels` added without touching `_merge_display_settings` |
| 2. Correct the shipped documentation for the widened value domain | shipped-as-specified | divergence renders as a third per-label token that never sets `healthy = False` |

⭐ **The implementation avoided the trap the spec was written around.** `_merge_display_settings` is also
consumed by `_terminal_title_active()`, so widening it would have changed an unrelated consumer's
behaviour. The plan added a sibling detector instead. ⭐ And D4's deliberate non-claim — *whether Claude
Code executes both byte-identical entries* — is recorded in `contract.md` rather than guessed, which is
this epic's own discipline applied by the plan to itself.

## Metrics and Anomalies

- **4,171,248 tokens / 113,009,997 billing-weighted** ⇒ **27.1×**, inside the normal 12-28× band. No
  billing anomaly.
- **Wall 19h25m vs worked 4h22m ⇒ 15h02m idle (77.5%).** ⚠ **Recorded as a FIGURE, not a diagnosis.**
  PLAN-TRUTH-107's idle figures (81% on `-075`, 62% on `-095`) were attributed to stop-and-wait only
  after a transcript-level momentum/direction classification. **This number has had no such analysis**,
  and CI, merge-queue and review-bot windows are legitimate idle. ⛔ Do not add it to `-107`'s evidence
  as a third stop-derived figure; it is a third *unexplained* one, which is what `-107` D0(b)'s standing
  corpus sweep exists to resolve.
- 77 builds executed; `build_time` will report **all-zero** — see Open Defects below.

## Routing and Merge Behavior

- **`automatic-review`: 3 bots, 9 findings, quorum satisfied.** `review-retrospective` measured **2 of
  3** reviewers. ⚠ The one-reviewer gap between "3 bots participated" and "2 measured" is the
  participation-vs-coverage distinction `review-apparatus/PLAN-PR-045` was forwarded for. Not analysed
  here; the sibling epic owns it.
- **`pre-submission-self-review`: 13 defects fixed over 10 rounds** — none reached the PR. See the
  Follow-Ups section: the plan itself flagged the cost shape as a finding.
- CI green at `31fb2730`; merged through the queue; branch cleaned; **main clean at `19453cb1b`**.
- ⚠ Main has since advanced past this landing — `6884e9329` (#1385) and `9fd095718` (#1387) are also on
  `origin/main`. **Neither is a truthful-signals plan**, so no queue row is owed for them here.

## Reconciliation Actions

- [x] row `status` → `shipped` — `queue --transition PLAN-TRUTH-102 --status shipped`
- [x] row `pr` stamped `#1384`
- [x] row `landing` stamped `landings/PLAN-TRUTH-102.md`
- [x] row `plan_marshall_plan_id` already stamped at launch
- [x] epic.md regenerated from status.json (`compact`)
- [x] Open Defect opened for the destroyed-oracle zero (below)
- [x] resume_anchor updated

## Follow-Ups — three the plan asked to be weighed, adjudicated

**1. ⛔⛔ `build_time` reports all-zero over 77 builds — and the zero is byte-identical to a build-free
run.** `branch-cleanup` destroys the worktree-resident ledger oracle *before* the reporting steps read
it. ⭐⭐⭐ **This is the SAME ROOT CAUSE as `PLAN-TRUTH-127` arm (2)**, which records that
`transition --completed` is unreachable post-finalize *because `branch-cleanup` removed the worktree*.
⇒ **One cause, two consequences: a repair path closed, and a measurement destroyed.** Recorded as an
Open Defect and cross-referenced on `-127`; the plan routed it as its own candidate `-009`, which the
drain will reconcile. **Do not treat the two as separate root causes.**

**2. The self-review cost 50.6% of the plan for 13 defects, and rounds 6-10 cost more than 1-5 for
fewer.** The plan's own diagnosis: *"I kept fixing the instance a finding named rather than the class"*
(~572K tokens avoidable), and it **closed the step without a confirming clean round, at a point where
the residue-hit rate was 5-of-5**. ⭐ Both halves belong to `PLAN-TRUTH-108` (*the self-review decides
its own close and its distinguishing property is invisible*) — the second half especially: **a step that
closes itself while still finding defects at a 100% hit rate is deciding its own close on no stopping
criterion.** Recorded as evidence on this landing; ⛔ NOT folded into `-108` unprompted.

**3. A `marshalld` timeout abandons the WAIT but not the BUILD.** Three pytest suites ran concurrently
before a process-table scan reaped them, and **one `timeout` verdict was outright FALSE — the abandoned
build had passed, 62 seconds after the budget elapsed.** ⇒ A timeout verdict is a statement about the
*waiter*, not the *build*, and the two are reported as one. ⭐ The plan corrected the lesson it had
contaminated (`2026-09-02-20-001`) **in place** rather than leaving a wrong premise in the corpus —
correct handling, recorded. Unowned; see Open Defects.

⚠ **A fourth item rode the paste and is NOT this plan's** — a suggested directive about giving
`inbox list` a subject column, from a leaf executing a dedup obligation. Read as an inbox-surface
observation, not a landing claim; it is the drain's to disposition, not this record's.
