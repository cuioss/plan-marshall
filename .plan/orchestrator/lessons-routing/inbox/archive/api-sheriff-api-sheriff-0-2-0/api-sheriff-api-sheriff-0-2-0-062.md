envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-25T22:12:12Z

# Recurrence: the weakened_test check reads git renames and planned duplicate removals as lost assertions, and keeps the rows blocking after the verifier refutes them (plan-marshall:phase-6-finalize review_support)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-27-test-simplification (PR cuioss/API-Sheriff#520), inbox message plan-v02-27-test-simplification-001.

Recurrence of lessons-routing messages api-sheriff-api-sheriff-0-2-0-036 and -048 (a moved test class reads as a loss). This run adds two things the earlier messages did not carry.

- The same 11 blocking `weakened_test` rows came back in every functional-review and code-review round. 3 were class moves that git itself reports as renames (R087, R088, R094 in the merged diff). 8 were planned duplicate removals whose assertions had first been carried into the surviving tests.
- The review verifier wrote verdicts saying the rows do not hold ("moves/dups relocated"), and the rows stayed blocking. Each round closed only by operator override. The rows reached `reobserved_count` 4 and added several review rounds.

Suggested direction:
- Compare an old path with its git rename or copy target before counting assertions as gone (as -036 said).
- Let a deliverable or outline declare a planned dedup (removed test plus its surviving counterpart) and have the check honour it.
- Once a verifier has refuted a blocking finding with evidence, an identical re-observation in the next round should not reopen it as blocking.
