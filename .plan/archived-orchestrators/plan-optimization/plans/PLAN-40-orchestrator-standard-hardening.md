# PLAN-40: Orchestrator Standard — Durable Verify-First, Proactive Emit, Single-Source Specs

epic: plan-optimization
workstream: WS-10

> Staged 2026-07-22 from three operator-directed aspects plus the promotion of lesson
> `2026-07-21-22-001`. **Written under the very practice it encodes** — every inferred mechanism
> below is labelled OBSERVED or HYPOTHESIS with a named confirm/refute artifact, and this spec is
> deliberately self-sufficient so its hand-off command is one line (a live demonstration of D4).

## Objective

Six coupled changes to how the `marshall-orchestrator` skill authors specs, dispatches its own
analysis, reports landings, and owns its ledger — plus the promotion of the verify-first discipline
from a transient lesson into the durable standard. Together they harden the orchestrator against its
own recurring failure mode (inferred claims presented as fact), eliminate the long duplicated
hand-off templates, and enforce the plan/orchestrator artifact-ownership boundary in both
directions (plan reads its brief from the spec; plan never writes the ledger).

> **Deliverable count = 6, at the split-guard presumption — deliberately kept as one plan.** All six
> touch the *same surface* (`orchestration-model.md`, `decompose.md`/`orchestrate.md`/`analyze.md`,
> the plan-spec template). Splitting them into parallel plans would create a self-collision on those
> files, so they must ship as one plan, sequenced internally. D4 retains its own PLAN-41 split
> trigger for the phase-1-init lifecycle half (a genuinely different surface).

## Aspect inventory (operator-directed 2026-07-22)

1. **Proactive emit** — after analyzing a landing, the orchestrator must return **not only the
   analysis but the next ready-to-run plan command(s) as copy-paste**, as a standing output — not
   an ad-hoc courtesy.
2. **Single-source specs** — all orchestrator carries (mechanism labels, expected surface,
   adjacency notes, re-grounding instructions, verify-first clauses) live **in the plan-spec
   file**, so the emitted command is a **one-line pointer** and the executing plan reads the brief
   from the file. No more long copy-paste hand-off templates.
3. **Durable + extended verify-first** — promote lesson `2026-07-21-22-001` from an ephemeral
   lesson into `orchestration-model.md` (a lesson is retired once "covered"; this rule must bind
   every session), **and extend its scope** beyond the failure *mechanism* to the orchestrator's
   Expected-Surface claims and finding-sharpenings — both of which are inferred and have been
   falsified (PLAN-37 #978: `_config_core.py` wrongly named a writer; "two populations" was
   actually three).
