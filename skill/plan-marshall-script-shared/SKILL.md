---
name: plan-marshall-script-shared
description: Shared Python modules consumed by other marketplace scripts via PYTHONPATH
mode: knowledge
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
metadata:
  bundle: plan-marshall
  skill: script-shared
---

# Script Shared

Shared Python modules consumed by other marketplace scripts via PYTHONPATH.

This skill has no user-facing workflow. It provides build utilities, extension framework helpers, workflow helpers, query modules, and shared parsers that are imported by executable scripts in other skills — **including scripts in other bundles**. `epic_spec_parser.py` is the standing case: it is homed here precisely because `pm-plugin-development:tools-epic-surface-partition` imports it alongside `plan-marshall:plan-orchestrator`, and a module two bundles read cannot live in either consumer.

## Directory Layout

```text
scripts/
  marketplace_paths.py    # Path/root resolution constants and helpers; defines NO_PLAN_SENTINEL
  resolve_project_dir.py  # The --plan-id / --project-dir argv routing layer
  epic_spec_parser.py     # The marketplace's SINGLE reader of a plan spec's `## Expected Surface`
  plugin_registry.py      # Shared reader of the plugin registry, the executor version and the cache versions
  build/        # Build system utilities (_build_*.py, _coverage_parse.py)
  extension/    # Extension framework (extension_base.py, extension_discovery.py, ...)
  workflow/     # Workflow helpers (triage_helpers.py)
  query/        # Query utilities (query-config.py, query-architecture.py)
```

## `epic_spec_parser` — one reader for `## Expected Surface`

`epic_spec_parser.py` is the sole parser of a plan spec's `## Expected Surface` section, and its being the only one is the point rather than a convenience: two readers of that section previously disagreed, and the weaker one was the one wired to the orchestrator's disjointness gate, so a spec that resolved six paths rendered as `(no expected surface)` and passed the gate as colliding with nothing. Both consumers — `plan-marshall:plan-orchestrator` (the queue renderer and `corpus` verbs) and `pm-plugin-development:tools-epic-surface-partition` (the partition/attribution report) — now call this module, so no consumer can resolve a *different* surface for the same spec.

What each consumer PROJECTS from that one resolution is its own contract and may differ — inside `plan-orchestrator` it does, for a `derived` spec that resolves entries. One reader buys one resolution, never one projection.

Alongside the spec's class, the reader resolves each entry's own **shape** — whether the spec CLAIMS the path or merely LEADS to it — from that entry's own bullet, by marker rules keyed on published grammar and on the spec's own words rather than on any plan identifier. The rule table lives with the consumer that acts on it, in `pm-plugin-development:tools-epic-surface-partition`'s `standards/epic-surface-derivation.md`; it is not restated here, because a second copy is what lets the two statements drift.

⛔ The shape is an **added field, not a re-partition**. An entry keeps its membership of `claimed` and of `excluded` whatever its shape, and the spec's class is unaffected, so a consumer that ignores the shape reads exactly the surface it read before the field existed. Demoting a lead-shaped entry to a non-owning verdict is a consumer's PROJECTION and is performed by the partition, never here: moving a lead out of `claimed` in the reader would shrink the orchestrator's disjointness input and make a colliding plan read as disjoint.

Do NOT add a second parser of that section in either consumer. It also defines `PLAN_ID_SEGMENT`, the plan-id grammar used to group specs by plan, which `plan-orchestrator`'s inbox seam imports from here rather than restating.

## `plugin_registry` — shared reader for the registry pin

`plugin_registry.py` answers "is the plugin registry pinned at the version it should be?". It reads three stores and writes none:

- **The registry** (`installed_plugins.json`) in the shape the plugin manager writes — `"plugins": {"{bundle}@plan-marshall": [scope entry, ...]}`. `read_registry` returns one row per scope entry (`bundle`, `scope`, `install_path_version`, `version`) plus a read state. Scope entries are never collapsed: a user-scope and a project-scope entry that disagree are two rows. Keys of any other marketplace are ignored. Which entries of a parsed registry document belong to the marketplace is decided by one walk, `iter_marketplace_entries(document, marketplace=MARKETPLACE_NAME)`: `read_registry` builds its rows from it, and a caller that rewrites entries walks it too, so its `(bundle, entry)` pairs line up with the rows index for index.
- **The executor**, for the value of its `MARSHALL_VERSION` assignment (`read_executor_version`).
- **The cache**, for the newest version directory of a bundle (`newest_cache_version`) and whether a version directory carries the `.orphaned_at` marker (`is_orphan_marked`). The marker is reported, never used for selection.

Every read function takes the path it reads. For a caller that has no path of its own, `default_registry_path`, `default_cache_root` and `default_executor_path` state where the three stores are: the registry and the cache root under the user's home directory, resolved on each call, and the executor under the checkout root the caller passes.

