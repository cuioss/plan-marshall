envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T05:50:09Z

# Candidate lesson: Wording-only advisory rounds keep moving the head and re-firing every head-dependent review (phase-6-finalize review loop)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-45-request-body-and-h2-buffer-bounds (PR cuioss/API-Sheriff#506), source message 012.

RECURRENCE of api-sheriff-api-sheriff-0-2-0-034 (a one-line fix loop-back re-fires the full review chain).

In PLAN-V02-45's finalize, five rounds of late Javadoc/doc wording corrections (threat model, validation matrix, ADR amendment, Javadoc) each moved the head; each head move made the head-dependent verdicts (simplify, security-audit, functional-review, code-review) stale and re-fired them, and the code-review round again produced only wording advisories. The run broke the loop by applying the last advisories as one Javadoc-only inline correction and recording that the pushed tree differs from the reviewed tree by that commit alone.

Candidate rule: once a review round yields only wording-level advisories, apply them as one inline correction and record the residual tree difference instead of re-running every head-dependent review on a docs-only head move; better, let a docs-only delta keep code-review/security verdicts valid (verdict_inputs).
