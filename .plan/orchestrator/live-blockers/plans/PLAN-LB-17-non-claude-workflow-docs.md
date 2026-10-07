# PLAN-LB-17: OpenCode and Antigravity installs ship skills without the files their SKILL.md routes to

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-17-non-claude-workflow-docs.md` and is queued as one row file, `queue/PLAN-LB-17.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The OpenCode and Antigravity generators, and the sync step that installs their output, copy a skill's `SKILL.md` plus exactly four named subdirectories (`standards`, `references`, `templates`, `scripts`). Every other subdirectory is dropped, so on those two harnesses the `plan-marshall` skill routes each action to `Read workflow/planning.md` or `Read workflow/execution.md` and the file is not there; the same holds for every other skill that keeps content under `workflow/`, `assets/`, `config/`, `styles/`, `knowledge/`, `examples/` or `documents/`, and for the `extension.py` that sits beside `SKILL.md` in each bundle's `plan-marshall-plugin` skill. The Claude target is unaffected because it copies the whole bundle tree. This plan replaces the allow-list with "everything in the skill directory except what is explicitly excluded" in both emitters and in the sync step, and adds a test that fails whenever a relative path a `SKILL.md` routes to is missing from any target's output. No earlier spec covers this defect.

## Deliverables

1. **Both emitters copy the whole skill directory, not four named subdirectories.** `_emit_skill` in the OpenCode and the Antigravity emitter emits every file under the skill directory other than `SKILL.md` itself (which keeps its frontmatter and body transform), still skipping `EXCLUDED_DIR_NAMES`, hidden files such as `.DS_Store`, and anything a `targets:` scope excludes for that target — the same exclusion set the Claude emitter applies. The `VERBATIM_SKILL_SUBDIRS` constant is removed from both modules, or kept only as a derived, non-authoritative value if a caller still needs it; no list of permitted subdirectory names remains. Done when: an emitter test whose fixture skill carries `workflow/a.md`, `assets/b.json`, a nested `workflow/sub/c.md`, a loose `extension.py` beside `SKILL.md`, a `__pycache__/x.pyc` and a `.DS_Store` fails at HEAD and passes after, asserting the first four are emitted byte-identical and the last two are not, for each of the two targets; and a regenerated `target/opencode/skill/plan-marshall-plan-marshall/` and `target/antigravity/skills/plan-marshall-plan-marshall/` both contain `workflow/planning.md`.

2. **The sync step installs whatever the generated skill directory contains.** `_deploy_skill` in `marketplace/targets/sync.py` mirrors the generated skill directory into the install location instead of iterating its own copy of the four-name list, and removes files and subdirectories that are no longer in the generated tree (today a subdirectory that disappears from source stays installed, because only the four named ones are ever replaced). `sync.py` must stay runnable under a bare `python3` with the standard library only, so it must not import the list from the `marketplace.targets` package; mirroring the already-filtered generated tree needs no list at all. Done when: a `test_sync.py` test that deploys a generated skill holding `workflow/x.md` and a loose root file to a temporary destination fails at HEAD and passes after for both `opencode` and `antigravity`; a second test deploys twice, removing `workflow/` from the source between runs, and asserts the destination no longer has it; `--dry-run` still writes nothing.

3. **A route-closure test over the real bundles, for every target.** A new test generates each registered harness target (`claude`, `opencode`, `antigravity`) from `marketplace/bundles/` into a temporary directory, and for every emitted `SKILL.md` extracts each skill-relative path the body routes to — at minimum Markdown link targets and backticked paths of the form `{subdir}/{file}` that resolve to an existing file in the source skill directory — and asserts the same relative path exists in that target's emitted skill directory. The expected set is derived from the source tree, never from a hand-written list of subdirectory names, and the test asserts it found a non-zero number of routes (so an extraction regression cannot pass vacuously). A path excluded by a `targets:` scope for that target is exempt, read from the same scope predicate the emitters use. Done when: the test fails at HEAD for `opencode` and `antigravity`, naming `plan-marshall/workflow/planning.md` among the missing paths, passes for `claude` at HEAD, and passes for all three after deliverable 1.

