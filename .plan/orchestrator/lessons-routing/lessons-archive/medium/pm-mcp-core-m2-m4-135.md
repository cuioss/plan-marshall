envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:00Z

# automatic-review passes --required-bots to review_completeness trigger-bot, which does not declare it

Component (suggested): plan-marshall:automatic-review, category bug (marketplace-owned; belongs in the plan-marshall store)
Signal: script-failure cluster, notation plan-marshall:automatic-review:review_completeness

## Observation

Every automatic-review round of this plan logged the same argparse rejection (work log hash d36d85; occurrences at 07:04, 09:03, 10:11, 11:43, 12:31 on 2026-10-12, plus earlier rounds):

`--required-bots` is not declared for `review_completeness trigger-bot` (declared: newest-kind, plan-id, stale-bots); the flag exists only on the sibling verbs `check` and `deficit`.

The step still completed (outcome=done) each time, so the failure is recovered but repeats deterministically.

## Candidate directive

Fix the automatic-review workflow's `trigger-bot` invocation (drop `--required-bots` there, or declare it on `trigger-bot` if the verb needs it), and add the invocation to the argparse-surface contract test so a sibling-verb flag cannot be copied onto it again.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); work log d36d85.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-008.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