`classify_parity` takes the registry rows and one reference version and returns exactly one verdict. The verdict set is closed and declared once, as the `PARITY_*` constants and the `PARITY_VERDICTS` tuple in this module; a consumer imports those names rather than restating the strings. The read states are likewise the module's `REGISTRY_*` and `EXECUTOR_VERSION_*` constants. `version_key` orders versions by digit runs, with the same semantics as `marketplace_bundles._version_sort_key`.

### Consumers

| Consumer | How it loads the module | Reference version it passes |
|----------|-------------------------|-----------------------------|
| The harness sync's Claude leg (`marketplace/targets/sync.py`) | By file location | The version the sync wrote in this invocation |
| The repin step (`marketplace/targets/claude/registry_pin.py`) | By file location | The `--target-version` it is given, else the newest cache version directory of each bundle |
| The pin-trap detector (`pm-plugin-development:plugin-doctor`) | By name, on the executor's PYTHONPATH | None — it reads the registry and executor values and compares them itself |
| The restart check (`plan-marshall:plan-orchestrator`) | By name, on the executor's PYTHONPATH | The executor's `MARSHALL_VERSION` |

The cache-root `dist-manifest.json` is never a reference version: it describes what was built, not what is pinned or loaded.

### Load-by-file-location constraint

`marketplace/targets/` runs outside the executor, so the `script-shared` directory is not on its `sys.path` and the module is loaded from its file path. Two rules follow, and both bind every future edit:

- ⛔ **No import of a sibling module** — only the standard library. A sibling import resolves on the executor's PYTHONPATH and fails when the module is loaded by file location.
- ⛔ **No `@dataclass`.** A module loaded by file location is not registered in `sys.modules`, where the dataclass machinery looks its defining module up. Rows are plain dicts and read results are plain tuples.

## Import Resolution

The executor's PYTHONPATH generation scans immediate subdirectories of each `scripts/` directory, so modules in `scripts/build/` and `scripts/extension/` are importable by any script in the marketplace without path manipulation.

`marketplace_paths.find_marketplace_path()` and `get_base_path()` accept an optional `marketplace_root` override. `find_marketplace_path()` resolves in the order explicit parameter → `PM_MARKETPLACE_ROOT` env var → cwd-based discovery. `get_base_path()` is stricter about what counts as an anchor for its cache-bypassing scopes: the explicit parameter always outranks the deployed-bundle cache, while the env var counts as an anchor only while nothing else has declared the context (`_env_anchor_is_last_resort`) — on a machine carrying a platform env signal or a declared `runtime.target`, an exported `PM_MARKETPLACE_ROOT` no longer pins the marketplace scope ahead of the cache. Use the explicit parameter to pin marketplace lookups to a specific worktree or test fixture instead of relying on cwd.

See `workflow-integration-git/standards/worktree-handling.md` for the worktree-specific application of this rule (path convention and the `--plan-id` / `--project-dir` binding contract for callers that need to bind to a specific working tree).

## `resolve_project_dir` — the argv routing layer, not a resolver

`resolve_project_dir.py` implements the `--plan-id` / `--project-dir` contract that every Bucket B (worktree-scoped) script shares, so consumer scripts have one implementation instead of one copy each. Its role is narrow and worth stating precisely, because it used to be wider:

- It is the **argv/flag layer**: it enforces mutual exclusion (`MutuallyExclusiveArgsError`), decides which of the two flags was supplied, and returns an absolute working-tree path string.
- It is **not** an independent worktree resolver. The worktree face is delegated to `file_ops.resolve_plan_context`, which owns the single `manage-status get-worktree-path` invocation in the codebase. `resolve_project_dir` calls it with `ensure=False` — resolving a working tree is a routing lookup and must not materialize or existence-check the plan — and returns `.worktree_path`.
- `--project-dir` is still returned verbatim (made absolute), and the no-flag case falls back to `file_ops.cwd_checkout_root()`.
- `WorktreeResolutionError` is **re-exported from `file_ops`**, not defined here; it is raised by the resolver, and callers surface its message verbatim.

Because the resolution goes through `resolve_plan_context`, `--plan-id NO_PLAN` is an accepted routing value on every Bucket B consumer and binds to the main checkout — a plan-less caller never resolves to a worktree. `NO_PLAN_SENTINEL` is **defined** in `marketplace_paths.py`, this bundle's pure-stdlib foundation, so that `file_ops` can import it on the bootstrap path where `tools-input-validation` is not on `sys.path`; `input_validation` re-exports it. See [`tools-file-ops/SKILL.md`](../tools-file-ops/SKILL.md) § "Plan-Context Resolution" for the resolver contract and [`tools-input-validation/SKILL.md`](../tools-input-validation/SKILL.md) § "The `NO_PLAN` sentinel (plan_id carve-out)" for the validator carve-out.
