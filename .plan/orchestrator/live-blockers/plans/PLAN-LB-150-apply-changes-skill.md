# PLAN-LB-150: One project-local `apply-changes` command carries a bundle change from the source tree to a restart-ready machine

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-150-apply-changes-skill.md` and is queued as one row file, `queue/PLAN-LB-150.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on the operator's word of 2026-11-14 ("give me a runbook lane for creating the skill"), after the operator asked whether the manual
> steps that follow a bundle change (`/sync-harnesses`, the registry repin, the executor regeneration) could be one project-level skill. One
> plan for one surface. Grounded by the orchestrator against `main` at `270fb4e07` by reading the three existing surfaces
> (`.claude/skills/sync-harnesses/SKILL.md`, `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md`,
> `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md`), ADR-025, the parity test
> `test/sync-harnesses/test_harness_command_parity.py`, the OpenCode entry point's head and `.claude/settings.json`. The scripts the command
> runs (`sync.py`, `registry_pin.py`, `reconcile_daemon.py`) were NOT read: their flags are taken from those documents. Every Done-when below
> fails at `270fb4e07` (the command does not exist there) unless it says "holds at". No Sonar. No token or measurement work. This is a
> convenience plan, not a blocker; it sits below the epic's high-and-blocking focus and was staged only because the operator asked for it.

## Objective

After a change under `marketplace/bundles/` an operator runs four things by hand: regenerate and sync the three harness installs, repin the
plugin registry, regenerate the executor, and restart the session. This plan adds one project-local command, `apply-changes`, that runs the
first three in the right order with the right gates and ends by telling the operator to restart, which no command can do for them. The sync
engine, the repin script, the daemon reconcile and the finalize step are reused unchanged, so the command is a composition and adds no new
mechanism.

## Deliverables

1. **The Claude Code entry point `apply-changes` prescribes the whole sequence and is allowed to run.**
   - Skills: pm-plugin-development:plugin-architecture, pm-documents:ref-documentation
   - Persona: documenter
   - `.claude/skills/apply-changes/SKILL.md`, a user-invocable skill in the shape of `sync-harnesses`, prescribes these steps, each in its own
     fenced `bash` block, one command per block, in this order:
     1. the three target regenerations through the build executor (`generate-claude`, `generate-opencode`, `generate-antigravity`), with the
        stop rule `sync-harnesses` states: any outcome other than `status: success` stops the run before the sync and names the failing
        target and the TOON's `log_file`;
     2. the sync engine, `python3 marketplace/targets/sync.py`, with NO argument, NO `$ARGUMENTS` pass-through, NO `--target` and NO
        `--repin` (a narrower sync is `/sync-harnesses`);
     3. the executor regeneration, `python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate`;
     4. the daemon reconcile, `python3 marketplace/targets/claude/reconcile_daemon.py`;
     5. the registry repin as its OWN step, `python3 marketplace/targets/claude/registry_pin.py --apply`, then the final registry verdict
        read from that script's output.
   - Steps 3, 4 and 5 run only when the Claude result reports `cache_status: success`, never on the Claude target's own `status`, and a
     `partial` caused only by a `behind` registry does not skip them; one failing harness never skips them while the Claude cache synced. The
     skill reports every harness row whose own install did not sync.
   - The skill ends with a post-run block that names the restart and states that `/reload-plugins` alone is not sufficient, and names
     `/reload-plugins` nowhere else. The command performs no restart.
   - The repin writes with the operator's own invocation as the consent and ignores the machine-local `registry-repin` setting, which stays
     the finalize step's opt-in. An entry pinned ahead of the synced version stays untouched and is reported, because the script never moves a
     pin backwards.
   - The skill states it runs on the main checkout of this repository only and is meta-project-only, like `sync-harnesses`.
   - `.claude/settings.json` gains `Skill(apply-changes)` and `Skill(apply-changes:*)` beside the two `sync-harnesses` entries and changes
     nothing else.

   *Done when:* each of these fails at `270fb4e07`: `.claude/skills/apply-changes/SKILL.md` exists and its frontmatter name is
   `apply-changes`; its prescribed `bash` commands are exactly the seven above in that order; its sync call is the bare engine call; no
   prescribed command is a direct `./pw` call; steps 3 to 5 name `cache_status: success` and no step names the bare status gate;
   `.claude/settings.json` parses as JSON and lists both new `Skill(...)` entries. This holds at `270fb4e07`: `.claude/skills/sync-harnesses/`
   and the other two `sync-harnesses` entry points are byte-identical after the plan, and `test/sync-harnesses/test_harness_command_parity.py`
   passes unchanged.

