# PLAN-LB-51: Antigravity fidelity — the deliverables PLAN-LB-39 did not ship

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-51-antigravity-fidelity-completion.md` and is queued as one row file,
> `queue/PLAN-LB-51.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Re-staged from the adversarial landing analysis of PLAN-LB-39 (#1768, `c8adaf178`),
> `landings/PLAN-LB-39.md` § Deliverable Fidelity. PLAN-LB-39 counted these done; they are not.
> The operator ruled on 2026-10-12 that Antigravity issues are this epic's highest priority.

## Objective

The Antigravity-specific half of PLAN-LB-39 (its D1, D3, D4) did not ship: generated Antigravity
documents still carry a bare `Task:` line with no native dispatch, the standing-rules "bridge" is a
two-line stub with no `CLAUDE.md` content, the no-plugin-prefix rule exists nowhere, and the
quality gate still lands in the phase-level list instead of per-task verification. This plan ships
them, each against a fixture that fails at `c8adaf178`. Grade each deliverable against THIS spec's
Done-when text; an outline that rewrites a Done-when must say so and why.

## Deliverables

1. **Generated Antigravity phase-5 documents name the native sub-agent mechanism.**
   - The Antigravity target maps the phase-5 dispatch sites (`Task: plan-marshall:execution-context-{level}`
     in `phase-5-execute`, `execute-task`, `plan-marshall/workflow/execution.md`, and the
     `verification-feedback` dispatch) to `invoke_subagent` with the resolved level, through
     `marketplace/targets/antigravity/mapping.json` / its emitter — today `Task:` is `preserve`
     (`mapping.json:43-46`).
   - A harness with no sub-agent mechanism runs an envelope inline only through an explicit
     `dispatch_mode: inline` branch that writes one dispatch-boundary row per envelope.
   - OpenCode's mapping (`Task` → `subagent`) is PLAN-LB-48 D2's; do not duplicate it here.

   *Done when:* a fixture generates the Antigravity target and asserts each named dispatch site
   reads `invoke_subagent` with a level and no bare `Task:` line; a test runs one inline-mode
   envelope and reads one boundary row. Both fail at `c8adaf178`.

2. **The project's standing rules actually reach a non-Claude agent.**
   - The bridge file (separate from `plan-marshall-target-rules.md` — PLAN-LB-50 D1) carries the
     rules of the repository's `CLAUDE.md`, generated from it, with drift detected by content
     (a hash of the source recorded in the bridge), not by mtime. Setup reports drift before it
     heals, and never reports `bridge_drift: False` for a bridge it just rewrote.
   - The base persona AND the Antigravity target rules carry both rules: (a) build and format
     commands resolve through `architecture resolve`, never a guessed plugin; (b) `No plugin found
     for prefix …` means the project does not use that plugin — stop, never retry it fully
     qualified. Rule (b) is absent everywhere at `c8adaf178`.

   *Done when:* a fresh Antigravity setup over a fixture with only `CLAUDE.md` yields a bridge that
   contains a sentinel line from that `CLAUDE.md`; editing `CLAUDE.md` makes setup report drift; a
   doc test finds rule (b)'s text in the persona and the Antigravity target rules.

3. **The quality gate reaches each task's `verification.commands`.** When the execution manifest
   stamps the gate per task, phase 4 synthesizes it into every applicable task's
   `verification.commands`, not into the phase-level `phase_5.verification_steps` (where
   PLAN-LB-39 put it; `phase-4-plan/SKILL.md:604` is prose only).

   *Done when:* a fixture manifest with a `per_task` gate yields tasks whose
   `verification.commands` contain the gate; fails at `c8adaf178`.

Split guard: three deliverables.

## Claim Labels

- OBSERVED: `marketplace/targets/antigravity/mapping.json:43-46` — `"Task:": {"disposition": "preserve", "note": "Leaf-aware: dispatcher prose is descriptive and preserved."}` (orchestrator-read).
- OBSERVED: PLAN-LB-39's diff touches nothing under `marketplace/targets/` (`git show c8adaf178 --stat`).
- OBSERVED: `antigravity_runtime.py:120-150` `_write_rules_bridge` body is a heading plus one sentence; drift compares `CLAUDE.md` mtime to the bridge mtime (orchestrator-read).
- OBSERVED: a content search for "No plugin found" in `marketplace/` returns 0 at `c8adaf178` (delegated agent); rule (a) is at `persona-plan-marshall-agent/standards/agent-behavior-rules.md:193`.
- OBSERVED: the stamp goes to `phase_5.verification_steps`; no fixture for per-task synthesis (delegated agent).
- HYPOTHESIS: the `platform-runtime subagent dispatch` seam carries no resolved level and never passes `spawning_tool_available`, so the inline no-op branches (`antigravity_runtime.py:999`, `opencode_runtime.py:1388`) are unreachable — confirm before wiring D1 (verify-at-outline).
- Verify-first clause: read PLAN-LB-50's landing first (bridge file path) and PLAN-LB-48's D2 state (OpenCode mapping) before outlining.
- Out of scope: OpenCode tool names (PLAN-LB-48), harness detection under OpenCode 2 (PLAN-LB-48 D4), the harness/model stamp (PLAN-LB-45), the harness-agnostic criteria and gate integrity (PLAN-LB-52).

## Expected Surface

- OBSERVED: `marketplace/targets/antigravity/mapping.json` (D1)
- HYPOTHESIS: `marketplace/targets/antigravity/emitter.py` (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — inline branch (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/` — task synthesis (verify-at-outline) (D3)
- HYPOTHESIS: `test/marketplace/targets/antigravity/` — generated-text fixture (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_antigravity_runtime.py` (D1, D2)
- HYPOTHESIS: `test/plan-marshall/phase-4-plan/` — per-task gate fixture (verify-at-outline) (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-50 (bridge file path, D2). Read PLAN-LB-48's state for the OpenCode side.
- Overlaps with: PLAN-LB-50 on `antigravity_runtime.py`; PLAN-LB-48 on the targets tree (other
  target).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-51-antigravity-fidelity-completion.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
