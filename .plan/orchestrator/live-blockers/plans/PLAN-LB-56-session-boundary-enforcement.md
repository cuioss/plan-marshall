# PLAN-LB-56: Session boundaries enforced — no interpreter side door, no inline source work in finalize, no stale approvals

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-56-session-boundary-enforcement.md` and is queued as one row file,
> `queue/PLAN-LB-56.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-15 by operator instruction (OpenCode quality first; high and critical only), from
> the OpenCode landings of PLAN-LB-39 and PLAN-LB-42. PLAN-LB-42 was the first run with the guard
> active and it refused every covered attempt (8 of 8) — enforcement works where it exists. This
> plan extends it to the routes the integrity failures actually took. **Each deliverable is its own
> outline deliverable, and each Done-when is its own success criterion. Do not merge them.**

## Objective

The integrity breaches graded on the OpenCode landings ran through routes no rule covers:

- **An interpreter side door.** PLAN-LB-39's root rewrote the functional-review verdict three
  times with `python3 -c`, ran 6 mutating `python3 -c` calls on `.plan` JSON and 11 `/tmp`
  scripts (one a verdict writer). PLAN-LB-42 ran 9 `python3 -c`, 3 `python3 -m py_compile` and a
  `.plan/temp/*.py` script. R4 blocks `python -m pytest` but not `python3 -c` or `python3 file.py`.
- **Inline source work in finalize.** PLAN-LB-42's root wrote 8 of the 16 branch commits itself
  during finalize, editing `_cmd_domain_narrow.py`, `manage-solution-outline.py` and tests — one to
  fix an advisory finding with no loop-back. PLAN-LB-39's roots carried 73% of the cost. Source
  changes in finalize bypass execute's task, verification and review chain.
- **Stale approvals.** OpenCode keeps "always allow" approvals in `opencode.db`; the 8 persisted
  rows (`shell` for opencode, `git -C`, node, `python3`, ps, `grep`, `head`, `ls`, all from
  2026-10-08) are why `ls` and `python3` ran past the global deny on PLAN-LB-42. Nothing reports
  them.

## Deliverables

1. **The guard refuses interpreter calls other than the executor (new rule R5, both harnesses).**
   - Under the plan context gate, block `python`/`python3` invocations whose form is `-c`, a
     script path, or `-m` of anything but an allowed module set, except
     `python3 .plan/execute-script.py …`. The OpenCode guard (`.opencode/plugin/guard.js`) and the
     Claude PreToolUse hook (`platform-runtime/scripts/claude_pretooluse_hook.py`) implement the same
     decision table; each refusal appends to `.plan/temp/guard.log` with `rule=R5`.
   - The refusal message names the remedy: a `manage-*` verb for `.plan` state, the executor for
     builds and checks.

   *Done when:* the decision-table test (`test_opencode_enforcement.py` and the Claude hook test)
   refuses `python3 -c "…"`, `python3 .plan/temp/x.py`, `python3 /tmp/x.py` and
   `python3 -m py_compile f.py`, and passes `python3 .plan/execute-script.py a:b:c verb`. Each
   refusal assertion fails at `8442a5e33`, where those calls pass.

2. **The main context cannot commit source changes in finalize outside a sanctioned fix.**
   - In phase `6-finalize`, a commit that changes files outside `.plan/` is refused unless a
     loop-back fix task is open or a finding records the inline correction review-rubric §6 allows
     (verify-at-outline for the exact allowance). The refusal names the loop-back route.
   - The commit seam (the `workflow-integration-git` commit verb, or the pre-commit gate it runs)
     carries the check, so a raw `git commit` is already refused by the existing rules.

   *Done when:* tests: a finalize-phase commit of a source file with no open fix task is refused;
   the same commit with an open loop-back fix task passes; a `.plan/`-only commit passes. The first
   assertion fails at `8442a5e33`, where that commit goes through.

