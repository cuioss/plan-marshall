# PLAN-LB-97: A flat install finds its sibling skills — the finalize step docs, the build extensions and the executor generator resolve without a bare skill-name join

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-97-flat-install-skill-resolution.md` and is queued as one row file, `queue/PLAN-LB-97.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-26, **high**, on the operator's instruction ("spec the plan"), from a failure the operator met on the
> `pm-mcp-core` project: a `marshall-steward` upgrade under OpenCode stopped at Stage 2 with
> `manage-config sync-defaults --backfill-bot-roster` → `configurable contract: step body doc not found:
> /home/oliver/.config/opencode/skills/automatic-review/SKILL.md`. The deployed and the plugin-cache copies of 0.1.2017 are
> byte-identical and the nested cache copy ran the same verb fine, so the defect is the flat-layout resolution, not a stale
> install. It is the concrete form of residue R1 and R2 of PLAN-LB-96 (#1868), which that landing recorded and the ledger held at
> medium until a second-machine run. **HOLD: do not emit until the operator has the second-machine result.** That result may add
> sites to this plan; re-ground before emitting. **Each deliverable is its own outline deliverable, and each Done-when is its own
> success criterion. Do not merge them.** A criterion that says "fails at `a1f981b94`" is evidenced only by a run against that
> tree.

## Objective

A script that runs from a flat deployed tree (OpenCode `skills/{bundle}-{skill}/`, Antigravity) must reach a sibling skill's
files. Nested trees name a skill by its bare name (`skills/phase-6-finalize/`); a flat tree names it `{bundle}-{skill}`
(`skills/plan-marshall-phase-6-finalize/`). PLAN-LB-96 made the bundles root and extension discovery flat-aware. A group of
scripts still builds a sibling skill's path by joining a bare skill name onto the skills root, so on a flat install the path does
not exist: the finalize step body docs and `automatic-review` cannot be read (`manage-config sync-defaults`, `step-get`, and the
`manage-execution-manifest` loadability checks all depend on them), the four build skills' extensions are not found (no
file-to-build route derivation), and the `marshall-steward` mode script names a `generate_executor.py` that does not exist. The
consequence the operator met is the worst one: the upgrade verb of `marshall-steward` cannot complete on any flat install, so a
flat install cannot be brought to a new version.

The shared layer already carries the flat vocabulary: `deployed_layout.flat_skill_dir_name`, `resolve_skill_path`,
`skill_roots`, and `marketplace_bundles.resolve_bundle_path`. The sites do not use it.

## Where the delta is (measured)

- `extension-api/scripts/configurable_contract.py` L61 `_phase_6_skill_dir()` returns `resolve_skills_root(Path(__file__)) /
  'phase-6-finalize'`, and L166-169 resolves the promoted `plan-marshall:automatic-review` and `automatic-review` ids to
  `skills_root / 'automatic-review' / 'SKILL.md'`. Every built-in step id ends at one of these two joins (workflow/ then
  standards/ under the phase-6 directory).
- Reproduced here against this machine's installed flat OpenCode tree (`~/.config/opencode/skills`, all script directories on
  `sys.path`, `python3 -I`): `resolve_step_doc_path('plan-marshall:automatic-review')` returns
  `~/.config/opencode/skills/automatic-review/SKILL.md` (absent) and `resolve_step_doc_path('default:push')` returns
  `~/.config/opencode/skills/phase-6-finalize/workflow/push.md` (absent). The first path is the one the `pm-mcp-core` report names.
- `manage-execution-manifest/scripts/_manifest_validation.py` L191-193 builds `_PHASE_6_SKILL_DIR` (and the `workflow` and
  `standards` directories under it) and L200 `_AUTOMATIC_REVIEW_SKILL_MD` the same way, at import time.
- `extension-api/scripts/extension_discovery.py` L92 joins `script-shared/scripts/extension`; L108-128
  `get_build_extension_paths` joins each of the four build-skill names (`build-pyproject`, `build-maven`, `build-gradle`,
  `build-npm`) and keeps only the ones whose `scripts/extension.py` exists, so on a flat tree it returns an empty list and
  `discover_build_extensions` finds none (residue R2 of PLAN-LB-96); L1395 and L1641 join `phase-5-execute` (the built-in step
  scans, residue R1).
