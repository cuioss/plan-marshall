envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:27:23Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=runtime-edge-paths-crash-or-silently-lose-data
source_aspects=compile_report_observed_in_this_run

# compile-report deletes the fragment bundle on the sections_dropped warning path

## Context

`plan-retrospective/SKILL.md` Step 4 states:

> **Cleanup**: `compile-report run` auto-deletes the fragment bundle after a successful report
> write. On failure paths (before the report is flushed to disk), the bundle is retained so the
> aspect fragments remain available for debugging.

The first compile in this run returned:

```
status: warning
sections_written[16]: ...
sections_dropped[1]:
  - Permission Prompt Analysis
message: "Dropped non-empty sections from the compiled report: Permission Prompt Analysis"
```

The report was written, so cleanup ran and the bundle was deleted. A follow-up
`collect-fragments finalize` confirmed it:

```
status: error
error: internal_error
message: "Bundle file does not exist: .../work/retro-fragments.toon"
```

`sections_dropped` is documented as the LOUD half of the non-emit path — "a registered fragment
that was present and carried payload but still did not render" — and the SKILL's Enforcement
section says a non-empty `sections_dropped` must never be treated as a clean pass, because "a
dropped fragment may have carried a live finding". So the one outcome that most demands
inspecting the fragments is the one that destroys them.

## Root cause

The cleanup predicate is "was the report flushed", not "was the compile clean". `status:
warning` satisfies the first and fails the second.

## Proposed action

Gate the bundle deletion on `sections_dropped` being empty, not on the report having been
written. On the warning path, retain the bundle and say so in the returned `message` so the
caller knows the evidence is still available.

## Consequence in this run

Recovery required re-running `collect-fragments init` plus fifteen `add` calls to rebuild a
bundle whose fragment files all still existed on disk — roughly seventeen avoidable script
invocations. The recompile then returned `status: success` with 17 sections and
`sections_dropped[0]`.

## Evidence

- observed directly in this run: first compile `status: warning` with one dropped section; the bundle was absent immediately afterwards
- `plan-retrospective/SKILL.md` Step 4 Cleanup paragraph, and the Enforcement bullet "Never treat a compile-report warning as a clean pass"

## Note on the dropped section itself

The drop was caused by the fragment using `prompt_evidence[]` where the canonical shape is
`prompts[]` — an authoring error on the caller's side, not a script defect. The detection
worked correctly and loudly. This proposal is only about what happens after the warning fires.
