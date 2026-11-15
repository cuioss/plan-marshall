envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-security-hardening-tier-1
epic=lessons-routing
kind=finding
created=2026-11-09T11:45:56Z

# Recurrence: verdict_currency classify invalidates every head-dependent finalize verdict (verdict_inputs_undeclared)

Recurrence of the live lessons-routing message `api-sheriff-api-sheriff-0-2-0-079.md` (same root cause, a second plan, with measured cost).

Source: API-Sheriff epic `security-hardening-tier-1`, inbox message `plan-sec-03-pending-authorization-store-fairness-002.md` (plan `plan-sec-03-pending-authorization-store-fairness`, PR cuioss/API-Sheriff#581, 2026-11-09).

## Observation

On every HEAD advance during phase-6-finalize, `phase-6-finalize:verdict_currency classify` returned `verdict: invalidated` with `reason: verdict_inputs_undeclared`, because no head-dependent settle-band step declares a `verdict_inputs` surface. Every head-dependent step re-fired after each loop-back or settle commit.

Measured re-fire counts in this one plan: `finalize-step-simplify` 15, `finalize-step-security-audit` 15, `functional-review` 7, `code-review` 7, `pre-push-quality-gate` 6. Most re-confirmed an unchanged verdict on a diff that did not touch their inputs.

## Why it matters

- The classifier is fail-closed by design (correct), but with zero adopters the "preserved" path is unreachable, so the mechanism buys nothing.
- The cost compounds with the per-source loop-back budget: each admitted round re-runs the whole settle band, including the two most expensive dispatched reviews.

## Suggested correction (from the reporting plan)

- Declare `verdict_inputs` on the head-dependent steps where the superset bar can honestly be met (verdict-currency.md names which families must not declare one), starting with the steps whose re-fire count dominates.
- Have `refire-report` surface `verdict_inputs_undeclared` as the dominant re-fire cause, so the gap is visible per plan.
