# Landing Analysis: PLAN-09 — Runtime seam completeness

epic: multiplattform
workstream: WS-01
pr: #1405 (https://github.com/cuioss/plan-marshall/pull/1405)

> Landing record for one shipped plan. Lives at `landings/PLAN-09.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Drained from `inbox/runtime-seam-completeness-001.md` (`kind: landing`, `lifecycle: live`,
`revision: 0`, valid). **Third** end-to-end OpenCode-lane inbox landing, after PLAN-05 and
PLAN-08.

## Deliverable Fidelity vs Spec

Every verdict re-derived from the merged tree at `c3a1aacbc`, not read off the message.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — every runtime operation documents how a target declines it | **shipped-as-specified** | `runtime_base.py` +49, `contract.md` +36, `opencode_runtime.py` +65. The decline vocabulary is stated per-op rather than as a blanket note. |
| **D2** — `metrics_capture` stops fabricating success, declines honestly on **every** input | **shipped-as-specified** | Read directly at `opencode_runtime.py:573`. The docstring states the no-op holds "on EVERY input, manual count included", names the reason (no session transcript, no persistence boundary on this target) and the alternative, and carries an explicit ⛔ against returning a success carrying the count — "the fabricate-success defect this no-op exists to close". |
| **D3** — the concrete runtime no longer enumerates the registered target set | **shipped-as-specified** | The exact defect is visible in the diff: `_claude_runtime_impl.py` replaced the hardcoded `"valid targets are: claude, opencode"` literal with `describe_targets(_REGISTRY.keys())`. A six-line change that removes a real duplication of the registry. |
| **D4** — target registration single-sourced | **shipped-as-specified** | `platform_runtime.py:190` `_TARGET_RECORDS` is now the sole record; `_DEFAULT_TARGET` (:209), `_REGISTRY` (:213) and the bootstrap-libs map (:216) are all *derived* from it by comprehension. `marketplace_paths.py` swapped its `_DEFAULT_RUNTIME_TARGET` constant for a lazy `_default_runtime_target()` that reads `platform_runtime._DEFAULT_TARGET`, with a sentinel fallback — the lockstep test that previously held two literals equal is replaced by structural single-sourcing. |
| **D5** — SKILL.md per-target status restatements trimmed | **shipped-as-specified** | `SKILL.md` ±20. |

`deliverables_done=5/5` is **upheld in full**. Unlike PLAN-08, no done-condition was half-met.

### Surface fidelity — clean, and the three-owner partition held

⭐ **This landing stayed exactly inside its declared surface.** Every touched path is declared,
including `_claude_runtime_impl.py` (declared on the D2/D3 row) and the four
`test/plan-marshall/platform-runtime/` files. Two declared paths went untouched
(`claude_runtime.py`, `test/plan-marshall/script-shared/**`) — over-declaration, the safe
direction. **There is no under-declaration at all**, in direct contrast with PLAN-08's
repo-root `CROSSING-INVENTORY.md`.

⭐ **The `marketplace_paths.py` three-owner partition was respected and is now evidenced.**
The spec declared that file as "**`_DEFAULT_RUNTIME_TARGET` only**", and the diff confirms the
plan touched only that symbol and its call sites. It did **not** touch `get_base_path`'s scopes
(PLAN-07's) or the fallback-composer constants (PLAN-10's). The ledger's three-owner sequencing
note has been treated as a hypothesis since ingestion; this is the first landing that tests it,
and it holds. **PLAN-07 and PLAN-10 inherit a moved boundary, not a broken one** — the constant
they may have expected is now a function.

## Metrics and Anomalies

- **Tokens: not reported.** `total_tokens=unknown`; `landing-check` returns
  `complete: false, missing_keys: [total_tokens]` — the known, expected OpenCode-lane gap.
- **Tests:** 1,244 passed in the platform-runtime suite, 92 in the contract-canonical set
  (plan-reported; not independently re-run here).
- ✅ **The message carried a narrative section as well as the facts block** — a visible
  improvement over PLAN-08, whose message was a bare block. The open defect recorded at that
  landing (the lane dropping a spec's report-in-the-inbox obligation) is *narrowed* by this:
  the lane can and does carry prose. It is not closed — PLAN-09's spec asked for no
  in-message enumeration, so the obligation was never exercised.

## Routing and Merge Behavior

- **Review:** CodeRabbit obtained, all findings handled. **Sourcery was rate-limited (hard
  quota) and the run disclosed it** rather than reporting a clean review — the correct
  handling under the standing policy (only CodeRabbit required).
- **CI/merge:** merged as `c3a1aacbc`; `state: merged` and `merge_commit_sha` corroborated
  through the CI abstraction and against `origin/main`.
- **Branch prefix:** `fix/runtime-seam-completeness` — a canonical prefix, so CI's
  push-triggered runs applied normally.
- **No collision materialized.** PLAN-09 ran solo at `parallelization_scope: 1`. Its
  pre-measured 6-path overlap with PLAN-08 was never exercised (PLAN-08 had already landed),
  and the 1-path overlap with PLAN-14 on `contract.md` remains live for the WS-01 chain.

## Reconciliation Actions

- [x] row `status` → `landed` — `orchestrator queue --transition PLAN-09 --status landed`
- [x] row `pr` stamped `#1405`
- [x] row `landing` stamped `landings/PLAN-09.md`
- [x] row `plan_marshall_plan_id` stamped `n/a` (OpenCode lane)
- [x] New Open Defect recorded: the executor self-heal cache-depth defect (below)
- [x] Watch retired: the `LEVEL_TABLE` / `model_map` import-direction watch is **not** affected
      by this landing and stays open
- [x] START-HERE and Ordered Queue blocks regenerated; `resume_anchor` updated
- [x] Message archived to `inbox/archive/runtime-seam-completeness/`

## Follow-Ups

- ⚠️ **Executor self-heal walks the wrong plugin-cache depth — a NEW defect, found only
  because the worktree was torn down.** Reported by the run and **partially corroborated
  here**: the plugin cache nests as `{marketplace}/{bundle}/{version}/`, and for this bundle
  the two names collide —
  `~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1594/` — which is exactly the
  depth ambiguity a walk can get wrong. The executor's pinned script paths pointed into the
  deleted worktree, and the self-heal that should have recovered did not; the operator
  regenerated `.plan/execute-script.py` via `generate_executor.py generate --force`
  (154 → 162 scripts) to unblock the inbox write.
  ⛔ **I did not independently reproduce the failing walk** — that needs the teardown
  condition. The cache nesting is verified; the walk defect is the run's claim, recorded as
  such. → **Open Defect**, out of epic scope: it belongs to
  `tools-script-executor/scripts/generate_executor.py`, which no plan here owns, and it is a
  third defect in the same "orchestrator/executor tooling" class as the `queue --transition`
  status-token hole and the `corpus set-verdict` off-by-one.
- **PLAN-07 and PLAN-10 must re-derive `marketplace_paths.py` before acting.**
  `_DEFAULT_RUNTIME_TARGET` is gone, replaced by `_default_runtime_target()` plus a
  `_DEFAULT_RUNTIME_TARGET_SENTINEL`. Both specs' hit lists over that file predate the change.
  This is a sequencing note, not a defect — recorded in `### Queue annotations`.
- **The lane's inbox-narrative capability is now demonstrated.** Whoever fixes the RUNBOOK
  Step 10 obligation gap should note the channel already carries prose; only the
  carry-the-spec's-reporting-obligation half is missing.
