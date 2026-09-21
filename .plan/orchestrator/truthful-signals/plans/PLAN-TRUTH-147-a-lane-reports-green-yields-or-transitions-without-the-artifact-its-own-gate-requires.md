# PLAN-TRUTH-147: A lane reports green, yields, or transitions without the artifact its own gate requires

## Objective

Four defects on the execution lanes, all the same shape: a phase hands back control while the artifact its
own gate requires is absent, and nothing at the hand-back notices. Phase 5 reports green over work it did not
verify or commit; the phase runner yields without naming a reason, so a stop cannot be told from a stall; the
finalize branch table has no arrival path for one verdict shape, so a clear verdict over an empty population
reads as a checked negative; and the light lane cannot author the PR title its own entry gate requires.

## Deliverables

12 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: re-ground at HEAD and derive all four populations.** Derive BOTH yield populations (PLAN-TRUTH-107 D0 — neither is known today), the verdict-arrival population (PLAN-TRUTH-104 D0), and re-ground PLAN-TRUTH-142 and PLAN-TRUTH-141 at HEAD. ⛔ Publish each population and its size.
2. **D1 — Make every canonical the finalize step names seedable.** (PLAN-TRUTH-142 D1.)
3. **D2 — Observe the tree on a phase-5 leaf's return.** The hand-back is the only moment the uncommitted work is still visible. (PLAN-TRUTH-142 D2.)
4. **D3 — Declare the yield set CLOSED, and require every yield to name itself BEFORE returning control.** (PLAN-TRUTH-107 D1.)
5. **D4 — Separate the progress channel from the control channel, in the standards.** (PLAN-TRUTH-107 D2.)
6. **D5 — THE MECHANISM: make the next step arrive as tool output, not as recall.** A step recalled from context is a step that can be silently skipped. (PLAN-TRUTH-107 D3.)
7. **D6 — A detector: a phase that ended without a terminal yield record is reportable.** (PLAN-TRUTH-107 D4.)
8. **D7 — Protect the honest stop, explicitly and by name.** ⛔ A change that makes every stop look like a stall is the opposite failure and strictly more expensive. (PLAN-TRUTH-107 D5.)
9. ⛔ **D8 — MOVED OUT 2026-09-18 to `PLAN-TRUTH-172`.** (The finalize branch table's missing arrival path; PLAN-TRUTH-104 D1.)
10. ⛔ **D9 — MOVED OUT 2026-09-18 to `PLAN-TRUTH-172`.** (The light lane authors `metadata.pr_title`; PLAN-TRUTH-141 D1.)
11. ⛔ **D10 — MOVED OUT 2026-09-18 to `PLAN-TRUTH-172`.** (Transition-time phase-array invariant; PLAN-TRUTH-141 D2.)
12. **D11 — Controls for the members that REMAIN here.** Matched controls per member of D1–D7. ⚠ The `-104` and `-141` control sets moved out with their deliverables and are now `PLAN-TRUTH-172` D3; what stays is the `PLAN-TRUTH-142` D3 set plus the yield-population controls.

⛔ **SPLIT 2026-09-18 (cleanup A5). This spec carried 13 deliverables against the epic's ceiling of 12.**
The members split along the seam this spec's own objective already named: *a phase hands back control*
(D0–D7, D11 — which stay) versus *a lane transitions without the artifact its gate requires* (D8–D10,
now `PLAN-TRUTH-172`). ⛔ **Never pair the two halves in one `next` block** — they share
`phase-6-finalize` and `manage-status`, and the split was made to reduce plan size, not to license
concurrency. Deliverable count re-derived after the split: **9**.

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-142 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-142-phase-5-reports-green-over-work-it-did-not-verify-or-commit.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-107 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-107-the-phase-runner-yields-control-without-naming-a-reason.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-104 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-104-a-clear-verdict-over-an-empty-population-is-reported-as-a-checked-negative.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-141 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-141-the-light-lane-cannot-author-the-pr-title-its-own-entry-gate-requires.md` § `## Claim Labels` (verify-at-outline)

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` — carried from PLAN-TRUTH-142
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py` — carried from PLAN-TRUTH-142
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — carried from PLAN-TRUTH-142
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py` — carried from PLAN-TRUTH-142
- `test/plan-marshall/phase-5-execute/` — carried from PLAN-TRUTH-142
- `test/plan-marshall/manage-config/` — carried from PLAN-TRUTH-142
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — carried from PLAN-TRUTH-107
- `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — carried from PLAN-TRUTH-107
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — carried from PLAN-TRUTH-107
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — carried from PLAN-TRUTH-107
- `test/plan-marshall/manage-status/` — carried from PLAN-TRUTH-107
- `test/plan-marshall/phase-6-finalize/` — carried from PLAN-TRUTH-107
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — carried from PLAN-TRUTH-107
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` — carried from PLAN-TRUTH-107
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/` — carried from PLAN-TRUTH-107
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py` — carried from PLAN-TRUTH-104
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/**` — carried from PLAN-TRUTH-104
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — carried from PLAN-TRUTH-104
- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/` — carried from PLAN-TRUTH-104
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` — carried from PLAN-TRUTH-141
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — carried from PLAN-TRUTH-141
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — carried from PLAN-TRUTH-141
- `test/plan-marshall/plan-marshall/` — carried from PLAN-TRUTH-141
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — carried from PLAN-TRUTH-141

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-142-phase-5-reports-green-over-work-it-did-not-verify-or-commit.md` (PLAN-TRUTH-142)
- `PLAN-TRUTH-107-the-phase-runner-yields-control-without-naming-a-reason.md` (PLAN-TRUTH-107)
- `PLAN-TRUTH-104-a-clear-verdict-over-an-empty-population-is-reported-as-a-checked-negative.md` (PLAN-TRUTH-104)
- `PLAN-TRUTH-141-the-light-lane-cannot-author-the-pr-title-its-own-entry-gate-requires.md` (PLAN-TRUTH-141)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-147-a-lane-reports-green-yields-or-transitions-without-the-artifact-its-own-gate-requires.md"
```

## ⭐ FOLDED 2026-09-13 — PRE-SUBMISSION-SELF-REVIEW HAS NO CONVERGENCE SIGNAL

Forwarded via `review-apparatus` (`inbox/review-apparatus-038.md`), from `plan-pr-046`'s own finalize (PR
#1477). Expected Surface unchanged — `phase-6-finalize/workflow/pre-submission-self-review.md` is already
listed above.

`pre-submission-self-review` fired 7 times with 6 loop-backs on PR #1477, and nothing in the loop computes
whether it is converging. `done` is not convergence (already a recorded epic rule), and a loop with no
convergence signal cannot distinguish "found a new class of defect" from "re-finding the same one."
Finalize was 48.5% of a 6.77M-token run on that PR, more than execute. Give the loop a computed
convergence signal rather than relying on the terminal `done`/`loop_back` outcome alone.

## ⭐ FOLDED 2026-09-14 — DOC-CONSISTENCY IS ENFORCED ONLY AT FINALIZE, THE MOST EXPENSIVE GATE

Forwarded via `truthful-signals-010.md` finding 1 (revision 3, split from a broader operator-directed
analysis). Expected Surface unchanged — `phase-5-execute/SKILL.md` and `phase-5-execute/**` already cover
the execute-time obligation this fold targets.

A doc-drift-language sweep across `marketplace/bundles/plan-marshall/skills` matches four files
(`phase-6-finalize/workflow/create-pr.md`, `phase-6-finalize/scripts/pr_intent_section.py`,
`persona-plan-orchestrator/standards/orchestration-model.md`, `manage-lessons/SKILL.md`) — none in
`phase-5-execute`. Nothing obliges a task to update the documentation its own footprint invalidated at
execute time; the only enforcement point is inside `pre-submission-self-review`, already the most
expensive gate in the system (PLAN-TRUTH-089: 81% of a 13.9M-token run, self-review fired 19×, all 17
loop-back iterations exhausted, 27% self-seeded findings). Two costs are independently recorded — the
recurring `doc-contract-divergence` archetype, and that cost profile — but the causal link between
placement and recurrence is a hypothesis, not established. Lead: move the invariant to execute time — a
per-task obligation to update docs its own footprint invalidated, leaving finalize to verify rather than
discover. Caution carried forward: a per-task doc obligation derived from `affected_files` would inherit
that field's known under-recording defect (from `PLAN-CIS-001`) — reconcile before scoping.

## ⭐ FOLDED 2026-09-15 — TWO MORE SELF-REVIEW LOOP-COST INSTANCES, SAME DAY, CORROBORATING THE CONVERGENCE-SIGNAL FOLD

Forwarded from `plan-truth-148-001.md` and `plan-truth-157-002.md`, both landing the same day as the prior
fold on this subject. Expected Surface unchanged.

`plan-truth-148`: `pre-submission-self-review` fired 15 times, 11 `loop_back`, reaching
`loop_back_iteration: 13` — 85% of `6-finalize`'s measured tokens, 29% of the whole plan; no operator turn
fell inside any of the 13 iterations. Explicit recurrence of PLAN-TRUTH-089's already-recorded archetype.
This plan's own deliverables 8/9 shipped a partial fix (verifier independence, stop-question-of-the-
verifier) — but "neither could govern the finalize run that shipped them," so the fix is UNOBSERVED under
its own load. `plan-truth-157` independently reports the same shape: all 5 admitted loop-back iterations
consumed, landing held only because a late CodeRabbit triage resolved 2 findings as `taken_into_account`
rather than requiring a further round — see PLAN-TRUTH-163 for those two deferred findings.

