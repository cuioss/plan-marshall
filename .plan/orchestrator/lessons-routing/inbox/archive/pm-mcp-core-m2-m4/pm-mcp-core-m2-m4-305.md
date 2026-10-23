envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:38Z

# Candidate lesson: manage-findings qgate - invented verb "query" and invalid --type warning

Source: script-failure cluster plan-marshall:manage-findings:manage-findings (6 occurrences)
Component (suggested): plan-marshall:manage-findings / phase-4-plan Q-Gate (foreign bundle - route to plan-marshall lessons inbox)

## What happened

1. 2026-10-17T19:54:00Z, 3-outline:
   `qgate query --plan-id ... --phase 3-outline --resolution pending` -> exit 2
   `unknown_verb query`; accepted: add, clear, list, resolve, resolve-by-rule,
   resolve-evidenced. The read verb is `list`.
2. 2026-10-17T20:35:54Z-20:35:58Z, 4-plan Q-Gate, five consecutive calls:
   `qgate add --phase 4-plan --source qgate --type warning --title "Description drift: TASK-N uses structural token ..."`
   -> exit 2 each; `--type` choices are bug, improvement, anti-pattern, triage,
   tip, insight, best-practice, build-error, test-failure, lint-issue,
   sonar-issue, arch-constraint, pr-comment, pr-comment-overflow. `warning` is a
   severity, not a type. All five "description drift" findings (TASK-1, 3, 4, 9,
   14 citing deliverable numerals like D2/D5) were therefore never recorded.

## Candidate rule

`qgate` reads with `list`, never `query`. `qgate add --type` takes a finding
type (use `triage` for a Q-Gate drift observation), never a severity. Separately,
the 4-plan "structural token" drift check flagged cross-reference numerals
(deliverable numbers) as drift - a likely false-positive class worth reviewing
in the mechanical check itself, since the agent judged each one "not a
regularized value".
