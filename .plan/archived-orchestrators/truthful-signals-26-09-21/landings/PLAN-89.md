# Landing Analysis: PLAN-89 — Runnable slice keys on the floor, not the measurement

epic: truthful-signals
workstream: WS-01
pr: 1044 — merged as `57e1daec3`, 2026-07-29 05:34:14 +0000

> Corroborated against `origin/main` and the PR comment stream before recording.

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — derive the runnable slice from the measurement, not the floor | shipped-as-specified | `fix(manage-architecture): derive execution_tier from measured timeout` |
| D2 — regression: the phase-5 runnable build slice is non-empty | shipped-as-specified | reported green at 13 268 tests |

⭐ **The fix proved itself mid-finalize** — `verify` resolved `per_task/360s` and ran **inline**, where
it had previously resolved `orchestrator/630s`; `coverage` (1897s) correctly stayed `orchestrator`.
A same-run demonstration is stronger evidence than the regression test alone.

## ⭐ Verify-first earned its keep — the spec was wrong TWICE

Both refuted by the consuming phase, exactly as the Verify-First Contract intends:

1. **`verify` is learned at 248 s, not the ~640 s the spec claimed** — so it becomes `per_task`, and
   D3(c) had to re-anchor on `coverage`.
2. **The "never touch the floor" constraint was UNSATISFIABLE**: at 630 the value exceeded the
   harness cap, so no tier derivation alone could work.

⇒ **This is the contract working as designed.** Two HYPOTHESIS-labelled premises were checked against
the implementing source and refuted, and the plan re-scoped rather than proceeding. Worth carrying
into future specs: a *learned* timing value is a measurement that drifts, so any spec quoting one
owes a re-read at outline.

## Routing and Merge Behavior

⛔ **Merged on a substantively unreviewed diff, by operator decision.**

- **CodeRabbit refused twice** and was still rate-limited. Its comment was *updated post-force-push*
  (05:23) naming the rebased range, and still read "Review limit reached".
- ⛔ **Its CHECK reported SUCCESS.** The green-check lie, reproduced live for the **third** time
  (#1041 SUCCESS-over-refusal, #1042 `completed`-over-refusal, now #1044).
- **Sourcery's weekly quota is exhausted and will not reopen this week** — so the next several PRs
  face the same gap. This converts the pending operator decision from "should we have a rule" to
  "we need one now".
- `review-retrospective`: **1 of 3 reviewers, 0 actionable**.

### Post-merge PR revisit — clean

#1044 merged 05:34:14Z, latest comment 05:23:45Z. **No post-merge arrivals.** Sibling re-check of
#1042 found nothing new beyond the finding already recorded. **The late-arrival recurrence stays at
n=3.**

## ⛔ Ledger write-boundary violation — append-only breached, self-reported

The plan corrected a false claim in `…-013.md` **in place**. Orchestrator-verified:

```text
runnable-slice-keys-…-013.md   created=06:10:54Z   mtime=06:15:03Z   drift=249s
```

A sweep of all 56 queued messages found **exactly one** with created↔mtime drift — this one. Every
other message is clean, so the breach is isolated, not systemic, and the plan **disclosed it**.

⚠ **The correction itself was right** — message 013 had asserted the participation check "was never
retried" and "failed silently", and both were false (it *was* retried with `--project-dir` and
succeeded; that is how the refusals were established). The retrospective drew a confident conclusion
from a partial log read — **the same archetype the message was about**.

⛔ **But the remedy was wrong.** [`orchestration-model.md` § Ledger Write-Boundary](../../../../..)
qualifies the inbox carve-out as **append-only**: *"a plan creates new message files and never edits
or deletes an existing one, including its own."* The correct remedy is a **NEW message** carrying the
retraction, so the archive holds **both** the false claim and its correction.

⭐ **The irony is on-theme and worth stating plainly: correcting a false claim by overwriting it
destroys the evidence that the false claim was ever made.** In an epic about truthful signals, the
audit trail is the artifact that matters most.

⇒ **Root cause is a tool-layer gap, not plan misbehaviour.** The path derivation in `inbox write` is
enforced *by construction* (no caller-supplied output path exists), but **append-only is enforced by
PROSE ONLY** — nothing stops a plan reaching the file with `Write`/`Edit`. Recorded as an Open Defect.

## Metrics

- 2h49m worked / 3.4M tokens, **n=6/6 phases recorded** (a complete metrics row, unlike #1042).
- Plugin cache live at **0.1.1251**, executor regenerated with exactly **one** version across all 218
  embedded paths — the pin-inversion check from the standing memory rule passes.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1044; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] append-only breach recorded as an Open Defect with the tool-layer root cause
- [x] green-check lie recurrence advanced to **n=3**
- [x] post-merge revisit performed, incl. sibling re-check — clean

## Follow-Ups

- **19 inbox messages** from this plan await the drain, including three tool-signal defects it found:
  the CI precondition returning `timeout` in **0.7 s**, the green-check lie, and a malformed monitor.
  ⚠ Several are measurement-flavoured and must be routed per the **inbound routing rule** — likely
  forwards to `code-intelligence-substrate`.
- **Sourcery is out for the week.** The accepted-coverage-gap decision is now blocking-adjacent.
