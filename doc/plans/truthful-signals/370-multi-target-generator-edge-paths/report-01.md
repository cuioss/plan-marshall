# Run report — 370-multi-target-generator-edge-paths (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/multi-target-generator-edge-paths-7yae0m`    **PR:** (pending)    **Outcome:** in progress

## Skills loaded

Loaded by bundle path (fresh cloud clone; `plan-marshall` plugin not assumed present):

- `plan-marshall:ref-code-quality` (+ `standards/code-organization.md`)
- `pm-plugin-development:plugin-script-architecture`
- `plan-marshall:persona-implementer` (work identity for production code)
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`

## D0 — GATE: confirm every finding at HEAD by symbol, and re-count

Mutates nothing. Every location verified by **symbol** (line numbers in the source review are stale and were not used). Surface confirmed to be swapped/renamed relative to some claim prose, so each was re-derived against the tree.

| Finding | Symbol (verified at HEAD) | Verdict |
|---|---|---|
| Unguarded destructive wipe | `claude/emitter.py::emit_bundle_verbatim` — `if dest_root.exists(): shutil.rmtree(dest_root)` (no containment check) | **CONFIRMED — live** |
| Sibling containment helper exists | `opencode/emitter.py::_safe_rmtree(path, output_dir)` refuses a target outside `output_dir` | **CONFIRMED** |
| Docstring's false safety argument | `emit_bundle_verbatim` docstring: "Target/claude/ is a pure build output (gitignored…), so the wipe is safe" | **CONFIRMED — live** |
| Non-pruning emitter | `opencode/emitter.py::emit_bundles` / `_emit_skill` / `_emit_agent` / `_emit_command` only `mkdir` + `write_text`; top-level `skill/`,`agent/`,`command/` output is never cleared | **CONFIRMED — live** |
| Frontmatter fence by raw substring | `opencode/frontmatter.py::parse_frontmatter` — `end = content.find('---', 3)` | **CONFIRMED — live** |
| Sibling anchors the fence on a newline | `claude/variant_emitter.py::parse_frontmatter` — `end = text.find('\n---\n', 4)` | **CONFIRMED** |
| Unguarded JSON read | `claude/equality_check.py::_read_emitted_plugin_json` — `json.loads(plugin_json.read_text(...))` with no guard | **CONFIRMED — live** |
| Adjacent read is guarded | `claude/equality_check.py::_check_marketplace_json` — `try: json.loads(...) except json.JSONDecodeError` | **CONFIRMED (asymmetry is the evidence)** |
| Path-keyed cache blind to content | `claude/variant_emitter.py::_load_mapping` — `@lru_cache` keyed on `Path` only | **CONFIRMED — live** |
| Diff double-count REACHABLE | `claude/equality_check.py::check_bundle` two layers (manifest + orphan) | **CONFIRMED in code, UNREACHABLE in practice → D6 DROPPED (see below)** |
| Prefix-strip idiom retired + guarded | repo-wide sweep + `test/marketplace/test_prefix_strip_idiom_retired.py` | **CONFIRMED — DELETED at D0 (already closed)** |

### Already-closed deliverable — DELETED, not restated

The prefix-strip idiom (`lstrip('./')` / `lstrip("./")`) returns **zero occurrences** under `marketplace/` (precise literal sweep, both spellings). The population-derived build guard `test/marketplace/test_prefix_strip_idiom_retired.py` fails the build on re-introduction. Per D0 this deliverable is **deleted** — not re-verified by inspection beyond the one confirmation the plan permits.

### Reverse sweep (both directions)

The two emitters were compared each way. The only material asymmetries are the two the plan already names: (1) `claude` has the dangerous unguarded wipe but no containment helper (D1); (2) `opencode` has the containment helper but no top-level prune (D2). No *other* asymmetry survives: `claude/iter_bundle_dirs` is traversal-safe by construction (it filters real directory entries by name membership rather than joining an arbitrary name), so it needs no `..` guard the way `opencode/iter_bundle_dirs` does. The frontmatter parsers (D3) and the JSON reads / cache (D4/D5) live in different modules, not in the emitter pair.

### D6 reachability — CONSTRUCTED and judged UNREACHABLE → DROPPED

The double-count was reasoned from code; per the plan it was **confirmed by constructing the out-of-sync state**. Four states were built and run through `check_bundle`:

| State | Setup | `check_bundle` entries |
|---|---|---|
| C1 hand-corrupted | component in **source + on disk**, absent from emitted `plugin.json` | **2** (manifest `only_in_generated` **and** `agents-orphans`) |
| C2 added-not-re-emitted | in source; absent from manifest **and** disk | 1 |
| C3 deleted-not-re-emitted (the *documented* orphan scenario) | absent from source; still in manifest **and** disk | 1 |
| C4 pure orphan | on disk; absent from source **and** manifest | 1 |

Only **C1** double-counts, and C1 requires the emitted tree to be **internally inconsistent** — a `.md` file present on disk yet absent from its own sibling `plugin.json`, while that component still exists in source. The emit pipeline (`ClaudeTarget.generate`, target.py) writes files (`emit_bundle_verbatim`, which wipes+rewrites the whole bundle dir) and regenerates `plugin.json` together, from one source and one cached `mapping.json`, in the same loop iteration — so **after any emit, on-disk always equals the manifest.** A crash between the two steps leaves *no* `plugin.json` (the wipe removed it), which hits `run_equality_check`'s `missing` path, not C1. C1 is therefore reachable only by hand-corrupting the gitignored build output in a shape the emitter never produces.

Per the plan ("If unreachable, DROP this deliverable rather than 'fixing' a path that cannot occur — that would be a vacuous fix, which is this epic's own archetype") **D6 is dropped.** No code was added for it.

### Surviving deliverable set

**D1, D2, D3, D4, D5, D7.** D6 dropped (above). The already-closed prefix-strip deliverable deleted (above). The remainder is non-empty, so the plan is not a no-op.

## Deliverables

(Filled in as each lands.)

## Build gate

(Pending — Python changes expected, so `./pw verify` takes its full path.)

## Findings

(Verification sub-agent / CI / PR review findings recorded here as they arrive.)

## Reviewer participation

(Recorded after the PR review cycle.)

## Cost

(Recorded at close.)

## Contract check (Step 9)

(Recorded at close.)

## What have we learned (Step 9)

(Recorded at close.)

## Residue

(Recorded at close.)
