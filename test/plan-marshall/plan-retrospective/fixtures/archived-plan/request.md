# Request: collect-fragments add/finalize should infer mode from bundle, not require --mode on every call

plan_id: lesson-2026-04-18-13-001
source: lesson
source_id: 2026-04-18-13-001
created: 2026-04-18T11:45:37Z

## Original Input

# collect-fragments add/finalize should infer mode from bundle, not require --mode on every call

## Context

The newly-landed `collect-fragments.py` script (PR #234, lesson 2026-04-18-09-001) requires `--mode {live|archived}` on every subcommand invocation — including `add` and `finalize`, which operate on a bundle that `init` already created. The mode is part of the bundle's identity (it determines the on-disk path), so the bundle file itself should carry it.

During the dogfooded retrospective of the same PR, the orchestrator's first `add` call failed with `error: the following arguments are required: --mode`, requiring the flag to be retried on every subsequent `add` call.

## Root cause

`resolve_bundle_path` takes `mode` as input and returns the path. Path resolution lives on the caller side, so every subcommand needs `--mode`. No metadata is persisted inside the bundle to let the script recover the mode from the file.

## Proposed action

Two options:

1. Persist `mode` as a top-level key inside the bundle file on `init`. `add` and `finalize` read it from the bundle and do not require `--mode`. `init` remains the only subcommand that accepts `--mode`.
2. `add` infers mode by probing `{plan_dir}/work/retro-fragments.toon` first, falling back to the OS tmp path for archived.

Option 1 matches the pattern used by other stateful scripts in the bundle. Also update SKILL.md Step 3/4 command examples to drop the redundant `--mode` on `add`/`finalize` once implemented.

## Clarifications

1. **Q:** Which approach to eliminate `--mode` from `add`/`finalize`?
   **A:** Option 1: persist `mode` as a top-level key in the TOON bundle on `init`. `add`/`finalize` read `mode` from the bundle; `--mode` flag is removed from the `add` and `finalize` argparse. `init` remains the only subcommand accepting `--mode`.

2. **Q:** Is breaking the CLI contract (removing `--mode` from `add`/`finalize`) acceptable?
   **A:** Yes. `compatibility=breaking` per project config. No downstream consumers outside this repo. Delete `--mode` from `add`/`finalize` argparse; update `test/plan-marshall/plan-retrospective/test_collect_fragments.py` to drop the flag on add/finalize calls; update SKILL.md Step 3/4 example commands.

## Clarified Request

Modify `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/collect-fragments.py` so that `mode` is persisted inside the TOON bundle by `init` and inferred by `add`/`finalize` from the bundle contents.
