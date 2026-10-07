envelope_version=1
sender_type=plan
sender_id=plan-truth-127
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T19:49:23Z

# Put the could-not-look discriminator in the payload, never only in a docstring

component=plan-marshall:plan-retrospective
category=improvement
confidence=high
source_plan=plan-truth-127
theme=confident-signal-hides-a-caveat

## Context

Three guards in this run's own measuring apparatus reported clean because they could not reach
what they claim to check. None of the three announced that in its output.

**1. `build_time` — the discrimination lives in a docstring.**
`analyze-logs.py::summarize_build_ledger` returns
`{total_build_seconds: 0.0, build_count: 0, suspect_count: 0, pass: 0, error: 0, timeout: 0,
killed: 0, status_unknown: 0}` when the change-ledger holds no `kind=build` row for the plan.
Its docstring is explicit that this "the reader treats as *unavailable*, never as *no builds
ran*" — but the returned dict carries no field that distinguishes the two, so the reader has
nothing to key on. On this plan the block published all zeros while the *same fragment*
records 37 `pyproject_build` calls totalling 14,757,680 ms — 68.65% of all plan script time —
and the plan directory holds 17 build-result logs. The retrospective's own efficiency input
therefore said "no build time" about a plan whose dominant cost was building.

**2. The status-summary carve-out cannot fire on the real record shape.**
`review_retrospective._is_status_summary` delegates to `review_gate_delta.is_status_summary`,
which matches the registry's `review_body_summary_patterns` against
`_BODY_FIELDS = ('body', 'message')`. Every `pr-comment` record in this plan's store carries
the comment text **only** under the quarantined `raw_input.body`; no top-level `body` was
promoted. With nothing to match, both of CodeRabbit's "Actionable comments posted: N"
`review_body` records were classified **actionable** rather than meta. On this PR that landed
on the correct side by accident (both bodies also carried a real finding), but the mechanism
is not the documented one, and on a PR whose status summary is purely a summary the same path
inflates `actionable_count` by one per review round.

**3. A constant that documents an invariant it does not enforce.**
`_status_core.py`'s `UNTOUCHED_PHASE_STATUSES` is derived by set difference from
`VALID_PHASE_STATUSES` so that a future fourth phase status lands in the untouched set by
default. It has **zero executable readers** — the definition, two docstring mentions, and one
line of prose. The safety property is actually delivered by `in_progress_phases`' positive
`== in_progress` filter, which would hold identically if the constant did not exist. Recorded
as anti-pattern finding `939919` and accepted unfixed as a contract decision. Note that this
plan's own review-fix work made it *more* prominent, not less.

## Root cause

Each of the three states its contract somewhere a machine consumer never looks: instance 1 in
a docstring, instance 2 in a field name that the live record shape does not populate, instance
3 in prose about a symbol nothing reads. In all three the *output* is byte-identical between
"I checked and found nothing" and "I could not check". That is the epic's theme reproduced
inside the instrument that measures it.

## Proposed action

1. **`build_time` — add the field.** `summarize_build_ledger` publishes
   `ledger_rows_scanned` (or an equivalent population key). When the ledger held no rows for
   the plan, OMIT `total_build_seconds` rather than emitting `0.0`. This is exactly the shape
   this very plan's census verb adopted for its own cohorts — omit the population key rather
   than publish a bare zero — so the fix has a worked precedent in the same tree. The
   consuming reference (`plan-efficiency.md`) already instructs the reader to render
   `unavailable`; the point is that the reader should not have to be instructed.
2. **Status-summary carve-out — match against the shape that exists.** Either promote a
   top-level `body` on the ingest path, or make `_BODY_FIELDS` reach `raw_input.body`. Whichever
   is chosen, add a positive test built from a **real** stored record rather than a
   hand-constructed fixture — a fixture that happens to carry a top-level `body` is what let
   this pass unnoticed.
3. **General, and this is the transferable rule.** For every carve-out, guard, or predicate,
   demonstrate one positive case constructed from the live record shape that makes it fire. If
   no such case can be constructed, the guard is vacuous and must be either wired to the real
   shape or demoted to prose — never left in place reading as enforcement. A guard is not
   verified by the absence of failures; it is verified by a failure it actually catches.

## Evidence

- `fragment-log-analysis.toon`: `build_time.build_count: 0` beside
  `script_cost_rollup.ranked[0] = pyproject_build, 37 calls, 14,757,680 ms, 68.653%`.
- `analyze-logs.py::summarize_build_ledger` — the docstring naming the unavailable/zero
  distinction, and the return dict that omits it.
- review-retrospective.md § "Instrument Observations", item 1 — the `raw_input.body`
  quarantine, verified by reading record `8ff2c2` in full.
- anti-pattern finding `939919` — `UNTOUCHED_PHASE_STATUSES` with zero executable readers,
  accepted unfixed.
- ROUTING NOTE for the orchestrator: instance 2 belongs to the `review-apparatus` epic by the
  standing three-way routing rule (PR/review findings go there). It is carried here because the
  mechanism is shared with instances 1 and 3, and separating it would lose the recurrence
  evidence. Split it out if the epics prefer clean ownership over the shared archetype.
