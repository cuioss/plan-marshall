envelope_version=1
sender_type=plan
sender_id=plan-lb-29-harness-sync
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T14:12:27Z

component=plan-marshall:manage-execution-manifest
category=improvement
created=2026-10-09

# Align manifest verification steps with the freshness gate's single-row rule

## Context

The execution manifest of plan `plan-lb-29-harness-sync` stamped two verification steps for the execute phase: `verify:quality-gate` and `verify:module-tests`. Both ran green over the whole tree. The freshness check (`pre-commit-verify-freshness`) still reported `stale` with reason `build_scope_narrow` (`canonical_performs_too_few_analyses`) and refused the phase transition from execute to finalize, and later refused the push after the pre-push gate's separate arms were all green. It only accepted one whole-tree `verify` run.

## Root cause

The freshness check cites a single build record and never a union of records. For a branch that changes Python files that one record must perform compile, lint and test over the whole tree. `module-tests` is test-only and `quality-gate` is compile plus lint, so no combination of the steps the manifest prescribes can ever satisfy the check. The manifest and the gate that consumes its results disagree by construction, and the disagreement surfaces only at the transition, after all the prescribed runs have been paid for.

## Proposed action

Pick one and make both sides agree:

- have the manifest stamp a single whole-tree `verify` as the end-of-phase step whenever the footprint spans more than one module or includes paths no module owns; or
- let the freshness check accept a set of records over the same tree whose analyses together cover compile, lint and test.

Either way, add a test that composes a manifest for a multi-module Python footprint, records exactly the steps the manifest prescribes as green, and asserts the freshness check passes.

## Evidence

- aspect: chat_history_analysis — the executing step at the end of execute reported `freshness_status: stale`, `freshness_reason: build_scope_narrow`, six refused records (two quality-gate, two per-bundle verifies recorded twice) and named whole-tree `verify` as the only command the gate would cite.
- aspect: log_analysis — the two slowest script calls of the plan are whole-tree `pyproject_build` runs of 1,169,240 ms and 1,166,800 ms.
- dispatcher context for this retrospective — the push was refused with `build_scope_narrow` after the pre-push gate's separate arms were green, until a single whole-tree `verify` ran.
