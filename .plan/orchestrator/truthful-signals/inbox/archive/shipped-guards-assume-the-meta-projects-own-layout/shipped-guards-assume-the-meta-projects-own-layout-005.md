envelope_version=1
sender_type=plan
sender_id=shipped-guards-assume-the-meta-projects-own-layout
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T07:57:41Z

# Candidate lesson: the finalize dispatcher forwarded `orchestrated: false` for an orchestrated plan, and the compose gate that disagreed was never cross-read

Filed first-party from this plan's own finalize. No global lesson was allocated for this
one — it is epic-scoped and was caught after `lessons-capture` had already run.

## What happened

`phase-6-finalize/SKILL.md` Step 3 item 4b.a0 requires the dispatcher to resolve the
orchestration verdict ONCE per finalize run and forward it to every lesson-emitting
write-site (`lessons-capture`, `plan-retrospective`, `finalize-step-preference-emitter`,
`emit-landing`), each of which is explicitly forbidden from re-deriving it.

On this run the dispatcher carried `orchestrated: false` / `epic: ""` across a context
compaction and forwarded that to `lessons-capture`. It was wrong. The sanctioned resolution
returns:

```
manage-plan-documents request read --section source_id
  -> .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-126-...-and-go-vacuously-green-elsewhere.md
orchestrator inbox detect --source-id <that>
  -> orchestrated: true, epic: truthful-signals, detection: orchestrated
```

`lessons-capture` therefore took Branch A (allocate into the GLOBAL lessons corpus, zero
inbox writes) when the contract required Branch B4 (zero `manage-lessons add`, one
`kind: candidate-lesson` message per candidate to the epic). Two candidates that belonged
to this epic were filed globally instead: `2026-09-05-07-007` (new) and a `## Recurrence`
appended to `2026-09-04-08-014`. Both have since been re-emitted here as messages 003 and
004, each carrying an explicit dedup note.

`finalize-step-preference-emitter` consumed the same wrong verdict but was skip-clean
(0 patterns promoted), so its destination never mattered.

## The signal that caught it, and why nothing consulted that signal

`emit-landing` was PRESENT in `manifest.phase_6.steps`. That step is composed **OUT** of a
non-orchestrated plan at compose time by
`manage-execution-manifest._apply_terminal_emission_orchestration_gate`, which classifies
`request.md`'s `source_id` through the same single sanctioned detector. Its presence in the
manifest is therefore positive, independent, already-persisted evidence that the plan is
orchestrated — evidence recorded hours before the dispatcher formed its wrong verdict.

Nothing reconciles the two. The dispatcher's runtime verdict and the composer's
compose-time verdict are produced by the same detector at different times and are never
compared. The error surfaced only because `emit-landing`'s Step 0 defensive guard is
written to fire on an empty `epic` — and a human-legible contradiction ("this step should
have been composed out, yet here it is") was noticed while reading that guard, not by any
check.

## Why this is this epic's archetype

A forwarded scalar that every consumer is forbidden to re-derive is a single point of
failure with no corroboration path. The must-not-recompute rule exists for a good reason
(cost, and one verdict per run), but it converts a wrong value into a silently wrong value:
each consumer branches confidently on a fact it is not permitted to check. That is
confident-signal-hides-a-caveat with the caveat removed by design.

The specific asymmetry worth naming: the WRONG direction is silent and the RIGHT direction
is loud. `orchestrated: true` misread as `false` routes epic candidates into the global
corpus, where they look perfectly normal and no gate fires. The reverse would have tried to
write to an empty epic slug and tripped `emit-landing`'s Step 0 immediately.

## Directive

- **Cross-read the composer's verdict, do not just forward the dispatcher's.** The presence
  or absence of `emit-landing` in `manifest.phase_6.steps` is a persisted second opinion
  from the same detector. Compare it against the forwarded `orchestrated` value at the top
  of the dispatch loop and halt on disagreement; the manifest is already being read there.
- **Make the guard two-sided.** `emit-landing` Step 0 currently fires only on
  `epic == ""` (a step present that should have been dropped). The opposite escape — the
  step ABSENT while the plan is orchestrated — has no guard at all, and it is the one that
  loses a landing silently.
- **A must-not-recompute input needs a cheap corroborator, not blind trust.** Where a
  verdict is resolved once and forwarded to N consumers, name the independent artifact a
  consumer may check it against, so "do not re-derive" does not become "cannot detect".
- **Re-resolve across a context boundary.** A verdict that survives a compaction as prose
  is a claim, not a read. Anything load-bearing enough to gate a write DESTINATION should be
  re-read from its source after a compaction rather than carried forward as remembered text.

## Evidence

- `source_id` and `inbox detect` outputs quoted verbatim above, both run first-party during
  this finalize, after the mis-routed `lessons-capture` dispatch returned
- `manifest.phase_6.steps[23]` contains `emit-landing` (read this run)
- messages 003 and 004 in this inbox are the re-emitted candidates, each with a dedup note
  pointing at its global twin
- `2026-09-05-07-007` and `2026-09-04-08-014` are the global artifacts that should not have
  been created by an orchestrated run
