# PLAN-23: Push-boundary evidence that a clean checkout can reproduce

> ✅ **Staged 2026-09-29 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-23-push-boundary-evidence.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make the evidence that admits a push, and the waits that follow it, describe the commit being pushed.
Three observed failure modes:
- A green whole-tree `module-tests` arm (28,361 tests) admitted a push that CI then failed twice on the
  same SHA. The local population came from untracked, generated `target/` state that a clean checkout
  does not have.
- A pre-push gate whose four arms all went green on the exact tree still could not satisfy the freshness
  gate it anchors (`build_scope_narrow`).
- Every wait on a ~25-minute CI run returned a timeout verdict while nothing had failed.

## Deliverables

1. **Green evidence is refused when the tree differs from a clean checkout.** When the worktree carries
   untracked or ignored generated state under a path a tracked test scans (here `target/`, left by
   `./pw generate --target opencode`), the pre-push gate refuses a green verdict, or builds on a
   clean-checkout-equivalent tree. Two gates reading one contaminated input are one witness, not two:
   say so in the gate contract. Regression test: generated state present and the scanning test green
   locally → refused; clean tree → admitted.
2. **The documented clean verb resets generated trees.** `build-pyproject clean` does not remove generated
   target trees, so the sanctioned cleanup could not have reset the state that caused (1). Make it
   remove them, or document the verb that does and call it from the gate.
3. **The quality gate's own rows satisfy the freshness gate it anchors.** `pre-push-quality-gate.md`
   claims its just-completed builds are what make `default:push`'s freshness precondition pass. Yet
   with all four arms green on the exact tree (quality-gate ×2, test-compile, a 28,128-test
   module-tests run), `pre-commit-verify-freshness` refused `stale: build_scope_narrow`, because every
   row is `canonical_performs_too_few_analyses` and only a single `verify` row is accepted. The
   pipeline therefore always pays a second full `verify` (~40 min). Either the gate runs `verify`, or
   freshness accepts the union of rows at one SHA that together cover compile, lint and test. Take the
   union only once (1) guarantees the rows describe a clean tree.
4. **A wait lapse on a live run is "still pending", not a verdict.**
   - (a) `ci_complete_precondition` clamps its wait to 569 s, below the harness ceiling, while this
     repo's `verify` job takes ~25 min. The first two waits returned `wait_failed / ci_final_status:
     timeout` with every check IN_PROGRESS and none failed, which ci-verify would classify as
     `ci_timeout` findings for triage. A non-terminal in-progress run resolves to "pending, re-wait",
     with a documented bounded re-wait loop.
   - (b) `await-long-running.md` forbids backgrounding or sleeping the daemon build wait, yet every
     orchestrator-tier build (745–1437 s budgets) exceeded the harness's 600 s per-call ceiling, so
     the harness backgrounded it anyway. Give the build client a bounded wait below the ceiling, with
     an explicit re-poll.

## Claim Labels

- OBSERVED: local green (28,361 tests) vs CI red twice on the same SHA, caused by untracked generated `target/` — cited at `inbox/archive/opencode-bootstrap-executor-fix/opencode-bootstrap-executor-fix-003.md` § What happened; the sender's remedy is corroborated on PR #1646's branch (`python-verify.yml:66 pre-verify-goals: 'generate'`, new `test/plan-marshall/plan-marshall/test_target_tree_foundational_skill_freshness.py`, PR checks now green)
- HYPOTHESIS: `build-pyproject clean` does not remove generated target trees — confirm/refute at `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py` § the `'clean'` command mapping (line 564) and the `clean` script in `pyproject.toml` (verify-at-outline)
- OBSERVED: four green arms, freshness refused `build_scope_narrow` / `canonical_performs_too_few_analyses` — cited at `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-004.md` § 21; the same refusal is a recorded operator hazard ("never `--force` the freshness gate")
- OBSERVED: ci-complete wait clamp and timeout-verdict-on-pending — cited at `plan-13-…-004.md` § 22; `ci_complete_precondition.py` carries a harness-ceiling clamp (`clamp_state`, lines 20 and 50–52 at HEAD)
- OBSERVED: the build-wait rule cannot be honoured under the 600 s harness ceiling — cited at `plan-13-…-004.md` § 5

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — gate contract (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — freshness acceptance (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — row coverage (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/` — clean verb (D2)
- OBSERVED: `pyproject.toml` — `clean` script (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_complete_precondition.py` — wait clamp and pending resolution (D4a)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md` — bounded build wait (D4b)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/` — client wait bound (D4b)
- OBSERVED: `test/plan-marshall/manage-tasks/` — freshness tests
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — gate and wait tests

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-20 / PLAN-21 (`test/plan-marshall/phase-6-finalize/`), PLAN-19 (`manage-tasks/`). Check the gate. The opencode-bootstrap-executor-fix plan's PR #1646 (open) is adjacent: it adds the CI-side `generate` pre-goal, and this spec adds the local gate half. Emit after #1646 lands.
- Reclaimed from truthful-signals: items 5, 21 and 22 were routed there on 2026-09-28 (`truthful-signals/inbox/process-compliance-002`), but their target specs PLAN-TRUTH-169, PLAN-TRUTH-150 and PLAN-205 are parked under the PM-MCP supersession, so no plan would act on them. They are owned here.
- Scope-bloat guard: 4 deliverables.

## Folded inbox material (same act)

- `opencode-bootstrap-executor-fix-003.md` (finding; envelope repaired 2026-09-29 on operator instruction): deliverables 1, 2
- `plan-13-finalize-mechanism-defects-004.md` items 5, 21, 22 (reclaimed from the dead-end routing): deliverables 3, 4

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-23-push-boundary-evidence.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
