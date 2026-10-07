envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:30Z

component=plan-marshall:phase-5-execute
category=bug

# canonical_verify.md names integration-tests as an orchestrator-tier candidate but omits it from canonicals:, making it unseedable as a phase-5 verification step

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-08-09-001` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-08-09-001`, created 2026-09-08, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Context

Observed in TokenSheriff plan `refresh-2a-coverage-priorities` (integration-test coverage work),
2026-09-08.

`plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` carries two statements that
contradict each other:

- **Prose (line 86)**: \"Long-running canonicals (full test suites, Docker cold-start
  integration-tests) are the prime candidates for this tier [`execution_tier=orchestrator`].\"
- **Frontmatter (`canonicals:`)**: lists only `quality-gate`, `module-tests`, `coverage`.

`_discover_all_verify_steps()` expands the `canonicals:` list — and nothing else — into the
`default:verify:{canonical}` step IDs that `manage-config plan phase-5-execute add-step` will
accept. So `default:verify:integration-tests` is refused with `missing_order`, and the canonical
the prose calls the *prime* orchestrator-tier candidate can never be seeded as a phase-5
verification step.

## Impact

A project whose architecture model resolves `integration-tests` correctly (TokenSheriff resolves it
to `verify -Pintegration-tests -pl <module> -am`, `bash_timeout_seconds: 887`,
`execution_tier: orchestrator`) still cannot put that command in `verification_steps`. Phase 5
then verifies integration-test work with a `verify` command that runs no ITs at all — the module
sets `skipITs=true` and declares failsafe executions only inside profiles — so the gate is green by
construction. That is the exact defect class the TokenSheriff `lessons-handling-26-09-04-01` epic
exists to close (PLAN-01 gate truthfulness, PLAN-12 gate cannot fail by construction).

## Directive

Add `integration-tests` (and consider `e2e`) to the `canonicals:` frontmatter list in
`canonical_verify.md`, so the discovery path can seed them. Both are already named in the step
body's own dispatch prose; only the machine-readable list is missing them.

Until that lands, the documented workaround is for the orchestrator to run the resolved
orchestrator-tier command directly at the end of phase 5, outside the manifest — which is where an
`execution_tier: orchestrator` command belongs anyway, since a dispatched leaf may not invoke one.
