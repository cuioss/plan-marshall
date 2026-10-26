# PLAN-LB-96: A flat OpenCode install works end to end — it resolves its bundles root without a bundle marker, and extension discovery finds the domain bundles in it

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-96-flat-install-bundles-root.md` and is queued as one row file, `queue/PLAN-LB-96.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-26, **critical**, on the operator's instruction ("stage it"), from a failure the operator met on a second
> machine: a runbook lane under OpenCode stopped at `runbook_lane resolve` with
> `resolve_bundles_root: could not locate a 'plan-marshall' bundle above
> /Users/oliver/.config/opencode/skills/plan-marshall-manage-architecture/scripts/_cmd_client_build.py`. A second report from
> the same machine put the same failure to the lane as a blocking question. **Widened the same day by operator instruction
> ("Widen the plan now"):** with a hand-made bundle marker in place the lane passed that error and stopped at the next one,
> `find_extension_path` finding no bundle, so `architecture modules` was empty and neither `quality-gate` nor `verify`
> resolved (D4). **Each deliverable is its own outline deliverable,
> and each Done-when is its own success criterion. Do not merge them.** A criterion that says "fails at `cff686064`" is
> evidenced only by a run against that tree.

## Objective

A script that runs from a flat deployed tree (OpenCode `skills/{bundle}-{skill}/`, Antigravity) must find its bundles root
without a `plan-marshall/.claude-plugin/plugin.json` ancestor. `resolve_bundles_root` accepts only the two nested shapes (the
marketplace source and the versioned plugin cache) and raises for a flat tree, which has no bundle directory at all. Six call
sites run it at import time, so the import itself raises and the command never starts. The consumers that matter on a flat install
(`runbook_lane`, `manage-architecture`, `manage-config`, `manage-execution-manifest`) are all dead on an OpenCode machine that does
not happen to carry a hand-made marker. The rest of the shared layer already handles the flat shape: `resolve_bundle_path`,
`collect_script_dirs` and `deployed_layout` take a flat root. Only the one walk that finds the root does not.

A second break sits behind the first. Extension discovery (`discover_all_extensions`, `_scan_skills_roots_for_implementors`)
lists directories under the bundles root and treats each as a bundle, and a flat tree has none; and even a flat-aware
enumeration finds nothing, because the OpenCode and Antigravity emitters write only `name`, `description`, `mode`,
`compatibility` and the `metadata` identity block into a skill's frontmatter, so a domain bundle's `implements:
…/ext-point-domain-bundle` declaration, the only thing `find_extension_path` reads, never reaches the deployed file. With no
extension found, module discovery is empty and no build command resolves: a lane cannot run its quality gate or its tests.

## Where the delta is (measured)

- `script-shared/scripts/marketplace_bundles.py` L246-287 `resolve_bundles_root` walks the script's parents and returns the first
  ancestor holding `plan-marshall/.claude-plugin/plugin.json` or `plan-marshall/<version>/.claude-plugin/plugin.json`; otherwise it
  raises `RuntimeError`. It has no flat leg. Its sibling `resolve_skills_root` (L290-335) accepts a skill-root ancestor but demands a
  manifest beside it.
- Six call sites run it at import time: `manage-architecture/_cmd_client_build.py` L120, `manage-config/_config_core.py` L39,
  `manage-execution-manifest/_manifest_validation.py` L211, `pm-plugin-development/.../plugin_discover.py` L47,
  `plugin-doctor/_doctor_shared.py` L37 and `_cmd_extension.py` L24. `runbook_lane.py` L444 and L502, `recipe_scoring.py` L355,
  `manage_personas.py` and `manage-metrics.py` call it inside functions.
- Reproduced in this pass against the freshly generated OpenCode tree (`target/opencode/skill`, all script directories on
  `sys.path`): all six import-time modules raise `resolve_bundles_root: could not locate a 'plan-marshall' bundle above …`.
- This machine's installed OpenCode tree masks it: `~/.config/opencode/skills/plan-marshall/.claude-plugin/plugin.json` exists
  ("Bundle-identity shim for the flat OpenCode deployment", version 0.1.2010), which satisfies the nested walk. No file in the
  repository at `cff686064` writes it, so a machine without it fails.
