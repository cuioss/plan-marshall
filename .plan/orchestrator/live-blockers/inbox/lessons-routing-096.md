envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-24T12:42:31Z

# finding (high, operator): phase-6-finalize refuses an inline-fix source commit with `no_sanction` because the triage and review-correction dispatches carry no manifest step id

**Severity:** high (operator-graded 2026-11-24). **Bundle:** `plan-marshall`, component `plan-marshall:workflow-integration-git` commit gate and the phase-6-finalize dispatches that call it.

**Ground truth (read at `3da9e1f44`, re-read by the orchestrator).** `git-workflow.py:533` sanctions a source-tree commit in 6-finalize on an exact membership test, `step in manifest_steps`; there is no normalisation of a bundle-prefixed id (`plan-marshall:automatic-review` against the bare manifest id). The refusal at `:564-581` is `no_sanction` and names the three routes (loop-back fix task, `--step` with a composed manifest step id, section-6 record) but not the ids it would accept. A triage or functional-review-correction inline fix runs as a dispatch that is given no owning step id, so the commit is refused and the caller has to improvise one of the routes. Drafting-leaf reading, not re-read by the orchestrator: no dispatch in `triage.md`, `verification-feedback.md` or the functional-review-correction path forwards the owning step id.

**Recurrence.** Six sources in three repositories: `libraries-initial-implementation-010`, `-063`; `client-framework-aspects-007`, `-012`; `pm-mcp-core-m2-m4-v2-035`, `-046`. Earlier archived lows: TokenSheriff `2026-11-10-09-001`, `2026-11-12-18-003`, graded low then because the guard is deliberate; the new evidence is that the dispatches themselves never obtain a sanction.

**Ask of `live-blockers`.** (1) Normalise `bundle:step` to the bare id, or refuse while naming the accepted ids in a structured error. (2) Forward the owning step id into the unified-triage, functional-review-correction and verification-feedback dispatches. (3) Document the sanction before the commit call in `triage.md` and `verification-feedback.md`. (4) Tests, including the prefixed-id negative control. Check first whether a staged `live-blockers` plan already owns the commit gate.
