envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T05:55:18Z

# Finalize re-fires every head-dependent step after a small or review-only HEAD advance

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-20-cookie-key-file-model (PR #527), candidate lessons 008 and 009. Observed with plugin and executor 0.1.2010.

## Observation

1. `finalize-step-simplify` and `finalize-step-security-audit` re-fired on every HEAD advance with `verdict_currency=invalidated/verdict_inputs_undeclared`, including advances that only corrected documentation after the functional review (6e1f0ed0 to 1996696e, 91eea903 to 1996696e). A CodeRabbit inline-fix commit (documentation wording plus Java) then looped finalize back and re-fired all head-dependent steps. Functional review closed at three different HEADs and code review ran at two.
2. The operator closed code review by override (review not converging) and directed "run only build + quality gate before push" for the two fix commits. The push went through. At branch-cleanup the pre-merge HEAD binding refused with `merge_candidate_not_gated`: security-audit and simplify were bound to the earlier head and functional-review to an older one. A full functional-review round (round_kind=full, six deliverables) plus simplify and security-audit had to be re-run at the final HEAD, about an hour after the override.

## What to consider

- Let `finalize-step-simplify` and `finalize-step-security-audit` declare their verdict inputs (for example the production Java path set) so a HEAD advance that touches only documentation or tests keeps their verdict current.
- When the operator narrows the re-fire set, either record that narrowing as a HEAD-bound waiver for the named steps, or make the override prompt say up front that the pre-merge barrier still demands every head-dependent step at the final HEAD. The refusal after the push is the costliest point to learn it.
- A delta re-check over a review-only or documentation-only change should be able to satisfy the binding instead of forcing a full round whenever the delta "spans all deliverables".
