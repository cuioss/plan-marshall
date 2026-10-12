envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:05Z

# phase-4-plan Step 8 prescribes qgate add --type warning, which manage-findings rejects

Component (suggested): plan-marshall:phase-4-plan, category bug (marketplace-owned)
Signal: plan-retrospective, 4-plan leaf report; manage-findings qgate argparse rejections in script-failure-analysis (26 occurrences, subcommand qgate, first 2026-10-11T14:34:09Z)

## Observation

The 4-plan leaf reported that Step 8 prescribes `manage-findings qgate add --type warning` for the description-token check, but `warning` is not an accepted `--type` value (the accepted set is bug, improvement, anti-pattern, triage and others), so the warning-only finding was not emitted and the omission was only logged. The 3-outline Q-Gate leaf separately had `--component` rejected with `invalid_component` when it passed a deliverable title. The script-failure aspect shows 26 exit-2 rejections of `manage-findings qgate` in this plan; the stderr was not captured, so which call sites account for them is not established here.

## Candidate directive

Align the phase-4-plan Step 8 example with the `qgate add --type` choices (or add the value), and capture stderr for argparse rejections of `manage-findings qgate` so the 26-call cluster can be attributed to its call sites.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); 4-plan and 3-outline Q-Gate leaf reports.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-017.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
