envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T05:55:19Z

# Call shapes are guessed instead of read: three invented flags or verbs in one plan

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-20-cookie-key-file-model (PR #527), candidate lessons 011, 012 and 014. Observed with plugin and executor 0.1.2010.

## Observation

Each case is an argparse rejection caused by a call shape the caller invented:

- `manage-solution-outline get-deliverable --number N`, rejected twice within 16 minutes in 5-execute. The declared flags are `--deliverable-number` and `--plan-id`. The rejection text already lists the right flag, yet the same paraphrase recurred, which suggests the call shape comes from prose.
- `plan-marshall:build-maven:maven resolve-test-scope`, a verb that does not exist (registered: check-warnings, coverage-report, discover, parse, rewrite-log, run, run-config-key). The caller fell back to `architecture resolve --narrow-unit`, which worked.
- `manage-config effort resolve-target --step-id ...` from a finalize dispatch; the accepted flags are apply, caller, default, field, phase, plan-id, role, workflow, workflow-gated.
- `manage-findings qgate list` without `--phase`. `lessons-capture.md` tells the orchestrated branch to read Q-Gate findings across five phases but shows no invocation, so a whole-plan call without `--phase` is the natural first try and is rejected; the caller then needs five calls.

## What to consider

- Grep the workflow prose for `get-deliverable --number` and any `resolve-test-scope` mention, and align the text with the declared surface.
- Show the per-phase `qgate list --phase` loop in `lessons-capture.md`, or let `qgate list` without `--phase` return every phase.
- Do not give `effort resolve-target` a step-id flag; the step is identified by role and workflow.
