# PLAN-LB-94: One executor serves every harness — no harness refuses, rewrites or outranks another's `.plan/execute-script.py`

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-94-one-executor-all-harnesses.md` and is queued as one row file, `queue/PLAN-LB-94.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-25 on the operator's instruction ("how to fix this need for overwriting ... the core idea: the different
> harnesses can use the same executor"). **Critical**: until it ships, a Claude session and an OpenCode lane that share one
> checkout refuse each other's calls and regenerate the file back and forth. **Each deliverable is its own outline
> deliverable, and each Done-when is its own success criterion. Do not merge them.** Do D2 first: it ends the refusals.

## Objective

`.plan/execute-script.py` is one git-ignored file per checkout, and a Claude orchestrator and OpenCode lanes both run
through it. PLAN-LB-43 D5 (shipped) stamps the executor with the harness it was generated for and makes any other harness's
call fail with `executor_target_mismatch`. The refusal's only remedy is to regenerate for the refused harness, which refuses
the first harness in turn. The two regenerate each other's file. This plan makes the executor harness-independent, so a
regeneration by any harness yields the same file and a call from any harness dispatches.

## Where the delta is (measured)

Two executors were generated in this checkout with the same generator, `--target claude` and `--target opencode`, and
diffed. They differ in the places below, and nowhere else:

| Hunk | Claude | OpenCode |
|---|---|---|
| `_EXECUTOR_TARGET` stamp | `'claude'` | `'opencode'` |
| `EXECUTOR_PLUGIN_ROOT` and the one `_CACHE_RECOVERY_ROOTS` entry | `~/.claude/plugins/cache/plan-marshall` | `~/.config/opencode/skills` |
| Four embedded script paths (`extension_base`, `query-architecture`, `query-config`, `triage_helpers`) | a versioned plugin-cache path | a flat install path |
| The resolver section heading | `target: claude` | `target: opencode` |
| `_resolve_notation_by_target` body | tree probe, then the newest plugin-cache version | tree probe, then seven dash-namespaced skill roots |
| (behaviour, not text) `resolve_notation` leg 0 | skipped | tree-first probe, gated on the stamp |

The other 164 marketplace paths, the argument surfaces and the bootstrap directories are byte-identical, because generation
rewrites every mapping to the checkout's `marketplace/bundles` tree when one exists. In this repository the two executors
therefore run the same scripts. The refusal protects nothing here; it only creates the war. It protects a consumer project
that has no tree, where the embedded paths point into one harness's install.

## Deliverables

1. **The generated executor does not depend on which harness generated it.**
   - The bytes of `.plan/execute-script.py` are a function of the checkout and the installs present on the machine, not of
     the invoking harness or of `--target`. `--target` becomes a hint for which install to prefer when several are present.
   - The stamp becomes informational (`generated_for`), the plugin root and recovery roots list every installed harness's
     root, and no placeholder carries the invoking harness.

   *Done when:* a test generates in one fixture with `--target claude`, `--target opencode` and `--target antigravity`, and
   under each harness's ambient environment signal: the three files are byte-identical. It fails at HEAD (the differences tabled above).

2. **No harness refuses an executor another harness generated, and a call from any harness dispatches.**
   - `executor_target_mismatch` is retired for a target difference. The refusal stays for an executor that is unreadable,
     absent or cannot start (the recovery cases).
   - Resolution order is one list for every harness: the checkout's tree first, then the runtime harness's own install
     (detected from the environment at call time), then the other harnesses' installs. When the call had to use a foreign
     harness's install, the executor says so once on stderr and dispatches.
   - The status metadata keys `executor_target` and `executor_plugin_root` (`manage-status`, `_cmd_lifecycle.py`
     `_executor_target_stamp`) keep their names and mean "generated for"; nothing reads them as a lock.

   *Done when:* tests: an executor generated under one harness's environment dispatches a notation under each of the other
   two environments and exits 0 with the script's output; a fixture with only a foreign install resolves it and writes the
   one-line note; an unreadable executor still produces the recovery refusal. The first fails at HEAD
   (`executor_target_mismatch`, exit 2). The PLAN-LB-43 D5 tests (`test_executor_target_stamp.py`,
   `test_executor_target_resolution.py`, `test_executor_recovery.py`) are rewritten to this contract, not deleted.

