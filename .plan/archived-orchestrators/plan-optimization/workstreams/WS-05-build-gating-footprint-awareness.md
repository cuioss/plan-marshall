# WS-05: Build-Gating Footprint Awareness

epic: plan-optimization

> Charter document for one workstream. Lives at `workstreams/WS-05-build-gating-footprint-awareness.md`
> and tracked in the epic `status.json` `workstreams[]` field.

## Charter

Fix the "when to build" mechanism so phase-5 builds/tests **iff the footprint contains buildable
changes** (e.g. Java), and skips otherwise. The nifi docs-only incident is the visible symptom; the
operator's reframing (2026-07-18) is the real target: the footprint-driven build-gating that already
exists (`should_execute_build` / `build_map`) gates ONLY phase-6, while phase-5's build/test/
quality-gate steps are **footprint-immune by design** (PLAN-01's model, `_manifest_rules.py:131-132`).
That immunity is the defect — a Java change SHOULD trigger phase-5's build; a pure-doc change should
NOT — and today phase-5 relies solely on the narrative-derived `aspect`, which is unreliable
(nifi's docs-migration read as `implementation`). This workstream makes footprint the authority for
phase-5 build gating, with operator endorsement to revisit PLAN-01's intentional immunity.

## Scope

- In scope: extend the footprint-driven build-gating (`should_execute_build` / `build_map`, currently
  phase-6-only) to gate phase-5 build/test/quality-gate/coverage steps; footprint-aware aspect
  derivation (operator-chosen option A) as the consistency layer so `aspect` and footprint agree
  (pure-doc footprint → `aspect=analysis`/`drops_build_steps`, feeding PLAN-01 #926's existing drop).
- Out of scope: the narrative negation-phrase classifier (PLAN-01 kept it — keep); consumer
  config-integrity (WS-03); finalize barrier (WS-04). Coordinate with in-flight PLAN-08 on the
  manage-config compose path (adjacent files).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-11-footprint-driven-build-gating | ✅ shipped (PR #938) | Gated phase-5 whole-tree build on the EXISTING `build-decision`/`should_execute_build` authority (q-gate rejected a dup verb); aspect-classify kept pure. Fixes nifi docs-only-builds |
| PLAN-17-fast-ci-footprint-gating | staged | CI-LAYER sibling: footprint-gate plan-marshall's GitHub CI (`.plan`/md/adoc-only skips the build) via the merge-queue-safe gate→conclusion pattern. Shares the footprint definition with PLAN-11 |

## Sequencing and Surface Notes

- Consumer-surfaced (nifi-extensions `2026-07-18-documentation-cleanup`, executor 0.1.1137). Root
  cause orchestrator-verified 07-18: `request_aspect=implementation` in the archived status.json →
  phase-5 quality-gate ran full `verify -Psonar`; phase-6 correctly saw docs-only (0 bundles).
- **HIGHER PRIORITY than the remaining WS-03/WS-04 plans** (operator: "this aspect is more important")
  — it is a core build-correctness mechanism, not a point-fix.
- Surface (`_manifest_rules.py` / `_manifest_decide.py` build-gating + phase-4/5 compose + aspect
  derivation) is adjacent to in-flight PLAN-08 (`_config_defaults.py` / manage-config compose path) —
  coordinate/rebase if the compose reads overlap.