4. **Tests and documentation that pin the four-name list are corrected.** `test_verbatim_skill_subdirs_constant_exposed` in the OpenCode emitter test asserts the set equals the four names, which pins the defect as intended behaviour; it and the fixtures that build skills by iterating `VERBATIM_SKILL_SUBDIRS` are rewritten against the new contract. The emitter module docstrings, `doc/developer/antigravity.adoc` and any other document that states the four-name list are changed to state the rule (whole skill directory minus exclusions). Done when: a content search for `VERBATIM_SKILL_SUBDIRS` and for the literal four-name sequence under `marketplace/targets/`, `test/marketplace/targets/` and `doc/developer/` returns only text consistent with the new rule.

## Claim Labels

- OBSERVED: the OpenCode emitter copies only four named subdirectories per skill — read at `marketplace/targets/opencode/emitter.py:80` (`VERBATIM_SKILL_SUBDIRS = ('standards', 'references', 'templates', 'scripts')`) and `:263-274` (the loop in `_emit_skill`); nothing else under the skill directory is read.
- OBSERVED: the Antigravity emitter carries its own identical copy of the list and loop — read at `marketplace/targets/antigravity/emitter.py:51` and `:212-223` § `_emit_skill`.
- OBSERVED: the sync step carries a third copy and would drop the directories even if the emitters produced them — read at `marketplace/targets/sync.py:119` and `:313-326` § `_deploy_skill`, which copies `SKILL.md` and then only the four named subdirectories.
- OBSERVED: `_deploy_skill` never removes a subdirectory that is absent from the generated tree; it only replaces the four named ones when present — read at `marketplace/targets/sync.py:319-326`.
- OBSERVED: the Claude emitter has no allow-list; it walks the whole bundle with `rglob('*')` and skips only `EXCLUDED_DIR_NAMES`, `.claude-plugin/plugin.json` and target-scoped components — read at `marketplace/targets/claude/emitter.py:52,77-81,150-169` § `emit_bundle_verbatim`.
- OBSERVED: the shared exclusion set is `EXCLUDED_DIR_NAMES = frozenset({'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'})` — read at `marketplace/targets/component_targets.py:177`; both non-Claude emitters already import it.
- OBSERVED: across `marketplace/bundles/*/skills/*/` the subdirectory names and their counts are `standards` 105, `scripts` 76, `references` 21, `templates` 19, `__pycache__` 10, `workflow` 9, `assets` 3, and one each of `styles`, `knowledge`, `examples`, `documents`, `config` — enumerated with `ls -d marketplace/bundles/*/skills/*/*/`. Seventeen directories in fifteen skills fall outside the four-name list.
- OBSERVED: the fifteen affected skills are `plan-marshall` bundle: `plan-marshall`, `phase-3-outline`, `phase-6-finalize`, `plan-orchestrator`, `recipe-refactor-to-profile-standards` (all `workflow`), `manage-plan-documents` (`documents`), `manage-solution-outline` (`examples`), `ref-toon-format` (`knowledge`); `pm-documents`: `ref-asciidoc`, `ref-documentation` (`workflow`), `ref-narrative-styles` (`styles`); `pm-plugin-development`: `ext-outline-workflow` (`workflow`), `plugin-create` (`assets`), `plugin-maintain` (`assets`), `plugin-doctor` (`workflow`, `assets`, `config`) — same enumeration.
- OBSERVED: ten skills carry a loose `extension.py` beside `SKILL.md` (`{bundle}/skills/plan-marshall-plugin/extension.py`, one per bundle), which the non-Claude emitters also drop — `target/claude/plan-marshall/skills/plan-marshall-plugin/` lists `extension.py`, `target/opencode/skill/plan-marshall-plan-marshall-plugin/` does not.
- OBSERVED: the generated trees confirm the gap — `target/claude/*/skills/*/*/` contains `workflow` 9, `assets` 3 and the five single names; `target/opencode/skill/*/*/` and `target/antigravity/skills/*/*/` each contain only `standards` 104, `scripts` 71, `references` 20, `templates` 19.
- OBSERVED: the installed copies confirm it — `~/.config/opencode/skills/plan-marshall-plan-marshall/` and `~/.gemini/config/plugins/plan-marshall/skills/plan-marshall-plan-marshall/` each list `SKILL.md`, `references`, `scripts`, `standards` and no `workflow`, while the source skill has `workflow/`. The installed `plan-marshall-phase-6-finalize` (OpenCode) and `plan-marshall-plan-orchestrator` (Antigravity) lack `workflow/` likewise.
- OBSERVED: the emitted OpenCode `plan-marshall` `SKILL.md` still routes to the missing files — read at `target/opencode/skill/plan-marshall-plan-marshall/SKILL.md:95-103,170-175,181` (`Read workflow/planning.md`, `Read workflow/planning-outline.md`, `Read workflow/execution.md`, `Read workflow/recipe.md`).
- OBSERVED: an existing test pins the four-name list as the contract — read at `test/marketplace/targets/opencode/test_emitter.py:169-171` § `test_verbatim_skill_subdirs_constant_exposed`; the Antigravity emitter test builds and checks its fixture by iterating the same constant at `test/marketplace/targets/antigravity/test_emitter.py:61,81`.
- OBSERVED: `test/marketplace/targets/test_sync.py` has no assertion on skill subdirectory copying — a search of the file for `standards`, `references`, `templates`, `scripts/` and `subdir` returns nothing.
- OBSERVED: `sync.py` must not import from the `marketplace.targets` package, whose `__init__` pulls in third-party dependencies — stated at `marketplace/targets/sync.py:19-23` and § `_load_cache_sync_module` docstring.
- OBSERVED: documentation restates the list — `doc/developer/antigravity.adoc:349` and the module docstrings at `marketplace/targets/opencode/emitter.py:7` and `marketplace/targets/antigravity/emitter.py:7`; `doc/developer/repository-layout.adoc:53` already names `workflow/` as a normal skill subdirectory.
- HYPOTHESIS: workflow documents dispatched by notation (`{bundle}:{skill}/workflow/{file}.md`, described at `doc/developer/marketplace-build.adoc:29-31`) are resolved on the non-Claude harnesses against the installed skill directory, so emitting the directory is sufficient and no notation resolver needs a change — confirm/refute at `marketplace/bundles/plan-marshall/agents/execution-context.md` and the body-transform rules in `marketplace/targets/opencode/mapping.json` / `marketplace/targets/antigravity/mapping.json` (verify-at-outline)
- HYPOTHESIS: files under the newly emitted subdirectories need no body transform to be usable; the four subdirectories copied today are also emitted byte-for-byte, so the plan keeps that behaviour — confirm/refute at `marketplace/targets/body_transform_engine.py` and its call sites in both `target.py` modules (verify-at-outline)
- HYPOTHESIS: the Antigravity `install.sh` and the OpenCode `install.sh` templates copy skill directories whole and need no matching change — confirm/refute at `marketplace/targets/antigravity/templates/install.sh` and `marketplace/targets/opencode/templates/install.sh` (verify-at-outline)
- HYPOTHESIS: the small count differences between the Claude tree and the two others for the four allowed names (`standards` 103 against 104, `references` 21 against 20) come from `targets:` scoping and stale local `target/` trees, not from a second defect — confirm/refute by regenerating all three targets and re-counting (verify-at-outline)
- Verify-first clause: before scoping deliverable 1, decide the exclusion rule for loose files and say it in one place: the plan assumes "emit every file except `SKILL.md`, `EXCLUDED_DIR_NAMES` members, dot-files, and `targets:`-scoped paths". If any skill directory holds a file that must not reach a non-Claude harness, that file gets a `targets:` scope or a named exclusion; a new allow-list is not an acceptable outcome.
- Verify-first clause: before writing deliverable 3, enumerate the route grammars actually used in `SKILL.md` bodies (Markdown links, backticked `Read workflow/x.md`, bundle notation) and fix which ones the test extracts; a route form the test does not parse must be listed in the test as a known gap, not silently skipped.
- Verify-first clause: confirm at outline whether the content-drift and equality checks under `marketplace/targets/claude/` or any dist-manifest test count emitted files per target; a file-count pin would need updating with deliverable 1.

