# PLAN-119: The pre-merge review barrier deadlocks when a required bot refuses, and the fix for the last defect removed the only escape

epic: truthful-signals
workstream: WS-01

## Objective

The Pre-Merge Review-Completeness Barrier is fail-closed on required-bot participation. When a
required bot is **refusing for reasons outside the repo's control** (rate limit, quota), the barrier
can never pass, `fail_into_loopback` loops the plan back, the loop-back produces no new commit,
the bot refuses again — and the plan cannot merge at all. There is no sanctioned way to record
"this bot is degraded, proceed with a documented gap."

## The defect, and why it is on-theme

`branch-cleanup.md:579-581` states the barrier's design plainly, and the design is **correct**:

- Predicate 1 (unhandled comments) cannot see an **absence** — a bot that never reviewed publishes
  nothing and reads as clean.
- Predicate 2 re-derives participation from the provider, **deliberately not trusting** the
  `automatic-review` step record, because the force-done escape hatch produces a record
  *byte-identical* to an earned pass.

⭐ **The previous fix closed a false-green hole and opened a permanent-red one.** Making force-done
non-authorizing was right — it stopped a forced record buying a merge. But force-done was **the only
escape**, and nothing replaced it. The barrier now asks a question that an external service's
availability answers, and offers the operator no way to answer it.

⛔ **This is the epic's recurring archetype: a fix for a defect that reproduces the defect's family.**
Recurrence n≥6.

## Live evidence (orchestrator-verified 2026-07-29)

On PR #1057, `ci pr comments --pr-number 1057` returned:

- `sourcery-ai` — *"you have reached your weekly rate limit of 500000 diff characters"*
- `coderabbitai` — *"you've reached your PR review limit, so we couldn't start this review"*
- `cuioss-review-bot` (pr-agent) — an informational Guide, zero actionable content

⚠ **Both refusals were stated ONLY in the comment bodies. The check states showed nothing.** A
detector reading check state concludes "no problem"; a detector reading participation concludes
"unproven"; neither concludes "the service refused, and that is a different thing."

## Deliverables

1. **D1 — GATE (mutates nothing): DERIVE the barrier's terminal-state population.** Enumerate every
   state in which the barrier can end, and classify each as *passable by the plan's own action* or
   *not*. ⛔ A state a plan cannot exit by acting is a **deadlock**, and deadlocks are the finding.
   Include at minimum: bot refused (rate limit / quota), bot absent entirely, bot posted a canned
   no-op, bot posted a substantive review. **The rate-limit case is a SAMPLE — derive the rest.**
2. **D2 — distinguish "unproven" from "refused".** A required bot that **published a refusal** is a
   materially different state from one that was silent, and the two demand opposite operator
   responses. ⚠ **The refusal is only visible in the comment BODY** — a detector reading check state
   or row count cannot see it. This is the same wrong-observable family as PLAN-116; **coordinate,
   do not duplicate the detector.**
3. **D3 — a sanctioned, recorded coverage-gap acceptance AT THE BARRIER.** The operator must be able
   to authorize a merge with a known review gap, and the authorization must be:
   - **explicit** — an operator decision, never a leaf's own judgement (this is exactly what made
     force-done wrong);
   - **recorded** — the audit trail states *merged with a known gap, which bot, why, authorized by
     the operator*, so it is never mistaken for an earned pass;
   - **distinguishable** — the resulting record MUST NOT be byte-identical to an earned pass. ⛔ That
     byte-identity is the precise defect the previous fix was written to remove; **do not reintroduce
     it in a new location.**
4. **D4 — the barrier's failure message must name the exit.** A `fail_into_loopback` that a
   loop-back cannot fix is a misleading instruction: it tells the operator to do something that
   cannot work. When the barrier detects a not-passable-by-action state, it must say so and name the
   available exits, rather than looping.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) A required bot publishing a rate-limit refusal
   is classified `refused`, not `unproven`. (b) A loop-back that produces no new commit does not
   re-enter the same barrier expecting a different answer. (c) An operator-authorized coverage-gap
   merge produces a record **distinguishable** from an earned pass. (d) The terminal-state population
   is derived, non-empty, and contains every known member.

## Claim Labels

- OBSERVED (orchestrator-verified 2026-07-29): the three #1057 comment bodies and their content; that
  both refusals appear only in bodies; `pre_merge_comment_barrier` default `fail_into_loopback`;
  `barrier_mode` valid values `fail_into_loopback` / `ask`; the `branch-cleanup.md:579-581` design
  rationale.
- OBSERVED (operator paste): with `fail_into_loopback`, a force-done of `automatic-review` does not
  buy the merge — the barrier re-checks, still finds the bot unproven, and loops back.
- HYPOTHESIS: the loop-back is non-terminating when no new commit is produced — **confirm/refute at
  D1**. **Confirm/refute artifact**: the loop-back re-entry condition in
  `phase-6-finalize/SKILL.md` and the barrier's re-check in `branch-cleanup.md`.
- HYPOTHESIS: `ask` mode already provides a partial exit — **confirm/refute at D1 before designing
  D3**, since an existing partial exit changes D3's shape. ⛔ **Do not assume `ask` is absent.**
- ⚠ Line numbers OBSERVED at 2026-07-29 HEAD on a hot surface. **Re-ground by SYMBOL / heading.**

## Expected Surface

- OBSERVED: `phase-6-finalize/standards/branch-cleanup.md` (the barrier section and its two predicates)
- OBSERVED: `automatic-review/standards/bot-participation-contract.md`
- HYPOTHESIS: `automatic-review/SKILL.md` § "Force-done with an explicit recorded reason"
  (verify-at-outline)
- HYPOTHESIS: the loop-back re-entry path in `phase-6-finalize/SKILL.md` (verify-at-outline)
- OBSERVED: the corresponding finalize tests

## Dependencies and Sequencing

- Depends on: none.
- ⛔ Overlaps with **PLAN-116** (review detectors / participation observables — D2 is adjacent to its
  Defects C and D) and **PLAN-117** (same `branch-cleanup.md` merge path). **Sequence, never pair
  with either.** ⚠ **PLAN-112** and **PLAN-113** are also on `phase-6-finalize`.
- ⭐ **Resolves an operator-owed decision**: the standing "accepted-coverage-gap" question is exactly
  D3. Staging this plan does not decide it — **D3's design still needs the operator's answer on what
  an acceptable gap is.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-119-review-barrier-deadlocks-on-a-refusing-bot.md"
```

## Write-Boundary

This plan MUST NOT create or edit any file under `.plan/local/orchestrator/`. Its only channels back
to the epic are its PR and its `inbox/` OUTBOX.
