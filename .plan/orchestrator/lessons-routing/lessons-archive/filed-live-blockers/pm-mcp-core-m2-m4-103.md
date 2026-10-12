envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:45Z

# ci_verify.py emits producer names that verification-feedback.md rejects as unknown_producer

## Observation

On the second ci-verify pass (CI red on the cold-start IT), ci-verify returned producer `ci-verify-policy`. verification-feedback.md's input guard accepts only `build-runner, sonar, pr-comment, plugin-doctor, pr-state, finalize-feedback` and rejected the dispatch as unknown_producer. The finalize dispatcher had to re-dispatch by hand with `producer=pr-state` (decision.log: "Tooling contract mismatch between ci_verify.py and verification-feedback.md").

Orchestrator-reported, not visible in the plan logs: the failing "Integration Tests" workflow was classified `ci-verify-policy` instead of `ci-verify-build` because its name carries no build token.

## Suggested direction

- Make the producer vocabulary one shared constant read by both ci_verify.py and the verification-feedback guard (or map `ci-verify-*` onto an accepted producer at the ci-verify boundary), and add a contract test that every producer ci_verify can emit is in the accept-set.
- Classify CI checks by what they run (job/step metadata or configured mapping), not only by name tokens, so "Integration Tests" lands in the build class.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-013.md` from plan runtime-lifecycle (PLAN-08, #29)