3. **Mappings and argument surfaces do not bind the executor to the generating harness's install.**
   - The four script-shared entries that sit in sub-directories of `scripts/` (`extension/`, `query/`, `workflow/`) are
     rewritten to the tree like the other 164: `_rewrite_mappings_to_tree` joins `scripts/{script}.py` only.
   - In a project with no tree, an embedded path counts only when it lies in the runtime harness's install or the tree;
     otherwise the runtime harness's install is consulted first and the embedded foreign path is the last resort.
   - The `PYTHONPATH` the executor builds comes from the same root as the script it resolved, never a mix of a tree script
     with a foreign install's helpers.
   - An embedded argument surface is applied only to the script it was derived from. Today the surface digest is read at
     regeneration only (template L426-430), so a surface derived from install A can reject a flag that the script resolved
     from install B accepts. At dispatch, a surface whose script path or digest differs from the resolved script is ignored
     and the call spawns (fail-open, as the template already does for an absent surface).

   *Done when:* tests: in a tree fixture all notations, including the four nested ones, resolve to the tree under both
   environments; in a consumer fixture holding a claude cache at one version and an opencode flat install at another, each
   environment resolves a notation to its own harness's file and builds `PYTHONPATH` from that same root; a surface derived
   from one version rejects nothing for a script resolved from a version that adds a flag. Each fails at HEAD.

