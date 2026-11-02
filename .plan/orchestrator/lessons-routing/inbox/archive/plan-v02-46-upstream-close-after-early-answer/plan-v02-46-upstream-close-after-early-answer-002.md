envelope_version=1
sender_type=plan
sender_id=plan-v02-46-upstream-close-after-early-answer
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T18:04:11Z

# Candidate lesson: a scope-criterion wording sweep found more copies in every Q-Gate pass instead of all at once (plan-marshall:plan-marshall Q-Gate / phase-3-outline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-46-upstream-close-after-early-answer (PR cuioss/API-Sheriff#513, merge e70743f), lessons-capture step.

Related, not identical: api-sheriff-api-sheriff-0-2-0-039 (q_gate_validation=once leaves outline findings pending) and api-sheriff-api-sheriff-0-2-0-018 (outline consumer sweep missed consumers).

## Observation

With `q_gate_validation=once`, every validation pass found further copies of the same incorrect wording ("reset frees the connection"): 3 copies at outline, 2 more at plan, and 1 more at execute. Each pass fixed only the copies it happened to see, so the same finding class came back three phases in a row.

## Why it matters

When a Q-Gate finding is about a wording or claim that can recur across the corpus, fixing only the reported instance leaves the rest for a later phase, where it costs more and may slip past `once` validation entirely.

## Suggested direction

When a Q-Gate finding names a wording/claim defect, the resolution should require an exhaustive sweep for that wording over the whole affected surface (outline, specs, affected docs) in the same pass, and record the sweep pattern and hit count on the resolution so the next pass can verify it was complete.
