> ⛔⛔ **SUPERSEDED 2026-08-08 — MERGED INTO `PLAN-TRUTH-014`.**
> Absorbed under the raised 12-deliverable cap, grouped by COMPONENT so that plans on different
> components stay parallel-safe. The receiving spec carries the merge rationale and this plan's
> deliverables. **Do not implement. Do not emit.** Retained as the record — *close freezes, never deletes.*

# PLAN-TRUTH-021: The operator's phase-1-init posture answer never reaches the immunity channel, so `scope_gated_finalize` still drops the step they named

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-30 from inbox `compose-time-subtractions-drop-steps-013.md`. **This is the OPEN half of
> PLAN-202's D2 (#1066, merged `d04ac98ed`).** Not a new defect — the *originating* Defect A scenario of
> PLAN-202, still live after that plan shipped.

## Objective

PLAN-202 shipped the immunity **channel**, **both** compose-side readers, and a **manual CLI writer**.
**No caller writes the `phase-1-init` posture answer into the channel.** Close that gap so an operator's
answer is honoured without a second manual step.

## The live scenario — claim labels CORRECTED 2026-07-30, see the note below

⛔ **LABEL CORRECTION.** This section originally marked all three claims `OBSERVED`. **They were not
observed by the orchestrator** — every one came from inbox message
`compose-time-subtractions-drop-steps-013.md` and from the operator's landing report. Relabelled per
API-Sheriff round-6 #1: *"Mark a claim OBSERVED only when it was verified against the tree during that
decompose pass."* Plausible-and-probably-true is `HYPOTHESIS`.

- **REPORTED (plan `-013` + operator, NOT orchestrator-verified)** — the operator was asked at
  `phase-1-init`, answered, and **named `pre-submission-self-review` specifically**; **27 minutes later**
  `scope_gated_finalize` removed exactly that step.
  *Confirm/refute artifact:* the plan's `status.json` `metadata` posture answer and the compose decision
  log for that run.
- **REPORTED (same source)** — what shipped in #1066: `status.metadata.finalize_step_overrides` (the
  channel), both readers merged through one seam, and `manage-config finalize-steps set-lane --plan-id …`
  (a manual writer).
  *Confirm/refute artifact:* `manage-config`'s `finalize-steps set-lane` handler and the
  `scope_gated_finalize` reader in `manage-execution-manifest`.
- ⛔ **HYPOTHESIS — the highest-risk claim here, and it is an asserted ABSENCE:** that #1066's footprint
  touches **no `phase-1-init` file** and no posture-gathering workflow. The Verify-First Contract names
  absence claims as the higher-risk half precisely because nothing downstream trips over them.
  *Confirm/refute artifact:* `git show --stat` on `d04ac98ed` — a one-command check that was **not run
  before this spec was staged.** **Run it at D1 before anything else.**
- ⇒ **If those hold**, re-running the scenario today still silently drops the operator-named step unless
  they independently know to call `set-lane`, and nothing prompts them to.

⭐ **A CLI verb an operator must know to invoke is a writer for a TEST, not a producer for the flow the
deliverable exists to fix.** That distinction is the whole plan.

## Deliverables

### D1 — GATE: locate the posture-answer site and decide the write point (mutates nothing)

Find where `phase-1-init` gathers the execution-profile / posture answer and persists it, and decide
whether the write into `finalize_step_overrides` happens **there** (at answer time) or at a later
normalisation seam. ⚠ **Verify the answer is actually persisted somewhere today** before assuming it can
be forwarded — if it is only held in context and never written, the fix is a persistence change first and
a wiring change second, and that reordering is the gate's real output.

⚠ **HYPOTHESIS to settle here, not to assume:** that the answer is captured in a form naming *steps*.
`scope_gated_finalize` skips a step by name, so an answer recorded as a coarse profile/posture label may
not be reducible to a step set at all. If it is not, D2 changes shape — say so rather than forcing it.

### D2 — wire the answer into the channel at the moment it is answered

Write the operator's named step(s) into `status.metadata.finalize_step_overrides` through the **same seam**
the manual CLI writer uses — one producer, not a parallel path. `scope_gated_finalize` then honours
operator intent with no second step.

### D3 — the completing question, applied at deliverable granularity

For the state this plan writes, name the **producer in the ordinary unprompted flow** and assert it in a
test. ⛔ **A test that calls the CLI writer does not discharge this** — that is precisely the shortfall
being fixed. The test must exercise the answer-to-honoured path.

### D4 — tests

(a) The originating scenario end-to-end: operator answers naming a step → that step survives
`scope_gated_finalize`. **Verified red before the fix**, since #1066's state is the pre-fix state. (b) No
regression to the manual `set-lane` path. (c) An operator who names nothing is unaffected — the guard must
not become vacuous in the opposite direction by always granting immunity.

## Expected surface

- HYPOTHESIS: the `phase-1-init` posture/execution-profile answer site (named at D1, **not guessed here**)
- **HYPOTHESIS** (was mislabelled OBSERVED): `manage-execution-manifest` — the `scope_gated_finalize`
  reader seam shipped by #1066. *Confirm/refute:* the reader function itself; **not read by the
  orchestrator.**
- **HYPOTHESIS** (was mislabelled OBSERVED): `manage-config` — the `finalize-steps set-lane` writer seam.
  *Confirm/refute:* that verb's handler; **not read by the orchestrator.**
- HYPOTHESIS: `status.metadata` schema docs, if the write point changes the field's documented producer
- ⛔ **TO BE AUTHORED** (was mislabelled OBSERVED — incoherently, since it does not exist yet): tests under
  `test/plan-marshall/**` covering the answer-to-honoured path. **A future artifact can never be
  `OBSERVED`**; that label asserted a read of something unwritten.

**Disjointness:** `phase-1-init` + `manage-execution-manifest` + `manage-config`. ⚠ `manage-config`
overlaps **PLAN-TRUTH-007** (`_config_core.py`) and **PLAN-TRUTH-009** (`manage-config`) — check before
pairing. `manage-execution-manifest` is free now that PLAN-202 has shipped.

## Dependencies and Sequencing

- Depends on: PLAN-202 (**SHIPPED** #1066) — this consumes its channel and readers.
- Overlaps with: PLAN-TRUTH-007, PLAN-TRUTH-009 (`manage-config`). Not with PLAN-57 (`manage-status` lane
  router) on current reading — **re-derive at emit.**

## Notes — the generalisable rules from `-013`, carried here rather than promoted to the corpus

Recorded in the spec because this epic's own PLAN-90 established that the lessons corpus is written to and
rarely read from; a rule attached to the work that needs it is likelier to be applied.

1. **When the outline folds request deliverables, carry each request deliverable's acceptance criterion
   forward individually.** The fold may merge the *work*; it must not merge the *grading*. PLAN-202's
   request named four deliverables with individual acceptance language and the outline produced two —
   which is how a partial deliverable became structurally ungradeable.
2. **Apply the reader/writer completing question at DELIVERABLE granularity, not only file granularity:**
   for the new state a deliverable introduces, name the producer *in the flow the deliverable is meant to
   fix*.
3. **Retrospective Goals-vs-Outcomes grading must be against the REQUEST's deliverable list, not the
   outline's** — otherwise a fold hides a shortfall from the one check meant to catch it.

⭐ Third recorded instance of a plan reproducing its own target defect class inside its own work (cf.
PLAN-86, and PLAN-202's self-review finding 8 instances of its target class in its own diff).

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
