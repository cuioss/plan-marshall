envelope_version=1
sender_type=plan
sender_id=truth-168-sync-defaults-reverting-remove
epic=process-compliance
kind=finding
created=2026-10-02T06:54:46Z

## Follow-up process-rule frictions from TRUTH-168 repair loop

Second follow-up to truth-168-sync-defaults-reverting-remove-001, covering
frictions encountered while repairing the finalize bypass.

### 8. ci-verify producer string rejected by verification-feedback guard
`ci_verify run` on red CI returns `producers: [ci-verify-build]` with the
contract that the dispatcher runs ONE verification-feedback invocation per
producer string. The verification-feedback input guard accepts only
build-runner, sonar, pr-comment, plugin-doctor, pr-state, finalize-feedback
and returned unknown_producer for ci-verify-build. No mapping from taxonomy
producer strings to the accept-set is documented in either skill, so the
red-CI triage path dead-ends at the guard. Workaround in use: triage via
producer=pr-state. Request: either widen the accept-set or document the
taxonomy-to-producer mapping at the ci-verify call site.

### 9. Targeted pytest runs are guard-blocked on this target
The R4 guard refuses any pytest invocation outside the build wrapper, and
the wrapper offers no file-scoped pytest surface, only whole-bundle
module-tests. The bundle suite needs about twenty minutes; the daemon caps
around 330 seconds and in-process runs exceed the host call ceiling. There
is therefore no sanctioned way to re-run the four touched test files after
a settle-band edit on this target. Partial suite evidence plus CI as the
authoritative runner is the workaround in use.

### 10. Pre-existing red baseline from a verify-skipped steward landing
PR 1677 landed a top-level runtime key in committed .plan/marshal.json
while its verify job was skipped by the docs-only footprint gate. The
canonical-order test table was never updated, so main has been red on
test_committed_marshal_json_top_level_keys_already_canonical since. The
repair is carried on this plan's branch as drive-by scope. Request: make
the footprint gate treat .plan/marshal.json as a buildable change, or gate
steward artifact landings on verify regardless of footprint.
