envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-30T05:35:57Z

# Recurrence: an operator-accepted weakened_test removal is re-raised as blocking at every later head, and the verifier refused a grading because of it (plan-marshall:phase-6-finalize weakened_test check)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-51-lane-conditional-guards (PR cuioss/API-Sheriff#538), inbox message plan-v02-51-lane-conditional-guards-001.

Recurrence of lessons-routing messages api-sheriff-api-sheriff-0-2-0-049 (an operator-accepted finding does not carry to the next head) and -062 (the weakened_test rows stay blocking). This run adds the variant where the removal is deliberate and the operator accepted it at the first prompt.

- Deliverable 1 removed `TlsEdgeActivationWiringTest.failsafeWiresMtlsSystemProperties` on purpose, replaced by the stricter per-lane `MtlsLaneSelectionContractTest`. The check flagged the 7 removed assertions; the operator accepted the removal.
- The same finding came back as a new blocking Q-Gate finding at every later head: functional-review 02cf35 (round 1), a876ff and ba4c05 (delta rounds), each re-closed as `accepted` with the same rationale; code-review 3422d9 and 643067, each marked taken-into-account.
- In one code-review round the verifier refused the grading (verdict_refused a94280) only because it read the accepted removal as mis-graded; its other findings were supported.
- Two delta rounds found nothing blocking apart from this finding, and each still needed its own accept-close.

Suggested direction (the plan's): key an operator-accepted weakened_test disposition to the removed test identity (the file plus the method, against the base), not to the reviewed head. Carry it forward as accepted while the removed set is unchanged, re-open it only for a different or larger removal, and tell the verifier about the carried acceptance so it does not refuse a grading because of it.

Evidence: Q-Gate findings 02cf35, 3422d9, a876ff, 643067, ba4c05, a94280; decision log 01c22b and bb669f, in plan-v02-51-lane-conditional-guards.
