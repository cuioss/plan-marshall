# ADR Integration

Conceptual companion to `adr-propose.md`. Describes WHY adr-propose exists, when it fires, the decision-shape signals it detects, and the lesson-vs-ADR split. The mechanical executor lives in `workflow/adr-propose.md`; this document carries no dispatch logic of its own.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Purpose

At plan completion, the architectural decisions a plan settled — the structural choices the plan made and the alternatives it rejected — should be captured as durable Architectural Decision Records so future work respects the shape the plan established. `adr-propose` is the writing hook that turns a finished plan's decision-bearing artefacts into proposed ADRs.

ADRs are the durable counterpart to lessons. Where a lesson records an ephemeral recurrence pattern, an ADR records a decision that should still read as a standalone record long after the plan that produced it has been archived.

## When adr-propose fires

Activation is decided by the manifest, not by this document. When `adr-propose` is in `manifest.phase_6.steps`, the dispatcher evaluates the decision-shape Signal Gate (owned by `phase-6-finalize/SKILL.md` Step 3) on every Phase 6 entry. The composer in `manage-execution-manifest:compose` includes `adr-propose` for every change-type that produces non-trivial work, alongside `lessons-capture`; the documented exclusions are the same minimal-step paths that drop `lessons-capture`.

- **Signal Gate present** → the `adr-propose.md` workflow body is dispatched and applies the decision-shape criteria below to decide which decisions to propose.
- **Signal Gate absent** (no decision-shape signal) → the dispatcher records `outcome=skipped` directly; the workflow body is not dispatched.

Within an active `adr-propose` run, the agent applies the criteria below to decide whether to propose an ADR or record `no ADRs proposed`. This is content judgement, not step activation.

## Decision-shape signals

A plan signal is ADR-worthy when the plan record exhibits one or more of:

| Signal | Description |
|--------|-------------|
| Rejected concrete alternatives | The outline or decision log names an alternative approach and states why it was not chosen (e.g. the `compatibility` line, an "Alternatives Considered" passage, a decision-log fork with a rationale). |
| Principle statements | The plan asserts a general rule the architecture now follows ("X is always owned by Y", "Z is derived, never authored"). |
| Architecture-affecting changes | The plan introduces, relocates, or removes a structural element (a new extension point, a bundle move, an ownership transfer, a new lifecycle hook) whose shape future work must respect. |

A plan that merely implements a deliverable against an already-decided shape carries no decision-shape signal — there is nothing new to record. The signal is the presence of a *choice with a rationale*, not the presence of work.

## The lesson-vs-ADR split

`adr-propose` and `lessons-capture` look back at the same plan history but record different kinds of durable signal. They MUST NOT double-record the same observation:

- **Lesson = recurrence pattern.** "We hit this defect class, here is the diagnostic signature to watch for next time." Ephemeral; pruned once the recurrence stops. Owned by `lessons-capture` / `manage-lessons`.
- **ADR = decision.** "The architecture is X because alternatives Y and Z fail in ways A and B." Durable; reads as a standalone decision record years later. Owned by `adr-propose` / `manage-adr`.

The boundary test: if the prose is "we hit this bug, watch for the pattern", it belongs in a lesson. If it is "the architecture is X because alternatives Y/Z fail in ways A/B", it belongs in the ADR. The single source of truth for this boundary is the `manage-adr` Authoring Discipline § "What goes into a lesson instead" — consult it rather than re-deriving the criteria.

## Avoiding double-records within the corpus

Before proposing, the workflow body scans the existing ADR corpus via `manage-adr scan --affects {module}` and skips any decision already covered by an existing ADR's `summary`. A decision is proposed only when it is both decision-shaped AND not already in the corpus.

## Authoring the proposed ADR

Proposed ADRs are created as `Proposed` and authored per the `manage-adr` Authoring Discipline. That standard is authoritative for the durable-decision-record shape — Context as a problem class (not an incident), Decision as a principle plus mechanisms, Consequences as steady-state properties, Alternatives Considered on their merits, References to durable artefacts only (no PR numbers, commit SHAs, lesson IDs, or dates). Do not restate the section-shape rules here; follow the `manage-adr` standard.

## Advisory nature

ADR proposal is **advisory only** at the content level:

- Each proposal is surfaced to the user for confirmation via `AskUserQuestion`; the user may decline any individual proposal.
- A timeout on the agent (5-minute budget per the SKILL.md Step 3 dispatch wrapper) records `outcome=failed` but does not block subsequent finalize steps.

## Related

- `plan-marshall:manage-adr` — ADR storage, the `scan` progressive-disclosure surface, and the Authoring Discipline
- `standards/lessons-integration.md` — the sibling conceptual companion for `lessons-capture`
