envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:21Z

# Candidate lesson: ci_verify returns producer strings (ci-verify-policy, ci-verify-build, ...) that verification-feedback rejects as unknown_producer, so a red-CI triage can never run

- Component: plan-marshall:phase-6-finalize
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-11-07-001 (created 2026-10-11), epic pm-mcp-core-m2-m4

## Observation

plan-06-store-substrate (pm-mcp-core, PR 26): `ci_verify run` on red CI returned
`outcome: needs_triage` with `producers: [ci-verify-policy]` and filed 5 triage findings.
`ci-verify.md` says the dispatcher runs ONE `verification-feedback` per producer string.
The dispatched `verification-feedback` rejected it at its input guard:
`error: unknown_producer` — it accepts only `build-runner`, `sonar`, `pr-comment`,
`plugin-doctor`, `pr-state`, `finalize-feedback`.

So every red-CI path through ci-verify dead-ends; the findings had to be resolved by hand.

Second gap: the failure was only the SonarCloud quality gate surfaced through the
`build / sonar-build` job (sonar-maven-plugin `QUALITY GATE STATUS: FAILED`). Taxonomy row (a)
says ci-verify must not double-report the Sonar gate, but the classifier only recognises a
Sonar check by provider, not a Maven job that runs the Sonar scanner, so it filed 5
`ci_policy_failure` findings for one Sonar gate.

## Directive

- Register the ci-verify producer strings in verification-feedback's accepted producer set
  (or map them to an accepted producer at the ci-verify dispatch site), and add a contract test
  pinning the ci_verify producer vocabulary to verification-feedback's accepted set.
- Teach ci_verify to recognise a sonar-scanner quality-gate failure inside a build job
  (log line `QUALITY GATE STATUS: FAILED`) and defer it to sonar-roundtrip (row a).
