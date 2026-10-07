envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:23:50Z

## Candidate lesson: a newly-shipped finalize step is absent from every already-composed manifest, so this run's landing had no owner

**Component**: `plan-marshall:phase-6-finalize` / `plan-marshall:manage-execution-manifest`
**Category**: bug
**Observed on**: `spec-corpus-review-and-cleanup-entry-point` (PR #1134, merged)

### What happened

This plan's `manifest.phase_6.steps` was composed on 2026-08-09 and carries **22 steps**. `emit-landing`
(order 1000) is **not among them** — it is present in the current bundle source at
`phase-6-finalize/standards/emit-landing.md`, but it shipped after this manifest was composed.

`emit-landing.md` states that activation "is controlled by the dispatcher in `phase-6-finalize/SKILL.md`
Step 3, driven solely by presence of `emit-landing` in `manifest.phase_6.steps`". The manifest is composed
once, at plan-creation time, and persisted. So for every orchestrated plan whose manifest predates the
step, the activation predicate is permanently false and the step can never fire.

The consequence is the failure this epic exists to name: `lessons-capture` (order 991) was relocated so it
no longer emits the landing, and `emit-landing` (order 1000) was created to take it over — but on this run
**neither** emitted it. `orchestrator inbox list --slug truthful-signals` showed 6 live messages, all
`kind: candidate-lesson` from `plan-retrospective`, and **zero** `kind: landing`. The epic would have lost
this plan's machine-readable hand-off entirely, silently, behind a fully green finalize — and
`archive-plan` (order 1100) destroys the plan directory immediately after, so the facts would have been
unrecoverable.

### Why it is not visible

Every guard in the area is a *presence* check against the manifest, and the manifest is exactly the
artifact that is stale. There is no check that asks the complementary question: *does the composed step
set still contain every `default_on: true` step the current dispatch table declares?* A green finalize
therefore proves the composed steps ran — it does not prove the composed set is still the right set.

This is the same read-direction shape the epic already tracks: a confident signal (22/22 steps done)
whose scope silently narrowed underneath it.

### Proposed rule

A step relocation that moves an obligation from step A to a NEW step B is not complete when B is added to
the dispatch table. Already-composed manifests still name A and not B, so the obligation is dropped rather
than moved. Either:

1. **Reconcile at finalize entry** — compare `manifest.phase_6.steps` against the live dispatch table's
   `default_on: true` set and report additions as a WARNING naming each missing step, so the gap is
   observable rather than silent; or
2. **Keep A emitting until no un-composed manifest can exist**, and only then remove the obligation from A.

The generalisation worth carrying: **an activation predicate read from a persisted artifact freezes the
capability set at compose time.** Any capability added after that artifact was written is unreachable for
that artifact's lifetime, and no runtime signal reports the absence — because absence from a list is
indistinguishable from a deliberate opt-out.

### Corroboration

- `manage-execution-manifest read --plan-id spec-corpus-review-and-cleanup-entry-point` → `phase_6.steps[22]`, no `emit-landing`.
- `architecture find --pattern "**/emit-landing*"` → the step doc exists in the current bundle.
- `orchestrator inbox list --slug truthful-signals` → 6 messages, 0 landings, before this step ran.
