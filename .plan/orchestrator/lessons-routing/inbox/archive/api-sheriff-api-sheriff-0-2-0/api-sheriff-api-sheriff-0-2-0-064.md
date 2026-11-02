envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-25T22:12:13Z

# Recurrence: every fix loop-back re-fires simplify, security-audit, the functional review and the code review at full scope (plan-marshall:phase-6-finalize loop-back re-entry)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-27-test-simplification (PR cuioss/API-Sheriff#520), inbox message plan-v02-27-test-simplification-003.

Recurrence of lessons-routing messages api-sheriff-api-sheriff-0-2-0-034, -043, -049 and -054. Measured cost in this run, from the plan's decision log and execution manifest:
- simplify and security-audit ran 4 times (the initial run plus 11:48, 17:07 and 20:12), including after wording-only and Javadoc-only fixes.
- The functional review ran 3 full rounds plus 1 delta round (481k, 399k and 394k tokens; 970 s and 699 s on two of them). The code review ran 1 full round (482k tokens) and 1 delta round (289k tokens).
- Most later rounds re-raised only the 11 already-refuted `weakened_test` rows (see -062), so they bought little new signal. The operator skipped the closing full round.

Suggested direction (as in the earlier messages, now with numbers):
- After a loop-back whose fix commits touch a bounded path set, default the re-fired reviews to delta rounds over the new commits.
- Let simplify and security-audit skip when the fix delta holds no production source, or sits in a path class already cleared at the prior HEAD.
- Treat "the same blocking set as last round, all operator-accepted" as a convergence signal that ends the loop.