- `marshall-steward/scripts/determine_mode.py` L1199 returns `_SKILLS_DIR / 'tools-script-executor' / 'scripts' /
  'generate_executor.py'`, while the same file's L176-180 import loop already tries `plan-marshall-{lib}` as a flat fallback, as
  do `bootstrap_plugin.py`, `gitignore_setup.py` and `permission_fix.py`.
- The generated flat tree carries the same inner layout under the flat names: `plan-marshall-automatic-review/SKILL.md`,
  `plan-marshall-phase-6-finalize/{workflow,standards}/`, `plan-marshall-phase-5-execute/standards/` (listed in
  `target/opencode/skill/` this pass), so the files exist; only the join is wrong.
- Other sibling-skill joins are anchored on `Path(__file__).parent...` rather than on `resolve_skills_root`:
  `tools-integration-ci/_ci_log_filter.py` L289-290, `ci_base.py` L2134, `script-shared/build/_build_queue_slot.py` L94 and L116,
  `_build_execute_factory.py` L173, `workflow-integration-git/integrate_into_main.py` L118, `git-workflow.py` L1721 and
  `prepare_execute.py` L236. Whether each one has a flat fallback was not read.

## Deliverables

1. **Built-in step docs, build extensions and the executor generator resolve through one flat-aware helper.**
   - One function answers "the directory (or file) of skill `S` of bundle `B`, as deployed here" for a nested checkout, the
     versioned plugin cache and a flat tree, built on `deployed_layout` (`flat_skill_dir_name`, `resolve_skill_path`) and
     `marketplace_bundles.resolve_bundle_path`. Whether it is a new function beside `resolve_skills_root` or a call to the existing
     `resolve_bundle_path` is decided at outline and the reason is recorded; no second spelling of the flat name `{bundle}-{skill}`
     is written.
   - Every join in the measured list above goes through it: `configurable_contract` (L61, L166-169), `_manifest_validation`
     (L191-193, L200), `extension_discovery` (L92, L108-128, L1395, L1641) and `determine_mode` (L1199). The nested and cache
     results are unchanged and keep their order.
   - A missing skill is reported against the path the helper looked for, naming both shapes, so a flat install no longer reads as
     an incomplete one.

   *Done when:* tests, against the flat fixture PLAN-LB-96 added (`test/plan-marshall/_flat_install_fixtures.py`, built from the
   real emitter output): `resolve_step_doc_path` returns an existing file for `plan-marshall:automatic-review`, `default:push`,
   `default:sonar-roundtrip` and one `standards/`-resident step, and `get_build_extension_paths` returns the four build skills'
   `extension.py` paths (each fails at `a1f981b94`); `determine_mode`'s generator path exists in the fixture; the same assertions
   in a nested marketplace fixture and a versioned-cache fixture return what they returned before.

2. **A guard keeps every sibling-skill join honest.**
   - A test finds, over `marketplace/bundles/**/scripts/*.py`, every join of a literal skill name onto a path derived from the
     skills root (`resolve_skills_root(...)`, a `_SKILLS_DIR`-style constant, or a `Path(__file__)` parent chain) and asserts each
     one is either routed through D1's helper or declared in the test with the reason it is flat-safe (for example the
     `plan-marshall-{lib}` import loops that already try the flat name).
   - The population is discovered from the source (AST or a bounded regex over the tree), not hand-listed, and is compared with
     the declarations in both directions, as `test_flat_install_call_sites.py` does for `resolve_bundles_root`.

   *Done when:* tests: the guard fails at `a1f981b94` on the joins listed in D1 and passes after; dropping one declaration, and
   adding an undeclared join to a scratch module in the scanned tree, each turn it red (mutation evidence, order labelled).

