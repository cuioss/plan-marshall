# PLAN-LB-65: Enforcement that actually engages — R5 covers root sessions, the finalize gate reads the real plan state, the approval report reads the real database

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-65-lb-62-completion.md` and is queued as one row file,
> `queue/PLAN-LB-65.json`, in the epic ledger. This spec is SELF-SUFFICIENT.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the hand-off contract.

> Staged 2026-10-17 from the landing analysis of PLAN-LB-62 (#1790, `bd8ff3236`),
> `landings/PLAN-LB-62.md`: 0 met / 2 partial / 1 unmet. Its enforcement is inert on real data,
> and its R5 gate leaves root sessions unprotected. Critical and high only. Runs in the OpenCode
> runbook lane.
>
> **Each Done-when below is a test you write, see fail at `bd8ff3236`, then see pass, against the
> REAL layout:**
> - a real `status.json` written by `manage-status` (field `current_phase`), located where a real
>   plan keeps it;
> - a real `opencode.db` `permission` schema: `id, project_id, action, resource, time_created,
>   time_updated`.
>
> Never test against an invented layout.

## Objective

PLAN-LB-62 made R5, R6, the finalize commit gate and the approval report pass their own tests,
but:

- every phase reader reads `phase`, which no plan status carries (it is `current_phase`), and looks
  for plan state under the worktree, where none exists — so the commit gate and R6 never engage;
- R5 now applies only to sub-agents and worktree cwds, so a `/plan-marshall` root or a runbook-lane
  root in the main checkout runs `python3 -c` and ad-hoc scripts freely;
- the allow-list matches bare basenames by suffix, so `/tmp/x/permission_fix.py` runs anything;
- the approval reporter requires a decision column the live table does not have, so it never
  checks the real database.

## Deliverables

1. **R5 protects every session, and the allow-list is exact.**
   - R5 applies in every session in this repository — root sessions included, on both harnesses —
     except for the documented allow-list. The steward and wizard commands a consumer needs before
     any plan exists stay allowed through the allow-list, not through a context gate.
   - Allow-list entries match the **repository-relative path** of the script (resolved against the
     repository root), never a basename suffix. A path outside the repository never matches.
   - The executed guard.js tests (node harness) also refuse `python3 foo.py`, `python3 -u x.py` and
     `python3 -Ic "x"`.
   - The `marketplace/targets/generate.py` entry is removed, or its citation corrected; its cited
     line argues against direct calls.

   *Done when:* tests, each failing at `bd8ff3236`:
   - guard.js and the Claude hook, in a ROOT session with the cwd in the main checkout, refuse
     `python3 -c "x"`;
   - both refuse `python3 /tmp/x/permission_fix.py`;
   - both allow the documented `python3 marketplace/bundles/.../permission_fix.py` form;
   - guard.js refuses `python3 -u x.py`.

2. **The finalize commit gate and R6 read the plan's real phase.**
   - The phase comes from the plan's own `status.json` field `current_phase`, located via the
     main-anchored plan resolution the other `git-workflow` verbs use (the worktree path names the
     plan) — never from `<worktree>/.plan/local/plans`, and never "the first plan found".
   - An unresolvable phase is reported as `unknown`, and the commit verb then refuses source
     commits from a plan worktree (fail closed), while a runbook-lane worktree (no plan status) is
     identified as such and passes.
   - `--step` sanctions only the step ids of the plan's composed phase-6 manifest, not any
     non-empty string. `--phase` is not caller-settable in the commit verb.

   *Done when:* tests, each failing at `bd8ff3236`, using a status written by `manage-status`:
   - a plan in `6-finalize` committing source with no sanction through the verb is refused;
   - the same with a manifest step id passes;
   - `--step not-a-step` is refused;
   - raw `git commit` in that plan's worktree is refused by R6 on both harnesses;
   - a runbook-lane worktree commit passes.

3. **The approval reporter reads the live schema.**
   - A `permission` table with `action` and `resource` and no decision column is recognised:
     every row is a persisted allow. Rows are scoped to the project by `project_id` (resolved from
     the `project` table's worktree path).

   *Done when:* a test with the live schema and rows `('shell','grep *')` and `('shell','ls *')`,
   against a config denying `grep *`, reports the `grep *` contradiction. It fails at `bd8ff3236`
   (`schema_unrecognised`).

Split guard: three deliverables.

## Claim Labels

- OBSERVED: `guard.js:578` `data.phase`, `claude_pretooluse_hook.py:802` and `git-workflow.py:805` `data.get('phase')`; archived plan `status.json` files carry `current_phase` and no `phase` — orchestrator-checked.
- OBSERVED: `opencode_runtime.py:302` `_DECISION_COLUMNS = ('effect', 'decision', 'status', 'approval')`; the live table is `permission(id, project_id, action, resource, time_created, time_updated)` — orchestrator-read, 2026-10-16.
- OBSERVED: the R5 allow-list matching is "second token equals the entry, or ends with `/` + entry"; five entries are bare basenames (delegated agent).
- OBSERVED: guard.js R5 is applied only inside `inPlanContext` (sub-agent signal OR worktree workdir/root) (delegated agent).
- HYPOTHESIS: the steward bootstrap scripts a consumer runs before any plan exists are all covered by the allow-list once it matches by repository path — confirm with the doc sweep (verify at the start of D1).

## Expected Surface

- OBSERVED: `.opencode/plugin/guard.js` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/r5-allowlist.json` (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/_guard_node_harness.py` (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_guard_hook_parity.py` (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_claude_pretooluse_hook.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` (D2)
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` (D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D3)

## Dependencies and Sequencing

- Depends on: none. Critical: until it lands, R5 does not protect root sessions and the finalize
  commit gate does not engage.
- Overlaps with: PLAN-LB-64 (staged) on `opencode_runtime.py` (different functions).

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
