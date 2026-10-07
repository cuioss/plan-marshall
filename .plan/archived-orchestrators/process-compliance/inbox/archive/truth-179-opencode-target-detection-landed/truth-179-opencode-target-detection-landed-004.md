envelope_version=1
sender_type=plan
sender_id=truth-179-opencode-target-detection-landed
epic=process-compliance
kind=finding
created=2026-09-24T05:29:19Z
revision=2
amended=2026-09-24T06:36:32Z

# Process-rule issue: Step-4 entry blocked by handshake drift on concurrently-drained ledger plus manage-config import crash

Reporter: plan `truth-179-opencode-target-detection-landed` at `planning-outline.md` Step 4 entry (phase-3-outline done, approved, transitioned; 4-plan in_progress).

Two independent stop conditions, either alone blocks Step 4 dispatch:

## 1. Handshake verify drift (workflow-mandated stop) — CLEARED on re-check

`phase_handshake verify --phase 3-outline --strict` initially returned `status: error`,
`error: main_checkout_dirtied_during_plan`, `newly_dirty[3]` (process-compliance `epic.md` +
`status.json` rewritten by a concurrent drain of this run's own three filings, plus one
other-epic mail file). Per `planning-outline.md` Step 4 ("Stop on status: drift"), phase-4-plan
was NOT dispatched. After the operator confirmed a clean tree, re-verification returned
`status: ok` (only informational diffs: `main_sha` advanced with concurrent landings,
dirt `1 -> 0`). This half of the block is resolved; no filing needed beyond this record.

## 2. manage-config unrunnable (import-time crash, all verbs) — PERSISTS after sanctioned recovery

Every `manage-config` invocation aborts before argparse with:

`RuntimeError: resolve_bundles_root: could not locate a 'plan-marshall' bundle above /home/oliver/.config/opencode/skills/plan-marshall-manage-execution-manifest/scripts/_manifest_validation.py`

Chain: marketplace `manage-config.py` line 33 imports `_cmd_finalize_steps` → `_cmd_quality_phases` → `_manifest_validation`, which resolves to the OpenCode plugin-cache copy instead of the marketplace tree copy, and that copy sits outside any bundle directory. The identical calls succeeded repeatedly earlier this session, so the cross-skill import resolution flipped mid-session.

### Checkout-independence (proven)

The crash reproduces byte-identically on main (`/home/oliver/git/plan-marshall`, branch `main`)
AND inside the live worktree `.plan/local/worktrees/implement-opencode-enforcement-parity`
(which resolves its own per-tree executor): same winning cache file, same `RuntimeError`.
This plan never materialized a worktree (phases 1-4 run on main; materialization is a phase-5
event), so there is no plan-local workspace implicated at all. The shadowing copy lives in
user-global state (`~/.config/opencode/skills/`, outside every checkout), and every executor —
main's freshly regenerated one and the worktree's move-in one — builds a `sys.path` where the
flat-layout cache dir precedes the tree dir. Machine-global defect, not session-local.

### Recovery attempted (sanctioned, failed to unblock)

- `generate_executor verify` → `status: error` ("Logging module not found" under a nested
  `plan-marshall/skills/...` cache path that does not exist — the live cache uses the flat
  `plan-marshall-<skill>/` layout). Executor fails verification.
- Direct-path `generate_executor.py bootstrap --marketplace --marketplace-root .` (the documented
  broken-executor recovery) → `status: success, action: generated, reason: executor_invalid`,
  319 scripts, 217 surfaces derived. The executor WAS invalid and was regenerated.
- Retest `manage-config` after regeneration → identical crash. Regeneration does not change the
  cache-dir-ahead-of-tree-dir import precedence, so the recovery cannot fix this defect class.

### Root-cause narrowing (evidence, not speculation)

- Cache `_manifest_validation.py` mtime 2026-09-23 09:52 +0200 (pre-session); tree copy mtime
  2026-09-15 (pre-session). Neither file appeared mid-session — the flip is in path ORDER, not
  file presence.
- Preflight `executor_version` read `0.1.1762` at session start, `unknown` after the flip:
  the generated `.plan/execute-script.py` bytes were replaced mid-session (concurrent
  steward/sync run), consistent with `main_sha` advancing twice across three handshake captures
  (`a41de18 -> 92e935e -> 3e62afce`) while this plan ran.
- Defect shape: flat-layout cache roots precede tree roots on the executor-built `sys.path`,
  and tree `resolve_bundles_root` assumes the nested bundle layout for every copy on that path.
  This is adjacent to D0's own subject matter (generated path-emission ordering).

Scope: ALL manage-config verbs are down (effort resolution, config reads) on every checkout.
manage-status / manage-logging / manage-plan-documents / orchestrator verbs still work. Blast
radius: no plan-marshall plan can pass init Step 7 (`domain-detect`) or any `resolve-target`
dispatch while this holds — the planning path is fully blocked, not just this plan.

## Parked state (safe to resume)

Outline user-approved ("Proceed to create tasks"), 4-plan in_progress, drift gate now `ok`,
tree clean. Resume with `/plan-marshall plan=truth-179-opencode-target-detection-landed`
(auto-detect → outline Step 4) once `manage-config` imports resolve to tree code again.
No source-tree edits were made by this run; D0/D1/D2 implementation is untouched and still
fully staged in the approved outline.
