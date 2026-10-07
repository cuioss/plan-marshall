envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:44:41Z

component=plan-marshall:manage-execution-manifest
category=bug

# An empty footprint at compose time is read as "nothing to build", not as "unknown"

From this plan's decision log, written by the manifest composer during **phase-4-plan**:

```
[2026-07-29T14:36:03Z] (plan-marshall:manage-execution-manifest:compose)
  pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
```

At compose time no task has run. No code has been written. The footprint is **necessarily** empty for every plan, always. The predicate therefore cannot distinguish "this plan changes nothing" from "this plan has not started yet" — and it resolves that ambiguity in the dangerous direction, by dropping the pre-push quality gate.

The gate survived this run only by accident. Two log lines later:

```
[2026-07-29T14:36:03Z] ceremony_finalize selection — finalize.qgate=always,
  added pre-push-quality-gate to phase_6.steps
```

A *different* rule, keyed on an unrelated config knob, re-added the step in the same second. Had `finalize.qgate` been anything other than `always`, this plan would have shipped with its pre-push quality gate silently omitted — on a change touching `pyproject.toml`, the root `conftest.py`, and 6 test modules. The omission would have appeared in the manifest as a legitimate routing decision, with a confident, plausible-reading justification attached.

This is the same shape as the standing merge-lock rule ("never judge a merge lock stale from a worktree-scoped store — an empty store means *unknown*, not *absent*"). An empty measurement taken before the thing exists is not evidence of absence.

## Solution

- **Make the predicate tri-state.** The footprint read must return `empty` / `non-empty` / `not-yet-derivable`, and `not-yet-derivable` MUST NOT satisfy a drop condition. At compose time the answer is always `not-yet-derivable`.
- **Never let an omission be justified by a pre-execution measurement.** Any compose-time rule whose drop condition depends on the realized footprint is structurally unsound. Either defer the decision to a point where the footprint exists (recompose at end-of-execute, which the manifest already supports) or drop the rule.
- **Do not rely on a second rule to rescue the first.** The two rules that fired here are independent; their interaction happened to be safe under this project's config. Audit for other compose-time rules that read the footprint — this one was discoverable only because the composer logs its reasoning, which is a credit to the logging, not a guarantee that it is the only instance.

## Evidence

- aspect: `manifest-decisions` — decision-log entry `c409ae` (omission) and `660085` (re-addition), same timestamp `2026-07-29T14:36:03Z`
- the realized footprint was 8 files, including `pyproject.toml` and `test/conftest.py` — a change class the pre-push gate exists to cover
- the manifest's `phase_6.steps` shows `pre-push-quality-gate` present, and `phase_steps` records it as `done` with `"1 bundle + whole-tree quality-gate green"` — so the gate did run, purely because `finalize.qgate=always`
