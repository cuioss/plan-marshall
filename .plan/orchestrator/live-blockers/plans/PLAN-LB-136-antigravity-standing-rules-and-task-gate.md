# PLAN-LB-136: The project's standing rules reach an Antigravity agent, and the quality gate reaches each task's verification commands

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-136-antigravity-standing-rules-and-task-gate.md` and is queued as one row file, `queue/PLAN-LB-136.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the parked PLAN-LB-51 (D2 and D3; its D1, the native dispatch, is PLAN-LB-140).
> The operator ruled on 2026-10-12 that Antigravity issues are this epic's highest priority and on 2026-10-15 that the OpenCode plans
> come first; PLAN-LB-48, PLAN-LB-64 and PLAN-LB-83's successors (PLAN-LB-134 and PLAN-LB-135) are the OpenCode side. Every claim was
> re-grounded against `main` at `9cd644892` by a read-only leaf on 2026-11-09. **Each deliverable is its own outline deliverable, and
> each Done-when is its own success criterion. Do not merge them.** Every Done-when below fails at `9cd644892` unless it says
> "holds at". No Sonar. No token or measurement work.

## Objective

An Antigravity agent still gets a two-line stub as the standing-rules bridge with drift judged by file modification time, and its
target rules carry neither the build-command rule nor the no-plugin-prefix rule that the shared persona and the OpenCode rules carry.
The execution manifest stamps the quality gate per task, but phase 4 and the compose step put it only in the phase-level verification
steps, so no task's `verification.commands` contains it. This plan gives the Antigravity agent the project's rules and gives each task
its gate.

## Deliverables

1. **The Antigravity target rules carry both shared rules.**
   - `plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md` section 2 gains the two bullets the shared persona
     (`agent-behavior-rules.md` L193-205) and the OpenCode rules (`opencode-rules.md` L66) already carry: (a) build and format commands
     resolve through `architecture resolve`, never a guessed plugin; (b) `No plugin found for prefix …` means the project does not use
     that plugin: stop, never retry it fully qualified.

   *Done when:* each of these fails at `9cd644892`: a test in `test/plan-marshall/platform-runtime/test_antigravity_runtime.py`
   asserts `antigravity-rules.md` contains `No plugin found for prefix` and `architecture resolve` (the OpenCode sibling is pinned in
   `test_opencode_runtime.py`).

2. **The Antigravity bridge carries the repository's `CLAUDE.md` rules and drift is judged by content.**
   - `antigravity_runtime.py` `_write_rules_bridge` (L108-145) writes a heading plus a two-sentence stub (L119-124) and rewrites when
     the baseline is newer by modification time (L126-140); `standing_rules_drift_status` (L148-173) reports `baseline_newer`. The
     OpenCode bridge was converted to a content-hash bridge (`_SOURCE_HASH_PATTERN` L137, `_baseline_text`, `_bridge_body`,
     `_write_rules_bridge` L174-203, `standing_rules_drift_status` L206-236 in `opencode_runtime.py`), all module-private. The shared
     parts (`_baseline_text`, `_bridge_body(label, text)`, the hash pattern, the drift logic) move into `runtime_base.py` or a shared
     module with the harness label and `_rules_dir` as the only differences; both harnesses use the same file names and marker.
     Decide the module at outline and record why. The Antigravity bridge carries the full baseline and records `source-sha256:`;
     setup reports drift from what the write did and never `bridge_drift: false` for a bridge it just rewrote.
   - `antigravity-rules.md` L62 describes the marker and the content hash, not modification times.
   - Sequencing note: PLAN-LB-135 changes the OpenCode copy of these helpers (decode safety, the drift verdict). This plan lifts the
     helpers after that plan, or lifts the current form and the OpenCode plan follows the shared module; say which in the outline.

   *Done when:* each of these fails at `9cd644892`, in `test_antigravity_runtime.py`: a fresh Antigravity setup over a fixture with
   only `CLAUDE.md` containing a sentinel line yields a bridge that contains that sentinel and `source-sha256:`; touching the baseline
   newer with unchanged content reports `in_sync` (it reports `baseline_newer` at `9cd644892`); editing the baseline content reports
   drift; a doc test asserts `antigravity-rules.md` no longer describes modification-time drift. And this holds at `9cd644892` and
   must keep holding: a baseline that cannot be read keeps the existing bridge.