2. **The OpenCode command and the Antigravity skill carry the same sequence.**
   - Skills: pm-plugin-development:plugin-architecture, pm-documents:ref-documentation
   - Persona: documenter
   - `.opencode/commands/apply-changes.md` and `.agents/skills/apply-changes/SKILL.md` prescribe the same commands in the same order as
     deliverable 1 and carry a byte-identical post-run block, in each harness's own entry-point shape (an OpenCode command is named by its
     file and carries a `description` only; an Antigravity skill carries a frontmatter `name`).
   - The description of each entry point names no single harness's install location, as `sync-harnesses` already holds.

   *Done when:* each of these fails at `270fb4e07`: both files exist; the three entry points' prescribed `bash` command lines are equal as
   lists; their post-run blocks are byte-identical; the OpenCode file has no frontmatter `name` and each skill file's `name` is `apply-changes`.

3. **A parity test holds the three entry points together and pins the sequence.**
   - Skills: pm-dev-python:python-core, pm-dev-python:pytest-testing
   - Persona: module-tester
   - `test/apply-changes/test_apply_changes_command_parity.py`, in the form of `test/sync-harnesses/test_harness_command_parity.py` (read by
     explicit path, because the entry points lie outside the architecture inventory), pins: the three entry points exist and the harness
     set is derived from `SYNC_TARGETS`; the prescribed command lists are equal; the order of the seven commands; the sync call is bare;
     `registry_pin.py --apply` is its own step and no `--repin` appears anywhere; steps 3 to 5 gate on `cache_status` and not on the bare
     status; no direct `./pw` call; the post-run blocks are byte-identical and carry the restart and the reload sentence; `/reload-plugins`
     appears only inside that block.
   - Each pin has a matched control that plants the violation in a temporary tree and shows the detector fires (a reordered step, a
     `--repin` on the engine call, an ungated step, a direct `./pw`, a diverged mirror). A detector with no control fails the plan.
   - The test reuses the existing helpers (`_documented_example_scan`, `conftest`) and does not copy the `sync-harnesses` test's code.

   *Done when:* this fails at `270fb4e07` (the module does not exist) and passes after the plan; and each pin's matched control fails when
   its planted violation is removed from the control, shown red in the run record. This holds at `270fb4e07`:
   `test/sync-harnesses/test_harness_command_parity.py` and `test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py` pass unchanged.

4. **The operator-facing documents point at the command and do not restate the sequence.**
   - Skills: pm-documents:ref-documentation, pm-documents:ref-asciidoc
   - Persona: documenter
   - The `## Harness Sync` section of `CLAUDE.md` and the matching section of `AGENTS.md` name `/apply-changes` as the one-command path after a
     bundle change and say what it adds to `/sync-harnesses` in one sentence, cross-referencing the skill instead of repeating its steps.
   - `doc/developer/marketplace-build.adoc`, in its "After a Claude sync" section, names the command and links the sequence it follows
     with an `xref:`; blank line before lists, AsciiDoc formatting.
   - Nothing in ADR-025 is edited; the ADR already states that the sequence is told once as one ordered procedure.

   *Done when:* each of these fails at `270fb4e07`: `CLAUDE.md`, `AGENTS.md` and `marketplace-build.adoc` each name `apply-changes`; none of
   the three repeats the five-step list. This holds at `270fb4e07`: every existing test that reads those three files passes unchanged
   (verify-at-outline which tests those are).