## Expected Surface

- OBSERVED: `marketplace/targets/opencode/emitter.py` — `VERBATIM_SKILL_SUBDIRS`, `_emit_skill`, `_copy_verbatim`, module docstring, `__all__`
- OBSERVED: `marketplace/targets/antigravity/emitter.py` — `VERBATIM_SKILL_SUBDIRS`, `_emit_skill`, `_copy_verbatim`, module docstring, `__all__`
- OBSERVED: `marketplace/targets/sync.py` — `VERBATIM_SKILL_SUBDIRS`, `_deploy_skill`
- OBSERVED: `test/marketplace/targets/opencode/test_emitter.py` — `test_verbatim_skill_subdirs_constant_exposed` and the fixture skill layout
- OBSERVED: `test/marketplace/targets/antigravity/test_emitter.py` — `fixture_bundle`, `test_emit_bundles_copies_verbatim_subdirs`
- OBSERVED: `test/marketplace/targets/test_sync.py` — new deploy and prune cases for arbitrary subdirectories
- HYPOTHESIS: `test/marketplace/targets/test_skill_route_emission.py` — new route-closure test over the real bundles for every target (verify-at-outline)
- OBSERVED: `doc/developer/antigravity.adoc` — line 349 restates the four-name list
- HYPOTHESIS: `doc/developer/opencode.adoc` — may describe the emitted skill layout (verify-at-outline)
- HYPOTHESIS: `marketplace/targets/README.md` — may describe the emitted skill layout (verify-at-outline)
- HYPOTHESIS: `marketplace/targets/component_targets.py` — home for a shared "is this skill file emitted" predicate if the two emitters stop duplicating it (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-15 (`PLAN-LB-15-plugin-registry-pin.md`) — both edit `marketplace/targets/sync.py`. This plan touches `VERBATIM_SKILL_SUBDIRS` and `_deploy_skill` (the OpenCode/Antigravity deploy path); PLAN-LB-15 touches the Claude leg (`_sync_claude`, `cache_sync.py`) and the aggregate result. The functions are disjoint but the file is shared, so the two run in sequence, in either order.
- Adjacent to: `marketplace/targets/claude/emitter.py` — already copies the whole bundle; it is the reference behaviour and is not changed.
- Adjacent to: `marketplace/targets/body_transform_engine.py` and the two `mapping.json` files — vocabulary rewriting of the emitted bodies; whether subdirectory documents should be transformed too is a separate question and is left out on purpose.
- Adjacent to: the `dist-opencode` / `dist-antigravity` publication described in `doc/developer/distribution.adoc` — it publishes the generated tree, so it picks the fix up with no change of its own.
- Operational note: after this plan merges, the installed OpenCode and Antigravity copies stay incomplete until `/sync-harnesses` is run once on the developer machine; the plan's own finalize sync step does that when it runs in the normal lane.
- Left out on purpose: making the missing-route test part of the sync step's runtime output (a sync-time detector), and any change to how non-Claude harnesses are exercised as runtimes — only Claude Code is tested as a runtime.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-17-non-claude-workflow-docs.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
