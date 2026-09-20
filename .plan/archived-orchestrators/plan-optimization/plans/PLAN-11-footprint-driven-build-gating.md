# PLAN-11: footprint-driven-build-gating

epic: plan-optimization
workstream: WS-05

> Staged plan spec. Consumer-surfaced (nifi-extensions `2026-07-18-documentation-cleanup`) + root
> cause orchestrator-VERIFIED 2026-07-18 (`request_aspect=implementation` in the archived
> status.json). **This plan REVISITS an intentional design decision** — PLAN-01's phase-5 build-step
> footprint-immunity — with explicit operator endorsement (2026-07-18): footprint should be the
> authority for "when to build". Re-ground all file:line citations at outline.

## Objective

Make the "when to build" decision footprint-driven for phase-5: build/test/quality-gate/coverage run
**iff the footprint contains buildable changes** (e.g. Java), and are skipped when it does not (e.g. a
pure `doc/**` change). Today this footprint gate (`should_execute_build` / `build_map`) governs ONLY
phase-6; phase-5's build steps are footprint-immune by design and rely solely on the narrative-derived
`aspect`, which is unreliable — nifi's "documentation cleanup and PlantUML-to-SVG migration" was
classified `implementation`, so phase-5 ran full `verify -Psonar` on a docs-only change while phase-6
correctly reported docs-only (0 bundles). This asymmetry is the defect.

## Deliverables

### D1 — footprint gates phase-5 build/test/quality-gate (the core mechanism)

**Verified (orchestrator, 2026-07-18):** phase-6 is footprint-aware (nifi archived status.json:
`pre-push-quality-gate` "green for 0 bundle(s) — docs-only"; `ci-verify` "docs-only") but phase-5's
quality-gate sweep ran `verify -Psonar` because `request_aspect=implementation`. PLAN-01's model:
`build_map`/`should_execute_build` gates ONLY the phase-6 `pre-push-quality-gate` drop
(`manage-execution-manifest.py:525-554`), NOT phase-5; the phase-5 build/coverage steps are
footprint-immune by design (`_manifest_rules.py:131-132`) and injected by execution_tier routing
(`:851-868`). **Fix:** extend the footprint-driven gate so phase-5 build/test/quality-gate/coverage
steps are dropped when the footprint has no buildable changes — the same authority phase-6 already
uses. **Acceptance:** a plan whose footprint is pure `doc/**` composes a phase-5 with NO
build/test/quality-gate/coverage regardless of the narrative aspect; a plan touching `*.java` still
composes and runs them. Add compose-level tests for both footprint classes.

### D2 — footprint-consistent aspect derivation (operator option A — the consistency layer)

So `aspect` and footprint agree: when the resolved footprint is purely non-compilable (`doc/**` and
peers), derive `aspect=analysis` / `drops_build_steps=true` so PLAN-01 #926's existing aspect-step-drop
also fires and the two mechanisms never disagree. This keeps the narrative negation-phrase classifier
(PLAN-01 kept it) intact and adds footprint as a second, authoritative signal. **Acceptance:** a
docs-migration request that reads as implementation but whose footprint is pure `doc/**` resolves to a
build-free phase-5 via BOTH the D1 footprint gate and a footprint-consistent aspect.

> **Design note (do NOT skip at outline):** D1 revisits PLAN-01's deliberate phase-5 footprint-immunity.
> The outline MUST confirm WHERE the footprint is known with enough fidelity at compose time (the
> footprint may only be fully resolved after planning) and whether the gate belongs at compose,
> execution_tier routing, or a per-step guard. Option B (blanket phase-5 short-circuit) was NOT chosen;
> the mechanism must build on `should_execute_build`/`build_map`, not a new parallel path.

## Out of scope / do NOT expand
- The narrative negation-phrase classifier (PLAN-01 Gap C1 — keep).
- Phase-6 gating (already footprint-aware — the reference behavior, not the target).

## Absorbs
- The nifi docs-only-still-builds observation (2026-07-18) — the visible symptom.
- The broader "when-to-build mechanism didn't gate phase-5" reframing (operator, 2026-07-18) — the root.

## Expected Surface

- `manage-execution-manifest/scripts/_manifest_rules.py` + `_manifest_decide.py` + `manage-execution-manifest.py` (build-gating + compose)
- phase-4/phase-5 compose + execution_tier routing (where phase-5 build/coverage steps are injected)
- the aspect derivation path (D2 consistency layer)
- tests: compose-level footprint-class tests (pure-doc vs java)

## Dependencies and Sequencing

- Depends on: none (builds on PLAN-01 #926's shipped aspect-drop + the existing `should_execute_build`).
- Overlaps with: in-flight PLAN-08 (`_config_defaults.py` / manage-config compose path) — adjacent
  compose surface, likely different functions; rebase if they collide. Disjoint from PLAN-09/PLAN-10.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-11-footprint-driven-build-gating.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-11.md is recorded}