3. **The remaining sibling-skill joins are classified and the broken ones fixed.**
   - Each site in the last bullet of the measured list is read and put in one of two groups: it already tries the flat name or
     never runs on an installed tree (declared in D2's guard with the reason), or it fails on a flat tree (routed through D1's
     helper). The classification is recorded in the guard's declarations and in the PR.
   - A site that executes at import time or on the upgrade and lane paths (`git-workflow` regenerating the executor,
     `prepare_execute`, the build-queue slot, the CI log filter) is exercised from the flat fixture, not only declared.

   *Done when:* every listed site is either declared flat-safe with a one-line reason the guard checks, or a flat-fixture test
   executes it and passes (the ones classified as broken fail at `a1f981b94`).

4. **The upgrade reconcile runs on a flat install.**
   - The verbs the `marshall-steward` upgrade runs in Stage 2 work against the flat fixture and return what they return on a
     nested one: `manage-config sync-defaults --backfill-bot-roster`, `manage-config` `step-get` for the finalize steps, and the
     `manage-execution-manifest` compose and loadability path that imports `_manifest_validation`.
   - The bot roster read from `automatic-review/SKILL.md` on a flat install is the nested one (`required_bots: coderabbit`,
     `optional_bots: sourcery`), proving the doc read is the same bytes.
   - Any further verb of the upgrade flow that fails on the flat fixture for the same family of cause is fixed here; one that
     fails for a different cause is reported in the landing, not fixed.

   *Done when:* tests drive each named verb against the flat fixture (they fail at `a1f981b94` with `step body doc not found`
   or an import-time resolution error) and assert the same TOON status and roster as the nested fixture.

Split guard: four deliverables, one theme (a flat tree finds its sibling skills). D1 is the resolver and its sites, D2 the guard
that keeps the population closed, D3 the sites outside the first list, D4 the end-to-end upgrade path. D3 and D4 depend on D1
only through the helper; a run may order them freely and report each on its own.

## Claim Labels

- OBSERVED (D1): `configurable_contract.py` L61 `_phase_6_skill_dir` returns `resolve_skills_root(Path(__file__)) / 'phase-6-finalize'`, and L166-169 resolve `plan-marshall:automatic-review` and `automatic-review` to `skills_root / 'automatic-review' / 'SKILL.md'` (read at `a1f981b94`).
  - verdict: corroborated | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: configurable_contract.py L61 returns resolve_skills_root(...) / 'phase-6-finalize'; L166-169 join 'automatic-review' / 'SKILL.md' for the two promoted ids (read in full).
- OBSERVED (D1, D4): reproduced against this machine's installed flat OpenCode tree: `resolve_step_doc_path('plan-marshall:automatic-review')` returns `~/.config/opencode/skills/automatic-review/SKILL.md` and `resolve_step_doc_path('default:push')` returns `~/.config/opencode/skills/phase-6-finalize/workflow/push.md`; neither file exists (orchestrator-run probe, `python3 -I`).
  - verdict: corroborated | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Run this pass: python3 -I with every plan-marshall-*/scripts dir of ~/.config/opencode/skills on sys.path; resolve_step_doc_path for plan-marshall:automatic-review, default:automatic-review and default:push returned paths directly under skills/ (automatic-review/SKILL.md, phase-6-finalize/workflow/...), is_file False.
