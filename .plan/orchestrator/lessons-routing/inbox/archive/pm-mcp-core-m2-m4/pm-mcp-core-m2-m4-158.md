envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:51Z

# Candidate lesson: manage-solution-outline get-deliverable called with `--number`

- Component: plan-marshall:manage-solution-outline
- Suggested category: anti-pattern
- Signal: script failure cluster (argparse_rejection, 2 occurrences, phase 5-execute)

## Evidence

- work.log 2026-10-12T17:11:13Z and 17:11:14Z: script_failure notation=plan-marshall:manage-solution-outline:manage-solution-outline
  exit_code=2: "`--number` is not declared for ... get-deliverable: ['deliverable-number', 'plan-id']".

## Suggested correction

The flag is `--deliverable-number`. Find where `--number` is suggested (task or execute workflow
prose) and fix it.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-008.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
