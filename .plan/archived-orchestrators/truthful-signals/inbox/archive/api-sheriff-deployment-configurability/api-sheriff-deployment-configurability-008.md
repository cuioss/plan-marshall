envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:48Z

component=plan-marshall:phase-3-outline
category=bug

# Light lane still never authors metadata.pr_title, and no phase transition checks the "at most one non-terminal phase" invariant

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Filed in **API-Sheriff's** store, whose
repo does not own the `plan-marshall` bundle. Written here first and removed there second
(integrate-then-remove), `deployment-configurability` epic lessons intake 2026-09-11.

Origin id: `2026-09-06-07-001` (created 2026-09-06).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| light lane left `2-refine` `in_progress` while transitioning `3-outline` | FIXED by #1399 (`d03ca621c`, 2026-09-05) | orchestrator transitions and captures `2-refine` before dispatching the light envelope (`planning.md:233-258`, `light-lane.md:266`) | shipped |
| light lane never writes `metadata.pr_title` | STILL-VALID | the only writers are in phase-2-refine (`phase-2-refine/SKILL.md:266`, `refine-workflow-detail.md:808`); `light-lane.md` never writes it, so the 2-refine capture now fails `pr_title_missing` (`_invariants.py:1676`) | lessons `2026-09-04-12-001`, `2026-09-08-15-001` (both active); `truthful-signals/settled.md:1927` — **no staged plan** |
| no transition checks "at most one non-terminal phase; every phase before `current_phase` is `done`" | STILL-VALID, **UNTRACKED** | `cmd_transition` (`_cmd_lifecycle.py:342-440`) marks the completed phase done and the next in progress; it asserts nothing about earlier phases | nearest: PLAN-TRUTH-127 (staged; archiving after loop-back, not a general invariant) |

**What this message adds:** a further independent sighting of the `pr_title` gap — with two active
lessons and a settled note already on file and no staged plan, this is the push to stage one; and the
general transition-time invariant, which would have made the fixed `2-refine` defect fail at the
transition that created it rather than several phases later.

---

## Original lesson `2026-09-06-07-001` (verbatim)

id=2026-09-06-07-001
component=plan-marshall:phase-3-outline
category=bug
status=active
created=2026-09-06

# The light lane elides a phase's substantive work AND its terminal bookkeeping - pr_title unauthored and a phase left in_progress behind an advanced current_phase

## Provenance — this was DISCARDED once and the discard was wrong

PLAN-15 filed this as inbox candidate `trusted-proxy-breadth-and-probe-doc-003.md` on 2026-09-05. The
orchestrator **discarded** it on a store-boundary ground: the defect lives inside plan-marshall's
light-lane envelope, a bundle this repository does not own.

PLAN-13 then filed `2026-09-06-01-001` against `plan-marshall:tools-integration-ci` **in this very
store**, for a defect of exactly the same shape. The two cannot both be right, and the plan's
instinct was the better one, so this is promoted retroactively.

⛔ **The corrected rule: the deciding question is whether THIS repository repeatedly pays the cost,
not which bundle owns the remedy.** A foreign-bundle defect that costs local plans on every run
belongs in the store the local plans consult — the store is CWD-keyed, so a lesson filed elsewhere is
invisible to the plans that keep hitting it. `--allow-foreign-store` exists for exactly this case.
The store-boundary rule still holds for a foreign observation carrying **no local cost and no local
actionable**; that is a much narrower class than the one it was applied to.

## Observation

PLAN-15 routed `planning_lane: light`. That envelope left **two** handoff obligations unmet, both
discovered downstream by the orchestrator and both fixed by hand:

1. **`metadata.pr_title` was never authored.** The lane transitioned out of `3-outline` without
   writing the field, so the finalize pipeline reached PR creation with nothing to title the PR.
2. **`2-refine` was left `in_progress` while `3-outline` was transitioned.** The phase array
   therefore carried two non-terminal phases at once — a state the sequential phase model does not
   admit.

## Why the second is the serious one

A missing `pr_title` **announces itself** at PR-creation time: something asks for it, it is not
there, it gets supplied.

A phase left `in_progress` behind an advanced `current_phase` **fails nothing immediately**. It
corrupts the record that every later resume, retrospective and progress calculation reads, and it can
only be caught by someone noticing the array is inconsistent. `progress` counts only `done` phases,
so the plan **under-reported its own completion for the rest of the run**.

## The general shape

**When a lane elides a phase's substantive work, the phase's terminal bookkeeping is not part of what
it may elide.** The light lane exists to be cheaper, not to be less complete about its handoff
contract. A lane that emits a structurally invalid `status.json` is not a cheaper lane — it has moved
its cost onto the next reader, who pays it in manual reconciliation.

## Directive

1. **After any light-routed plan, check the phase array before trusting `progress`.** The invariant
   is: *at most one non-terminal phase, and every phase before `current_phase` is `done`.*
2. **Check `metadata.pr_title` exists before finalize reaches `create-pr`**, rather than discovering
   it at the step that needs it.
3. **Upstream remedy**: a lane variant should be checkable against that invariant at each transition,
   so a skipped-but-not-closed phase fails at the transition that created it rather than surfacing
   several phases later.

⚠ **Recurrence risk is high for `deployment-configurability`**: light routing is the expected default
for the bounded, well-specified changes that make up most of that epic, so every light-routed plan
reproduces this and costs the same manual reconciliation.
