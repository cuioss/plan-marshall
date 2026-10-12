envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:22Z

# Lessons ingest: red CI has no triage route — verification-feedback refuses every producer ci-verify emits

Severity: high (graded at this ingest: the documented red-CI triage path is unreachable; backlog § 1.24 listed it as small). Bundle: `plan-marshall` (`phase-6-finalize/scripts/ci_verify.py`, `plan-marshall/workflow/verification-feedback.md`).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, four plans. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-003` | #18 | Red CI (Sonar gate); dispatch refused `unknown_producer`; findings waited for the unified triage. |
| `pm-mcp-core-m2-m4-024` | #20 | Same refusal for `ci-verify-policy`. |
| `pm-mcp-core-m2-m4-042` | #25 | Same. |
| `pm-mcp-core-m2-m4-103` | #29 | Same; dispatcher re-dispatched by hand with `producer=pr-state`. An "Integration Tests" workflow was classed `ci-verify-policy` rather than `ci-verify-build` because its name has no build token. |

Ground truth at `fc0090a24`: `ci_verify.py:121-125` emits `ci-verify-missing/-build/-policy/-timeout/-cancelled`; `verification-feedback.md` § Inputs and Step 1 guard accept only `build-runner, sonar, pr-comment, plugin-doctor, pr-state, finalize-feedback`. **Still present.**

Asked for: one shared producer constant for both sides, or a mapping at the ci-verify boundary; a contract test pairing every ci-verify producer with the accept-set; CI-check classification by what the job runs, not by name tokens.

Owner today: PLAN-LB-24 (`review-step`, running) — its declared surface includes `verification-feedback.md` and `test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py`. Check whether it closes this.
