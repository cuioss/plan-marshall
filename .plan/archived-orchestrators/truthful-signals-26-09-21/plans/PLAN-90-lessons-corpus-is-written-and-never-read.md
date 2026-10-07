# PLAN-90: The Lessons Corpus Is Written To And Never Read From — A Lesson That Predicts A Failure And Does Not Prevent It

epic: truthful-signals
workstream: WS-01

> Staged plan spec — ready for `/plan-marshall` hand-off.
> Raised by PLAN-79's own `plan-retrospective` (PR #1023), inbox message
> `terminal-title-channel-reconciliation-008`. The operator's verdict on that run: **"the
> retrospective's finding outranks the feature."**

## Objective

`finalize-step-lessons-housekeeping` runs and works, but it only ever asks the **retrospective**
question — *"did this plan close a lesson?"* Nothing in the lifecycle asks the **prospective** one —
*"does an active lesson predict a risk on the path this plan is about to take?"* The corpus is an
append-only write surface with a housekeeping pass, not an input to planning or gate selection. Give
it a read side at a point where it can still change behaviour.

## ⚠ Mechanism — measured, not inferred

- OBSERVED (PLAN-79 retrospective, first-party): **five of nine** lesson candidates that run produced
  deduped onto lessons **already active** in the corpus.
- OBSERVED: the run's two most expensive failures were both **predicted in writing before the plan
  started**:
  - `2026-07-17-09-002`, filed **ten days earlier**, describes the exact CI red the run hit — a
    scoped-vs-whole-tree gate parity gap. Cost: a full red CI cycle plus a loop-back. ⚠ **The
    lesson's own wording names plugin-doctor as the CI runner, which is FALSE** — CI runs pytest
    whole-tree and never invokes plugin-doctor (`grep -rn "doctor" .github/` → zero hits across all
    six workflows). **The prediction was right about the symptom and wrong about the mechanism**;
    D1 must not inherit the wrong half.
  - `2026-06-22-11-001` — *"all in-house gates clean, only the PR bot caught it"* — recurred as a
    250-candidate `pre-submission-self-review` returning CLEAN before CodeRabbit found three real
    defects.
  - `2026-07-22-00-002` — recurred as the manifest's contradictory adjacent log lines
    (`pre-push-quality-gate omitted — footprint is empty` immediately followed by `added
    pre-push-quality-gate`).
- **⇒ The theme, turned on the epic's own machinery.** The corpus is a confident signal — 146 lessons,
  actively curated, triaged three times — that hides a caveat: **nothing reads it before the fact.** A
  lesson that predicts a failure and does not prevent it is indistinguishable, in outcome, from a
  lesson that was never filed. Every triage pass this epic has run has been improving the *quality of
  an unread store*.

## Deliverables

### D1 — GATE: choose the consult point and the surfacing mode (mutates nothing)

(a) **Confirm the absence first-party.** Enumerate every consumer of the lessons store and verify no
prospective read exists. ⚠ **An asserted absence is verified exactly like an asserted presence** — if
some phase already consults the corpus, the premise narrows and D1 re-scopes.
(b) **Choose the consult point.** Candidates from the source message: **phase-3-outline** (the surface
is known, so a component-scoped query is possible) or **phase-4-plan** (the gate set is being
composed, so a lesson can still change which gates run). Decide which, and whether both.
(c) **Choose the surfacing mode, and bias AWAY from auto-application.** The cheap version is a scoped
query — *"active lessons whose component intersects this plan's affected modules"* — **surfaced to the
outline rather than auto-applied.** ⚠ Auto-applying a lesson would let a stale or wrong lesson steer a
plan, and this epic has a live example: `2026-07-17-09-002`'s mechanism is wrong while its symptom is
right. A surfaced lesson is judged; an applied one is obeyed.
(d) **Decide the precision bound.** A component-intersect query over 146 lessons could return a
large, mostly-irrelevant set; a too-narrow filter returns nothing and re-creates the current state
with extra machinery. **State the failure mode you are choosing** — noise or silence — and why. ⚠ Note
the epic's standing counter-example: **volume is not coverage** (250 candidates CLEAN, 75 candidates
CLEAN). A consult that returns 40 lessons nobody reads is the same defect wearing a read-side costume.

