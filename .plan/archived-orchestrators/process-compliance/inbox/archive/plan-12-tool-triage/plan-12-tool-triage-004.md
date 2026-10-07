envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-27T14:23:52Z

# phase-1-init Step 8d posture prompt text contradicts `lanes preview`

## Observed

The documented `AskUserQuestion` option descriptions in phase-1-init Step 8d say:

- full: "everything below plus a security review and a written look back at how the run went"
- standard: "build, review and merge as usual, with no security review and no write-up"

`manage-execution-manifest lanes preview --plan-id plan-12-tool-triage` shows
`plan-marshall:plan-retrospective` (the written look back) in ALL three postures — minimal, standard
and full. What full actually adds over standard is `finalize-step-security-audit`, `sonar-roundtrip`,
`adr-propose` and `lessons-capture`. The static prose therefore tells the operator a false cost/benefit
trade. The orchestrator wrote the descriptions from the preview data instead of the template.

Secondary: `lane_report_count: 25` while `full.phase_6_steps_count: 26` —
`plan-marshall:plan-retrospective` is missing from `lane_report[]`, so the per-step lane report does not
enumerate the full set it indexes.

## Suggested fix

Render the per-posture description from the `lanes preview` kept/dropped diff (it is already in the
payload) instead of static prose, and make `lane_report[]` cover every step that appears in any posture.
