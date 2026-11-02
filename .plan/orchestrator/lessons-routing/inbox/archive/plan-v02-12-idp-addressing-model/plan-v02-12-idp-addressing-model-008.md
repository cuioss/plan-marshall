envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=finding
created=2026-10-20T20:30:09Z

# Recurrence: every finalize HEAD advance re-fires the review steps, and each round finds smaller nits in the previous round's fix (plan-marshall:phase-6-finalize verdict_inputs / loop-back re-fire)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492), lessons-capture step.

Recurrence of pending message api-sheriff-api-sheriff-0-2-0-034 ("a one-line fix loop-back re-fires the full review chain (verdict_inputs undeclared)"). Related: the self-review non-convergence pattern (operator rule: once a ceiling round yields only wording nits, fix and proceed without further rounds).

## Evidence

In this run every HEAD advance during finalize re-fired four review steps. Each review round reported smaller nits located in the code the previous round's fix had just written, and fixing those advanced HEAD again. Review cost therefore multiplied with the number of fix rounds instead of converging.

## Suggested direction

Beyond the `verdict_inputs` scoping already proposed in 034: scope a re-fired review to the delta since its last verdict, and add a convergence rule (e.g. stop re-firing when the previous round's findings were all below a severity floor), so fix-of-fix rounds cannot cascade.