4. **Higher-effort analysis dispatch (raise the orchestrator's OWN input quality)** — the
   orchestrator may run its analysis work (landing ground-truth verification, decompose research)
   through a **higher-effort `execution-context`** using the established dispatch pattern, to lift
   the quality of what it reasons over. ⚠ **Hard boundary — do NOT duplicate plan mechanisms**:
   the orchestrator does **high-level + analyze**; the plan does **fine-grained**. A higher-effort
   analysis dispatch gathers/verifies evidence and returns a structured verdict — it must never
   reproduce the plan lifecycle's fine-grained implementation work.
5. **Parallelization-scope knob + queue-fill emit** — at orchestration start, **ask the operator
   the parallelization scope** (1 = sequential … N = parallel) via `AskUserQuestion`; then on each
   emit, fill the queue up to that scope with as many *disjoint, ready* commands as sensible
   (scope 5 with 1 running ⇒ up to 4 more) — **only if sensible** (surface-disjointness and
   prep-readiness govern; never emit a collision or an unprepared plan just to fill a slot).
6. **Write-boundary: only the orchestrator writes orchestrator files** — a plan must **never write
   into `.plan/local/orchestrator/{epic}/`** (status.json, epic.md, `landings/`, or the spec's own
   Status Trail). The orchestrator owns every ledger write; a plan reports outcomes only through
   its normal PR/landing, and the orchestrator reconciles from that ground truth via `analyze`.
   The plan-spec template and decompose flow must **document this to the executing plan**, and the
   Status Trail must be relocated out of the plan-authored surface so the plan is never invited to
   fill it. (This is the write-direction complement of aspect 2's read-direction single-source.)

## Deliverables

### D1 — Promote the verify-first rule into the standard (OBSERVED — lesson exists, standard does not carry it)

Confirmed at HEAD: `grep` of `orchestration-model.md` / `decompose.md` for the practice returns
**nothing**; it lives only as lesson `2026-07-21-22-001` (active). Promote it into
`persona-marshall-orchestrator/standards/orchestration-model.md` as a named section (mirror the
`## Dispatch Decision Rule` / `## Terminal-Title Repaint Contract` section shape #967/#968
established). Then retire the lesson via the standard promotion path (the
`finalize-step-lessons-housekeeping` promote-then-retire flow). **Acceptance**: the rule binds any
session that loads the standard, independent of whether the lesson is in context.

### D2 — Extend the rule's scope to ALL orchestrator-inferred claims

The lesson today covers only the inferred failure *mechanism*. Extend the promoted rule to state:
a staged spec's **mechanism, its Expected Surface (file/line lists), and any orchestrator
finding-sharpening** are ALL inferred claims — each must be labelled OBSERVED or HYPOTHESIS and,
when HYPOTHESIS, carry a named confirm/refute artifact and be marked verify-at-outline. **Evidence
this is needed** (both from PLAN-37 #978): the Expected Surface named `_config_core.py` a
`credentials_config` writer (it is not — key-ordering only), collapsing a flagged adjacency
cluster to a phantom; and the orchestrator's "two caller populations" sharpening missed a third
(`_cred_edit.py:59`). **Acceptance**: the standard explicitly names Expected-Surface and
sharpenings as verify-at-outline, not just the mechanism.

### D3 — Proactive, queue-filling emit as a standing analyze/next output

Amend `marshall-orchestrator/workflow/orchestrate.md` (and the `analyze.md` reconciliation flow)
so that **every landing analysis concludes by emitting the next ready-to-run `/plan-marshall`
command(s)** as a copy-paste block — OR an explicit "nothing emittable, blocked on X" statement.
This makes the land→analyze→next loop a single closed step rather than requiring a separate `next`
invocation.

**Queue-fill (aspect 5)**: the emit is not just "the next one" — it fills the queue up to the
**operator-set parallelization scope** (asked at orchestration start via `AskUserQuestion`,
persisted as an epic-level knob; `1` = strictly sequential). With scope `N` and `R` plans running,
emit up to `N − R` disjoint ready commands. **The "only if sensible" guard is normative**: a
candidate is emitted only when it is surface-disjoint from every running AND every
already-emitted-this-round plan AND is prep-ready (no owed re-grounding / verify-first clause).
Never emit a collision or an unprepared plan to fill a slot — report the shortfall instead
(*"scope 5, 1 running, only 2 more disjoint+ready; PLAN-X blocked on re-grounding"*).

**Acceptance**: the parallelization scope is asked once at start and stored; `analyze`/`next`
output structurally includes a queue-filling next-command block (or a blocked-reason enumerating
what is not yet emittable and why); the emit-only hand-off rule (the orchestrator EMITS, never
launches) is preserved.

### D5 — Higher-effort analysis dispatch, extending the Dispatch Decision Rule (aspect 4)

Amend the **Dispatch Decision Rule** that PLAN-31 (#968) added to `orchestration-model.md`, adding
an **effort dimension**: for the read-only analysis dispatches that rule already sanctions
(landing ground-truth verification, decompose research), the orchestrator may use a
**higher-effort `execution-context-level-N`** to raise input quality. **Encode the boundary
explicitly and durably**: orchestrator = high-level + analyze, plan = fine-grained; the
higher-effort dispatch **gathers and verifies, returns a structured verdict, and never reproduces
the plan lifecycle's fine-grained implementation work** — otherwise the orchestrator duplicates
plan mechanisms (the exact anti-pattern the tier boundary exists to prevent). Preserve PLAN-31's
`dispatch-gathers, the-orchestrator-decides` maxim and the read-only-by-instruction constraint.
**Acceptance**: the Dispatch Decision Rule names an effort tier for analysis dispatch and restates
the high-level-vs-fine-grained boundary as the guard against mechanism duplication.

### D6 — Enforce the write-boundary in the spec template + decompose flow (OBSERVED — template invites the violation)

**Confirmed at HEAD**: every staged spec under `plans/` (PLAN-40 included) ends with a `## Status
Trail` block carrying orchestrator-owned fields (`plan_marshall_plan_id`, `pr`, `landing`) *inside
the orchestrator directory* — a standing invitation for the executing plan to write orchestrator
state. Fix in two parts:

- **Document the boundary to the plan.** Add to `orchestration-model.md` and the plan-spec template
  a normative statement: the executing plan MUST NOT create or edit any file under
  `.plan/local/orchestrator/{epic}/`; the orchestrator owns status.json, epic.md, and `landings/`,
  and reconciles them from the landed PR via `analyze`. The plan's only channel back is its PR.
- **Remove the invitation.** Relocate the per-plan status trail out of the plan-authored spec into
  an orchestrator-owned surface (status.json already holds `plan_marshall_plan_id`/`pr`/`landing`;
  the spec's Status Trail is redundant with it). The spec template ships without a plan-writable
  status block.

**Acceptance**: the standard states the write-boundary in normative terms; the spec template
carries no orchestrator-owned writable field; a plan implementing a spec touches only its own
source/tests, never the orchestrator ledger.

### D4 — Single-source specs + one-line hand-off (⚠ GATED HYPOTHESIS — has a possible lifecycle half)

The target: the emitted command is `/plan-marshall task="implement {spec_path}"` and the plan
reads its full brief from the spec file — no duplicated instruction block.

- **OBSERVED**: `task=` becomes the plan source (`planning.md:30`) and phase-1-init Step 5 records
  it **verbatim into `request.md`** (`phase-1-init/SKILL.md:35` — even detailed task text is
  "request material to record," not a path to read). So today the lifecycle does **not** formally
  ingest a referenced spec file's contents.
- **HYPOTHESIS**: whether a downstream phase (refine/outline) nonetheless reads the referenced
  path reliably, or whether the one-line command silently loses the brief.
  **Confirm/refute artifact**: trace `request.md` → phase-2-refine → phase-3-outline and establish
  whether the referenced spec-file contents actually reach the executing context.
- **Fork on the D4 gate**:
  - **Orchestrator half (ships here regardless)**: update the plan-spec template
    (`marshall-orchestrator/templates/plan-spec.md`), `decompose.md`, and the `orchestrate.md`
    emit contract so **all carries live in the spec** and the emitted command is a one-line
    pointer. This is the demonstration this very spec already follows.
  - **Lifecycle half (SPLIT TRIGGER)**: if the gate finds phase-1-init must be taught to detect a
    `task=` referencing a plan-spec file and **ingest its contents into `request.md`**, that is a
    `phase-1-init` change — a **different surface** — and **splits to a follow-up plan (PLAN-41)**.
    PLAN-40 then ships D1-D3 + the orchestrator half of D4 and records the split as an epic
    decision. Do NOT absorb a phase-1-init change into this orchestrator-doc plan.

## Expected Surface (OBSERVED where cited; verify at outline per D2)

- `persona-marshall-orchestrator/standards/orchestration-model.md` (D1/D2 promoted rule; D5 dispatch-effort; D6 write-boundary)
- `marshall-orchestrator/workflow/orchestrate.md` (D3 emit + D4 emit contract)
- `marshall-orchestrator/workflow/analyze.md` (D3 — next-command as analyze output)
- `marshall-orchestrator/workflow/decompose.md` (D4 author-carries-into-spec; D6 boundary documented to the plan)
- `marshall-orchestrator/templates/plan-spec.md` (D4 single-source template; D6 — no plan-writable status block)
- lesson `2026-07-21-22-001` (D1 — retired on promotion)
- ⚠ possibly `phase-1-init` (D4 lifecycle half — **only if the gate confirms it; else SPLIT**)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **none in flight** — PLAN-39 (`manage-execution-manifest` + architecture-resolve)
  is disjoint. Emittable immediately.
- **Self-referential, deliberately**: this plan encodes the verify-first practice and is itself
  written under it; D4's own lifecycle mechanism is a gated hypothesis, not an assertion.
- Re-ground against #967 (Terminal-Title Repaint Contract) and #968 (Dispatch Decision Rule) at
  outline — they are the section-shape precedent D1 mirrors, and #968 already touched
  `analyze.md`/`decompose.md`, so cited line numbers may have moved.

## Hand-Off Command

> Demonstrates D4: the command is a one-line pointer; the full brief is THIS FILE.

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-40-orchestrator-standard-hardening.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-40.md is recorded}