3. **The quality gate reaches each task's `verification.commands` when the manifest stamps it per task.**
   - Task `verification.commands` come only from `architecture derive-verification` (`phase-4-plan/SKILL.md` L594-602), whose closed
     mapping (`manage-architecture/standards/resolve-command.md` L235-240) emits only `compile`, `test-compile`, `module-tests`,
     `verify` or nothing; it never emits `quality-gate`. The gates go only into `manifest.phase_5.verification_steps`
     (`manage-execution-manifest/scripts/_manifest_rules.py` `_read_marshal_phase_5_gates`). `phase-4-plan/SKILL.md` L604 is prose
     only. `cmd_compose` already rewrites task verification (it annotates a task's command with `bash_timeout_seconds` through
     `_write_task` / `_read_task`), which makes compose the site to append the resolved gate per task. Decide at outline whether the
     compose step or phase 4 owns the synthesis and record why; the prose at L604 then states what the code does.

   *Done when:* each of these fails at `9cd644892`: composing with `project_gates: ['verify:quality-gate']` and a `per_task` stamp
   leaves every applicable task's `verification.commands` containing the resolved quality-gate executable (read with `_read_task`),
   in `test_manage_execution_manifest_compose_request_project_gates.py` using the fixtures of
   `_manage_execution_manifest_manage_execution_manifest_compose_fixtures.py`. And this holds at `9cd644892`: a manifest with a
   phase-level gate keeps it in `phase_5.verification_steps`.

Split guard: three deliverables. D1 is a two-bullet document change and ships first if the plan is split; D3 touches a different
skill family (the execution manifest) and splits off first for size.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The bridge is kept whenever its baseline cannot be read; setup reports what it did.
- One helper for the bridge: the shared module is imported by both runtimes; no copy.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture, are shown red where a Done-when says so.
- Executor regeneration only if a verb or a flag is added.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `antigravity_runtime.py` `_write_rules_bridge` L108-145 writes a heading plus a two-sentence stub with no `CLAUDE.md` content and rewrites by modification time (L126-140); `standing_rules_drift_status` L148-173 returns `baseline_newer` (L169-170); `antigravity-rules.md` L62 describes marker plus modification times — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py`
- OBSERVED: the OpenCode content-hash helpers are module-private in `opencode_runtime.py` (L137-236); `git log -S _bridge_body` touches only that file; the "OpenCode bridge" label is hard-coded at L159 and L166
- OBSERVED: rule (a) is at `persona-plan-marshall-agent/standards/agent-behavior-rules.md` L193-199 and rule (b) at L201-205 (added in `148558aa1`); `opencode-rules.md` L66 carries (b); `antigravity-rules.md` (63 lines) carries neither
- OBSERVED: `phase-4-plan/SKILL.md` L594-604; `resolve-command.md` L235-240; `test_manage_execution_manifest_compose_request_project_gates.py` L63-137 asserts only on `manifest['phase_5']['verification_steps']`; `test_manage_execution_manifest_compose_per.py` L13-30 shows `cmd_compose` annotating a task command
- HYPOTHESIS: the shared bridge module can live in `runtime_base.py` without a circular import with either runtime — confirm (verify-at-outline, D2)
- HYPOTHESIS: the compose step can resolve the quality-gate executable the way phase 4 resolves task commands (`architecture resolve`) — confirm (verify-at-outline, D3)
- Verify-first clause (D2): read PLAN-LB-135's state first and decide the lift order; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md` — section 2, L62 (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` — `_write_rules_bridge`, `standing_rules_drift_status` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — the bridge helpers lifted out (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — the shared bridge helpers (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — L594-604 (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_rules.py` and the compose script of that skill (D3)
- OBSERVED: `test/plan-marshall/platform-runtime/test_antigravity_runtime.py` (D1, D2)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` — the bridge tests that follow the lifted helpers (D2)
- OBSERVED: `test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_compose_request_project_gates.py` and `test/plan-marshall/manage-execution-manifest/_manage_execution_manifest_manage_execution_manifest_compose_fixtures.py` (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-64 (the separate bridge file, shipped).
- Overlaps with: PLAN-LB-135 and PLAN-LB-134 on `opencode_runtime.py` and `test_opencode_runtime.py` (D2 lifts helpers out of the OpenCode runtime), and PLAN-LB-140 on `antigravity_runtime.py`; sequence this plan after PLAN-LB-135, and PLAN-LB-140 after this plan.
- Adjacent to: the OpenCode target rules (not edited), the mapping and emitter of the Antigravity target (PLAN-LB-140).
- PLAN-LB-135 and PLAN-LB-134 are shipped and PLAN-LB-140 is shipped too, so the OpenCode helpers this plan lifts are the form on `main`
  now (a staged write that replaces the path, a `_BridgeWrite` result, strict decode, a drift verdict read from the write), not the form the
  line numbers above describe. Read `landings/PLAN-LB-135.md` in the ledger before the outline: its L1-1 (the writer turns any `OSError`
  into "nothing written", so an unwritable rules directory reads as a clean setup) and L1-6 (the Antigravity copy still catches only
  `OSError`, reads the drift status after the heal, and judges drift by modification time) are the defects the shared helper either
  carries or repeats. This adds no deliverable; the Standing Constraints "setup reports what it did" and "one helper for the bridge" apply
  to the lifted write, and the outline records how the shared writer reports a write that failed.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-136-antigravity-standing-rules-and-task-gate.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
