envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-22T19:31:18Z

# Recurrence: phase-4-plan documents a `qgate add --type warning` form that argparse rejects (plan-marshall:phase-4-plan)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-22-demo-client-and-doc-leftovers (PR cuioss/API-Sheriff#512), inbox message plan-v02-22-demo-client-and-doc-leftovers-002.

Recurrence of the item in the lessons-archive index row listing 135, 136, 138, 139, 140, 143 ("phase-4-plan Step 8 `qgate add --type warning`"). In phase 4 of this plan the documented `manage-findings qgate add --type warning` call was rejected by argparse. The accepted form is `--type triage --severity warning`.

Suggested direction: correct the phase-4-plan SKILL.md example to `--type triage --severity warning`. The item is still open, so the example is still wrong in the version this plan ran on (0.1.1977).
