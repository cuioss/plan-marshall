envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:00Z

# Finalize ran nine review/fix rounds; each widened fix round drew new findings

Component (suggested): plan-marshall:phase-6-finalize (loop-back ceiling) and pm-mcp-core planning practice, category improvement
Signal: automatic-review outcome across rounds; decision log loop-back grants

## Observation

PR #30 went through about nine review/fix rounds (CodeRabbit, cuioss-review-bot, Sonar), past the 3-round loop-back ceiling, each extra round granted by the operator (decision log 5f59aa round 5, c7dfe9 round 6, b678d5 round 7, 2706fb round 8, 5016e1 round 9). Rounds 5 and 6 were deliberately widened ("fix everything", plus summary points: recovery wiring, policy checks before signing, cross-instance key race, atomic pair); each widened round produced code the next review found new defects in (round 7: e5704b, 2f1223; round 8: 53f5f7 on the round-7 fix; round 9: a8ae90). Only after the round-7 decision to record low/cosmetic findings instead of looping did the rounds shrink.

## Candidate rules

- Scope expansion during finalize (new wiring, new atomicity, new policy) is new feature work that restarts review; prefer a follow-up plan to widening a fix round.
- When granting rounds past the ceiling, state the exit criterion in the grant (as round 7 did: "afterwards low/cosmetic findings are recorded, not looped").
- Possibly for plan-marshall: surface the cumulative round count and the per-round new-finding count at each grant so the operator sees the trend.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); decision log entries listed above.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-007.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
