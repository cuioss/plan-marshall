# PLAN-LB-44: Red CI reaches triage, and a CI check is classed by what it ran

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-44-red-ci-triage-route.md` and is queued as one row file, `queue/PLAN-LB-44.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the Open Defect "Red CI has no triage route":
> - `lessons-routing-019.md`, `lb-25-phase-and-merge-gates-001.md`, lesson `2026-10-11-16-001`;
> - recurrences in `lessons-routing-028.md` items 153 and 189 (lesson `2026-10-11-07-001`).

## Objective

When CI goes red:

- `ci-verify` files its findings, and the dispatcher hands them to `verification-feedback` under a `ci-verify-*` producer that the workflow refuses with `unknown_producer`. Five plans had to route the failure by hand.
- The executor decides build versus policy from the workflow name, so a test workflow without a build word becomes a policy failure.
- A Sonar quality-gate failure inside a Maven job is filed as `ci_policy_failure` instead of being left to `sonar-roundtrip`.

This plan gives red CI one accepted triage route and classifies a failing check by what it ran.

## Deliverables

1. **`verification-feedback` accepts the CI producer, from one shared constant.**
   - `ci_verify.py` exports the producer value the dispatcher passes.
   - `verification-feedback.md` adds it to its single accept-set, with a Step 1 store-only branch over the pending `triage` findings that `ci-verify` filed (component `plan-marshall:phase-6-finalize`), then falls through to the shared INGEST and TRIAGE steps.
   - `ci-verify.md` (§ Notes, "one `verification-feedback` invocation per producer string") and `phase-6-finalize/SKILL.md` (L1039) state the one dispatch shape.
   - A contract test pairs every producer `ci_verify` can return with the accept-set.
   - The HEAD test that pins the `ci-verify-timeout` rejection is rewritten to the new rule.

   *Done when:* the contract test fails at HEAD — `ci_verify` returns `ci-verify-build` / `-policy` / `-missing` / `-timeout` / `-cancelled` / `-action-required` / `-stale`, and the accept-set holds none of them. A fixture red-CI dispatch reaches Step 1.4 instead of returning `unknown_producer`.

2. **A failing check is classed by what it ran.**
   - (a) The default flips: a failing check is `ci-verify-build` unless its workflow or job name matches a closed list of policy workflows (licence/CLA, dependency review, CodeQL, labels/title). An unknown name therefore fails toward a fix, not toward an "accept".
   - (b) When the manifest carries `sonar-roundtrip`, a failing check whose persisted job log shows a Sonar quality-gate failure is classed as row (a). It is filed as a `[ci_sonar_gate]` deferral to `sonar-roundtrip`, not as `ci_policy_failure`. A check that failed for any other reason in the same job stays a build failure.
   - The claim in `ci_verify.py` L115-117 and `ci-verify.md` L258-260, that projects override the match rule "via the architecture skill's config", is removed, because no such configuration exists.

   *Done when:* fixtures show:
   - an "Integration Tests" workflow failure classed as build;
   - a `license/cla` failure classed as policy;
   - a `build / sonar-build` job whose log carries the quality-gate failure classed as the Sonar deferral;
   - the same job with a compile error classed as build.

   At HEAD the first and third are policy.

Split guard: two deliverables, one surface (the `ci-verify` → `verification-feedback` route).

## Claim Labels

- OBSERVED: the accept-set is `build-runner, sonar, pr-comment, plugin-doctor, pr-state, finalize-feedback`. The Step 1 guard returns `error: unknown_producer` for anything else, and `ci-verify-timeout` is named as rejected on every path — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` L30, L57-68.
- OBSERVED: `ci_verify.py` declares seven producer strings — `ci-verify-missing`, `-build`, `-policy`, `-timeout`, `-cancelled`, `-action-required`, `-stale` (L120-127) — and returns them in `producers[]` on `needs_triage` (L732-744). `ci-verify.md` L275-280 says the dispatcher runs one `verification-feedback` per producer string. `phase-6-finalize/SKILL.md` L1039 routes red CI to `verification-feedback`.
- OBSERVED: `test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py` L13-20 pins the six-member accept-set, and L35-40 pins the `ci-verify-timeout` rejection — the HEAD test encodes the defect.
- OBSERVED: build versus policy is a substring match of `{'verify', 'quality-gate', 'module-tests', 'coverage'}` against the lower-cased workflow name, and anything else is policy — `ci_verify.py` `_BUILD_PROFILE_NAMES` L118, `_matches_build_profile` L165-175, `classify_check` L201-204. "Integration Tests" and "build / sonar-build" match none.
- OBSERVED: no configuration overrides the match rule. A content search for `_BUILD_PROFILE_NAMES` / `_matches_build_profile` finds only `ci_verify.py` and its tests, contradicting `ci_verify.py` L115-117 and `ci-verify.md` L258-260.
- OBSERVED: `ci-verify` findings are filed with `--type triage --component plan-marshall:phase-6-finalize` (`_run_manage_findings_add`, L381-408). Row (a) — Sonar is out of `ci-verify` scope — is documented at `ci-verify.md` L209 and L244-250.
- OBSERVED: `manage-ci-artifacts persist` writes one log per job under `artifacts/ci-runs/{run_id}/` before classification (`ci-verify.md` L282-290).
- HYPOTHESIS: the persisted job log carries a stable Sonar quality-gate marker (for example `QUALITY GATE STATUS: FAILED`) — confirm against the plan-06 log of lesson `2026-10-11-07-001` or a fresh Maven Sonar run (verify-at-outline). If no stable marker exists, narrow 2(b) to a name match plus a manifest-carries-`sonar-roundtrip` condition, and record the residue.
- Verify-first clause: choose one producer value (`ci-verify`, recommended) or the seven-member family. Do not ship both. The finding subtype tag in the title keeps the per-row distinction either way.
- Verify-first clause: before the edit, read PLAN-LB-26's landed `verification-feedback.md` and its return-field change, and keep the new branch outside its sections.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` — Producer modes table, Inputs, Step 1 guard, new branch (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` — shared producer constant, classification (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md` — taxonomy notes, dispatch shape (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the red-CI dispatch sentence at L1039 only (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md` — the producer vocabulary line (L19), only if it lists producers (verify-at-outline)
- OBSERVED: `test/plan-marshall/plan-marshall/test_verification_feedback_producer_vocab.py` (D1)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_core.py` (D2)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_ci_verify_cli.py` (D1, D2)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_ci_verify_reporting.py` — only if the producer list it asserts changes (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-26 (running).
  - Its spec declares `verification-feedback.md` as a HYPOTHESIS surface for its D3: the return fields its triage short-circuit reads.
  - Its spec also edits `plan-marshall/workflow/triage.md` (§ FIX task shape) and `execution.md`.
  - Its scope does not touch the producer accept-set, the Step 1 guard or `ci_verify.py`, so the overlap is one file in different sections.
  - Sequence after PLAN-LB-26 lands, so the second plan re-reads `verification-feedback.md` once.
- Overlaps with:
  - PLAN-LB-26 on `plan-marshall/workflow/verification-feedback.md`.
  - PLAN-LB-41 (staged) on `phase-6-finalize/SKILL.md`. PLAN-LB-41 documents the `review_support` modules; this plan changes the L1039 sentence — a different section.
  - None of the other four candidates.
- Adjacent to:
  - `triage.md` — the FIX / SUPPRESS / ACCEPT bodies are reused, not edited.
  - `sonar-roundtrip.md` — the owner of row (a); not edited.
  - `ci_complete_precondition.py` — the `consume-failures` envelope is unchanged.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-44-red-ci-triage-route.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
