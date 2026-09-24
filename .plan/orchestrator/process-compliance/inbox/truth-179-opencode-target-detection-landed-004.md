envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=process-compliance
kind=finding
created=2026-09-24T05:29:19Z

# Process-rule issue: Step-4 entry blocked by handshake drift on concurrently-drained ledger plus manage-config import crash

Reporter: plan `truth-179-opencode-target-detection-landed` at `planning-outline.md` Step 4 entry (phase-3-outline done, approved, transitioned; 4-plan in_progress).

Two independent stop conditions, either alone blocks Step 4 dispatch:

## 1. Handshake verify drift (workflow-mandated stop)

`phase_handshake verify --phase 3-outline --strict` returned `status: error`,
`error: main_checkout_dirtied_during_plan`, `newly_dirty[3]`:

- `.plan/orchestrator/process-compliance/epic.md`
- `.plan/orchestrator/process-compliance/status.json`
- `.plan/orchestrator/test-quality/inbox/carried-defects-and-watches-closure-002.md`

Attribution: the first two are the process-compliance epic ledger. This plan filed three findings there (`-001`/`-002`/`-003`) earlier this session; a concurrent process-compliance session has since drained/consumed inbox traffic and regenerated the epic ledger blocks. Phase-3-outline writes only `.plan/local/plans/{plan_id}/**` and did not touch these files. The third file is the known other-epic unprocessed mail already disposed twice this session. Per `planning-outline.md` Step 4 ("Stop on status: drift"), phase-4-plan was NOT dispatched. Ironic closure worth naming: the compliance filings this run was ordered to make were consumed mid-run, and that consumption is what trips this plan's drift gate.

## 2. manage-config unrunnable (import-time crash, all verbs)

Every `manage-config` invocation now aborts before argparse with:

`RuntimeError: resolve_bundles_root: could not locate a 'plan-marshall' bundle above /home/oliver/.config/opencode/skills/plan-marshall-manage-execution-manifest/scripts/_manifest_validation.py`

Chain: marketplace `manage-config.py` line 33 imports `_cmd_finalize_steps` → `_cmd_quality_phases` → `_manifest_validation`, which resolves to the OpenCode plugin-cache copy (`/home/oliver/.config/opencode/skills/...`) instead of the marketplace tree, and that copy sits outside any bundle directory. The identical `effort resolve-target` and `plan ... get` calls succeeded repeatedly earlier this session (init through review gate), so the cross-skill import resolution flipped mid-session — consistent with the heavy concurrent activity observed all run (ledger commits landing under the plan: main_sha moved `a41de18 -> 92e935e -> 3e62afce` across three handshake captures). Suspected concurrent plugin-cache sync or steward run; not proven from inside this session.

Scope: ALL manage-config verbs are down (effort resolution, config reads). manage-status / manage-logging / manage-plan-documents / orchestrator verbs still work (verified this session after the breakage). Blocked workflow steps: Step 4 `effort resolve-target --role phase-4-plan` (no dispatch target obtainable) and any subsequent config gate reads.

Suggested owner: whoever owns executor PYTHONPATH ordering (generated `sys.path`/resolver emission — note this is adjacent to D0's own subject matter: generated path emission preferring a stale cache copy over tree code) and the `resolve_bundles_root` fail-closed contract. At minimum the crash should be a legible TOON refusal, not a bare traceback; structurally, a cache copy outside a bundle dir should never shadow the tree copy on the import path.

## Parked state (safe to resume)

`get-routing-context` confirms: 1-init/2-refine/3-outline done, 4-plan in_progress, outline user-approved ("Proceed to create tasks"). Resume with `/plan-marshall plan=truth-179-opencode-target-detection-landed` (auto-detect → outline Step 4) once the drift is reconciled and manage-config imports resolve to tree code again. No source-tree edits were made by this run; D0/D1/D2 implementation is untouched and still fully staged in the approved outline.
