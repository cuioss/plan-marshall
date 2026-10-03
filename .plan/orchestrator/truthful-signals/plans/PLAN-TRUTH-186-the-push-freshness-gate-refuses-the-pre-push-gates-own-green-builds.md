# PLAN-TRUTH-186: The push freshness gate refuses the pre-push gate's own green builds

epic: truthful-signals
workstream: WS-01

> ⛔ **DELIVERY-BREAKING EXCEPTION (operator-confirmed 2026-09-28).** Staged despite the PM-MCP supersession
> because every finalize today either pays a second full `verify` (~40 min) or halts at push. Keep it narrow.
> The implementation-independent invariant (D1) also belongs in PM-MCP's Implementation Watch
> (`plan-marshall-mcp/doc/implementation-watch/phase-workflows.adoc` / `job-runtime.adoc`) — the operator carries it.
> Source: `process-compliance` inbox `process-compliance-002` item 21 (from the PLAN-13 run, archived under
> `.plan/orchestrator/process-compliance/inbox/archive/plan-13-finalize-mechanism-defects/`); parked
> `PLAN-TRUTH-150` / `PLAN-205` carry the wider freshness family and stay parked.

## Objective

`pre-push-quality-gate` claims its just-completed builds are what satisfy `default:push`'s freshness
precondition. They cannot: `pre-commit-verify-freshness` credits only a single row whose canonical performs every
required analysis, so the gate's green quality-gate, test-compile and module-tests rows at the exact settled SHA
are each refused as `canonical_performs_too_few_analyses` and the verdict is `stale: build_scope_narrow`. Make the
freshness check credit the UNION of green build rows at one worktree SHA that together cover the required
analyses, so the gate's own runs are sufficient and no second `verify` is needed.

## Deliverables

0. **Gate — re-ground against HEAD.** Reproduce the refusal from the fixture shape below against
   `_freshness_crosscheck.py` as it stands; confirm no later change already admits a union. Re-scope if refuted.
1. **Union coverage at one SHA.** When no single row covers the required analyses, the check combines the green,
   non-killed, non-timed-out `kind=build` rows carrying the CURRENT worktree SHA (and the same module scope) and
   permits when their union covers every required analysis. Each contributing row is named in the verdict. Rows
   at another SHA, red rows, killed/timed-out rows and zero-test rows never contribute (the existing
   `_measured_zero_tests` and killed-row refusals keep their force).
2. **Honest refusal when the union falls short.** A refusal names the missing analyses (e.g. `test` not covered)
   and the rows it examined, instead of the blanket `build_scope_narrow`.
3. **Doc parity.** `pre-push-quality-gate.md` line 54's claim ("only this gate's just-completed builds can have
   written [the ledger row]") becomes true as written; `manage-tasks/SKILL.md` documents the union rule.
4. **Controls.** (a) quality-gate + test-compile + module-tests green at SHA X ⇒ fresh at X. (b) the same rows at
   SHA X, HEAD at Y ⇒ stale. (c) union missing `test` ⇒ refused, naming `test`. (d) one killed row among
   otherwise-covering rows ⇒ that row contributes nothing. (e) a single `verify` row still passes unchanged.

## Claim Labels

- OBSERVED: the refusal codes live in `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — `REASON_SCOPE_NARROW = 'build_scope_narrow'` (:257), `ROW_CANONICAL_TOO_WEAK = 'canonical_performs_too_few_analyses'` (:272), per-row judgement in `_row_refusal` (:504) and `scope_check_candidates` (:548), coverage requirement in `required_coverage` (:375).
  - verdict: corroborated | checked_at: 0a099a1071c1bc315d03d2d8008f74d89d0e29e0 | by: truthful-signals/cleanup | rescoped: n/a | evidence: All symbols at stated lines: REASON_SCOPE_NARROW :257, ROW_CANONICAL_TOO_WEAK :272, required_coverage :375, _row_refusal :504, scope_check_candidates :548.
- OBSERVED: the doc claim is at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:54` ("it permits on a `kind=build` ledger entry carrying the current worktree SHA, which only this gate's just-completed builds can have written for the settled tree").
  - verdict: corroborated | checked_at: 0a099a1071c1bc315d03d2d8008f74d89d0e29e0 | by: truthful-signals/cleanup | rescoped: n/a | evidence: pre-push-quality-gate.md:54 carries the quoted kind=build ledger-entry claim verbatim.
- HYPOTHESIS (run-reported, not re-verified by the sender): in PLAN-13's finalize all four gate arms were green on the exact tree (quality-gate ×2, test-compile, 28128-test module-tests) and freshness still refused with `stale: build_scope_narrow`, every row `canonical_performs_too_few_analyses` — confirm by constructing the same row set against `scope_check_candidates` (verify-at-outline).
  - verdict: unverifiable | checked_at: 0a099a1071c1bc315d03d2d8008f74d89d0e29e0 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Run-reported PLAN-13 outcome; confirming needs the same row set constructed against scope_check_candidates — D4 owns that fixture.
- HYPOTHESIS: the rows are evaluated one at a time with no aggregation step — confirm at `_freshness_crosscheck.py` § `scope_check_candidates` (verify-at-outline).
  - verdict: corroborated | checked_at: 0a099a1071c1bc315d03d2d8008f74d89d0e29e0 | by: truthful-signals/cleanup | rescoped: n/a | evidence: scope_check_candidates loops per-row _row_refusal (:595-601); each row must fully cover required (:530-539); no cross-row union of partial coverage.
- Verify-first clause: if HEAD already aggregates rows, re-scope to the doc/diagnostic half (D2/D3) only.
  - verdict: corroborated | checked_at: 0a099a1071c1bc315d03d2d8008f74d89d0e29e0 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Condition evaluated at HEAD: no cross-row aggregation exists, so the re-scope branch does not trigger.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — union rule (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — verdict/reason rendering (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — documented rule (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — line 54 claim (D3)
- OBSERVED: `test/plan-marshall/manage-tasks/` — controls, beside `test_pre_commit_verify_freshness*.py` (D4)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none among live rows (parked `PLAN-TRUTH-150` / `PLAN-205` / `PLAN-TRUTH-169` touch the same
  family but are not emittable).
- Adjacent to: `pre-push-quality-gate`'s own arm selection — untouched; the fix is on the crediting side.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-186-the-push-freshness-gate-refuses-the-pre-push-gates-own-green-builds.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other
ledger write — and reports its outcome through its PR and its inbox message. See
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