4. **Staleness and version are judged per runtime harness, so no stamp makes one harness permanently stale.**
   - `generate_executor preflight`, `runbook_lane executor-skew` and `MARSHALL_VERSION` read the manifest of the harness that
     is running (`installed_manifest_probe_paths(target=…)`), not the manifest of the generating one. The executor embeds what
     it needs for that (a version per installed harness, or the tree's version) and the choice is recorded at outline.

   *Done when:* tests: a fixture with a claude manifest at one version and an opencode manifest at an older one, one executor:
   `preflight` and `executor-skew` under each environment report that harness's own staleness; neither reports `skew`
   merely because the other harness generated the file. Fails at HEAD.

5. **Regeneration converges, and no workflow treats a harness difference as a reason to regenerate.**
   - The executor is written atomically (temporary file in the same directory, then rename), and a regeneration whose output is
     byte-identical to the file on disk does not touch it.
   - The lane text, the steward text and the finalize step stop naming a target mismatch as a trigger for regeneration;
     regeneration stays for a changed script set or a stale version. `finalize-step-sync-plugin-cache` step 3 keeps its
     unconditional regeneration (now a no-op when nothing changed).
   - A test run is a third writer. The PLAN-LB-90 landing reports that a full `module-tests` run twice left the main
     checkout's executor stamped `claude`, and the execution log of 2026-10-25 shows every `generate_executor` verb
     (`--help`, `verify`, `bootstrap`, `paths`, `generate`, `drift`, `cleanup`, `recover`, `preflight`) run through the main
     executor inside the lane's test window (08:04:51Z to 08:05:46Z). HYPOTHESIS (verify-at-outline): those tests
     address the real checkout's executor; if so they must address a fixture project, or, failing that, write nothing.

   *Done when:* tests: two interleaved generations from different environments leave one valid file equal to a single
   generation; a generation killed after the temporary file is written leaves the previous executor intact; a no-change
   regeneration leaves the modification time unchanged; a doc test finds no instruction in the shipped lane, steward or
   finalize text that regenerates in response to `executor_target_mismatch`; the generator tests leave the checkout's own
   `.plan/execute-script.py` byte-identical (modification time included). Each fails at HEAD except the last, whose
   failure at HEAD is the HYPOTHESIS above.

Split guard: five deliverables, one theme (an executor does not belong to a harness). The generator's discovery, the
argument-surface derivation and the notation grammar are not changed. The flat-install bootstrap of the generator itself
stays in PLAN-LB-93 D1-D2.

## Claim Labels

- OBSERVED (the delta): the two generated executors differ only in the places tabled above (orchestrator-run, 2026-10-25, cache generator `0.1.2007`, both generated into scratch checkouts with `PLAN_TRACKED_CONFIG_DIR`; every other line is identical, including 164 of the 168 marketplace mappings).
- OBSERVED (why they match here): `generate_executor.py` `_rewrite_mappings_to_tree` (L1865-1907) rewrites a non-tree path to `marketplace/bundles/{bundle}/skills/{skill}/scripts/{script}.py` when that file exists; a script under `scripts/<sub-directory>/` has no such file at that path, so the four nested entries keep a harness-specific path.
- OBSERVED (the refusal): the template's `_check_executor_target` (L244-284) exits 2 with `executor_target_mismatch` when `detect_target_from_env()` (`target_context.py` L157; `CLAUDE_CODE_SESSION_ID`, `OPENCODE`, `ANTIGRAVITY_AGENT`) differs from the stamp, and its `regenerate_command` names the refused harness. It was added by PLAN-LB-43 D5 (#1851).
- OBSERVED (the war, session store and executor log): the PLAN-LB-90 OpenCode lane root hit the mismatch on a claude-stamped executor, asked the operator at 07:55:59Z on 2026-10-25, then ran `generate_executor recover`, `generate --marketplace-root`, `generate --target opencode` (07:59:21Z), a call prefixed with `CLAUDE_CODE_SESSION_ID=1 OPENCODE= OPENCODE_PID= ANTIGRAVITY_AGENT=` (07:59:30Z) and `preflight`. The orchestrator regenerated for `claude` at about 08:01Z, so the file flipped at least twice within three minutes. The executor's modification time on 2026-10-24 (22:01 local, 20:01Z) coincides with the same lane's `executor-skew`, `generate_executor drift` and `preflight` calls at 20:00Z; that earlier flip is not attributed to one command (command words and times only).
- OBSERVED (a bypass already tried): the lane's env-prefixed call above is an attempt to satisfy the check by spoofing the platform signals.
- OBSERVED (target-dependent generation inputs): `generate_executor()` resolves one target and uses it for `generate_target_aware_resolver_code(resolved_target)` (L2041-2042), `_shared_bundle_cache_roots_for(resolved_target)` (L2090), `read_installed_manifest(base_path, target=resolved_target)` (L2119) and the `{{EXECUTOR_TARGET}}` / `{{EXECUTOR_PLUGIN_ROOT}}` substitutions (L2141). The resolver has three bodies (`_resolve_notation_by_target`, L922/1017/1106 of the generator), one per target.
- OBSERVED (resolution order): `resolve_notation` (template L1627-1684) probes the tree first only when `_EXECUTOR_TARGET == 'opencode'` (L1661); legs 1-2 return an embedded path that still exists, so a claude-generated consumer executor run under OpenCode would return a claude-cache path silently, which is the reason D5 gave.
- OBSERVED (surfaces): `SCRIPT_SURFACES` entries carry a `digest` (template L426-431) that is consulted when the next regeneration reuses them; no dispatch-time comparison exists (`grep digest` in the template finds only those comments). Rejection is "only ever done from positive knowledge" (L1009-1012).
- OBSERVED (readers of the stamp): outside the generator and the template, only `manage-status/scripts/_cmd_lifecycle.py` (`_executor_target_stamp`, L1446-1466; written into plan status metadata at L1543) reads it, as metadata.
- OBSERVED (writers of the main executor): `finalize-step-sync-plugin-cache` step 3 runs `generate_executor generate` through the executor after a successful sync, so the stamp follows the harness that runs the finalize; the lane text names `generate_executor generate --marketplace-root .` as the one bootstrap (`runbook-lane/SKILL.md` L441) and `executor-skew` as the start-of-run check (L129-143); `recover` regenerates for the harness named by `--target`.
- HYPOTHESIS: the antigravity resolver body (L1106 of the generator) can join the same function without changing its roots; confirm by generating all three (verify-at-outline).
- HYPOTHESIS: `PYTHONPATH` is built by the template from the directories of the resolved mapping (`SHARED_MODULE_DIRS`, `build_pythonpath`) and can be made to follow the resolved root; confirm where it is assembled before D3 (verify-at-outline).
- HYPOTHESIS: the status metadata keys can keep their names; no consumer outside `_cmd_lifecycle.py` reads them (grep, orchestrator-run) — confirm no test asserts them as a lock (verify-at-outline).
- Verify-first clause (design): the chosen design is ONE file whose content does not depend on the harness (the operator's stated idea). If determinism cannot hold at outline (for example a consumer project's per-harness embedded paths make the bytes depend on which installs exist), the fallback is a stable target-neutral entrypoint `.plan/execute-script.py` that selects a per-harness body under `.plan/executors/{target}.py`, each harness regenerating only its own. Record which was chosen and why; do not ship both.
- Verify-first clause (D1/D4): the bytes must not contain a clock value, an environment-derived value or an ordering that depends on directory listing order. Decide what `MARSHALL_VERSION` is when several harness installs carry different versions (a version per installed harness, or the tree's version) and record the reason.
- Verify-first clause (D2): the one-line stderr note must not appear on the normal path (tree or the runtime harness's own install), or every dispatch becomes noisy and a caller that parses stderr breaks.
- Operator step after the merge: the executors that exist before this ships still carry the old check, so regenerate the main checkout's executor once from the merged template, then `/sync-harnesses`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — resolver bodies, recovery roots, manifest lookup, mapping rewrite, atomic write, `recover` (D1, D2, D3, D4, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — the stamp, `_check_executor_target`, `resolve_notation`, surface use at dispatch, `PYTHONPATH` (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md` and `standards/` — the target stamp and recovery contract (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — `_executor_target_stamp` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` and `scripts/runbook_lane.py` — `executor-skew`, the regeneration text (D4, D5)
- OBSERVED: `.claude/skills/finalize-step-sync-plugin-cache/SKILL.md` — step 3 (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/` (`upgrade.py`, `determine_mode.py`, `references/`) — preflight and regeneration text (verify-at-outline) (D4, D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` and `target_context.py` — per-target cache roots (verify-at-outline) (D1, D2)
- OBSERVED: `test/plan-marshall/tools-script-executor/` — `test_executor_target_stamp.py`, `test_executor_target_resolution.py`, `test_executor_recovery.py`, `test_executor_tree_first.py`, `test_generate_executor*.py`, `test_executor_runtime.py` (D1-D5)
- HYPOTHESIS: `test/plan-marshall/runbook-lane/test_runbook_lane.py` and `test/plan-marshall/manage-status/` — skew and metadata (verify-at-outline) (D2, D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-43 (shipped, #1851), whose D5 this plan relaxes.
- Overlaps with: PLAN-LB-93 on `generate_executor.py` and the template (its D1-D2 change the generator's bootstrap loop at L176-193; this plan changes resolver and generation code). Run this plan first; PLAN-LB-93 D1-D2 then rebase. The gate will ask. PLAN-LB-90 (shipped, #1859) changed `runbook-lane/SKILL.md` and `runbook_lane.py`, so this plan's D4/D5 lane text edits start from that merged text.
- Adjacent to: PLAN-LB-92 (shipped), whose per-worktree executors are generated by the same generator and become harness-independent through D1 without a change of their own.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-94-one-executor-all-harnesses.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