- OBSERVED (D1): the generated flat tree holds `plan-marshall-automatic-review/SKILL.md`, `plan-marshall-phase-6-finalize/workflow/` and `standards/`, and `plan-marshall-phase-5-execute/standards/` (listed under `target/opencode/skill/` at `a1f981b94`).
  - verdict: corroborated | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Listed target/opencode/skill: plan-marshall-automatic-review/SKILL.md and standards/*.md, plan-marshall-phase-6-finalize/{workflow,standards,references,templates}, plan-marshall-phase-5-execute/standards/ (five docs) all exist.
- OBSERVED (D1): `_manifest_validation.py` L191-193 and L200 join `phase-6-finalize` and `automatic-review` onto `resolve_skills_root(Path(__file__))` at import time (read at `a1f981b94`).
  - verdict: corroborated | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Read _manifest_validation.py L184-224: L191 _PHASE_6_SKILL_DIR, L192-193 workflow and standards dirs under it, L200 _AUTOMATIC_REVIEW_SKILL_MD, all from resolve_skills_root(Path(__file__)) / bare name at module level.
- OBSERVED (D1): `extension_discovery.py` L92 and L108-128 (`get_build_extension_paths`, four bare build-skill names) join a bare skill name onto the skills root; L1395 and L1641 do the same for `phase-5-execute` (the last two seen as grep lines, not read in full).
  - verdict: corroborated | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Read extension_discovery.py L84-128: L92 joins script-shared/scripts/extension; get_build_extension_paths joins the four bare build-skill names and keeps existing files only. L1395 and L1641 seen as grep lines (phase-5-execute joins), not read in full.
- OBSERVED (D1): `determine_mode.py` L1199 joins `tools-script-executor` onto `_SKILLS_DIR`, while L176-180 of the same file try `plan-marshall-{lib}` as a flat fallback for the import loop (grep lines at `a1f981b94`).
  - verdict: corroborated | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: grep lines: determine_mode.py L176 _SKILLS_DIR = resolve_skills_root, L178-180 import loop tries _lib then plan-marshall-{_lib}, L1199 returns _SKILLS_DIR / 'tools-script-executor' / 'scripts' / 'generate_executor.py' with no flat spelling. Surrounding function not read.
- OBSERVED (D1): `deployed_layout.resolve_skill_path(root, bundle, relative_path)` returns the flat path of a skill-anchored subpath or `None`, and `flat_skill_dir_name(bundle, skill)` is the one spelling of the flat name; `resolve_skills_root` returns the `skills` directory when its parent carries `opencode.json` (read at `a1f981b94`).
  - verdict: corroborated | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Read deployed_layout.py L291-341 (resolve_skill_path probes skill_roots with flat_skill_dir_name, returns None when absent) and marketplace_bundles.py L330-375 (resolve_skills_root accepts a manifest beside the skills dir: .claude-plugin/plugin.json, plugin.json or opencode.json).
- HYPOTHESIS (D3): the `Path(__file__).parent...` sibling-skill joins in `_ci_log_filter.py`, `ci_base.py`, `_build_queue_slot.py`, `_build_execute_factory.py`, `integrate_into_main.py`, `git-workflow.py` and `prepare_execute.py` are broken on a flat install, or each has a flat fallback or runs only in a source checkout (verify-at-outline by reading each and running it from the flat fixture).
  - verdict: unverifiable | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Only grep lines were seen (_ci_log_filter L289-290, ci_base L2134, _build_queue_slot L94 and L116, _build_execute_factory L173, integrate_into_main L118, git-workflow L1721, prepare_execute L236); none of the sites was read for a flat fallback, nor run from a flat tree. Open for the outline.
- HYPOTHESIS (D4): the `pm-mcp-core` lane stopped at the first failing verb, so other Stage 2 verbs of the upgrade (`step-get`, the manifest compose, the executor regeneration) fail on a flat install for the same cause or not at all (verify-at-outline by driving each against the flat fixture; the lane's own read-only `step-get` ran from the nested cache copy and said nothing about the flat one).
  - verdict: unverifiable | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Not checked here. The second machine's steward report shows the same step-doc failure in sync-defaults on a flat OpenCode install and a completed reconcile with OPENCODE unset (Claude-cache copy). Which further Stage 2 verbs fail on a flat tree is not shown by either report; open for the outline.
- Verify-first clause (D1): decide whether the helper is a new function beside `resolve_skills_root` or a use of the existing `resolve_bundle_path`, and what a missing skill returns (a path to report against, as `resolve_step_doc_path` does today, or `None`), before the sites are changed; record why.
  - verdict: unverifiable | checked_at: a1f981b949c7dccf133acbd18800549bd89a9fbe | by: live-blockers/cleanup | rescoped: n/a | evidence: Outline-time design decision (new helper beside resolve_skills_root versus resolve_bundle_path, and the missing-skill return), not a code fact at HEAD.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/configurable_contract.py` — `_phase_6_skill_dir`, `resolve_step_doc_path` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py` — `_PHASE_6_SKILL_DIR`, `_AUTOMATIC_REVIEW_SKILL_MD` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — `get_extension_api_scripts_path`, `get_build_extension_paths`, the two `phase-5-execute` scans (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py` — the generator path at L1199 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py` and `deployed_layout.py` — the helper's home, reused rather than re-spelled (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/_ci_log_filter.py` and `ci_base.py`, `script-shared/scripts/build/_build_queue_slot.py` and `_build_execute_factory.py`, `workflow-integration-git/scripts/integrate_into_main.py`, `git-workflow.py` and `prepare_execute.py` — the sibling joins D3 classifies; changed only where the read shows they fail on a flat tree (verify-at-outline) (D3)
- HYPOTHESIS: `test/plan-marshall/_flat_install_fixtures.py` — reused from PLAN-LB-96, extended where a verb needs more of the tree (verify-at-outline) (D1, D4)
- HYPOTHESIS: `test/plan-marshall/script-shared/` — the guard beside `test_flat_install_call_sites.py` (D2)
- HYPOTHESIS: `test/plan-marshall/extension-api/`, `manage-config/`, `manage-execution-manifest/`, `marshall-steward/` — the existing tests that stay green and the new flat-fixture tests (D1, D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-96 (shipped, #1868): its `resolve_bundles_root` flat leg and `test/plan-marshall/_flat_install_fixtures.py`. Nothing else unshipped.
- **Hold: not to be emitted until the operator has weighed the second-machine result.** The first report is in: on the second machine a `marshall-steward` upgrade and land completed at 0.1.2017 (executor regenerated, `sync-defaults --backfill-bot-roster` added 2 params and materialized 5 lanes, `executor-preflight` all `0.1.2017`). The operator confirms that machine also ran OpenCode, so the same verb passed on one OpenCode install and fails on another. Two probes settle most of it. A direct import of the flat OpenCode tree on the second machine (`~/.config/opencode/skills`, `python3 -I`) loads the flat `configurable_contract.py` and resolves `plan-marshall:automatic-review` to `~/.config/opencode/skills/automatic-review/SKILL.md`, which does not exist: the defect is present there exactly as here. Both machines' executors carry the same two entries per script (the `default-bundle:plan-marshall-*` flat copy and the `plan-marshall:*` nested Claude cache copy), and the executor picks by the runtime harness detected from the environment, falling back to the declared root order (Claude cache first) when nothing signals one. So whether an upgrade hits the flat copy depends on the session's environment, not on the machine: the second machine's steward hit the same `step body doc not found: ~/.config/opencode/skills/automatic-review/SKILL.md` failure in `sync-defaults --backfill-bot-roster` and completed the reconcile by running the `manage-config` verbs with `OPENCODE` unset, so the executor dispatched the Claude-cache copy of the same 0.1.2017 code (no file hand-edited; `marshal.json` written only through the scripts). Its report names the same fix as D1: resolve the step doc through `deployed_layout.resolve_skill_path`, which already models both shapes. The defect is real on both machines; D1 to D4 stand. Add or drop sites (PLAN-LB-96 R3 and R4 are deliberately left out of this plan) before the emit.
- Overlaps with: the staged PLAN-LB-93 on `marshall-steward/scripts/determine_mode.py`, `script-shared/scripts/deployed_layout.py` and `test/plan-marshall/script-shared/`. Neither edits the other's functions as far as the specs say; the emit gate decides, and the order is the operator's. This plan is the more blocking of the two (a flat install cannot upgrade without it).
- No file shared with the running PLAN-LB-58 (its `extension-api` touch is a standards doc, not the discovery script).
- Operator workaround until this ships: run the remaining Stage 2 reconcile verbs against the byte-identical nested plugin-cache copy of the same version, then verify and land. It hides the defect; it is not the fix.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-97-flat-install-skill-resolution.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
