> ⛔ **MERGED OUT 2026-09-18 (cleanup A5) — this spec is RETIRED and must not be launched.**
> Its substance now lives in **PLAN-TRUTH-169** as D5/D6: a timeout verdict describes the wait, not the work — both specs are a time-or-state signal naming the wrong subject, over one file family.
> The deliverables were carried, not summarised, and this spec's own gate collapsed into the
> receiving spec's D0 rather than being duplicated. This file stays on disk unchanged below the
> line — a superseded spec is never deleted. Its queue row is `parked`, because
> `queue --transition` cannot write `superseded` (see PLAN-TRUTH-143 D9).

# PLAN-TRUTH-158: A missing freshness-reconciliation record is reported as un-built source drift, though the contract has two other ways to produce that same absence

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-13 from a candidate-lesson filed by `plan-truth-127` at its own landing (PR #1483,
`inbox/plan-truth-127-004.md`). The plan itself hit the third of the three causes it names — a
finalize-internal commit moved the tree, no reconciliation record was emitted, and the push freshness
gate refused, attributing the refusal to un-built source drift, which was not what had happened.

## Objective

**`phase-6-finalize/standards/push.md` § "Finalize-internal re-stale reconciliation" attributes a
`stale` / `worktree_mutated` refusal to genuine un-built source drift purely from the ABSENCE of a
`freshness-reconcile` decision record naming the live HEAD — but that same contract can produce that
absence in at least three distinct ways, and the consumer cannot currently tell them apart:**

1. No finalize-internal commit happened (the intended meaning: genuine un-built source drift).
2. `SKILL.md` Step 3 item 5f(d) deliberately fail-closed — no `status: success` build entry existed, so
   the record was skipped ON PURPOSE, even though a finalize-internal commit did happen.
3. The record was owed (a finalize-internal commit happened, a successful build existed) and simply not
   emitted — item 5f(d) is an unenforced obligation with no guard between the commit and the push gate.

The halt itself is correct on every one of the three causes; the DEFECT is that the refusal message
names cause 1 specifically, when the consumer has observed only "no record names this HEAD" — an
ambiguous fact it is currently reporting as an unambiguous cause. `plan-truth-127` hit cause 3.

**Explicitly NOT the fix.** "The record is owed at the commit, not at the refusal" is already how
item 5f(d) is written (`"ONLY after a non-empty commit was made at (b)"`) — the producer-side contract
is correct. The gap is entirely on the CONSUMER side: what it concludes when the record is absent.

## Deliverables

Three deliverables.

**D0 — GATE: derive the population and separate corroborable from uncorroborable causes.** Confirm the
three-cause enumeration against `push.md`'s current text at HEAD, and confirm whether the dispatcher's
`phase_steps` records (specifically per-step `head_at_completion`) can independently establish whether
live HEAD is a finalize-internal `mutates_source` commit — the corroborator the source lesson proposes
for separating cause 1 from causes 2/3. Publish what is and is not corroborable before choosing a fix.

**D1 — Report the observation, not the inferred cause.** Change the refusal to report
`reconciliation_record_absent` (or equivalent) rather than asserting "genuine un-built source drift,"
and name the causes that absence admits, so the operator's next action is chosen against what was
actually observed rather than a guess dressed as a fact. Do NOT change the fail-closed halt behaviour —
it is correct on all three causes.

**D2 — Corroborate cause 1 where D0 found it cheap, and surface cause 2 distinctly.** Where the
dispatcher's own step records can independently establish whether HEAD is a finalize-internal commit,
use that to separate cause 1 from causes 2/3 rather than trusting the record's presence alone. Surface
cause 2 (the last build did not succeed) as a materially different operator action from cause 1/3 (you
edited source after the build) — today both arrive as the same sentence.

## Claim Labels

