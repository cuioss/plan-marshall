# PLAN-LB-95: The executor puts only the resolved script's own plugin version on PYTHONPATH — a consumer project with several cached versions imports the helpers of the version it runs

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-95-executor-pythonpath-own-version.md` and is queued as one row file, `queue/PLAN-LB-95.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-25, **critical**, on the operator's instruction ("analyze carefully and create a plan for fixing with the highest prio"),
> from a failure the operator met on a second machine: `marshall-steward` on a not yet enrolled project stopped at Step 4 with
> `ImportError: cannot import name 'STANDING_RULES_BRIDGE_MARKER' from 'antigravity_runtime'`, the module loaded from the `0.1.1916`
> cache directory while the script ran from `0.1.2010`. The cause is a regression PLAN-LB-94 (#1861, D3) shipped. **Each
> deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do not merge them.** A criterion
> that says "fails at `ee00687b8`" is evidenced only by a run against that tree.

## Objective

A generated executor that dispatches a script from a deployed plugin cache must build `PYTHONPATH` from the version of the cache
the script lives in, never from every version the cache holds. PLAN-LB-94 D3 made `PYTHONPATH` follow the resolved script's root
and implemented "root" as the whole cache directory, so a consumer project (or any harness install) with more than one cached
version gets every version's script directories, sorted oldest first; a helper module is then imported from the oldest cached
version that has it. Scripts that need a newer helper crash; scripts that do not crash run old helper code silently, which is worse.
Every consumer project carries several cached versions in normal use, and a developer checkout is spared only because its scripts
resolve to the tree.

## Where the delta is (measured)

- `execute-script.py.template` L588-621 `_same_root_script_dirs` globs `*/*/skills/*/scripts`, `*/skills/*/scripts`, `*/scripts`,
  `skills/*/scripts` and `skill/*/scripts` under the install root, returns `sorted(set(found))` (a plain string sort), and
  `pythonpath_for` (L624-643) appends the whole list after the script's own directory.
- On this machine the Claude cache holds 15 versions; the walk returns 1065 directories and puts `platform-runtime` of `0.1.1969`
  at position 38 and of `0.1.2010` at position 808, so the 15 copies of a helper resolve oldest first. The operator's machine
  reported the same shape with eight versions (`0.1.1916` at position 39, `0.1.2010` at position 366).
- The same file already knows the right order elsewhere: `harness_independent_resolver.py.template` L1-12 `_version_key` and
  L78-124 `_scripts_dirs_in_root` order version directories newest first by numeric tuple, and the recovery probe at L195-219 takes
  the newest. Only the new walk is unordered and unbounded.

## Deliverables

1. **The same-root walk returns only the resolved script's own version.**
   - From the resolved script path, take the version directory the script lives in: `{root}/{bundle}/{version}/skills/...` or
     `{root}/{version}/skills/...`. The walk enumerates the sibling bundles' directories **of that version** only
     (`{root}/*/{version}/skills/*/scripts`, or `{root}/{version}/skills/*/scripts`), so a helper is imported from the version the
     script belongs to.
   - A script in the flat shape (`{root}/{bundle}-{skill}/scripts`) has no versions and keeps its current handling.
   - A script outside every install root (a tree script, a project-local script) still gets no same-root walk.

   *Done when:* a test renders the real template into a consumer-project fixture (no marketplace tree) whose cache holds
   `plan-marshall/0.1.1916` and `plan-marshall/0.1.2010`, each with a `platform-runtime/scripts` module of the same name, the old one
   lacking a symbol the new one defines; dispatching a `0.1.2010` script that imports that symbol succeeds and the `PYTHONPATH`
   it was given contains no `0.1.1916` directory. It fails at `ee00687b8` (`ImportError`, and the old directory ahead of the new
   one).

2. **A sibling bundle that has no directory at the script's version resolves to its newest version, newest first by numeric
   version.**
   - When a bundle in the cache has no directory for the script's version (bundles are not always installed at one version), its
     newest version is used, ordered by `_version_key`, never by a string sort. `0.1.1000` outranks `0.1.999`.
   - The order is the same everywhere the executor orders versions: the new code reuses `_version_key`, it does not spell a second
     comparison.

   *Done when:* tests: a fixture with `pm-dev-python` at `0.1.2004` and `0.1.1916` and `plan-marshall` at `0.1.2010` puts only
   the `0.1.2004` directory of `pm-dev-python` on `PYTHONPATH` (it fails at `ee00687b8`: both are there, the old one first); a
   fixture where a bundle holds `0.1.999` and `0.1.1000` and none at the script's version resolves to `0.1.1000`. The second
   case is the guard against fixing D1 with a string `max()` or `sorted()`, which picks `0.1.999`; it passes at `ee00687b8` by
   accident of the string order and is reported as a forward guard, not as regression evidence.

3. **Every shape the walk served keeps working, and a guard keeps one version per skill ahead.**
   - The single-version nested shape, the `{root}/{version}` nested shape, the flat shape, an env-declared root and the tree case
     keep their `PYTHONPATH` unchanged (the PLAN-LB-94 D3 tests stay green).
   - A guard test asserts, for a multi-version fixture, that no skill appears twice in the dispatch `PYTHONPATH` with the older
     copy ahead of the newer one.

   *Done when:* the existing `test_d3_*pythonpath*` tests pass unchanged; the guard test fails at `ee00687b8` on the multi-version
   fixture and passes after.

4. **The regression is reproduced against the failure that was reported.**
   - The consumer fixture of D1 uses the reported shape: a helper that gained a symbol between two cached versions, a script from the
     newer version that imports it, and the cache holding more versions than the default retention keeps (at least eight).

   *Done when:* the test of D1 runs with eight cached versions and fails at `ee00687b8` with an `ImportError` naming the missing
   symbol; the failing output is recorded in the PR body.

Split guard: four deliverables, one theme (`PYTHONPATH` follows the resolved script's version). D1 is the fix, D2 its ordering
rule, D3 the guard against the sibling shapes, D4 the reproduction. A run may order them freely and report each on its own.

## Claim Labels

- OBSERVED (D1): `execute-script.py.template` L588-621 `_same_root_script_dirs` enumerates five glob patterns under the install root and returns `sorted(set(found))`; L624-643 `pythonpath_for` appends the whole list after the script's own directory (orchestrator-read at `ee00687b8`).
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: execute-script.py.template L588-621: five glob patterns under the install root, returns tuple(sorted(set(found))); pythonpath_for L624-643 appends the whole list after the script's own directory.
- OBSERVED (D1): introduced by PLAN-LB-94 (`git log -S_same_root_script_dirs` finds only `ee00687b8`); before it the `PYTHONPATH` came from the baked, generation-time directory list of one install.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: git log -S_same_root_script_dirs on the template finds only ee00687b8 (PLAN-LB-94, #1861).
- OBSERVED (D1): measured on this machine's Claude cache (15 versions): the walk yields 1065 directories, `platform-runtime` of `0.1.1969` at index 38 and of `0.1.2010` at index 808; 15 copies of that helper in total (orchestrator-run, string sort of the glob).
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Re-run in this pass: sorted glob of */*/skills/*/scripts under ~/.claude/plugins/cache/plan-marshall yields 1065 directories, platform-runtime 0.1.1969 at index 38 and 0.1.2010 at index 808, 15 copies.
- OBSERVED (D1): the operator's second machine, a project not yet enrolled, reported `ImportError: cannot import name 'STANDING_RULES_BRIDGE_MARKER' from 'antigravity_runtime'` from the `0.1.1916` copy while the executor mapped 168 scripts to `0.1.2010`, eight versions cached, and an earlier `cache_freshness` failure from a `0.1.1916` generator in its log (operator report, not re-read).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: The report comes from the operator's second machine (a macOS checkout, not reachable from here). The mechanism it names is reproduced on this machine's cache (claim 2) and the code path is read (claim 0); the ImportError itself was not re-run.
- OBSERVED (D2): `harness_independent_resolver.py.template` L1-12 `_version_key` and L78-124 `_scripts_dirs_in_root` order versions newest first by numeric tuple; `execute-script.py.template` L195-219 takes the newest by the same rule. The walk of D1 is the only unordered one.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: harness_independent_resolver.py.template L1-12 _version_key (numeric tuple) and L78-124 _scripts_dirs_in_root (versioned dirs sorted reverse=True); execute-script.py.template L195-219 takes max by _vkey.
- OBSERVED (D1): a developer checkout resolves scripts to the tree, so `_install_root_of` returns no root and no walk runs; that is why this checkout, the PLAN-LB-94 lane and its test suite did not see the defect.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read: _install_root_of (L564-579) returns (None, None) for a path under no known install root and _same_root_script_dirs (L601-603) returns [] on no root; install_of_path (L1841) tests only the known install roots. Not run.
- OBSERVED (D3, D4): PLAN-LB-94's D3 tests build single-version install fixtures (landing § D3, `test_d3_each_harness_resolves_its_own_install_and_its_own_pythonpath` and siblings); none holds two versions of one skill.
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: test_executor_harness_independence.py fixtures build one version directory per bundle per root (e.g. L402 demo/0.1.9, L380 demo/0.1.1, L888 demo/0.1.1); no fixture holds two versions of one skill. The D3 PYTHONPATH tests are at L397, L692 and L778.
- HYPOTHESIS: the version directory can be read off the script path by position (`{root}/{bundle}/{version}/skills/` or `{root}/{version}/skills/`); confirm against `_install_root_of` and the shapes `_scripts_dirs_in_root` already handles, including an env-declared root whose layout differs (verify-at-outline).
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: Open for the outline: the layouts _scripts_dirs_in_root handles are read (L78-124), but an env-declared root with a different layout was not exercised. Note one fixture already holds a hidden version directory beside a visible one (test_d3_hidden_version_dirs_are_skipped, L881); the new walk must skip hidden version directories as that resolver does.
- HYPOTHESIS: `_version_key` is available in the rendered executor at the point `pythonpath_for` runs (the resolver body is inlined into the template at render time); if it is not, the helper moves, it is not copied (verify-at-outline).
  - verdict: corroborated | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: The resolver body is inlined at the {{TARGET_AWARE_RESOLVER}} placeholder (template L479, replaced in generate_executor.py L2116), which precedes _same_root_script_dirs (L588); the rendered .plan/execute-script.py carries one def _version_key.
- Verify-first clause (D2): decide what a bundle that has the script's version but also a newer one does (use the script's version; the script was resolved from it) and what a bundle with no version at or below the script's does (use its newest), and record why.
  - verdict: unverifiable | checked_at: ee00687b802ccf212445feb4231687baf758cb55 | by: live-blockers/cleanup | rescoped: n/a | evidence: An outline-time decision, not a fact at HEAD; no code answers it yet.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — `_same_root_script_dirs`, `pythonpath_for` (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/harness_independent_resolver.py.template` — `_version_key`, the ordering rule to reuse (verify-at-outline) (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md` — the PYTHONPATH contract sentence PLAN-LB-94 wrote (verify-at-outline) (D1)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_executor_harness_independence.py` — the D3 `PYTHONPATH` tests that stay green (D3)
- HYPOTHESIS: `test/plan-marshall/tools-script-executor/` — a new multi-version fixture test beside it (verify-at-outline) (D1, D2, D3, D4)

## Dependencies and Sequencing

- Depends on: PLAN-LB-94 (shipped, #1861), whose D3 introduced the walk.
- Overlaps with: the staged PLAN-LB-93 on `generate_executor.py` (D1-D2) and the `test/plan-marshall/tools-script-executor/` directory; this plan does not edit `generate_executor.py` unless the outline shows the helper must be rendered from it, so the overlap is one directory at most. Run this plan first.
- Adjacent to: PLAN-LB-58 and PLAN-LB-82, which share no file.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-95-executor-pythonpath-own-version.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
