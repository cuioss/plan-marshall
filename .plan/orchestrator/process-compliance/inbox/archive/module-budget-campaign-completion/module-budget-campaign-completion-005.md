envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-24T07:45:04Z

---
envelope_version: 1
sender_id: module-budget-campaign-completion
epic: process-compliance
kind: finding
target_plan: ""
created: 2026-09-24T07:45:00Z
---

# Finding: manage-config import chain resolves _manifest_validation from the opencode flat cache; resolve_bundles_root fails → every manage-config verb dies at import

## Symptom

Every `python3 .plan/execute-script.py plan-marshall:manage-config:manage-config …` invocation in the opencode environment crashes before argparse, with a `RuntimeError` from `resolve_bundles_root`. Reproduced deterministically twice (e.g. `plan phase-1-init get --field init_without_asking` and a retry). The failure blocks the canonical planning seam: `init_without_asking` reads and the `effort resolve-target` dispatch-target resolution both route through `manage-config`.

## Root cause

Import chain inside the executor-dispatched process:

```
marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py:33
  → _cmd_finalize_steps.py:40
      → _cmd_quality_phases.py:29
          → _manifest_validation.py:211
              _REPO_ROOT = resolve_bundles_root(Path(__file__)).parent.parent
```

The first three modules resolve from the **source tree** (they sit on the executor-built PYTHONPATH), but `_manifest_validation` resolves from the **opencode cache copy**:

```
/home/oliver/.config/opencode/skills/plan-marshall-manage-execution-manifest/scripts/_manifest_validation.py
```

and `resolve_bundles_root` (`/home/oliver/.config/opencode/skills/plan-marshall-script-shared/scripts/marketplace_bundles.py:239`) walks upward from `__file__` looking for a directory named `plan-marshall`. In the source layout (`marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/…`) that ancestor exists; in the opencode cache layout (`~/.config/opencode/skills/plan-marshall-manage-execution-manifest/scripts/…`) there is no `plan-marshall` directory — the cache flattens bundles to `skills/plan-marshall-<name>/` — so the walk exhausts `/` and raises.

So the opencode cache copy of `_manifest_validation.py` is structurally incompatible with `resolve_bundles_root`: the same file works from the source tree and dies from the cache.

## Consequence for this run

- `init_without_asking` could not be re-read; the prior recorded config value (`true`, Step 3a of this plan's init) and the documented "unset → default true" rule were used to continue.
- `effort resolve-target --role phase-2-refine` (the dispatch-target resolver for the deep-lane 2-refine dispatch) is unavailable.

## Scope / observed surface

Unaffected so far in the same environment: `manage-status` (incl. `metadata`, `transition`, `planning-lane route`, `set-phase`), `manage-logging`, `manage-metrics`, `manage-plan-documents request read`, `plan-orchestrator inbox` verbs, and `plan-marshall:plan-marshall:phase_handshake` all execute fine. Only `manage-config` pulls the `_cmd_finalize_steps → _cmd_quality_phases → _manifest_validation` chain.

## Suggested repair directions (not performed)

1. Make `resolve_bundles_root` (script-shared `marketplace_bundles.py`) aware of the flat opencode cache layout — e.g. anchor on a bundle-marker file or accept an explicit root — so a cache-resolved module resolves the bundle instead of raising.
2. Or have the executor PLATFORM include the source `manage-execution-manifest/scripts` dir on PYTHONPATH ahead of the opencode cache dirs, so `_manifest_validation` resolves from the source tree where the bundle ancestor exists.
3. Or regenerate/resync the opencode skill cache so cache copies carry the source layout expectations; note other cache-resolved modules already work, so a whole-cache reshuffle may be broader than needed.

The opencode target workstream (`truth-179-opencode-target-detection-landed`) is the natural owner for triage.