Split guard: four deliverables, one theme. D1 and D2 are the command, D3 pins it, D4 points at it. The plan stays whole.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- ADR-025 binds: the registry write stays a separate, explicitly named step run by `registry_pin.py --apply`, never part of the cache sync and
  never an argument of the engine call. This plan edits none of `marketplace/targets/sync.py`, `marketplace/targets/claude/registry_pin.py`,
  `marketplace/targets/claude/reconcile_daemon.py`, `marketplace/targets/claude/cache_sync.py`, the `sync-harnesses` entry points or the
  `finalize-step-sync-plugin-cache` step.
- ⛔ The lane NEVER runs the command it creates, and never runs `sync.py`, `registry_pin.py --apply`, `reconcile_daemon.py` or
  `generate_executor generate` against the real machine: they write the operator's plugin cache, plugin registry, daemon and executor.
  Verification is by the tests alone, with planted trees under a temporary directory. The command's first real run is the operator's.
- One reader per concept: the command names the existing scripts and restates no gate of their own; where a gate must be stated
  (`cache_status`), it is stated the way `sync-harnesses` states it.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour. Documentation standards of
  `CLAUDE.md` apply: no duplication, cross-reference instead.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture where a script is loaded, and are shown red where a Done-when says so.
- The PR states whether an executor regeneration is owed (none: no verb or flag is added) and that no `marketplace/bundles/` file is touched,
  so no harness sync is owed.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `sync-harnesses` is a project-local, user-invocable skill that regenerates the three targets through the build executor, runs `python3 marketplace/targets/sync.py $ARGUMENTS`, reconciles the daemon in Step 4 and only reports the registry pin in Step 5 — read at `.claude/skills/sync-harnesses/SKILL.md` § Workflow
