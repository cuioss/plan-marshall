# PLAN-PRQ-10: The finalize loop re-fires converged steps, and the self-review cannot tell a swept class from an unswept one

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-19 from three `candidate-lesson` messages filed first-party by `PLAN-PRQ-06`'s own
retrospective (PR #1541, `a1dd4901f`) and delivered to this epic's inbox by hand after `emit-landing`
failed open: `prq-06-a-lane-override-that-cannot-take-effect-is-003.md`, `-018.md`, `-019.md`. The three
name one phenomenon and three of its drivers, and two of them cross-reference each other in their own
text. Drafted by a dispatched `execution-context-level-5` leaf and adjudicated by the orchestrator.

⚠ `-019`'s payload was also filed to the global corpus as lesson `2026-09-19-12-001` during the run. That
lesson is superseded by this spec — see the epic's Decisions for the pointer.

## Objective

**Finalize cost more than the work it was finalizing, and the loop that drove the cost cannot tell when
it has converged.** On `PLAN-PRQ-06`, 6-finalize consumed 4,232,432 of 8,444,415 tokens (50%) against an
anchor that errors at 1.6M — 5.3× the error column — across 47 step firings over 9 steps where 9 would
suffice. The re-firing is not one expensive step: `finalize-step-simplify` fired 12 times reporting `0
edits`, `lessons-housekeeping` 8 times reporting `0 rm, 0 promo, 0 adapt`, `plugin-doctor` 7 times
reporting `clean`. Each re-fire paid a fresh envelope to re-confirm a settled answer, because no step is
gated on a convergence probe.

Two mechanisms inside the loop manufacture iterations rather than measuring them. The self-review's
`further_round_owed` predicate files a **loop-control fact as a Q-Gate finding**: four such findings on
one plan, every one resolved not by fixing anything but by recording that a later round superseded it, two
resolution texts byte-identical across pairs. And one of five content classes the round swept is covered
by **no detector at all**, so it returned zero candidates — and in the verdict, zero candidates is
indistinguishable from swept-and-clean. Re-firing that step could never change that signal; the defect in
that file was found only because an operator opened it by hand, twice.

⭐ This is the epic's own instrument applied to the loop that gates every plan's push: after this lands, a
reader must be able to tell *"this step has converged"* from *"this step keeps being asked"*, and *"this
class was examined and is clean"* from *"no instrument looked at this class"*.

## Deliverables

Six deliverables. D0 is a gate.

**D0 — GATE: derive the re-firing population and the detector→content-class reach map, and publish both
with their sizes.**
(a) Over the archived-plan corpus, per finalize step: firing count, distribution of last-reported
outcomes, and how many firings reported no work performed. ⛔ One plan's 47 firings is an instance; the
corpus figure decides whether D1 is a convergence probe or a threshold tweak. `manage-status`
`metadata.phase_steps` and `manage-execution-manifest refire-report` are the two available readers — ⛔
note `refire-report` reads ONLY `execution_log` (`manage-execution-manifest.py:2918`, helper
`:2801-2849`), which `PLAN-PRQ-08` D2 records as under-counting exactly the steps that re-fire most. Read
both ledgers and publish the disagreement rather than picking one.
(b) For every entry in the `ext-self-review-plan-marshall` `CANDIDATE_LISTS` registry, state which
`CONTENT_CLASSES` members it can produce a candidate for. Publish the matrix and the count of (class,
detector) pairs, and the classes with zero covering detectors. ⛔ This derivation is the whole load-bearing
question of D3 — see its Claim Label.

**D1 — A finalize step does not re-fire once it has converged, and "converged" is a published fact.**
Gate re-firing on a cheap idempotence probe rather than re-dispatching the whole ordered prefix at full
envelope cost on every loop-back. Three shapes are available and are not exclusive; D0's corpus figures
choose among them:
(i) **HEAD-bound skip** — several steps already stamp `head_at_completion`; when it equals current HEAD
and the last outcome was `done` with a no-work facts block, record `outcome: done, basis: unchanged-head`
without dispatching.
(ii) **`work_performed` generalised** — `finalize-step-sync-baseline` and `branch-cleanup` already publish
it; extend it to every step and treat two consecutive `work_performed: false` firings as convergence
until HEAD moves.
(iii) **Cap the prefix** — on loop-back iteration N, re-fire only the steps whose inputs the loop-back
actually invalidated.
⛔ Whichever is chosen, a skipped firing MUST be recorded as skipped-with-basis, never as a firing that
ran and found nothing: the two are different facts and collapsing them re-creates the epic's own
archetype inside its fix.

**D2 — A loop-control fact is not a Q-Gate finding.**
`further_round_owed` fires once per non-clean round and its only resolution is "a later round superseded
it" — four such rows on one plan, put through the triage surface and into every downstream finding count.
That a round which found things did not also close is already implied by the loop continuing. Either stop
filing it as a finding and record it as loop state, or restrict the filing to the load-bearing case. ⭐
The load-bearing case is identified and MUST survive: `5e9ee0`'s shape — a delta-scoped round verified
clean but `may_close=no` **because it was a delta round**, owing a full-surface confirmation — is what
prevents a delta pass from closing on a partial surface, and is already contractual
(`ext-point-self-review-surfacing.md:56`, "A delta-scoped round cannot close the step"). Keep that; retire
the bookkeeping rows.

**D3 — A per-class candidate count states which kind of zero it is.**
⛔⛔ **This deliverable contradicts a sentence in the governing standard, deliberately, and must discharge
it rather than ignore it.** `ext-point-self-review-surfacing.md:222` currently states that separating
"covered class, nothing found" from "no detector covers this class" *"would need a per-detector reach map
no implementor can derive, and publishing one would be a stronger claim than the evidence carries."* D0(b)
is the test of that claim. If D0(b) derives the map from the registry, this deliverable adds per-class
detector coverage beside `delta_coverage.by_class[]` (so a class with `files > 0`, `files_with_candidates:
0` and `detectors: 0` is visibly a GAP, not a pass) **and amends that sentence in the same act**, stating
what changed and why. If D0(b) shows the map is genuinely underivable, this deliverable ships the
refutation and the reason, and D4 covers the class instead. ⛔ Either outcome is a result. What is
forbidden is adding the field while leaving the sentence saying it cannot be derived.

**D4 — The uncovered class gets a detector, or its absence is declared at the registry.**
`doc/user/configuration.adoc` — AsciiDoc bullet-list prose — is the measured instance: the operator found
a stale floor enumeration in it by hand, of exactly the class the round was sweeping for, in a
user-facing document. Either add a detector reaching that class, or record the class as
deliberately-uncovered in the registry so D3's coverage field reports a stated exemption rather than an
accidental hole. ⛔ The fix set is whatever D0(b) returns — this one member was found by an operator
reading a file, which is the under-derived-population archetype.

**D5 — Controls.**
(i) A step whose inputs DID change still re-fires — the matched negative for D1, pinned by a case where
HEAD moved. (ii) A delta round still cannot close the step — the matched positive for D2's preserved
case. (iii) A class with a live detector and a real candidate still reports it, and a class with a live
detector and nothing to find still reports a clean zero — the matched pair for D3, so the new field
cannot report every zero as a gap. (iv) Per the epic's standing rule every guard here is
population-derived and publishes the population it scored; a probe that can report "0 unconverged steps"
from an empty firing set is the vacuous-guard archetype this epic has recorded at n≥6.

## Claim Labels

- OBSERVED: 6-finalize consumed 4,232,432 of 8,444,415 tokens (50%) across 47 firings over 9 steps and 6
  loop-back iterations on `PLAN-PRQ-06`; `finalize-step-simplify` 12 firings / "0 edits",
  `pre-submission-self-review` 9 firings with 7 of 8 prior returning `loop_back`, `lessons-housekeeping`
  8 / "0 rm, 0 promo, 0 adapt", `plugin-doctor` 7 / "clean". First-party from that plan's
  `status.metadata.phase_steps` and its `plan_efficiency` aspect. ⛔ The plan directory is archived —
  re-derive from the archived corpus at outline, do not re-read this restatement (verify-at-outline).
- OBSERVED: `may_close` and `further_round_owed` are defined and consumed in
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` and
  nowhere else outside tests — content sweep, 37 hits in that file, 6 across 5 test files, 0 elsewhere;
  3080 files scanned, 0 unreadable, no truncation, no elision (2026-09-19).
- OBSERVED: `ext-point-self-review-surfacing.md:222` declines the per-detector reach map on the stated
  ground that "no implementor can derive" it, while `:219` states the class vocabulary is declared in the
  implementor's own `CONTENT_CLASSES` registry, and that registry exists at
  `pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`. The two
  sentences sit in one document. Read directly, 2026-09-19.
- OBSERVED: `5e9ee0` is the load-bearing `may_close=no` case (delta round clean, full-surface confirmation
  owed) and is contractual at `ext-point-self-review-surfacing.md:56`. D2 must not retire it.
- ⚠ HYPOTHESIS: the four steps named above are not the whole re-firing population — D0(a) owns the
  derivation and may return a larger or smaller set (verify-at-outline).
- ⚠ HYPOTHESIS: AsciiDoc bullet-list prose is the only content class with zero covering detectors. ⛔
  Asserted by nobody; it was found by an operator opening one file. D0(b) owns it (verify-at-outline).
- ⚠ HYPOTHESIS: a `work_performed`-style convergence flag is derivable for every finalize step without a
  per-step change — confirm/refute at `finalize-step-sync-baseline` and `branch-cleanup`, which already
  publish it, and at the `ext-point-finalize-step` facts contract (verify-at-outline). If refuted, D1
  narrows to shape (i) or (iii).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — D2 (`may_close` / `further_round_owed`)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — D1 (the step loop and its re-fire path)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md` — D3 (the coverage field AND the `:222` sentence it amends)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py` — D0(b), D3, D4 (the `CANDIDATE_LISTS` and `CONTENT_CLASSES` registries)
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` — D0(b), D4 (§ Detection Rules, the authoritative enumeration)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — D1, only if the convergence fact rides the step facts contract (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — D0(a), only if `refire-report` must be read or extended (verify-at-outline)
- OBSERVED: `doc/user/configuration.adoc` — D4's measured instance (read for the class, not necessarily edited)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — D5 (i), (ii)
- OBSERVED: `test/pm-plugin-development/ext-self-review-plan-marshall/` — D5 (iii), (iv)

## Dependencies and Sequencing

- Depends on: none.
- ⛔⛔ **CROSS-EPIC, INVISIBLE TO BOTH GATES.** `code-intelligence-substrate` `PLAN-CIS-052` (staged, 10
  deliverables) declares `phase-6-finalize/workflow/pre-submission-self-review.md` for D1b and all of D5,
  and extends it with folds **N3** (a round that suppresses findings it identified still reports `clean`),
  **N4** (`cohort_size` is round-scoped), **N5** (clause-deletion fixes re-flag the same line round after
  round; `repeat_site: true`). N3 and N5 sit in the same document and the same neighbourhood as this
  spec's D2 and D3. ⛔ Never run concurrently; whichever lands first moves that file under the other, and
  the survivor is re-grounded before emit. Check that epic's queue and `manage-status list` before
  launching.
- ⚠ Shares `phase-6-finalize/**` with `PLAN-PRQ-04` and (conditionally) `PLAN-PRQ-07` — at
  `parallelization_scope: 1` that is automatic, but recorded so a raised knob does not pair them.
- D0(a)'s ledger-disagreement read is `PLAN-PRQ-08` D2's subject. ⛔ **Report the disagreement; do not fix
  `refire-report` here.** If PRQ-08 lands first, D0(a) consumes its corrected reader.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-10-finalize-refire-convergence-and-self-review-coverage-honesty.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
