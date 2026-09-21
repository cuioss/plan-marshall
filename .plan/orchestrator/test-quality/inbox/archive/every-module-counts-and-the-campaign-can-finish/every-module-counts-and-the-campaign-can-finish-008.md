envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:31:57Z

component=plan-marshall:tools-script-executor
category=improvement
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Publish each script's declared accept-set so an argparse rejection is preventable, not just diagnosable

## Context

The run recorded 15 `[ERROR] … script_failure` markers across 9 distinct script notations. 13 of the 15 are `failure_kind=argparse_rejection` — a call that never reached the script body — spread across 8 different scripts:

- `manage-solution-outline` x4 (undeclared flag on `get-deliverable`, on `read`, and a paraphrased verb corrected to `list-deliverables`)
- `manage-execution-manifest` x2 (plan id passed as the `step-params` positional; then missing required `--phase`)
- `tools-integration-ci:ci` x2 (undeclared flag on `checks logs`, on `pr prepare-comment`)
- `manage-findings` x1 (missing required `--phase` on `qgate list`)
- `build-server-client:build_server` x1 (`unrecognized arguments: --plan-id`)
- `manage-architecture:architecture` x1 (`unrecognized arguments: --plan-id`, flag written after the verb)
- `manage-metrics` x1 (`record-dispatch-boundary` flag set)

Every one of these is an instance of a signature already written down in `persona-plan-marshall-agent/standards/agent-behavior-rules.md` § "Never invent script subcommands — recurrence signatures". The checklist was loaded and the rejections happened anyway.

A 14th instance occurred inside the lessons-capture envelope itself, after all five signatures had been read in this same session: `manage-files list --subdir logs` -> `Use --dir … declared: ['dir', 'plan-id']`. That is the sharpest available evidence that a prose checklist is not the right control for this failure class.

## Root cause

The accept-set exists only in two places: inside the script's argparse declaration, and in the rejection message the caller sees *after* paying a round trip. There is no cheap read of "what flags does verb V of script S declare" that an agent can make before the call. The documented remedy is `--help`, which costs the same round trip as simply getting it wrong — so in practice the rejection message becomes the discovery mechanism, and the checklist prose is bypassed.

Note the executor's rejection messages are already excellent: each names the offending token AND the declared set (`Use --dir for … — declared: ['dir', 'plan-id']`), so remediation is one call. The defect is not diagnosis quality, it is that diagnosis is the only channel.

## Proposed action

Make the accept-set readable without a failing call. Options, cheapest first:

1. Have the executor expose the derived accept-set it already computes for its rejection messages as a first-class query (per notation, per verb: registered verbs, required flags, optional flags). `plugin-doctor`'s `manage-invocation-invalid` rule already performs a live `--help` walk, so the derivation exists.
2. Emit the accept-set alongside the `[DISPATCH]` line for scripts a workflow doc names, so a dispatched envelope carries the surface it is about to call.
3. Keep the prose checklist, but stop treating it as the control — it demonstrably does not bind.

## Evidence

- work.log lines 52, 55, 242, 609, 610, 659, 665, 666, 695, 846, 850, 851, 863, 998, 999 — the 15 `script_failure` markers, 13 of them `argparse_rejection`
- signal_script_failure_clusters_count = 9 distinct notations
- The 2 non-argparse failures are a different class and are not part of this candidate: two `plan-marshall:plan-marshall:phase_handshake` `script_internal_failure` drift reports (3-outline: `qgate_open_count` 2 -> 0; 1-init: `task_state_hash` + `unfinished_tasks_count` + `pending_findings_blocking_count`), which are the guard working as designed, and one `pyproject_build` failure that is a 15-second timeout invoking `manage-status get-worktree-path` through the worktree's own executor