- `extension-api/scripts/extension_discovery.py` L374-403 `discover_all_extensions` iterates `get_marketplace_bundles_path()` and
  calls `find_extension_path(bundle_dir)` per directory; L333-371 `find_extension_path` scans `{bundle}/skills/*/SKILL.md` and
  `{bundle}/{version}/skills/*/SKILL.md` for `implements: plan-marshall:extension-api/standards/ext-point-domain-bundle`.
  L1124-1204 `_scan_skills_roots_for_implementors` iterates the same way (via `_resolve_bundle_skills_root`, L1096-1121). Neither
  consults `deployed_layout`'s flat enumeration, so a flat root yields no bundle.
- `marketplace/targets/opencode/frontmatter.py` L229-284 `transform_skill_frontmatter` emits `name`, `description`, `mode`,
  `compatibility` and the identity `metadata` block only. The generated
  `target/opencode/skill/plan-marshall-plan-marshall-plugin/SKILL.md` carries no `implements:` line, while the source
  `skills/plan-marshall-plugin/SKILL.md` L4 does. `marketplace/targets/antigravity/frontmatter.py` L194 writes the same shape.
- The generated flat tree does carry each domain bundle's `extension.py` beside its `SKILL.md`, in a directory named
  `{bundle}-plan-marshall-plugin` (ten of them in `target/opencode/skill`), and `deployed_layout.read_flat_skill_identity` reads
  the bundle and skill back from the `metadata` block.

## Deliverables

