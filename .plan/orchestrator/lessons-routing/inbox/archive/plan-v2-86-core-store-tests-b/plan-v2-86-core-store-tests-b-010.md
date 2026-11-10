envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:30:07Z

# script-failure-analysis classes a deliberate gate refusal (exit 1) as a script-internal bug

- component: plan-marshall:plan-retrospective:script-failure-analysis
- category: bug
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

The one script_internal_error the retrospective's script-failure-analysis aspect reports (manage-status transition, exit 1, 2026-11-05T21:37:08Z) is the designed transition refusal execute_commits_unrecorded for a formatting commit that had no change-ledger row. The decision log shows it as a gate outcome that was resolved by appending a ledger row. Grading it as a bug with an empty stderr excerpt is a false positive. The aspect should recognise structured refusal payloads, or the exit code a gate uses, as a refusal class separate from internal errors.

Evidence: retrospective fragment-script-failure-analysis findings row 4; decision log entry babaf1 of 2026-11-05T21:37:26Z. Not verified by the reporting agent: the script-execution.log entry itself.