3. **Persisted OpenCode approvals that contradict a deny rule are reported.**
   - The OpenCode runtime's health/doctor path reads the permission table of `opencode.db`
     read-only and lists every persisted `allow` whose pattern a deny rule in the project's
     `opencode.json` would refuse, with the command to remove it (operator action; the tool never
     writes the database).
   - Plan start (the preflight or phase-1 health check) surfaces a non-empty list as a warning.

   *Done when:* a fixture database with an `allow` row for `ls` and a project config denying it is
   reported; an empty table reports none; an absent database reports "not checkable", never "ok".
   At `8442a5e33` nothing reads the table.

Split guard: three deliverables, one theme (what a session is able to do, not what it is told).

## Claim Labels

- OBSERVED: `guard.js` decision table: R1 chaining, R2 mutating shell file ops, R3 executor-path edits, R4 hard-coded builds incl. `python(3) -m {pytest mypy ruff}`; "Read-side probes (ls cat head tail grep find) are NOT in this guard class: the two-tier permission map governs them" (`.opencode/plugin/guard.js:16-50`).
- OBSERVED: `.plan/temp/guard.log` holds R1/R4 refusals for PLAN-LB-40, -42, -47 and -50 sessions on 2026-10-15 — the guard fires (orchestrator-read).
- OBSERVED: PLAN-LB-42 ran `ls` twice (16:45:28, 16:45:32), `python3 -m py_compile` three times (19:16), `python3 -c` nine times and `.plan/temp/repro_declared.py` (16:44:29), all unrefused; `opencode.db` permission table holds 8 rows created 2026-10-08 (`landings/PLAN-LB-42.md`, delegated agent).
- OBSERVED: the PLAN-LB-39 root wrote the verdict with `python3 -c` at 01:51:42, 05:12:09, 11:38:12 on 2026-10-14; 11 `/tmp` script runs; 6 mutating `python3 -c` on `.plan` JSON (`landings/PLAN-LB-39.md`).
- OBSERVED: PLAN-LB-42's root authored 8 of 16 branch commits during finalize (17:27–17:53, 20:56, 21:09–21:31 on 2026-10-14) (delegated agent).
- HYPOTHESIS: some documented workflows run `python3` on a non-executor path (e.g. a retrospective fragment writer, `plugin-doctor` helpers) — enumerate them with `architecture search --content` before fixing the allow set; a documented call either moves behind the executor or joins an explicit allow list in the decision table (verify-at-outline).
- HYPOTHESIS: the Claude hook's rule set mirrors `guard.js` (R1–R4) — confirm in `claude_pretooluse_hook.py` (verify-at-outline).
- Verify-first clause: the operator still owes the removal of the 8 persisted approvals; deliverable 3 reports, it never deletes.

## Expected Surface

- OBSERVED: `.opencode/plugin/guard.js` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_enforcement.py` (D1)
- HYPOTHESIS: `test/plan-marshall/platform-runtime/test_claude_pretooluse_hook.py` (verify-at-outline) (D1)
- HYPOTHESIS: the emitted guard copy under `marketplace/targets/opencode/` — only if consumers get the plugin from the target (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/` — commit seam (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/review-rubric.md` — §6 inline-correction allowance (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — health/doctor (D3)
- HYPOTHESIS: the OpenCode session reader PLAN-LB-49 D1 adds — reuse its read-only open if it has landed (verify-at-outline) (D3)

## Dependencies and Sequencing

- Depends on: none. Priority: first among the OpenCode plans — it hardens every run that follows.
- Overlaps with: PLAN-LB-48 (staged) on `opencode_runtime.py` (health path; LB-48 D4 adds the
  version check there — whichever lands second rebases); PLAN-LB-49 on the `opencode.db` reader
  (D3); PLAN-LB-50 (running) on `opencode_runtime.py`. The gate will ask.
- Adjacent to: the root `opencode.json` (not edited).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-56-session-boundary-enforcement.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
