envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T09:16:42Z

component=pm-dev-java:junit-core
category=improvement
bundle=pm-dev-java

# Two test-quality gaps that a review bot caught after the in-plan reviews passed: a hard-coded list mirroring production cases, and a boundary value that generated data almost never hits

Observed in PLAN-V2-40 (plan-v2-40-envelope-packing, PR #402). CodeRabbit raised two findings on the first push (4d163b inline, 3e61a3 review body); both were fixed in loop-back tasks 11 and 10 and verified.

1. `TaskCostEstimatorTest.LISTED_PROFILES` repeated the profile cases of `TaskCostEstimator.profileWeight`, and `unlistedProfile()` used that second set to pick inputs for the default-weight assertion. If production gains a case, the exclusion set drifts and admits an explicitly weighted profile. Fix: one `CONTRACT_PROFILE_WEIGHTS` map, used by the weighted-profile test (`@MethodSource`) and by the exclusion. The repository's coding rule already says a hard-coded list that must mirror a set defined elsewhere is a defect unless derived from that source.
2. `EnvelopeBudgetTest` tested the refusal of non-positive values only with generated negatives. Zero is the boundary and `Generators.longs(0, 1_000_000)` almost never yields it, so a regression that accepts zero would pass. Fix: a deterministic `refusesZero` test for each of the four inputs.

Why it matters: both were present in the first review round of the plan's own functional-review and code-review steps, which passed with advisories only. A generator-driven test suite needs an explicit check for each exact boundary (zero, empty, one) and for every list in a test that mirrors production.

Corrective action: add both checks to the test-review rules the code-review step cites (`junit-core`): "boundary values are tested deterministically beside generated ones" and "a test list that mirrors a production set is derived from it".
