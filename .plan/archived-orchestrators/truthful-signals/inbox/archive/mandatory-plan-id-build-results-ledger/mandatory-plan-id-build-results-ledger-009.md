envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:28:10Z

## Finding: Sonar's `count_status: confirmed` cannot distinguish "analyzed and clean" from "never analyzed"

**Observed in**: main, during finalize of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.

### What was observed

The `sonar-roundtrip` finalize step recorded:

```text
new-code issues: 0 (confirmed)
```

The evidence available at the same moment says SonarCloud had **no analysis of PR #1075 at
all**:

- the PR-decoration endpoint returned **404** for PR 1075;
- there has been **no CE (compute engine) task since 2026-06-29**;
- there is **no sonar workflow in the repository** to trigger one.

The producer nevertheless returned a **confirmed** zero.

### Why it matters

This is the textbook instance of this epic's theme. `count_status: confirmed` is doing
exactly the job a confidence discriminator exists to do — it exists to tell a consumer
"this zero is trustworthy" — and it is asserting trustworthiness over a measurement that
was never taken. A zero from an absent analysis is not a low number, it is **no number**.

Three separate absence signals were available and none of them demoted the verdict. That
is the important part: the fix is not "check one more thing", it is that the producer has
no representation for *unmeasured*, so every absence necessarily collapses into the
`confirmed`-zero branch.

### Relationship to the other findings in this batch

Same archetype as `scope_creep_check`'s `residual_count: 0` derived from
`reason: no_baseline_sha` (also in this batch). Both are "a count of zero that means
*did not count*". They should probably be fixed under one rule rather than as two
independent patches — the shared defect is that a measurement producer lacks an
`unmeasured` / `undecidable` state.

### Suggested shape of a fix (not implemented)

- Add an explicit `count_status: unmeasured` (or `unavailable`) branch and return it
  whenever the analysis backing the count cannot be located.
- Treat a 404 on PR decoration, an absent CE task, and an absent triggering workflow as
  **positive evidence of unmeasured**, not as an empty result set.
- Audit consumers: any consumer that reads `confirmed` as "safe to proceed" must handle
  the new state explicitly rather than defaulting it to green.