1. **`resolve_bundles_root` resolves a flat deployed tree.**
   - After the two nested probes find nothing, the walk takes the nearest ancestor that is a flat skill root
     (`deployed_layout.SKILL_ROOT_NAMES`, not a nested bundle's own `skills/`, per `deployed_layout.is_bundle_skill_root`) and
     returns the directory that CONTAINS it. That is the form `resolve_bundle_path`, `collect_script_dirs` and
     `deployed_layout.skill_roots` already accept, so every consumer of the returned root resolves flat paths unchanged.
   - The flat predicate and the skill-root vocabulary are the ones `deployed_layout` carries; no second spelling is written.
   - The nested probes run first and their result is unchanged, so a marketplace checkout, a versioned plugin cache and a flat tree
     that also carries the shim all resolve exactly as before.
   - A tree that is neither nested nor flat still raises, with the walked chain, and the message names both shapes it looked for.

   *Done when:* tests: a flat fixture (`{root}/skills/plan-marshall-{skill}/scripts/x.py`, no `plan-marshall/` directory anywhere,
   no manifest) resolves to `{root}`, for both the plural `skills` and the generated singular `skill`; a nested marketplace fixture
   and a versioned-cache fixture return what they returned before; a directory that is neither raises with both shapes named. The
   flat case fails at `cff686064` (`RuntimeError`).

2. **The six import-time modules import in a marker-less flat tree, and a guard keeps every caller of the walk honest.**
   - Every call site is read against the value it receives. `resolve_bundle_path(BUNDLES_DIR, …)` callers (`_config_core`,
     `_cmd_client_build`) work on the flat root with no change. `_manifest_validation` L211 derives `_REPO_ROOT` as
     `resolve_bundles_root(...).parent.parent`, which is meaningless for a flat root; it must not raise and must keep the
     behaviour its docstring (L219-225) describes for the cache layout. The three `pm-plugin-development` modules are authoring
     tools that are meaningless on an installed tree; they must import (so `--help` and discovery do not crash) and report the
     absence of a marketplace tree in their own terms.
   - A guard test finds every `resolve_bundles_root(` call site under `marketplace/bundles/` and asserts each one is covered by
     the flat fixture of D1 (imported, or called, in the fixture), so a seventh import-time call cannot be added unprotected.

   *Done when:* tests: against one marker-less flat fixture built from the generated tree layout, the six modules import without
   raising and `runbook_lane resolve` against a spec path in a fixture checkout returns its resolve envelope, not `resolve_failed`
   (it fails at `cff686064`); the guard fails at HEAD if one call site is left out of the fixture list and passes after.

3. **The failure names the flat shape and the fix, and a flat tree is no longer reported as "incomplete".**
   - When a tree is neither nested nor flat, the `RuntimeError` says so in terms an operator can act on. The two reports behind this
     plan read it as an incomplete install and asked for a reinstall, and one probed a flat directory by its un-prefixed name
     (`skills/tools-script-executor`, where the flat name is `skills/plan-marshall-tools-script-executor`).
   - The flat name rule is stated once where an operator looks first. Pick the existing home at outline
     (`tools-script-executor/SKILL.md` or the OpenCode target doc); do not add a new document.

   *Done when:* a test pins the message for the neither-shape case (both shapes named, the flat directory pattern shown); the doc
   sentence exists in one place and `plan-doctor` / the docs verify pass.

4. **Extension discovery finds the domain bundles in a flat deployed tree, so module discovery and the build commands resolve.**
   - The flat targets deploy a skill's `implements:` declaration: `transform_skill_frontmatter` of the OpenCode and the
     Antigravity emitter write it (the same value, scalar or block sequence, verbatim from the source) into the generated
     frontmatter, so the deployed file declares the archetype the source declares. Where it goes in the frontmatter (top level or
     under `metadata`) is chosen at outline against `read_implements_field`, which accepts either; the reason is recorded.
   - `discover_all_extensions` and `_scan_skills_roots_for_implementors` enumerate a flat root through `deployed_layout`
     (`flat_skill_dirs`, `read_flat_skill_identity`) and attribute each implementor to its bundle from the recorded identity,
     never by splitting the directory name (`is_flat_skill_dir_name` says that cannot be done). The nested and versioned legs
     and their order are unchanged; the flat leg runs when the root deploys the flat shape.
   - `find_extension_path` keeps its contract: no path heuristic, no body reading. A flat skill that does not declare the
     archetype is not discovered.

   *Done when:* tests: a fixture built by running the real OpenCode emitter over a two-bundle source (one domain bundle with an
   `extension.py`) yields a deployed `SKILL.md` that `read_implements_field` reads as the domain-bundle archetype (it returns
   an empty list at `cff686064`); with that fixture as the only root, `discover_all_extensions()` returns the domain bundle
   under its real bundle name and `discover_applicable_extensions` on a project the extension recognises returns a non-empty
   module list (both empty at `cff686064`); `_scan_skills_roots_for_implementors` finds a bundle-optional implementor in the
   same fixture. The same three assertions run against an Antigravity-emitted fixture. A nested marketplace fixture and a
   versioned-cache fixture return what they returned before.

Split guard: four deliverables, one theme (a flat tree works end to end). D1 is the root fix, D2 its call sites and guard, D3
the message, D4 the extension discovery behind it. D4 depends on D1 only through the shared fixture; a run may order them freely
and report each on its own.

## Claim Labels

- OBSERVED (D1): `marketplace_bundles.py` L246-287 `resolve_bundles_root` has two probes, `plan-marshall/.claude-plugin/plugin.json` and `plan-marshall/<version>/.claude-plugin/plugin.json`, and otherwise raises `RuntimeError`; it has no flat leg (read at `cff686064`).
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: marketplace_bundles.py L246-287: two probes (plan-marshall/.claude-plugin/plugin.json, plan-marshall/<version>/.claude-plugin/plugin.json), then RuntimeError; no flat leg.
- OBSERVED (D1, D2): import-time call sites are `_cmd_client_build.py` L120, `_config_core.py` L39, `_manifest_validation.py` L211, `plugin_discover.py` L47, `_doctor_shared.py` L37 and `_cmd_extension.py` L24; function-level ones are `runbook_lane.py` L444 and L502, `recipe_scoring.py` L355, `manage_personas.py` L516 and L639, `manage-metrics.py` L791 and L996, `_architecture_core.py` L295, L1178, L1209 and L1280, `_cmd_client_query.py` L675, `extension_discovery.py` L73, `_dep_index.py` L759 (grep at `cff686064`).
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: grep resolve_bundles_root( over marketplace/bundles: module-level at _cmd_client_build L120, _config_core L39, _manifest_validation L211, plugin_discover L47, _doctor_shared L37, _cmd_extension L24; the others sit inside functions or (extension_discovery L73) a helper.
- OBSERVED (D1): reproduced this pass: importing the six modules with every script directory of `target/opencode/skill` on `sys.path` raises `resolve_bundles_root: could not locate a 'plan-marshall' bundle` for all six (orchestrator-run probe, `python3 -I`).
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Run this pass: python3 -I probe with every scripts dir of target/opencode/skill on sys.path; _config_core, _cmd_client_build, _manifest_validation, plugin_discover, _doctor_shared, _cmd_extension each raised RuntimeError resolve_bundles_root: could not locate a plan-marshall bundle.
- OBSERVED (D1): this machine's installed OpenCode tree imports the same modules because `~/.config/opencode/skills/plan-marshall/.claude-plugin/plugin.json` exists; the repository at `cff686064` contains no writer of that file (grep for "identity shim" over `marketplace/`, `test/` and `doc/` is empty).
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read ~/.config/opencode/skills/plan-marshall/.claude-plugin/plugin.json (0.1.2010, identity-shim description); the same probe against ~/.config/opencode/skills passed five of six modules (plugin_discover failed on a probe artifact, see claim 8). grep for identity shim over marketplace, test and doc is empty.
- OBSERVED (D1): `resolve_bundle_path` (L127-167), `collect_script_dirs` (L180-243) and `deployed_layout.skill_roots` (L239-262) accept a flat root in both forms, the directory containing the skill root and the skill root itself.
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read marketplace_bundles.py L127-167 (resolve_bundle_path falls to deployed_layout.resolve_skill_path), L180-243 (collect_script_dirs enumerates flat_script_dirs first) and deployed_layout.py L239-262 (skill_roots accepts the containing directory and the skill root itself).
- OBSERVED (D2): `_manifest_validation.py` L211 `_REPO_ROOT = resolve_bundles_root(Path(__file__)).parent.parent` and its docstring at L219-225 describe the cache layout only.
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: grep _REPO_ROOT in _manifest_validation.py: L211 assignment from resolve_bundles_root(...).parent.parent; L221-222 docstring places it at ~/.claude/plugins for the cache layout; L271 relative_to(_REPO_ROOT). Only the grep lines were read, not the full function.
- HYPOTHESIS: the generated OpenCode and Antigravity trees carry no bundle marker in the install (nothing in `marketplace/targets/opencode/emitter.py` emits one; L106-157 only read manifests) (verify-at-outline against a fresh `/sync-harnesses` install, including the Antigravity tree).
  - verdict: unverifiable | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Partly seen: marketplace/targets/opencode/emitter.py only reads plugin.json (L127, L157) and the generated target/opencode tree holds no .claude-plugin at depth 3. The Antigravity emitter and a fresh sync install were not inspected.
- HYPOTHESIS: `_REPO_ROOT` of `_manifest_validation` is used only to relativise paths for the cache layout, so a flat value that is not a repository root is acceptable if no caller joins a repository-relative path to it (verify-at-outline; read the use at L271 and its callers).
  - verdict: unverifiable | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Only L271 (relative_to(_REPO_ROOT)) was seen; the callers of that helper and what they join to the result were not read. Open for the outline.
- HYPOTHESIS: `plugin_discover` imports once the subdirectory script paths (`script-shared/scripts/extension`) are on the path, as the executor puts them; the probe of this pass did not add subdirectories and so reported a missing `_build_discover` that is not a defect (verify-at-outline).
  - verdict: unverifiable | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_discover.py lives in script-shared/scripts/extension/ (a subdirectory) and collect_script_dirs adds subdirectories (L235-242), which my probe did not; so the earlier plugin_discover failure is a probe artifact by reading. Not re-run with the subdirectories on the path.
- OBSERVED (D4): `extension_discovery.py` L374-403 `discover_all_extensions` and L1124-1204 `_scan_skills_roots_for_implementors` iterate the directories under the bundles root as bundles; `find_extension_path` (L333-371) reads `implements:` from `{bundle}/skills/*/SKILL.md` or `{bundle}/{version}/skills/*/SKILL.md` (read at `cff686064`).
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read extension_discovery.py L374-403 (discover_all_extensions iterates bundle dirs under get_marketplace_bundles_path), L333-371 (find_extension_path scans {bundle}/skills and {bundle}/{version}/skills) and L1124-1204 (_scan_skills_roots_for_implementors iterates bundle dirs via _resolve_bundle_skills_root). No deployed_layout flat enumeration in any of them.
- OBSERVED (D4): `opencode/frontmatter.py` L229-284 `transform_skill_frontmatter` emits no `implements:`; the generated `plan-marshall-plan-marshall-plugin/SKILL.md` has no such line and the source `plan-marshall-plugin/SKILL.md` L4 has it (read and grep at `cff686064`).
  - verdict: corroborated | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read marketplace/targets/opencode/frontmatter.py L229-284: lines are name, description, mode (if present), compatibility, identity metadata. Read target/opencode/skill/plan-marshall-plan-marshall-plugin/SKILL.md L1-9: no implements line. grep on the source plan-marshall-plugin/SKILL.md: L4 implements: plan-marshall:extension-api/standards/ext-point-domain-bundle.
- HYPOTHESIS (D4): the Antigravity emitter drops `implements:` the same way (`antigravity/frontmatter.py` L194 writes the same fixed key set; its transform body was not read) and `read_implements_field` reads an indented `implements:` under `metadata:` because it strips each line before matching its key (verify-at-outline by reading the Antigravity transform and running the reader on an emitted file).
  - verdict: unverifiable | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Half read: read_implements_field (L256-295) strips each frontmatter line before matching its key, so an indented implements: under metadata: would match. The Antigravity transform body was not read (only the grep hit at antigravity/frontmatter.py L194 and a repo-wide grep showing no implements handling in targets/antigravity/frontmatter.py), and no emitted Antigravity file was run through the reader.
- HYPOTHESIS (D4): other readers of a skill's frontmatter on a flat tree (phase-5 and phase-6 step scans, `find_implementors`) are not affected, because those implementors are body docs under `workflow/` and `standards/` copied verbatim (verify-at-outline; confirm against a generated flat tree).
  - verdict: unverifiable | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: Not checked: the phase-5 and phase-6 implementor scans (_scan_phase5_for_implementors L1247, _scan_phase6_for_implementors L1207) and find_implementors were not read against a flat tree. Open for the outline.
- Verify-first clause (D1): decide what a tree that carries both a stray nested bundle and a flat skill root resolves to (the nested probes win; they have always run first) and record why, then confirm that a flat fixture with the hand-made shim resolves to the same root as before.
  - verdict: unverifiable | checked_at: cff68606426cd5961f6087e711e16b006d6a1fe7 | by: live-blockers/cleanup | rescoped: n/a | evidence: An outline-time decision, not a fact at HEAD. The existing order of the two nested probes is read (marketplace_bundles.py L272-283); no code answers the mixed-tree case.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py` — `resolve_bundles_root` (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py` — `SKILL_ROOT_NAMES`, `is_bundle_skill_root`, `skill_roots`; reused, not changed unless a predicate is missing (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py` — `_REPO_ROOT` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py`, `manage-architecture/scripts/_cmd_client_build.py`, `pm-plugin-development/.../plugin_discover.py`, `plugin-doctor/scripts/_doctor_shared.py`, `_cmd_extension.py` — call sites, changed only where the read in D2 shows they need it (verify-at-outline) (D2)
- OBSERVED: `test/plan-marshall/script-shared/test_marketplace_bundles.py` — the existing `resolve_bundles_root` tests that stay green (D1)
- HYPOTHESIS: `test/plan-marshall/script-shared/` — a new flat-fixture test beside it, and the call-site guard (verify-at-outline) (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — `discover_all_extensions`, `_scan_skills_roots_for_implementors`, `find_extension_path` (D4)
- OBSERVED: `marketplace/targets/opencode/frontmatter.py` — `transform_skill_frontmatter` (D4)
- HYPOTHESIS: `marketplace/targets/antigravity/frontmatter.py` — the same transform (verify-at-outline) (D4)
- HYPOTHESIS: `marketplace/targets/skill_identity.py` — the identity metadata lines, if `implements` is carried beside them (verify-at-outline) (D4)
- HYPOTHESIS: `test/plan-marshall/extension-api/test_extension_discovery.py` and `test_extension_discovery_behavior.py` — the existing discovery tests that stay green; a new flat-fixture test beside them, and the emitter tests under `test/` for the two targets (verify-at-outline) (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md` or the OpenCode target doc — the one sentence naming the flat directory pattern (verify-at-outline) (D3)

## Dependencies and Sequencing

- Depends on: nothing unshipped. PLAN-LB-94 (#1861) made the executor harness independent and reaches these scripts; this plan fixes what they do once reached.
- Overlaps with: the staged PLAN-LB-93 on `script-shared` (its flat-layout helper, D1-D2). That plan reuses `deployed_layout`'s flat helper in the generator's bootstrap; this plan reuses the same vocabulary in `marketplace_bundles.py`. Neither edits the other's functions, but both add tests under `test/plan-marshall/script-shared/`. Run this plan first; LB-93 is held.
- Adjacent to: PLAN-LB-95 (executor `PYTHONPATH`, no shared file), PLAN-LB-58 and PLAN-LB-82 (no shared file).
- Operator workaround until this ships: create `~/.config/opencode/skills/plan-marshall/.claude-plugin/plugin.json` on the affected machine (name `plan-marshall`, a version, a description), and, for D4, start the harness from a shell that has
  exported `PM_MARKETPLACE_ROOT` pointing at a plan-marshall checkout so extension discovery reads the source tree (untested).
  Both hide the defect and neither is the fix.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-96-flat-install-bundles-root.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
