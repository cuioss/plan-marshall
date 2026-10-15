envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:47Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-023.md
> NEW. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Code-review verdict refused: failure_class "none" on a fail-open finding

- Source: Q-Gate record 2d76ac (6-finalize, code-review-state, warning, verdict_refused), resolution `taken_into_account` (round 4 verifier accepted the grading at 77d2819).
- Suggested component: `plan-marshall:phase-6-finalize` (code-review workflow grading).

## Observation

The code-review author graded finding F2 (bbc237) with `failure_class: none`; the verifier refused the verdict because a keyless forged checkpoint making `verify()` answer Intact is wrong_result / fail_open. Grading, not the finding, decided the round.

## Candidate rule

A finding whose consequence is "the integrity check answers OK on tampered data" is fail_open by definition; the author's grading guidance should name that case so the verifier does not have to refuse it.