### D2 — implement the D1-chosen consult

Scoped to D1. **Hard constraint: the consult must be observable** — the plan's artifacts must record
which lessons were surfaced and what was done with them, or a future retrospective cannot tell a
consult that fired from one that did not. An unobservable consult is unfalsifiable.

### D3 — tests

(a) A plan whose affected modules intersect an active lesson's component surfaces that lesson at the
D1 consult point — **verified to FAIL against current code**, where no prospective read exists.
(b) A plan with no intersecting lesson proceeds unchanged and pays no visible cost.
(c) The surfaced set is recorded in the plan's artifacts per D2.
(d) Per D1(c), a surfaced lesson is NOT auto-applied — the assertion is that it is *presented*, not
that it mutated the plan.

Three deliverables (D1 a gate) — under the split guard.

## Claim Labels

- OBSERVED: the five-of-nine dedup, the three named recurrences, and the ten-day gap — all from
  PLAN-79's retrospective, read first-party from inbox `-008`.
- OBSERVED: `finalize-step-lessons-housekeeping` ran on PLAN-79 and retained 10 lessons.
- OBSERVED (asserted absence, orchestrator-verified): CI never invokes plugin-doctor — zero `doctor`
  hits across `.github/`. This corrects the cited lesson's own mechanism.
- HYPOTHESIS: that **no** prospective consumer of the corpus exists anywhere in the lifecycle —
  confirm/refute by enumerating readers of the `manage-lessons` store at D1(a) (verify-at-outline).
  ⚠ This is the plan's founding absence claim and the highest-risk one: if a consult already exists
  and is merely ineffective, the fix is different in kind.
- HYPOTHESIS: that a component-intersect query is selective enough to be useful on a 146-lesson corpus
  — confirm/refute by running the query offline against the live store at D1(d) (verify-at-outline).
- Verify-first clause: **D1(a) and D1(d) both gate D2.** If the corpus is already consulted, or if the
  query proves unselective, loop back and re-scope rather than shipping machinery that reproduces the
  current outcome.

## Expected Surface

- OBSERVED: `manage-lessons` — the query surface a scoped consult would use (read; extended only if
  D1 finds no suitable filter exists).
- HYPOTHESIS: `phase-3-outline` and/or `phase-4-plan` — the consult point, exactly one or both per
  D1(b) (verify-at-outline).
- HYPOTHESIS: `finalize-step-lessons-housekeeping` — touched only if D1 decides the retrospective and
  prospective passes should share a seam (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/manage-lessons/**` plus the chosen phase's test home.

**Disjointness:** `manage-lessons` + one or two phase skills. Disjoint from PLAN-91
(`workflow-integration-github`), PLAN-88 (`manage-build-server`), PLAN-86 (`phase-5-execute`),
PLAN-56 (`marshall-orchestrator`), PLAN-87 (`script-shared` / `pm-dev-oci`).
⚠ **Adjacent to PLAN-89** (`manage-architecture` + `phase-5-execute`) — different phases; re-check if
D1 picks a consult point that touches phase-5.
⚠ **Adjacent to PLAN-61** (`outline-plan-scope-derivation-integrity`) — **both may edit
phase-3-outline.** Sequence if D1(b) picks outline.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-61** if the consult lands in phase-3-outline — sequence, do not pair.
- Adjacent to: **PLAN-60** (`in-house-gate-ci-parity`) — PLAN-60 fixes the *specific* gate-parity gap
  that `2026-07-17-09-002` predicted; this plan fixes the *class* (a prediction nobody reads).
  **Both are wanted:** landing PLAN-60 alone closes one instance and leaves the corpus unread.
- ⚠ **This plan does not fix lesson QUALITY.** The corpus contains at least one lesson whose mechanism
  is wrong (`2026-07-17-09-002`). A read side surfaces wrong lessons as readily as right ones — which
  is exactly why D1(c) biases toward surfacing over auto-application.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-90-lessons-corpus-is-written-and-never-read.md"
```

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**
(`status.json`, `epic.md`, `plans/`, `landings/`); the `inbox/` channel is the sanctioned exception.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
