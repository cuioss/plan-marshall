envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=process-compliance
kind=finding
created=2026-09-24T07:50:08Z

# Process-compliance finding — executor regeneration poisoned in opencode sessions (truth-147-lane-reports-green)

## Observation

- During phase-6-finalize step 15 (`project:finalize-step-sync-plugin-cache`), the
  doc-prescribed regen `generate_executor generate` (no `--marketplace-root`)
  wrote a main executor whose local mappings + `_ALL_SCRIPT_DIRS` resolve to
  `/home/oliver/.config/opencode/skills/*` (160 opencode-target entries) instead
  of the repo's `.claude/skills` (6 entries, as in the last working executor).
- SortedChannel `_PYTHONPATH` then resolves stale opencode shared-module copies
  AHEAD of repo copies. Concretely, `manage-config` failed: the opencode
  `_manifest_validation.py` raises `resolve_bundles_root` RuntimeError because
  the opencode dash-namespaced layout has no `plan-marshall` bundle parent.
- Root mechanism: `discover_local_scripts` consumes the first skill root with
  data from the target-aware `layout skill-roots` op; in an `OPENCODE=1`
  session the opencode roots win even for `--target claude`. Unsetting
  `OPENCODE` for one recovery command did NOT change the outcome.
- The step-15 doc offers no `--marketplace-root` on its regen call (unlike the
  plugin-doctor Step 4 form), so the prescribed invocation cannot pin local
  discovery to the repo.

## Recovery applied this run (transparent, reversible)

- Regenerated via the steward bootstrap direct path (sanctioned for
  invalid executors), same poisoned result.
- One-line recovery edit to the GENERATED file only
  (`.plan/execute-script.py`, derived state, overwritten by next regen):
  `_SCRIPT_DIRS` sort key prefers `/marketplace/bundles/` paths so repo
  copies resolve before opencode fallbacks. No source file touched for this.
- Request: make the step-15 regen call carry the repo-anchoring the
  plugin-doctor Step 4 form already uses, or scope local discovery by
  `--target`, so an opencode session cannot poison a claude-target executor.
