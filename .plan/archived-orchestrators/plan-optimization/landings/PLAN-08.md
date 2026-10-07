# PLAN-08 executor-manifest-resolution — Landing

- epic: plan-optimization / workstream: WS-03
- plan_marshall_plan_id: executor-manifest-resolution
- PR: #934 (MERGED via merge-queue, SQUASH)
- posture: full (operator-selected) · planning_lane: light

## Delivered

- **D1 — resolver searches the marketplace clone root.** `find_installed_manifest_path`
  gained a 4th candidate mapping `.../plugins/cache/<mp>` →
  `.../plugins/marketplaces/<mp>/dist-manifest.json`, preserving env-override priority
  and existing candidate order; corrected the false "rides into the plugin cache"
  docstring. Cache-install regression test added.
- **D2 — non-destructive stamp.** `stamp_provisioning_fields` preserves an existing
  `provisioned_version` on an empty read while still creating the key as `''` when
  neither a real version nor a prior value exists (the key-always-present invariant).
- **D3 — fail closed on unresolvable manifest.** `cmd_preflight` emits a legible stderr
  warning and reports the new `marshal_status: unknown` (enum `fresh|stale|unknown`)
  instead of a vacuous `fresh`. Contract swept across producer + `tools-script-executor`
  SKILL + `determine_mode.py` docstring + `marshall-steward` SKILL/menu-healthcheck prose.
- **Security hardening (finalize security-audit):** added a containment guard rejecting a
  `.`/`..`/separator `marketplace_name` segment before building the clone-root Path, with
  a load-bearing regression test.

## Re-grounding correction

The spec attributed D3's `marshal_status` reporting to `_config_defaults.py`; re-grounding
found it lives in `generate_executor.py:cmd_preflight`. Corrected without expanding the
declared file set.

## Artifacts

- ADR-009 "Status reporting fails closed with an explicit unknown state" (Proposed).
- Lesson 2026-07-18-22-001 — scoped `quality-gate` (mypy+ruff) is blind to whole-bundle
  runtime invariant regressions; a key-always-present contract change needs whole-bundle
  `module-tests`. (Surfaced live: the D2 first cut passed the per-task scoped gate but the
  orchestrator-tier whole-bundle module-tests caught 33 failures → verification-feedback
  fix-task TASK-7.)

## Notes

- One loop-back cycle in phase-5 (the D2 regression above), cleanly recovered via
  finding → verification-feedback → fix-task → re-verify green.
- Merge required clearing a stale `merge-queue-merge-group-guard` merge-lock (the #933
  merge-lock mechanism change; `merge_lock` notation moved to `manage-locks`).
- Metrics: 2.5M tokens, 1h48m worked / 9h3m wall (heavy idle from CI + merge-queue waits).
