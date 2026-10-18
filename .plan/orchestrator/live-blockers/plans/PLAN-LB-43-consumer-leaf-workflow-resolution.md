# PLAN-LB-43: A dispatched leaf resolves its workflow document in a consumer repository

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-43-consumer-leaf-workflow-resolution.md` and is queued as one row file, `queue/PLAN-LB-43.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the Open Defect "In a consumer repository a dispatched leaf cannot resolve its workflow document" (`lessons-routing-021.md`; recurrence `lessons-routing-028.md` item 182).

## Objective

The generic `execution-context` agent maps a workflow notation only to `marketplace/bundles/…` under the working tree. A consumer repository has no such tree, so every dispatched leaf there either hits `workflow_not_found` or improvises. Leaves have read the plan-marshall source checkout or a stale `target/claude/` copy instead — two different trees for one notation.

This plan gives the leaf one script verb that returns the verified absolute path of the installed workflow document. It reuses the existing bundle-cache and version resolvers.

## Deliverables

1. **One verb resolves a workflow notation to a verified absolute path.**
   - `extension_api resolve-workflow --notation {N} --worktree {W}` accepts `{bundle}:{skill}/{relative path}.md` — the `SKILL.md`, `workflow/` and `standards/` forms alike.
   - It returns:
     - `{W}/marketplace/bundles/{bundle}/skills/{skill}/{path}` when that file exists (this repository and every other bundle-owning checkout, so worktree edits stay visible);
     - otherwise the installed copy, found through platform-runtime `layout bundle-cache-root` and `marketplace_bundles.resolve_bundle_path` (versioned layout with newest-eligible selection, and the flat OpenCode / Antigravity layout).
   - When neither exists it returns `status: error, error: workflow_not_found` with both probed paths.
   - No new path logic is written.

   *Done when:* fixture tests resolve one notation:
   - to the in-repository file when it exists;
   - to the newest version directory of a fixture cache when it does not;
   - to a flat-layout root;
   - to `workflow_not_found`, naming both probes, when the file exists nowhere.

   At HEAD no such verb exists.

2. **The agent's Step 4 uses the verb, and the extension-point standard states the order.**
   - `agents/execution-context.md` Step 4 calls the verb and `Read`s the returned path, replacing its two-row mapping to `marketplace/bundles/…`.
   - `ext-point-execution-context-workflow.md` states the resolution order once, and the agent cross-references it.
   - The generated level variants carry the change.

   *Done when:* a doc test asserts that Step 4 names the verb and no longer maps a notation only to `marketplace/bundles/`; the generated Claude, OpenCode and Antigravity variants carry the same Step 4. At HEAD, Step 4 (L107-122) maps only to `marketplace/bundles/`.

3. **An executor that fails to import is recovered by a script path that a broken executor can reach.** Added 2026-10-17 by operator instruction, graded **high**, from the PLAN-LB-63 landing (`landings/PLAN-LB-63.md`, Regression 1).

   **The defect.** PLAN-LB-63 D2 added an import probe (`_probe_executor_import`, `upgrade.py:779-811`) and `needs_recovery = executor_version is None or bool(import_failure)` (`:1052-1072`). That code runs only inside `upgrade plan`, and the only documented `upgrade plan` invocation goes through the executor itself (`upgrade-flow.md:87-89`):
   - if the executor cannot import, `upgrade.py` never runs;
   - if it can, the probe child, which inherits the same environment, succeeds as well.

   The probe therefore never fires in production. Recovery still depends on the LLM following the prose of `upgrade-flow.md` Step 0 (L67-81) by hand. PLAN-LB-63's test ran `upgrade.main()` in-process with a stub generator, so it could not see this.

   **Requirements.**
   - **One direct-path recovery entry.** The fix must be a single deterministic command that needs no working executor:
     - either `upgrade.py` run by its newest-cache script path, or a dedicated `generate_executor` verb — choose at outline and record why;
     - it finds the newest cache, probes, regenerates, **re-probes** the regenerated executor, and reports;
     - a regenerated executor that still fails to import is `action: regenerate_failed` with the probe's reason, never `regenerated`.
   - **The executor's own failure output names that command.** The bootstrap failure path (`execute-script.py.template:252-265`, the `execute-script.py cannot start:` message, and the uncaught `ImportError` path, which needs a guard) prints the exact recovery command line with the resolved newest-cache path. Any harness then recovers from the error text alone.
   - **The command must pass the R5 guard on every guarded harness.**
     - PLAN-LB-65 (`d3e9c2544`) made the R5 allow-list exact and repository-relative.
     - A newest-cache script path lies outside a consumer repository, so a cache-path invocation
       is refused.
     - Instead, PLAN-LB-65 allow-listed a documented CLI recovery command.
     - The recovery entry must be that allow-listed form, or an exact, narrow new entry. The
       allow-list must not be widened to cache paths.
     - Test: the guard and the hook both admit the exact command line that the executor prints.
   - **Step 0 in `upgrade-flow.md` calls that command** instead of describing the generator call in prose.
   - **The import-failure warning is not overwritten** by the version-split warning (`upgrade.py:1154-1158`): both are reported.
   - **Probe environment.** The probe runs with the interpreter and environment a fresh shell would use, not the parent's injected `PYTHONPATH` (`template:1774-1776`). Otherwise a probe started from a working executor can mask a broken one.

   *Done when:* every test below fails at `b90e8a25f`.
   - **End-to-end recovery.** A fixture project holds a real generated executor whose bootstrap directory has been removed (import fails). Run, as a subprocess:
     1. `python3 .plan/execute-script.py --list` — stderr contains the recovery command line;
     2. that exact command line — the executor is regenerated, `python3 .plan/execute-script.py --list` then exits 0, and the report says `regenerated`.
   - **Failed regeneration.** The same fixture, with a newest cache that is itself missing a bootstrap module, reports `regenerate_failed` naming the import error, not `regenerated`.
   - **Warning precedence.** An import failure combined with a post-regeneration version split reports both warnings.
   - **Probe environment.** A probe started from a process whose `PYTHONPATH` makes the import succeed still reports the failure of the on-disk executor.

