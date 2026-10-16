# PLAN-LB-62: Finish session-boundary enforcement — R5 refuses bypasses, not the repository's own workflows; the finalize commit gate is wired

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-62-lb-56-completion.md` and is queued as one row file,
> `queue/PLAN-LB-62.json`, in the epic ledger. This spec is SELF-SUFFICIENT.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the hand-off contract.

> Staged 2026-10-16 from the adversarial landing analysis of PLAN-LB-56 (#1781, `bd40e2420`),
> `landings/PLAN-LB-56.md`: 0 met / 2 partial / 1 unmet. R5 now refuses documented workflows in
> every OpenCode session, including the steward and `/sync-harnesses`. Runs in the OpenCode
> runbook lane. **Each deliverable is its own deliverable, and each Done-when is met as written.
> Do not merge or reword them.** "Fails at `bd40e2420`" is evidenced only by a run against that
> tree.

## Objective

R5 was meant to close the interpreter side door used to rewrite verdicts and run ad-hoc scripts.
Instead it:

- has no plan-context gate on OpenCode;
- refuses the repository's documented `python3` invocations (steward bootstrap, wizard
  `py_compile`, executor recovery, harness sync) and contradicts `opencode.json`;
- still lets `timeout 5 python3 -c …` through.

The finalize commit gate (D2) exists only as an uncalled function.

## Deliverables

1. **R5 targets bypasses, not the repository's own workflows.**
   - **Context gate.** guard.js applies R5 under the same plan-context gate as the Claude hook
     (`claude_pretooluse_hook.py` `evaluate`, :658) — a dispatched sub-agent, or a cwd under
     `.plan/local/worktrees/`. Choose and document the OpenCode signal for "sub-agent". The two
     decision tables are made identical: quoting-aware tokenisation and case handling.
   - **Allow-list.** One declared allow-list of documented non-executor invocations, sourced from
     the enumeration below and shared by both harnesses (one data file, read by guard.js and the
     hook). Candidates:
     - `python3 marketplace/targets/sync.py`, `generate.py`;
     - the `.claude/skills/{sync-harnesses,finalize-step-sync-plugin-cache}/scripts/*.py`;
     - the steward bootstrap scripts;
     - `generate_executor.py generate`;
     - an absolute or relative path ending in `/.plan/execute-script.py`.

     Each entry cites the documenting line. Whether `python3 -m py_compile` stays refused is
     decided at outline; if refused, rewrite the wizard steps to a documented alternative.
   - **Wrappers.** `timeout`, `nice`, `nohup`, `time`, `xargs`, `env -S` and versioned
     interpreters (`python3.12`) are stripped or recognised before matching, in both harnesses.
   - **Logging.** The Claude hook appends the same `guard.log` line as guard.js.
   - **Enumeration first.** List every documented `python`/`python3` invocation in `marketplace/`,
     `.claude/`, `.opencode/`, `doc/`, `AGENTS.md` and `CLAUDE.md`, and record it in the PR before
     changing either guard.

   *Done when:* tests, each failing at `bd40e2420`:
   - guard.js, executed (not grepped — run its hook function under node or an equivalent
     harness), refuses `timeout 5 python3 -c "x"` and `python3.12 -c "x"`;
   - both guards allow `python3 marketplace/targets/sync.py --target opencode` and
     `python3 /abs/repo/.plan/execute-script.py a:b:c verb`;
   - guard.js outside a plan context allows `python3 -m py_compile f.py`, or the wizard no longer
     documents it (whichever the outline chose);
   - the Claude hook writes a `rule=R5` guard.log line;
   - a doc-sweep test finds no documented invocation that the guards refuse.

2. **The finalize commit gate is wired into the commit path.**
   - `source-commit-gate` (`git-workflow.py:680`, predicate at :463) runs at the point every plan
     commit passes through: the `git-workflow` commit verb and the pre-commit seam the finalize
     steps use. A raw `git commit` of source files in phase `6-finalize` is refused by the guard
     (a guard rule, both harnesses).
   - The sanction is the documented one: an open loop-back fix task, or a `loop_back` to
     `6-finalize` per `review-rubric.md` §6. The phase-6 settle-band commits (lessons-housekeeping
     promotion, simplify, security-audit, quality-gate autofix) are recognised by their step,
     not by magic words in a finding.
   - It judges the staged commit, not the dirty tree. A refusal is an error exit, not
     `status: success, allowed: false`.

   *Done when:* tests, each failing at `bd40e2420`:
   - a finalize-phase `git commit` of a source file with no open fix task is refused through the
     real commit path;
   - a §6 loop-back correction commit passes;
   - a quality-gate autofix commit from the settle band passes;
   - a `.plan/`-only commit passes;
   - a refusal exits non-zero.

3. **The stale-approval report reaches the operator where it matters.**
   - The reader (`opencode_runtime.py:1277`) checks the real `opencode.db` permission-table
     schema — read the live schema, read-only — and returns `checkable: false` for an
     unrecognised one, never a clean result.
   - It also checks `agents.*.permissions` and the global `~/.config/opencode/opencode.json`.
   - It runs at plan start (the `orchestrator preflight` / phase-1 health path), and the runbook
     lane's equivalent (an executor verb the runbook can call), not only at first steward setup.
     Its output appears in the call's result, not only on stderr.

   *Done when:* tests, each failing at `bd40e2420`:
   - a fixture with the live schema and an `allow` for `ls` against a global deny is reported;
   - an unrecognised schema returns `checkable: false`;
   - the plan-start call carries the report in its result.

Split guard: three deliverables, each finishing one PLAN-LB-56 deliverable.

## Claim Labels

- OBSERVED: guard.js has no plan-context gate (`guard.js:313-401`); the Claude hook gates in `evaluate` (:658) (delegated agent; orchestrator-checked).
- OBSERVED: R5 refused `python3 marketplace/targets/sync.py` twice in PLAN-LB-56's own finalize (2026-10-16T06:20:58Z, 06:23:04Z) and the absolute-path executor call of PLAN-LB-61 (08:50:17Z) — `.plan/temp/guard.log`.
- OBSERVED: `opencode.json:182, 341` allow `python3 marketplace/targets/sync.py *` — orchestrator-read.
- OBSERVED: `source-commit-gate` appears in no file outside `git-workflow.py` and its test — orchestrator-checked.
- OBSERVED: documented refused invocations — `marshall-steward/SKILL.md:99, 106, 120, 126`; `wizard-flow.md` 12 sites; `upgrade-flow.md:75, 255`; `tools-script-executor/SKILL.md:319, 523-530, 566, 580, 661`; `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md:141, 244, 291, 297`; `.claude/skills/sync-harnesses/SKILL.md:108, 181, 204`; `.opencode/commands/sync-harnesses.md:37, 73, 86` (delegated agent).
- OBSERVED: `test_opencode_enforcement.py` R5 tests grep guard.js source only (delegated agent).
- HYPOTHESIS: OpenCode exposes a signal distinguishing a sub-agent session from the root (`parent_id` in `opencode.db`, or an env var in the shell) — confirm before choosing the gate (verify at the start of D1).
- HYPOTHESIS: node is available in CI to execute guard.js in a test — confirm in `python-verify.yml`; otherwise a JS-free equivalent must exercise the same decision table (verify at the start of D1).

## Expected Surface

- OBSERVED: `.opencode/plugin/guard.js` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_pretooluse_hook.py` (D1, D2)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_enforcement.py` (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_claude_pretooluse_hook.py` (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/` — the shared allow-list data file (verify at start) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md` — only if `py_compile` stays refused (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` (D2)
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_git_workflow_format.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` (D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — preflight surfacing (verify at start) (D3)
- OBSERVED: `doc/developer/test-impl-mapping.adoc` — remove the false row added by PLAN-LB-56 (D1)

## Dependencies and Sequencing

- Depends on: none. High priority: R5 blocks the steward, executor recovery and `/sync-harnesses`
  in every OpenCode session.
- Overlaps with: PLAN-LB-48 (staged) on `opencode_runtime.py`; PLAN-LB-50 (running) on
  `opencode_runtime.py`. The gate will ask.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
