envelope_version=1
sender_type=plan
sender_id=oc-lb-62-lb-56-completion
epic=live-blockers
kind=landing
created=2026-10-16T18:17:50Z

```landing-facts
schema=landing-facts/1
plan_id=oc-lb-62-lb-56-completion
epic=live-blockers
pr=#1790
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

# PLAN-LB-62 — report (supersedes oc-lb-62-lb-56-completion-001)

PR #1790 merged into `main` — merge commit `bd8ff323653563ee430c5965338a990196e2398d`.
Worktree removed, branch deleted, main checkout updated. All three deliverables
met and `verify`-green on the merged head `a6071ea2b`.

Commits: `c19fbdaf5` (D1), `9a3112ed5` (D2), `8a06fec20` (D3), `e64c0ef5a`
(verify follow-ups), `bbc89111d` (self-review round 1), `a6071ea2b` (PR-review
findings).

## 1. Deliverables

### D1 — R5 targets bypasses, not the repository's own workflows — MET

- (a) `test_guard_node_refuses_wrapper_and_versioned_interpreter` — guard.js
  executed under node refuses `timeout 5 python3 -c "x"` and `python3.12 -c "x"`.
- (b) `test_guard_node_allows_documented_non_executor_invocations` +
  hook `test_r5_allows_documented_sync_engine` / `test_r5_allows_absolute_executor`.
- (c) `test_guard_node_outside_context_allows_py_compile`; both wizard docs no
  longer document `python3 -m py_compile`.
- (d) `test_hook_writes_rule_r5_guard_log_line`.
- (e) `test_no_documented_invocation_is_refused` — 35 offenders before → 0 after.
- Artifacts: `.opencode/plugin/guard.js`; `claude_pretooluse_hook.py`;
  `pretooluse_gate.py`; `standards/r5-allowlist.json`. Commit `c19fbdaf5`.

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
  design: `event.agent` carries `execution-context`.
- HYPOTHESIS (D1): node is available in CI — CONFIRMED (runner image / CI).

## 3. Findings

- Self-review round 1 (9 findings): 6 fixed in `bbc89111d` (stale rule counts,
  deployed allow-list path, R4 `-m` coverage, `call=?` note); 3 recorded as
  accepted (settle-band `--step` is any non-empty id — dispatcher is the only
  caller and R6 forces the verb; the phase-6 dispatcher is an LLM flow, so prose
  + R6 is the wiring; enumeration recorded in the PR body).
- Self-review round 2: 0 Done-when failures; no new false docs.
- PR review (head `bbc89111d`, 7 inline comments): fixed in `a6071ea2b` — R6
  wrapper parity (`env git commit` now refused on both harnesses), the
  `env --split-string` bare form on both harnesses, the orchestrator import
  guard, two docstring/count drift items, plus wrapper-prefixed tests. The
  CodeRabbit `--step` roster-validation request is an accepted, documented
  deviation.
- CI on the merged head: `verify` green (merge-group run 38943334299, success).

## 4. Reviewers

- `cuioss-review-bot` — reviewed, COMMENTED (3 suggestions; 2 fixed, 1 answered
  as behaviourally equivalent).
- `coderabbit` — reviewed, COMMENTED (4 actionable + 3 nitpicks; actionables
  fixed).
- `sourcery` — refused (rate limit).
- Operator decision: the operator accepted proceeding with the merge with at
  least one review present ("there is at least one review. That is ok, so
  continue with merge"), rather than the two-bot re-review round.

## 5. Operator questions

One: whether to proceed to the merge with the current reviews — the operator
selected "continue with merge".

## 6. Rule check

All Section-1 rules kept, with ONE recorded exception: the runbook's merge gate
requires BOTH required reviewers on the current head; the operator explicitly
authorized merging before a second re-review of head `a6071ea2b` (`cuioss-review-bot`
reviewed `bbc89111d`; CodeRabbit reviewed `bbc89111d`). No other rule bent.

## 7. Residue

- The CodeRabbit `--step` roster validation is unimplemented by design (a
  hardcoded roster would risk stalling finalize for an unnamed mutating step);
  documented in the PR body. The `--step` sanction trusts the dispatcher as the
  sole caller and R6 forces the verb.
