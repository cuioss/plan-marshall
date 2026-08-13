# Run report — 360-collapse-the-version-selection-machinery (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/version-selection-collapse-gt8iqd (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (first action, the working contract)
- `plan-marshall:ref-code-quality` (+ `standards/code-organization.md`)
- `pm-plugin-development:plugin-script-architecture`
- `plan-marshall:persona-implementer`
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`

All loaded by reading the bundle source path (the `plan-marshall` plugin is not installed in this cloud session). No skill was unobtainable.

## D0 — GATE: chain, ownership, consumer sets, why-baked (confirmed from source)

### The seven-link chain, ownership confirmed by symbol

| # | Link | Symbol / site | Owner | Confirmed |
|---|------|---------------|-------|-----------|
| 1 | Cache layout `{base}/{bundle}/{version}/skills/` | assumed by `marketplace_bundles._partition_version_dirs`, `resolve_bundle_path` | **inherited** (plugin host) | yes |
| 2 | Sync creates a NEW version dir, never deletes | plugin-host install + our `marshall-steward` sync (not among the four expected files) | **ours** | yes (out-of-file; the accumulation is what the rest guards) |
| 3 | Executor bakes absolute version-pinned paths | `generate_executor.discover_scripts` → `{{SCRIPT_MAPPINGS}}` / `{{EXTRA_SCRIPT_DIRS}}` | **ours** | yes — but see "why-baked" below: the bake is a **fast path**, not a hard pin |
| 4 | Multi-version pollution detector | `generate_executor._detect_multi_version_pollution` | **ours** | yes |
| 5 | Orphan-marker writer | `generate_executor._mark_superseded_version_dirs` | **ours** | yes — the SOLE `.orphaned_at` writer under our tree |
| 6 | Retention pins | `generate_executor._retention_pinned_versions` (+ the independent keep-union in `cache_retention.py`) | **ours** | yes |
| 7 | Plugin host's own collector reads the marker | foreign Claude-Code plugin GC (epoch-ms encoding) | **shared field, two producers** | design argument (live-machine state, not reachable from clone) — its *consequence* needs no measurement |

⇒ Links 4–6 are all **ours**. The D0 gate condition "if any of links 4–6 is required by the plugin host rather than by us, re-scope" is **not triggered** — no re-scope on that axis.

### Consumer sets (both directions)

**`.orphaned_at` marker — READERS (existence only):**
1. `marketplace_bundles._partition_version_dirs` (the sole read site in that module; `select_live_version_dir`, `live_version_dirs`, `resolve_bundle_path`, `collect_script_dirs`, `find_bundles` all funnel through it).
2. `generate_executor._CLAUDE_RESOLVER_TEMPLATE` → baked `_resolve_notation_by_target` (the mandated policy mirror).
3. `pm-plugin-development plugin-doctor _plugin_pin_trap.py` — **the sibling detector, OUT OF SCOPE** (reads existence via a named constant `ORPHAN_MARKER_NAME`).
4. `_doctor_shared.py` — comment only; explicitly states it does NOT handle markers.
5. `cache_retention.py` — comment only; docstring states the marker is "advisory only and NEVER consulted."

**`.orphaned_at` marker — WRITERS:**
1. `generate_executor._mark_superseded_version_dirs` (ours, ISO-8601 UTC).
2. Foreign: Claude-Code plugin GC (epoch-ms).

**Baked executor path — READERS (what would break if SCRIPT_MAPPINGS stopped being version-pinned):**
- The generated executor's `resolve_notation` — but the direct `SCRIPTS[notation]` lookup is **existence-guarded** (`Path(direct).is_file()`), and misses fall through to `_resolve_notation_by_target` (runtime glob) then `_resolve_notation_by_cwd_walk`. So a deleted baked path already self-heals at runtime.
- `verify_executor`, `get_executor_mappings`, `cmd_paths`, `cmd_drift` read `SCRIPTS` back for diagnostics only.

### Why the paths were baked (D0 required)

**Startup cost / determinism**, not correctness. `SCRIPT_MAPPINGS` is a `dict[notation → absolute path]` for O(1) dispatch without a filesystem walk on every invocation; `{{EXTRA_SCRIPT_DIRS}}` bakes PYTHONPATH the same way. The runtime fallback (`resolve_notation` tiers 2–4) already resolves when a baked path is stale. ⇒ **The structural fix (D1) is a near-straight win, not a trade:** the executor already resolves at runtime; the baked map is a cache, and the direct lookup is existence-guarded. The only thing D1 removes is the *marker consultation* inside the runtime resolver and the selector — which is precisely the "a runtime resolver that still consults the marker set has MOVED the problem" hazard the plan names.

### Refuted-invariant circularity (checkable from source — confirmed)

`marketplace_bundles._partition_version_dirs` computes `live = [d for d in eligible if d == pinned or not (d/'.orphaned_at').exists()]`, and `select_live_version_dir` returns `max(live, key=version)`; the degraded branch fires only when `live == []`. The disk arm of the pin (`select_live_version_dir` inside `_retention_pinned_versions`) selects **among live dirs**, so once saturation is reached that arm returns nothing and cannot recover — the guard against reaching the state depends on not already being in it. Confirmed by symbol.

### The refuted "structurally impossible" claim — sites located (D5 targets)

- `generate_executor._retention_pinned_versions` docstring — "Pinning these is what makes marker saturation structurally impossible…" (deleted by D4).
- `generate_executor._mark_superseded_version_dirs` docstring — same claim (deleted by D4).
- `marketplace_bundles.select_live_version_dir` / `_partition_version_dirs` docstrings (rewritten by D1).
- `manage-config/standards/data-model.md` § "Plugin-cache retention semantics" — the "Pin resolution has exactly three arms" and "two sanctioned existence-read sites" paragraphs.
- `tools-script-executor/SKILL.md` § "Version-aware bundle-path resolution" — the degraded-fallback / pollution-detector / two-existence-read-sites / mirroring-mandate prose.
- `pm-plugin-development plugin-doctor _doctor_shared.py` — a comment referencing "the all-versions-orphaned contribute-zero bug fixed in `script-shared::find_bundles`".

### The D2 enforcement-test interaction (confirmed)

`test/plan-marshall/script-shared/test_orphan_marker_existence_only.py` is a population-derived test asserting **exactly two** sanctioned existence-read sites (`_partition_version_dirs`, the `_CLAUDE_RESOLVER_TEMPLATE` mirror) and **one** sanctioned write site (`_mark_superseded_version_dirs`). Removing the marker machinery (D1/D2/D4) removes all three subjects. The test therefore **must be retired** — recorded here and in the Findings section rather than deleted silently (the move this epic exists to catch). Reason: the invariant it enforces ("our sites read the shared field existence-only to stay encoding-agnostic vs. the foreign co-producer") has no subjects once our tree stops reading or writing the field. The only remaining reader, plugin-doctor's `_plugin_pin_trap.py`, is out of scope and was never one of the test's two sanctioned sites.

## Deliverables

- **D0 — GATE (chain + ownership + why-baked).** Done. Confirmed all seven links by symbol; links 4–6 are all ours (no re-scope). Established the paths were baked for **startup cost / determinism**, and that the runtime resolver (`resolve_notation`) already existence-guards the baked path and falls through to a runtime resolver — so D1 is a near-straight win, not a trade. Full analysis in the D0 section above.
- **D1 — LEVER A (runtime resolution, marker-free).** Done. `marketplace_bundles.select_live_version_dir` rewritten to numerically-newest-eligible-wins with **no `.orphaned_at` read and no degraded fallback**; `_partition_version_dirs` and `live_version_dirs` deleted (their only purpose was the marker partition / the deleted pollution counter). The executor's embedded `_CLAUDE_RESOLVER_TEMPLATE` mirror rewritten to drop the marker consultation (picks newest candidate). Startup cost: **none added** — the resolver already globbed the cache at runtime for a `SCRIPTS` miss; removing the marker `.exists()` probes is strictly less work. The resolver **no longer consults the marker set**, so the class is eliminated, not moved (D1's ⛔).
- **D2 — LEVER C (stop writing the shared marker) + enforcement-test interaction.** Done. `_mark_superseded_version_dirs` (the sole writer under our tree) deleted. **`test_orphan_marker_existence_only.py` retired** — its subjects (the two sanctioned existence-read sites `_partition_version_dirs` + `_CLAUDE_RESOLVER_TEMPLATE`, and the one sanctioned write site `_mark_superseded_version_dirs`) no longer exist under our tree, so the invariant it enforced ("our sites read the shared field existence-only to stay encoding-agnostic vs. the foreign co-producer") has no subjects. This is recorded, not silent (the move the epic exists to catch). Its "no marker write" guarantee is **re-established, not dropped**, by the new D6(d) test `test_no_production_source_writes_the_shared_marker`, which scans the whole production tree for a `.orphaned_at` write. No namespaced marker was introduced — none is needed, because the runtime resolver picks newest without any marker.
- **D3 — LEVER B (delete-on-sync).** Evaluated, **NOT adopted** (decision recorded). Delete-on-sync remains unsafe even after D1: a superseded version dir may still be on a *running* process's baked PYTHONPATH (the executor captures `_PYTHONPATH` at generation time), so immediate `rmtree` on sync would race a live process. The runtime resolver self-healing to newest reduces the *resolution* exposure but not the *import-path* exposure of an already-launched process. Pruning therefore stays the `marshall-steward` `cache_retention sweep`'s deferred union-keep job (newest-`N` ∪ younger-than-`D`-days ∪ newest-on-disk ∪ provisioned ∪ manifest ∪ executing-dir), which never deletes the live dir. `cache_retention.py` is unchanged.
- **D4 — Retire dead machinery.** Done. Deleted `_detect_multi_version_pollution`, `_retention_pinned_versions`, `_live_version_dirs`, `_carries_skills_tree`, `_mark_superseded_version_dirs`, the `cmd_preflight` pollution/marking block, the selector's degraded fallback, and the now-unused `select_live_version_dir`/`live_version_dirs` imports in `generate_executor.py`. **Guard 4 (`_check_emitted_path_provenance`) is retained** — it is marker-independent (confirmed by symbol and by the surviving guard-4 test suite) and still fail-closes a version-split executor at write time.
- **D5 — Correct the saturation claims.** Done. The "structurally impossible" claims lived in `_retention_pinned_versions` / `_mark_superseded_version_dirs` docstrings (deleted by D4). The restating docs were corrected: `data-model.md` (pin-resolution + existence-read paragraphs removed), `tools-script-executor/SKILL.md` (version-aware resolution section rewritten), `provisioning-fail-closed-audit.md` (`_detect_multi_version_pollution` row removed, `cmd_preflight` row updated), `plan-marshall/SKILL.md` (preflight pollution bullets), and the `_doctor_shared.py` comment. A tree-wide sweep confirms no document asserts the refuted guarantee.
- **D6 — Tests, red-first.** Done. Four deliverables in `test/plan-marshall/tools-script-executor/test_marker_free_resolution.py`, each verified against the pre-fix code:
  - (a) `test_resolver_ignores_orphan_mark_and_selects_newest_carrying_the_script` — **red pre-fix** (marked newest demoted to an older unmarked dir), green post-fix. A companion `test_resolver_survives_deletion_of_generation_time_version` documents the deletion-survival property (green both — the runtime resolver already survived deletion; the tree moved past the plan's premise here).
  - (b) `test_saturated_cache_resolves_to_newest_without_degraded_warning` — **red pre-fix** (degraded stderr fired), green post-fix.
  - (c) `test_broken_cache_with_no_eligible_candidate_fails_loudly` (+ companion) — the matched **negative control**: `None` on no eligible candidate. Passes pre- *and* post-fix by construction (the loud-failure path was never broken); its job is to keep the marker-free fix from degrading into an always-find-something resolver. Reported honestly rather than contrived red.
  - (d) `test_no_production_source_writes_the_shared_marker` — **red pre-fix** (`write_text` at the old `_mark_superseded_version_dirs`), green post-fix.

## Build gate

The `git diff --name-only origin/main...HEAD -- '*.py'` verdict is **non-empty** (production scripts + tests changed), so `./pw verify` took its full path. **Result: SUCCESS** — `19560 passed, 14 skipped` with every sub-step green: mypy(production) [398 files], ruff [marketplace/bundles, test, .claude], SPDX headers, plugin-doctor [marketplace-wide], mypy(test) [732 files], module-tests [whole-tree pytest]. No `uv.lock` or generated-file churn was produced (deliverable paths staged explicitly, `git status` clean of stray files before commit). `UV_HTTP_TIMEOUT=600` was exported on every `./pw` call per the lane's cloud-session note.

## Findings

_(pending)_

## Reviewer participation

_(pending)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

_(pending)_