- OBSERVED: `push.md` § "Finalize-internal re-stale reconciliation" reads, on its negative branch: "No
  reconciliation record names the current HEAD: the `stale` is genuine un-built source drift. Fail
  closed per the table above — halt, record `outcome=failed`, do NOT push." (quoted verbatim by the
  source candidate-lesson; re-verify at outline against HEAD).
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: push.md line 98 still reads verbatim: 'No reconciliation record names the current HEAD: the stale is genuine un-built source drift. Fail closed...'
- OBSERVED: `SKILL.md` Step 3 item 5f(d) states the record is emitted "ONLY after a non-empty commit
  was made at (b)," and that when no `status: success` entry exists it fails closed by skipping
  emission entirely — the producer-side contract is as-designed, not the gap (re-verify at outline).
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: SKILL.md:1279 still reads 'When NO status: success entry exists, fail closed: skip emitting the reconciliation record entirely'. Substance corroborated; the precise step/item label 5f(d) was located by text search, not by independently counting SKILL.md's own step numbering
- OBSERVED: `plan-truth-127` hit cause 3 directly — a finalize-internal commit moved the tree, no
  reconciliation record existed, and the gate's refusal named un-built source drift, which was not
  what had happened (source candidate-lesson `plan-truth-127-004.md`, filed at this plan's own
  landing).
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Confirmed against plan-truth-127's own candidate-lesson (inbox/plan-truth-127-004.md, read and reconciled at this epic's PLAN-TRUTH-127 landing) -- the plan self-reports hitting exactly this shape
- ⚠ HYPOTHESIS: the dispatcher's `phase_steps` per-step `head_at_completion` records are sufficient to
  independently determine whether live HEAD equals a finalize-internal `mutates_source` commit, without
  trusting the reconciliation record's presence. ⛔ Reasoned by the source lesson from the dispatcher's
  known data shape, not verified against the actual field at this HEAD. D0 confirms or refutes
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: phase_steps head_at_completion sufficiency not checked against the actual dispatcher script at cleanup time; D0 owns it
- ⚠ HYPOTHESIS: item 5f(d) has no guard between the commit and the push gate today, so a skipped
  emission (cause 3) is indistinguishable at the consumer from cause 1. ⛔ An asserted absence — verify
  directly against the dispatcher's step-ordering code before relying on it (verify-at-outline).
  - verdict: unverifiable | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: The absence of a guard between the finalize-internal commit and the push gate was not independently traced through the dispatcher's step-ordering code at cleanup time

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` — the
  freshness-reconciliation refusal text and attribution logic (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — Step 3 item 5f(d),
  the record-emission obligation (D0, D2) (verify-at-outline)
- HYPOTHESIS: the phase-6-finalize dispatcher script(s) that implement the push freshness gate and that
  carry `phase_steps`' per-step `head_at_completion` (D0, D2) — exact file(s) owed by D0
  (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/**` — coverage for the three-cause discrimination and
  the new observation-vs-cause reporting shape (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` —
  the self-committing step with no `mutates_source` declaration (fourth cause, folded 2026-09-15 (c))

## Dependencies and Sequencing

- Depends on: none.
- Distinct from the could-not-look-discriminator candidate filed by the same plan
  (`plan-truth-127-003`, promoted as lesson `2026-09-13-20-004`): that one is a script publishing a
  discriminator inside its own payload; this one is a consumer inferring a positive cause from the
  absence of a record a DIFFERENT component was obliged to write. No payload exists to add a field to —
  the remedy is on the reading side, not the writing side.
- plan-truth-148 and plan-truth-157 were running when this plan was staged and were NOT re-scoped.
- ⛔ Shares `architecture-refresh.md` with `PLAN-TRUTH-166`, RUNNING when the 2026-09-15 (c) fold landed —
  do not launch until 166 lands, and re-read 166's change to that step before scoping the fourth cause.

## ⭐ FOLDED 2026-09-15 (c) — A FOURTH CAUSE: A STEP THAT COMMITS ITSELF WITHOUT DECLARING `mutates_source`

Forwarded from `lessons-handling-26-09-04-01-058.md` Observation 2 (Token-Sheriff PR #744, self-commit
`bfcbc925`). Expected Surface extended in the same act (`architecture-refresh.md`, above). Observation 1 of
the same message — the descriptor-migration churn itself — is `PLAN-TRUTH-166`'s subject and was recorded
there as recurrence evidence in the epic ledger, not folded here.

`default:architecture-refresh` (order 10) runs after the last verified build and commits its own
descriptor changes with a direct `git commit` inside the step. Re-grounded at `7a028157e`: its frontmatter
declares no `mutates_source` at all, while `push.md` line 73 defines finalize-internal re-stale membership
as `mutates_source: true` AND `order >=` `default:pre-push-quality-gate`'s (order 5). The step therefore
moves HEAD while sitting outside the membership the reconciliation contract reads, so no record is ever
OWED — not skipped (cause 2), not dropped (cause 3), but never in scope. push's gate refused with
`stale / worktree_mutated` and the operator forced it over a descriptor-only commit that is not a Maven
build input. ⛔ A `--force` habit this produces hides real staleness. D0 adds this fourth cause to its
enumeration; the remedy either declares the step `mutates_source: true` so its commit is reconciled, or
has the gate treat a commit touching only `.plan/project-architecture/**` as build-neutral — D0 decides,
after reading what 166 did to the step.

**Recurrence, same day, second consuming repo** (`api-sheriff-deployment-configurability-016.md` § `-009`,
API-Sheriff PR #305): the `architecture-refresh` self-commit wrote no reconciliation record and push's gate
reported stale, forcing a full multi-minute quality-gate re-run over a commit containing only generated
`.plan/project-architecture/*` metadata no Maven build reads. Two independent repositories now; surface
unchanged by this recurrence.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-158-a-missing-freshness-reconciliation-record-is-reported-as-un-built-source-drift.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