## Claim Labels

- OBSERVED: Step 4 maps `{bundle}:{skill}/SKILL.md` and `{bundle}:{skill}/workflow/{file}.md` only to `marketplace/bundles/{bundle}/skills/{skill}/…` and otherwise returns `workflow_not_found` — `marketplace/bundles/plan-marshall/agents/execution-context.md` L107-122.
- OBSERVED: the agent's own example passes a third notation form, `plan-marshall:phase-6-finalize/standards/push.md` (L7), which the Step 4 table does not cover.
- OBSERVED: the same mapping appears in `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md` (a literal content search finds these two files only).
- OBSERVED: `layout bundle-cache-root` returns `/home/oliver/.claude/plugins/cache/plan-marshall` for the Claude target (live call at this checkout). The installed bundle sits at `…/plan-marshall/0.1.1919/` with its own `.claude-plugin/plugin.json`.
- OBSERVED: `marketplace_bundles.resolve_bundle_path` already resolves a subpath in both the nested, versioned cache (newest eligible version, through `select_live_version_dir`) and the flat deployed layout (through `deployed_layout.resolve_skill_path`) — `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py` L25-67, L127-167.
- OBSERVED: `extension_api.py` is an executor-registered CLI with `resolve-skills` and `derivation-resolvers` verbs (live `--help` at this checkout).
- OBSERVED: `phase-6-finalize/SKILL.md` L558-562 treats a later `workflow_not_found` as the first sign of post-rebase version skew and re-resolves from the worktree. The in-repository-first order of deliverable 1 keeps that behaviour.
- HYPOTHESIS: the generated level variants (`execution-context-level-*.md`) copy the agent body verbatim, so regenerating the targets carries the change — confirm at `marketplace/targets/opencode/variant_emitter.py` and `test/marketplace/targets/opencode/test_variant_emitter.py` (verify-at-outline).
- HYPOTHESIS: the leaf can run the verb before Step 4 in a consumer repository, because the consumer's executor maps `plan-marshall:extension-api:extension_api` to the installed cache (verify-at-outline).
- Verify-first clause: choose the host verb. The candidates are `extension_api` (the owner of the notation standard; recommended), a platform-runtime `layout` operation (which would collide with the running PLAN-LB-39 on `platform-runtime/standards/contract.md`), or `generate_executor`. Record why.
- Verify-first clause: confirm that in-repository first, installed second is right for this repository — worktree source edits must stay visible to leaves — and for consumers, where the in-repository probe misses.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/agents/execution-context.md` — Step 4 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-execution-context-workflow.md` — notation forms and resolution order (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_api.py` — the `resolve-workflow` verb, host per the verify-first clause (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/extension-api/SKILL.md` — canonical invocation of the verb (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/extension-api/` — new test module for the verb (D1)
- HYPOTHESIS: `test/marketplace/targets/opencode/test_variant_emitter.py` — only if it asserts the Step 4 text (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — probe environment, re-probe, warning precedence, direct-path entry (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — the failure output names the recovery command (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` — Step 0 calls the command (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` and its `SKILL.md` — only if the entry is hosted there (verify-at-outline) (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` — canonical invocation of the entry (verify-at-outline) (D3)
- OBSERVED: `test/plan-marshall/marshall-steward/` and `test/plan-marshall/tools-script-executor/` — the subprocess end-to-end tests (D3)

## Dependencies and Sequencing

- Depends on: none. D3 builds on PLAN-LB-63 (shipped, `b90e8a25f`).
- Split guard: three deliverables, each its own outline deliverable; each Done-when is its own
  success criterion. Do not merge them.
- D3 overlap: the running PLAN-LB-65 edits `marshall-steward/references/upgrade-flow.md` and
  `tools-script-executor/SKILL.md`. The emit gate decides.
- Overlaps with:
  - None of the declared running or staged plans on a file.
  - PLAN-LB-39 (running) declares `test/marketplace/targets/` and changes the OpenCode and Antigravity emitters' dispatch-line handling. If deliverable 2 needs emitter-test changes, sequence after PLAN-LB-39.
  - None of the other four candidates (the `runtime-stamp` candidate edits `platform_runtime.py`; this plan only calls its `layout bundle-cache-root`).
- Adjacent to:
  - `script-shared/scripts/marketplace_bundles.py`, `deployed_layout.py` and `plugin_registry.py` — reused, not edited.
  - `execution-context-reader.md` — carries no notation mapping, so it is not touched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-43-consumer-leaf-workflow-resolution.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
