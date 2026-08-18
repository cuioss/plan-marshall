# Verification — 360-collapse-the-version-selection-machinery

**Verified against:** commit `5cea6604a2a934fd6b7567bf44e4118ead017a5a`   **Landed as:** PR #1223, commit `d01edfdfd04e19d572625ad24d47af1b1f73bd3f`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landed commit (`git log --oneline --all --grep '#1223'` → `d01edfdf`, 15 files, +628/−2102) and read its stat and the per-file diffs for `marketplace_bundles.py`, `generate_executor.py`, `_doctor_shared.py`, `data-model.md`, `provisioning-fail-closed-audit.md`, `plan-marshall/SKILL.md`, `test_executor_version_split_regression.py`, `test_generate_executor.py`.
- Checked for later supersession: `git log d01edfdf..HEAD -- <each expected-surface file>`. Only one later commit touches any of them — `7cadb986` (#1272), a cosmetic `_REPO_ROOT = PROJECT_ROOT` swap in `test_marker_free_resolution.py`. No deliverable of this plan has been superseded.
- Opened at HEAD, in full or in the relevant regions: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_bundles.py` (whole file), `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` (§ `_CLAUDE_RESOLVER_TEMPLATE`, `cmd_preflight`, `_check_emitted_path_provenance`), `test/plan-marshall/tools-script-executor/test_marker_free_resolution.py` (whole file), `test/plan-marshall/tools-script-executor/test_executor_version_split_regression.py`, `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py`, `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_plugin_pin_trap.py`, `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md` §§ "Version-aware bundle-path resolution" / "Self-healing path resolution" / "generate_executor — preflight", `manage-config/standards/data-model.md`, `manage-config/standards/provisioning-fail-closed-audit.md`, `plan-marshall/SKILL.md:108`, and the retired `test_orphan_marker_existence_only.py` at `d01edfdf^`.
- Re-derived the sweeps rather than trusting the report: tree-wide grep for `orphaned_at` (`*.py`, `*.md`, `*.adoc`) and for `structurally impossible`, `saturat`, `retention pin`, `pollution detect`, `sanctioned existence`, `Pin resolution`, and every symbol D4 claims to have deleted (`_detect_multi_version_pollution`, `_retention_pinned_versions`, `_live_version_dirs`, `_carries_skills_tree`, `_mark_superseded_version_dirs`, `_partition_version_dirs`, `live_version_dirs`).
- Executed code rather than reading it where the claim is about a return value:
  - `loader_selected_version` from `_plugin_pin_trap.py` on four marker configurations — it returns the newest-overall dir in every case.
  - The D6(d) detector helper `_writes_marker` against six synthetic write shapes.
  - A glob-coverage comparison of `**/skills/**/scripts/*.py` vs `**/skills/**/scripts/**/*.py` under `marketplace/bundles` (386 vs 412 files; 26 uncovered).
  - The preflight return dict, counted field-by-field (seven).
- Ran tests: `uv run python -m pytest test/plan-marshall/tools-script-executor/ test/plan-marshall/script-shared/test_marketplace_bundles.py test/plan-marshall/marshall-steward/test_cache_retention.py test/pm-plugin-development/plugin-doctor/test_plugin_pin_trap.py -o addopts="" -q` → **503 passed**.
- **Two mutation checks**, each on a file first confirmed clean with `git diff --quiet`, each restored from a byte snapshot taken before the edit (never `git checkout`/`restore`/`stash`), each restored within the same step and re-confirmed clean:
  1. Re-introduced `and not (d / '.orphaned_at').exists()` into `select_live_version_dir`'s candidate filter → `test_saturated_cache_resolves_to_newest_without_degraded_warning` **FAILED** (`got None`). Restored; `git diff --quiet` exit 0.
  2. Re-introduced `and not (version_dir / '.orphaned_at').exists()` into the `_CLAUDE_RESOLVER_TEMPLATE` candidate filter → `test_resolver_ignores_orphan_mark_and_selects_newest_carrying_the_script` and `test_resolver_survives_deletion_of_generation_time_version` both **FAILED**. Restored; `git diff --quiet` exit 0.

  ⇒ The D6 production guards are **not vacuous**: each side of the two-site policy is independently pinned and goes red when the removed behaviour is put back.
- No file was mutated that another agent had modified. `git status` showed one unrelated file (`_cmd_baseline_reconcile.py`) already modified by another agent; it was not touched, snapshotted, or restored.

Only two files were written: this one and `gaps.md`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: confirm chain + ownership by symbol; establish why-baked | ownership column confirmed from source, both consumer sets enumerated | yes | yes | yes | yes | Every link the report names is confirmable at `d01edfdf^`: sole writer `generate_executor.py:2399` (`(version_dir / '.orphaned_at').write_text(...)`), sole selector read `marketplace_bundles._partition_version_dirs`, mirror read in `_CLAUDE_RESOLVER_TEMPLATE`, comment-only mentions in `_doctor_shared.py` and `cache_retention.py`, out-of-scope reader `_plugin_pin_trap.py:64,554`. Why-baked confirmed at HEAD: `.plan/execute-script.py:196` `SCRIPTS` is an absolute-path map, `:610` `_PYTHONPATH` is baked, and `tools-script-executor/SKILL.md:457-475` documents the four-tier existence-guarded self-heal — the bake is a fast path, not a hard pin. |
| D1 | LEVER A: stop baking absolute version paths; resolve at executor runtime | an executor generated against one version still resolves after that version is deleted | partly | **no — reinterpreted (disclosed)** | yes | yes | Marker removal done: `marketplace_bundles.py:16-58` `select_live_version_dir` is newest-eligible with no marker read and no degraded fallback; `generate_executor.py:477-540` template mirror likewise. `_partition_version_dirs` / `live_version_dirs` absent tree-wide. But **absolute paths are still baked** (`.plan/execute-script.py:196-198`, `:608-611`), so D1's headline action was not performed. Done-when holds (`test_resolver_survives_deletion_of_generation_time_version`) — and held pre-fix too, as report F3 states. |
| D2 | LEVER C: stop writing the shared marker; state the enforcement-test interaction | no write to the shared field remains under our tree | yes | yes | yes | yes | Tree-wide grep: the only `.orphaned_at` writes outside `doc/plans/` are in three **test fixtures** (`test_cache_retention.py:72`, `test_executor_version_split_regression.py:69,271`, `test_marketplace_bundles.py:36`, `test_marker_free_resolution.py:86,95,112`). No production write. `test_orphan_marker_existence_only.py` deleted, and the retirement is stated in the report (§ D0 last block, § Deliverables D2) and the PR body — not silent. |
| D3 | LEVER B: evaluate keeping ONE version dir | the decision is RECORDED either way | yes | yes | yes | yes | Recorded as **not adopted** with the running-process-PYTHONPATH reason, which the tree substantiates (`.plan/execute-script.py:610` bakes `_PYTHONPATH`). `cache_retention.py` is absent from `git show --stat d01edfdf`, matching "unchanged". |
| D4 | Retire what the levers make dead | no unreachable containment code remains | yes | yes | yes | yes | Tree-wide grep for `_detect_multi_version_pollution`, `_retention_pinned_versions`, `_live_version_dirs`, `_carries_skills_tree`, `_mark_superseded_version_dirs`, `_partition_version_dirs`, `live_version_dirs` → **zero hits** outside `doc/plans/` and `.pyc` caches. Guard 4 retained at `generate_executor.py:740` (`_check_emitted_path_provenance`), still called at `:1428`. |
| D5 | Correct the saturation claim wherever it is stated | no document asserts the refuted guarantee | yes | yes | yes | **no — 3 stale sites** | The refuted guarantee is gone: no `structurally impossible` hit anywhere relates to marker saturation; `data-model.md:507-513` rewritten; `tools-script-executor/SKILL.md:580-625` and `:770` rewritten; `provisioning-fail-closed-audit.md:95` rewritten; `plan-marshall/SKILL.md:108` corrected six→seven-field. **But** `test_executor_version_split_regression.py:180,222,226,227` still assert the deleted retention-pin mechanism. |
| D6 | Tests, each verified to FAIL pre-fix | all four pass, each seen red first | yes | (a) reinterpreted, (c) control by construction — both disclosed | yes | **(d) weaker than the guard it replaced** | All six tests in `test_marker_free_resolution.py` pass. Mutation 1 reds (b); mutation 2 reds (a) and its survival companion. (c) is a matched negative control, honestly labelled as green both ways. (d) `test_no_production_source_writes_the_shared_marker` passes but its detector `_writes_marker` (`:238-266`) catches only one AST shape — see below. |

### D1 — the headline action was not performed; the reinterpretation is disclosed

`plan.md` D1 reads "stop baking absolute version paths into the executor. Resolve bundle script directories **at executor runtime** from a single selector." At HEAD the generated `.plan/execute-script.py` still contains a fully-baked absolute-path `SCRIPTS` map (line 196 onwards) and a baked `_PYTHONPATH` (line 610), so link 3 of the plan's seven-link chain is **still present**. What D1 actually delivered is the removal of marker consultation from an already-runtime fallback resolver.

This is not concealed: report § D0 "why-baked" establishes the bake is a fast path, report finding **F3** states the deviation outright, and the PR body carries a dedicated "Note on D6(a)" saying the same. The plan's own *Done when* for D1 is satisfied. Graded "as documented: no" because the deliverable's stated action differs from what landed, not because the run misrepresented it.

### D5 — three stale restatements of deleted machinery in a test file

`test/plan-marshall/tools-script-executor/test_executor_version_split_regression.py` had its **module** docstring rewritten by this PR to the marker-free model, but three in-file statements were left behind:

- `:180` — `test_all_legs_agree_all_marked` docstring: "no marker carries a currency signal and all three legs **fall back to the retention-pinned NEWEST dir**".
- `:222` — section banner "Case 4: a marker on **the retention-pinned dir** does not suppress it".
- `:226-228` — `test_marker_on_the_retention_pinned_dir_does_not_suppress_it`, docstring "The newest-on-disk dir **is the retention pin**".

`_retention_pinned_versions` was deleted by D4 in this same commit. Both tests pass, but by a different route than they claim: nothing pins anything, and the marker is not read at all, so the assertion holds because eligibility alone drives selection. This is precisely the "fixture reaches the asserted state by a different route than the test claims" shape.

### D6(d) — a strictly narrower guard than the one it replaced

`_writes_marker` (`test_marker_free_resolution.py:238-266`) flags a `write_text`/`write_bytes` call only when the `.orphaned_at` **string literal** appears inside the call's own target expression. Executed against six shapes:

| shape | caught |
|---|---|
| `(version_dir / '.orphaned_at').write_text(...)` — the exact pre-fix shape | **yes** |
| `marker = version_dir / '.orphaned_at'` … `marker.write_text(...)` | no |
| `(version_dir / ORPHAN_MARKER_NAME).write_text(...)` | no |
| `open(version_dir / '.orphaned_at', 'w')` | no |
| `(version_dir / '.orphaned_at').touch()` | no |
| a write **inside** an emitted-code template string constant | no |

The retired `test_orphan_marker_existence_only.py` handled the first four of those misses by design — `_assigned_alias` / `_check_alias_uses` (`d01edfdf^:...:335-345`) resolved alias-bound marker paths, `_CONTENT_PARSE_CALLS` covered `open()`, `_METADATA_PROBE_ATTRS` covered non-`exists()` probes, and a dedicated template descent parsed `_CLAUDE_RESOLVER_TEMPLATE`. The alias-bound shape is not hypothetical: `_plugin_pin_trap.py:554` uses exactly it (`marker = entry / ORPHAN_MARKER_NAME`). The template shape matters most, because that constant is the code that ships into every generated executor.

The guard is **not vacuous** — it does go red on the defect it names — but the report's "re-established, not dropped" overstates it.

## Report accuracy

Checked claim by claim. Contradictions found:

1. **"Its 'no marker write' guarantee is re-established, not dropped, by the new D6(d) test"** (§ Deliverables D2). Contradicted. The replacement detects one AST shape; the retired test detected alias-bound writes, `open()` writes, metadata probes, and writes inside emitted-code template constants. Evidence: the six-shape execution table above, and `d01edfdf^:test/plan-marshall/script-shared/test_orphan_marker_existence_only.py:93,132,335-345`.
2. **"A tree-wide sweep confirms no document asserts the refuted guarantee"** (§ Deliverables D5). Narrowly true for the *saturation* guarantee; false for the machinery it depended on. Three statements naming the deleted retention pin survive at `test_executor_version_split_regression.py:180,222,226-228` — in a file this same commit edited.
3. **"D4 … the selector's degraded fallback, and the now-unused `select_live_version_dir`/`live_version_dirs` imports in `generate_executor.py`"** — `select_live_version_dir` was not made unused, it was **kept and rewritten** in `marketplace_bundles.py` and is imported by `test_executor_version_split_regression.py:28` and `test_marker_free_resolution.py:29`. Only the `generate_executor` re-export was dropped. Wording, not substance.

Verified as accurate, having re-derived each: the seven-link ownership table and both consumer sets (D0); `_mark_superseded_version_dirs` as the sole writer under our tree (`d01edfdf^:generate_executor.py:2399`, the only write hit in the pre-fix marketplace grep); the circularity argument (`live = [d for d in eligible if d == pinned or not (d/'.orphaned_at').exists()]`, `d01edfdf^:generate_executor.py:557`); Guard 4 retained and marker-independent (`generate_executor.py:740`, called at `:1428`); the five D5 doc sites all corrected in the landed diff; the preflight field-count correction (the return dict at `generate_executor.py:2290-2298` has exactly seven keys, and `_PREFLIGHT_FIELDS` in `test_generate_executor.py:1515` pins the same seven); F1's `SKILL.md` § preflight rewrite (`:770`); F2's test-comment rewrite; `cache_retention.py` unchanged as D3 states; the D3 rationale's premise that PYTHONPATH is captured at generation time (`.plan/execute-script.py:610`); the pin-trap detector left untouched.

Not verifiable from this clone, and so neither confirmed nor contradicted: the `./pw verify` figure `19560 passed, 14 skipped` (the tree has moved — #1272 reports 20,329); the wall-clock and branch-commit SHAs (squashed away); the reviewer-participation table and rate-limit bodies (GitHub state, not tree state); the live-machine saturation and marker-deletion observations, which `plan.md` itself labels unreachable from a clone.

## Out-of-scope compliance

Compliant.

- **"NEVER the plugin host's registry file. Read only."** — the landed diff touches nothing outside `marketplace/bundles/`, `test/`, and `doc/plans/`.
- **"Retiring the sibling detector plan … do not pre-emptively retire it."** — `_plugin_pin_trap.py` is absent from the diff and still present at HEAD with its marker reads intact (`:64`, `:554`).
- **"Re-opening the marker ENCODING question."** — not reopened; the change removes the field from our side rather than re-encoding it.

One collateral change, declared: the six-field → seven-field correction at `plan-marshall/SKILL.md:108`. It is a pre-existing defect in a file the PR already edited, is named in the report's Findings and Residue and in the commit body, and re-derives correctly against the actual return. No undeclared collateral change is present in the diff.

## Residue carried forward

| report-01.md residue item | Still open at HEAD? |
|---|---|
| Sibling detector re-scope — `_plugin_pin_trap.py` still reads `.orphaned_at` and still models retention pins / degraded fallback | **Open.** `:64` defines `ORPHAN_MARKER_NAME`, `:554` reads it, and `loader_selected_version` (`:269-289`) documents itself as mirroring a selector model that no longer exists. Executed on four marker configurations it returns newest-overall every time, so it does not currently mis-report the loader — but its `SHAPE_1_SATURATION` GC-exposure axis (`:368-372`) still ranks marker saturation as "repair before the fuse burns" for a resolver that no longer consults the marker. |
| Pre-existing field-count bug fixed in passing | **Closed.** `plan-marshall/SKILL.md:108` says "seven-field"; the return dict has seven keys. |
| "No follow-up owed on this PR's own surface" | **Contradicted** by the three findings above (D6(d) coverage, the three retention-pin statements, and the two smaller `cache_retention.py` restatements). |

## What could NOT be verified

Stated explicitly rather than passed by default:

- The `./pw verify` result quoted in the report (`19560 passed, 14 skipped`). The tree has moved since; the targeted suites relevant to this plan (503 tests) were run and are green, but the whole-tree figure at PR time cannot be reproduced.
- Everything about the live plugin cache: the measured saturation (every version dir marked), the foreign producer's write-and-delete behaviour, and the 66 ms marker-deletion observation. `plan.md` labels all three unreachable from a clone; nothing in the tree confirms or refutes them, and the design argument that rests on them needs no measurement.
- Reviewer participation, rate-limit bodies, auto-merge arming, and CI conclusion for PR #1223. Only the landing itself is confirmable: `d01edfdf` is an ancestor of HEAD on `main`.
- Whether the plugin host's own collector actually reads the marker in an epoch-ms encoding (third-party behaviour, outside this repository).
- The red-first evidence for D6(a)/(b)/(d) as claimed. The pre-fix reds were reproduced by *mutation* against today's code (both mutations went red, so the guards discriminate), not by checking out `d01edfdf^` and running the new tests against it.
