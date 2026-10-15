envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:12Z

# Name the credentials script notation in the sonar prerequisites

## Context

Four sonar-roundtrip firings (13:06:39, 14:14:08, 14:53:23, 16:04:16) each ran `plan-marshall:manage-providers:manage-providers --help` just before `sonar fetch_findings`. Each call failed at exit 1 with "Invalid notation ... The third part 'manage-providers' appears to be a subcommand, not a script name. Correct format: plan-marshall:manage-providers:credentials". The calls did no harm, but each one is an invented notation that cost a call and an error line.

## Root cause

workflow-integration-sonar/SKILL.md § Prerequisites says only "Credentials configured via `manage-providers` for `workflow-integration-sonar`". The agent built a notation from the skill name each time. The plan-scoped script-failure-analysis aspect missed the failures because they are logged only in the global script log; log-analysis caught them in the folded-in global logs (GLOBAL_LOG_ERRORS 5).

## Proposed action

Write the full credentials notation and verb in the prerequisite (`plan-marshall:manage-providers:credentials ...`), or point to the canonical-invocation block of manage-providers. Also consider having script-failure-analysis read the folded-in global logs, so invented notations rejected by the executor (rather than by argparse) are counted too.

## Evidence

- log-analysis: global_log_signals error_count 5; 4 identical manage-providers notation errors in logs/script-execution-2026-10-13.log
- script-failure-analysis: total_failures 0 (plan log only), which shows the coverage gap

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-010.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
