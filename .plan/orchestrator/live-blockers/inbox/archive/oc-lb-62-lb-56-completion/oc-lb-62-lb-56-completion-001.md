envelope_version=1
sender_type=plan
sender_id=oc-lb-62-lb-56-completion
epic=live-blockers
kind=landing
created=2026-10-16T17:26:47Z

```landing-facts
schema=landing-facts/1
plan_id=oc-lb-62-lb-56-completion
epic=live-blockers
pr=#1790
merge_state=open
cleanup_owed=true
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:partial,merge:blocked
```

# PLAN-LB-62 — report

Branch `fix/lb-62-lb-56-completion`, PR #1790. All three deliverables are
implemented, tested (fail-then-pass), and `verify`-green on head `a6071ea2b`.
The PR is NOT merged: the last push advanced the head past both reviewers'
reviews, and completing the required re-review + merge cycle needs a further
session (see Residue).

Commits: `c19fbdaf5` (D1), `9a3112ed5` (D2), `8a06fec20` (D3), `e64c0ef5a`
(verify follow-ups), `bbc89111d` (self-review round 1), `a6071ea2b` (review
findings).

## 1. Deliverables

### D1 — R5 targets bypasses, not the repository's own workflows — MET

- (a) `test_guard_node_refuses_wrapper_and_versioned_interpreter` — guard.js
  executed under node refuses `timeout 5 python3 -c "x"` and `python3.12 -c "x"`.
- (b) `test_guard_node_allows_documented_non_executor_invocations` +
  hook `test_r5_allows_documented_sync_engine` / `test_r5_allows_absolute_executor`.
- (c) `test_guard_node_outside_context_allows_py_compile`; and both wizard docs
  no longer document `python3 -m py_compile`.
- (d) `test_hook_writes_rule_r5_guard_log_line`.
- (e) `test_no_documented_invocation_is_refused` — 35 offenders before → 0 after.
- Guard: `.opencode/plugin/guard.js`; hook/`pretooluse_gate.py`; shared
  `standards/r5-allowlist.json`. Commit `c19fbdaf5`.

### D2 — the finalize commit gate is wired into the commit path — MET

- `test_source_commit_gate_commit_path.py` — 0 passed / 6 failed at baseline →
  6 passed: refused-through-the-verb (a), section-6 loop-back passes (b),
  settle-band `--step` passes (c), `.plan/`-only passes (d), refusal exits
  non-zero (e). Guard R6 on both harnesses refuses a raw `git commit` in
  `6-finalize`. Commit `9a3112ed5`.

### D3 — the stale-approval report reaches the operator — MET

- (a) `test_reporter_global_deny_catches_persisted_allow` (baseline `0 == 1`);
  (b) `test_reporter_unrecognised_schema_is_checkable_false` (baseline
  `True is False`); (c) `test_preflight_carries_persisted_approval_report`
  (baseline `KeyError: 'persisted_approval'`). Commit `8a06fec20`.

## 2. Hypotheses

- HYPOTHESIS (D1): OpenCode exposes a sub-agent signal — CONFIRMED as the gate
  design: `event.agent` carries `execution-context` (guard.js `inPlanContext`;
  probed live in this session).
- HYPOTHESIS (D1): node is available in CI — CONFIRMED: CI `OpenCode Generation
  Gate` and the runner image list Node.js; tests execute guard.js under node.

## 3. Findings

- Self-review round 1 (9 findings): 6 fixed in `bbc89111d` (stale rule counts,
  deployed allow-list path, R4 `-m` coverage, `call=?` note). 3 recorded as
  accepted: settle-band `--step` is any non-empty id (the dispatcher is the only
  caller and R6 forces the verb); the phase-6 dispatcher is an LLM flow (prose +
  R6, no script); enumeration recorded in the PR body.
- Self-review round 2: 0 Done-when failures; no new false docs.
- PR review (cuioss-review-bot + CodeRabbit, head `bbc89111d`): 7 inline
  comments. Fixed in `a6071ea2b`: R6 wrapper parity (`env git commit`),
  `env --split-string` bare form (both harnesses), orchestrator import guard,
  two docstring/count drift items, and wrapper-prefixed tests. Replied/left for
  the next session: the CodeRabbit `--step` validation request (rationale above).

## 4. Reviewers

- `cuioss-review-bot` — reviewed `bbc89111d` (COMMENTED, 3 inline suggestions);
  2 fixed, 1 (second-token) answered as behaviourally equivalent.
- `coderabbit` — reviewed `bbc89111d` (COMMENTED, 4 actionable + 3 nitpicks);
  actionables fixed in `a6071ea2b`. Its included-review allowance shows 0
  remaining, so a re-review may need the 90-minute wait policy.
- `sourcery` — refused (rate limit: review budget exhausted).

## 5. Operator questions

None asked.

## 6. Rule check

All Section-1 rules kept. Two deviations, both recorded: for D2/D3 the tests
were written after the implementation and the baseline was captured by
disabling the change in the worktree (the surfaces are the pre-change code);
D1's baseline is byte-identical at `bd40e2420`.

## 7. Residue

- Re-trigger both required reviewers on head `a6071ea2b`, handle any new
  comments, re-run `verify`/CI on the head, then merge and clean up.
- CodeRabbit's requested `--step` roster validation (accepted deviation,
  documented in the PR body).
