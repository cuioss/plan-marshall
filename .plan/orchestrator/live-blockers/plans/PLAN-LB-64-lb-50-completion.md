# PLAN-LB-64: The standing-rules bridge gets its own file, and harness setup always installs enforcement

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-64-lb-50-completion.md` and is queued as one row file,
> `queue/PLAN-LB-64.json`, in the epic ledger. This spec is SELF-SUFFICIENT.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the hand-off contract.

> Staged 2026-10-16 from the landing analysis of PLAN-LB-50 (#1777, `a95e88f21`),
> `landings/PLAN-LB-50.md`: its D1 was implemented backwards and its conflict resolution made the
> steward skip installing enforcement. Critical and high only. Runs in the OpenCode runbook lane.
> **Each deliverable is its own deliverable; each Done-when below is a test you write, see fail at
> `a95e88f21`, then see pass.**

## Objective

The OpenCode and Antigravity "standing-rules bridge" and the installed target rules
(`install.sh --emit-rules`) are the same file, `{.opencode|.agents}/rules/plan-marshall-target-rules.md`.
So a project setup replaces the full rules with a two-line stub. PLAN-LB-50 inverted the steward's
verdict: the stub reads `current` and the real rules read `damaged`. Its early return for
`damaged` now runs before the setup writers, so a standard install never gets the guard, the hook
or session-boundary enforcement.

## Deliverables

1. **The bridge has its own file, and setup never writes the installed target rules.**
   - `_bridge_rules_path` (`antigravity_runtime.py:60-62`, `opencode_runtime.py:86-88`) names a
     bridge file distinct from `plan-marshall-target-rules.md` (e.g.
     `plan-marshall-standing-rules.md`). `_write_rules_bridge` writes only that file.
   - The steward verdict (`configure_harness.py:65-106`) judges the bridge file only. A missing or
     stub bridge is reported, with a re-emit command that writes the bridge file and nothing else.
     The installed target rules are never judged `damaged` for lacking a bridge marker.
   - A project that still has the stub in `plan-marshall-target-rules.md` (a previous clobber) is
     reported, with the `install.sh --emit-rules` command that restores it.
   - `antigravity-rules.md:60-62` describes the two files correctly.

   *Done when:* tests, each failing at `a95e88f21`:
   - a setup over a fixture holding the full emitted rules leaves that file byte-identical, and
     writes the bridge to its own path;
   - a fixture whose target-rules file holds the stub is reported as clobbered, with the restore
     command;
   - the steward verdict for full rules plus a present bridge is `current`.

2. **Harness setup always runs the setup writers.**
   - `configure_harness.py` judges and reports the bridge state without returning before
     `project_initial_setup`, `project_install_hook` and `opencode_enforcement_apply`
     (`configure_harness.py:128-158`). Those always run, unless setup itself fails, which is then
     reported as such.
   - The #1781 persisted-approval warnings appear in the call's result, not only on stderr.

   *Done when:* tests, each failing at `a95e88f21`: configure-harness on a fixture with the full
   install.sh rules (no marker) calls `opencode_enforcement_apply` and `project_install_hook`, and
   reports the bridge verdict; the approval warnings are in the returned payload.

Split guard: two deliverables.

## Claim Labels

- OBSERVED: `_bridge_rules_path` returns `.opencode/rules/plan-marshall-target-rules.md` at `a95e88f21` — orchestrator-read; the Antigravity twin returns `.agents/rules/plan-marshall-target-rules.md` (delegated agent).
- OBSERVED: `configure_harness.py:128-134` returns `'damaged'` before `project_initial_setup` / `project_install_hook` / `opencode_enforcement_apply` (`:136-158`) — orchestrator-read.
- OBSERVED: `install.sh --emit-rules` writes the full rules to the same paths with no `bridge-version` marker (`marketplace/targets/{antigravity,opencode}/templates/install.sh`) (delegated agent).
- OBSERVED: `test_harness_config.py` `test_bridge_owns_own_file_only` checks `installed-target-rules.md`, which no code path writes (delegated agent).
- Downstream: PLAN-LB-51 D2 and PLAN-LB-48 D5 extend the bridge FILE this plan separates — they follow this plan.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall-antigravity/skills/target-rules/standards/antigravity-rules.md` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md` (D1)
- OBSERVED: `test/plan-marshall/marshall-steward/test_harness_config.py` (D1, D2)
- OBSERVED: `test/plan-marshall/platform-runtime/test_opencode_runtime.py` (D1)
- OBSERVED: `test/plan-marshall/platform-runtime/test_antigravity_runtime.py` (D1)

## Dependencies and Sequencing

- Depends on: none. **Critical** — enforcement is not installed on a standard consumer setup.
- Overlaps with: PLAN-LB-62 (running) on `opencode_runtime.py` (its permission reader, different
  functions). Before PLAN-LB-51 and PLAN-LB-48 D5.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