Proposed addition to this deliverable's own remedy: publish a token record for EVERY loop_back firing (3
of 11 currently carry none, so the cost is a measured floor, not a total), and give the step a declared
iteration budget whose exhaustion is a surfaced outcome, not a silent continuation.

## ⭐ FOLDED 2026-09-15 (c) — D9 WITNESSED DETERMINISTICALLY IN A CONSUMER, AND THE ROUND-INVARIANT REFUSAL CARVED OUT

Forwarded from `lessons-handling-26-09-04-01-056.md` (Token-Sheriff PR #744). Expected Surface unchanged —
`plan-marshall/workflow/planning.md`, `phase-3-outline/workflow/light-lane.md` and `plan-marshall/scripts/_invariants.py`
are already declared.

**D9 recurrence.** With `planning_lane=light`, the collapsed refine+outline+derive envelope never reaches
`phase-2-refine` Step 13, the only producer of `status.metadata.pr_title`; the 2-refine `phase_handshake
capture` then refused with `pr_title_missing` and the executing orchestrator set `pr_title` by hand.
Re-grounded at `7a028157e`: `pr_title_missing` is raised by `plan-marshall/scripts/_handshake_commands.py`
line 470 (invariant documented at `_invariants.py` line 321), and neither `planning.md` nor
`light-lane.md` mentions `pr_title`. Deterministic on every light-lane plan — a false-RED gate whose only
exit is a hand-authored value. ⚠ `_handshake_commands.py` is not in this spec's declared surface; D9's
remedy is on the producer side (`light-lane.md` / `planning.md`), so no surface is added — if outline
chooses the lane-aware-invariant alternative instead, it adds that file.

**FOLDED 2026-09-17 — the loop's self-seeding is now MEASURED, and the terminating move is known.**
Forwarded from `truth-166-architecture-refresh-migration-churn-006.md` (PR #1501, first-party). Expected
Surface unchanged. `pre-submission-self-review` fired 7 times (3 loop-backs, a 4th non-clean round closed by
operator decision, 3 terminal firings) and filed 20 substantive findings, all fixed. Self-seeded share by
round: **0% (6 findings) → 100% (7) → 50% (6) → 100% (1)**; **55% overall, and 11 of 14 — 79% — after round
1**. Round 2's own marker says it outright: the 7 findings were "all in prose the round-1 fix authored".
⛔ **The cause is the remediation posture, not the detector**: round 1 closed findings by ADDING explanatory
prose (new branches, a field enumeration, a rationale paragraph), and every addition became round 2's
contract-drift surface — the loop generated backlog faster than it drained it. When round 2 switched to
"deletion or pointer, no new explanatory prose", the share fell 100% → 50% → one finding. Two cheap
remedies, both feeding this spec's convergence-signal work: make **deletion-or-pointer the DEFAULT
remediation posture from round 2 onward** rather than a move each round rediscovers, and **publish the
per-round self-seeded share as the loop's termination signal** — mechanical, by joining each pending
finding's `file_path` against the commits that resolved earlier findings in the same phase. This is the
third independent measurement of PLAN-TRUTH-089's archetype, and the first that names the terminating move.

**Ownership split with `PLAN-TRUTH-167` (staged same drain).** The round-invariant self-review refusal —
a verifier `may_close: no` whose reason no further round can change (surfacer domain, zero detectors) —
is owned by `PLAN-TRUTH-167` D2. This spec's convergence-signal folds above consume that terminal outcome;
they do not re-implement it. The two share `pre-submission-self-review.md` and must not be paired in one
`next` block.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