- OBSERVED: `sync-harnesses` states the sequence "sync, repin, fully restart" and that `/reload-plugins` alone is not sufficient — read at `.claude/skills/sync-harnesses/SKILL.md` § After the sync
- OBSERVED: the finalize step runs the sync, then the executor regeneration, then the daemon reconcile, then the repin or report, each of the last three gated on the Claude `cache_status: success` and the regeneration non-fatal — read at `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md` § Execution steps 1, 3, 3b, 3c
- OBSERVED: the repin is consensual — `--apply` on the script or `--repin` on the engine, "the operator's own invocation" on a command, the machine-local `registry-repin` setting only for the finalize step; the sync never writes the registry; the repin never moves a pin backwards; the three-step procedure was accepted as a known cost — read at `doc/adr/025-The_harness_sync_repins_the_plugin_registry_only_on_operator_opt-in.adoc` § Decision (b) (c) (d) (e) and § Consequences (the ADR's status line reads Proposed)
- OBSERVED: `/marshall-steward upgrade` is a different flow (config reconcile, one target regeneration, executor regeneration, a landing PR) and neither syncs the harness installs nor repins the registry — read at `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` § The four stages
- OBSERVED: the existing parity test pins, for `sync-harnesses` only, the entry-point paths (`.claude/skills/sync-harnesses/SKILL.md`, `.opencode/commands/sync-harnesses.md`, `.agents/skills/sync-harnesses/SKILL.md`), equal prescribed commands, byte-identical post-sync blocks, no direct `./pw`, a `cache_status` gate on its steps 4 and 5, and `/reload-plugins` only inside the block — read at `test/sync-harnesses/test_harness_command_parity.py`
- OBSERVED: the `.claude/`, `.opencode/` and `.agents/` trees lie outside the architecture inventory, so a new entry point there is invisible to `architecture find` and `search --content` — stated at `test/sync-harnesses/test_harness_command_parity.py` (module docstring) and seen in the sweep: `architecture find --pattern **/sync-harnesses*` returned nothing while the files exist
- OBSERVED: `.claude/settings.json` allows `Skill(finalize-step-plugin-doctor)`, `Skill(finalize-step-sync-plugin-cache)`, `Skill(sync-harnesses)` and `Skill(sync-harnesses:*)` — read at `.claude/settings.json` § permissions.allow
- OBSERVED: an OpenCode entry point is a command file with a `description` frontmatter and numbered steps, no `name` — read at `.opencode/commands/sync-harnesses.md` (head, 40 lines)
- OBSERVED: `sync-harnesses` is referenced from 50 inventoried files, among them `CLAUDE.md`, `AGENTS.md`, `doc/developer/marketplace-build.adoc`, `doc/developer/manual-sync-recovery.adoc`, `marketplace/targets/README.md`, `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py` and `test/plan-marshall/tools-permission-doctor/test_permission.py` — `architecture search --content --pattern sync-harnesses` (inventory only; the `.claude`, `.opencode` and `.agents` trees are not swept)
- HYPOTHESIS: `sync.py` takes no `--repin` when run bare and `registry_pin.py --apply` is the writing form, exactly as the two skills above state — confirm/refute at `marketplace/targets/sync.py` § argument parser and `marketplace/targets/claude/registry_pin.py` § argument parser (scripts not read; verify-at-outline, D1)
- HYPOTHESIS: `reconcile_daemon.py` takes no arguments and is safe to run when the build server is absent — confirm/refute at `marketplace/targets/claude/reconcile_daemon.py` § `main` (not read; verify-at-outline, D1)
- HYPOTHESIS: the pin-trap detector flags a document that names the sync without the sync, repin, restart sequence, so the new entry points must satisfy it — confirm/refute at `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py` and `test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py` (not read; verify-at-outline, D1, D2)
- HYPOTHESIS: `test/plan-marshall/tools-permission-doctor/test_permission.py` pins the `Skill(sync-harnesses)` entries of `.claude/settings.json` and so needs no change, or needs the new entries added — confirm/refute at that file (not read; verify-at-outline, D1)
- HYPOTHESIS: `CLAUDE.md` and `AGENTS.md` carry the same `## Harness Sync` section and a test or a doctor rule holds them equal — confirm/refute by reading `AGENTS.md` and by searching `test/` for the section title (not read; verify-at-outline, D4)
- HYPOTHESIS: the executor regeneration through `.plan/execute-script.py` is correct from the main checkout and wrong from a plan worktree, where `generate_executor` needs `--marketplace-root` — confirm/refute at `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md` § `generate` and `marshall-steward/SKILL.md` Scripts table (stated there; not read at the script; verify-at-outline, D1)
- Verify-first clause: before scoping D1, read `sync.py`, `registry_pin.py` and `reconcile_daemon.py` argument parsers and state what each accepts, so the prescribed commands are the real ones; a flag the script does not accept is dropped from the clause and the PR says so. Before scoping D4, read `AGENTS.md` and name the tests that read the three documents.

## Expected Surface

- OBSERVED: `.claude/skills/apply-changes/SKILL.md` — new file (D1)
- OBSERVED: `.claude/settings.json` — `permissions.allow`, two entries added (D1)
- OBSERVED: `.opencode/commands/apply-changes.md` — new file (D2)
- OBSERVED: `.agents/skills/apply-changes/SKILL.md` — new file (D2)
- OBSERVED: `test/apply-changes/test_apply_changes_command_parity.py` — new file (D3)
- OBSERVED: `CLAUDE.md` — `## Harness Sync` (D4)
- OBSERVED: `AGENTS.md` — the matching section (D4)
- OBSERVED: `doc/developer/marketplace-build.adoc` — "After a Claude sync" (D4)
- HYPOTHESIS: `test/plan-marshall/tools-permission-doctor/test_permission.py` — only if it pins the settings entries (D1; verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. The scripts it composes shipped with PLAN-LB-137 and earlier.
- Overlaps with: none expected. PLAN-LB-136 (Antigravity standing rules and the task gate) declares the Antigravity runtime and rules surface; this plan adds one new file under `.agents/skills/apply-changes/` and touches no file PLAN-LB-136 declares. The cross-check names any exact file.
- Adjacent to: `.claude/skills/sync-harnesses/`, its two mirrors and `test/sync-harnesses/test_harness_command_parity.py`, which stay byte-identical; `marketplace/targets/` and the `finalize-step-sync-plugin-cache` step, which are reused and not edited; `/marshall-steward upgrade`, which is a different job and is not folded in.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-150-apply-changes-skill.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
