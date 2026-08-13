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

_(updated as the run proceeds)_

## Build gate

_(pending — Python + test changes expected, so `./pw verify` takes its full path)_

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
