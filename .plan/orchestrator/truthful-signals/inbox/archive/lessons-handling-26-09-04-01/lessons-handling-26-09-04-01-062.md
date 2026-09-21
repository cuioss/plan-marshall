envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:53Z

component=plan-marshall:manage-execution-manifest
category=improvement

# verify:coverage is composed for a plan whose only change in the failing module is a test-resource deletion, and one JaCoCo failure fans out into five findings

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15). **Bundles two
inbox messages** (`-009` Q-Gate `ce93cd`, `-010` Q-Gate `caa91e`), which come from the same JaCoCo run.

⚠ **Only the plan-marshall half is relayed.** The Token-Sheriff half, `benchmarking-common`
coverage below the inherited 0.80 minimum and never enforced by CI, is staged in Token-Sheriff as
`PLAN-15-benchmarking-common-coverage-alignment` on the operator's decision. Do not fix the
consumer's thresholds from here.

## Observation

- The manifest composed `verify:coverage` into phase 5 (per task) for a plan whose only change in
  `benchmarking-common` was deleting an unreferenced `.log` test resource. The inherited coverage
  gate (`cui-java-parent` 1.7.4 profile `coverage`, BUNDLE INSTRUCTION and BRANCH ≥ 0.80) failed on
  standing debt: 0.70 instructions, 0.57 branches.
- This triggered a verification-feedback triage round-trip that ended "accepted, no fix task"
  (decision.log `4cbd9a`, `ade78c`). The same debt was accepted on an earlier plan
  (`full-review-adoc-documents`, 2026-07-16), so every plan that composes the step pays it again.
- **Fan-out:** one failing `jacoco-maven-plugin:check` became 2 Q-Gate findings (one per counter)
  plus 3 build-error findings for the same failure (decision.log `3dcaec`), five findings for one
  fact. That is before the six trailer-boilerplate false positives in relay `-060`.

## Candidate direction

- When composing `verify:coverage`, consider whether the plan changed **main code** in the modules
  the gate would fail on. A test-resource-only change cannot move a coverage ratio.
- Or let the coverage step recognize a recorded accepted baseline for a module and report
  "unchanged from accepted baseline" instead of failing.
- Deduplicate per check, not per counter or per producer: one failed `check` execution should be
  one finding with counters as detail.
