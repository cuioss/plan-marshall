# Plan — manifest-compose-gaps (build/dispatch gating completion)

**GROUP: MANIFEST** (surface: `manage-execution-manifest.py` + `_manifest_rules.py` + `phase-4-plan/SKILL.md` compose) — disjoint from finalize-step, execution-context, and docs surfaces; runs in parallel with `finalize-step-integrity`, `leaf-validator-yield`, and `docs-contract-consistency`.

**Error class:** compose-time build/dispatch gating gaps — the manifest layer computes a correct verdict that never reaches (or never gates) the composed task.

> **Frozen-source caveat:** the file:line citations below are from the 2026-07-17 evidence pass and
> WILL have drifted. The outline MUST re-ground every citation against current source before
> implementing (`architecture files --module` + Grep for the named symbols), and reconcile with any
> changes Rung 1 (`plan-global-home-root`) may have made to the manifest/store surface.

## Why (evidence)

Two independent, confirmed gaps sit on the same compose surface. Both were left orphaned after P4 #916 and #897 respectively — P4 fixed only the classifier half of the first.

## Deliverables

### D1 — docs-only/design-first plans STILL run the full phase-5 build (the dominant open defect; P4-C1 wiring survivor)

**Confirmed end-to-end 2026-07-17 (post-#916 main):** an SS-class/docs-only plan still composes and runs phase-5 coverage/module-tests/quality-gate, because the correct aspect verdict is computed, persisted, then dropped before compose.

- The aspect-step-drop `_apply_aspect_step_dropping` (`_manifest_rules.py:165,197-203`) is the ONLY manifest-layer gate that can strip coverage/module-tests/quality-gate from phase-5; it fires only for `aspect∈{analysis,planning}`.
- **The classifier half is already FIXED** (P4 #916 Gap C1): `_cmd_aspect_classify.py` `_NEGATION_PHRASES` table + word-boundary matcher force `aspect=analysis`, `drops_build_steps=true` for "no build"/"docs only". Keep — do NOT re-touch the classifier.
- **The wiring half is OPEN (this deliverable):** phase-1-init persists `request_aspect` to `status.metadata` (`phase-1-init/SKILL.md:583-597`), but the phase-4 compose invocation omits `--aspect` (`phase-4-plan/SKILL.md:743-753`, 0 `aspect` hits) and the composer does a bare `aspect = getattr(args,'aspect',None)` with no self-read (`manage-execution-manifest.py:1472`, feeds the drop at `:1473-1477`). So `_apply_aspect_step_dropping(steps, None, …)` is a guaranteed no-op every run.

**Fix (either half closes it; consumer side PREFERRED — mirrors the existing `recipe_key` self-read precedent):**
- (a) consumer: `manage-execution-manifest.py:1472` self-reads `request_aspect` from `status.json` when `args.aspect is None`; OR
- (b) producer: add `--aspect {request_aspect}` to the `phase-4-plan/SKILL.md:743-753` compose block + a preceding read in its Inputs list (`:692-700`).

The composer's own comment already assumes the value is "forwarded here via `--aspect`" (`manage-execution-manifest.py:1464,1468-1469`) — this is a wiring omission, not a design question. **Acceptance:** an end-to-end docs-only/analysis plan composes a phase-5 with NO coverage/module-tests/quality-gate; a normal implementation plan is unaffected. Add a compose-level test asserting `drops_build_steps` reaches `_apply_aspect_step_dropping` with a non-None aspect.

**Mental-model corrections (keep, do not re-litigate):** `build_map`/`should_execute_build` gates ONLY the phase-6 `pre-push-quality-gate` drop (`:525-554`), NOT phase-5. Lane/posture prunes ONLY `phase_6.steps` (`:1442-1446`). Coverage/module-tests/quality-gate are structurally footprint-immune by design (`_manifest_rules.py:131-132`). The phase-5 coverage step is injected by execution_tier routing (`:851-868`).

### D2 — execution_tier=orchestrator guard does NOT cover the INITIAL phase-5 envelope call site (#897 gap)

The compose-time `execution_tier=orchestrator` structural guard shipped by plan-6 D6 (#893) fires correctly on re-dispatch/fix-task envelopes, **but #897 showed it does NOT cover the INITIAL phase-5 envelope call site** — that initial envelope backgrounded a build before the guard applied (recurrence appended to lesson `2026-06-24-18-001`).

**Fix:** extend the D6 guard to the initial-envelope dispatch site so a leaf never backgrounds a build on the first phase-5 dispatch either. **Acceptance:** a test exercising the initial phase-5 envelope confirms the orchestrator-tier yield is injected at that call site (parity with the re-dispatch site). Re-ground the D6 guard's current location before editing — plan-6's guard and the surrounding routing (`:851-868`) may have moved.

## Out of scope / do NOT expand
- The classifier (already correct — Gap C1).
- Any lane/posture change to phase-5 (footprint-immunity is by design).
- The leaf-can't-sub-dispatch validator topology — that is the separate `leaf-validator-yield` plan.

## Absorbs
- HANDOVER §5 "docs-only plans STILL run the full phase-5 build" (P4-C1 wiring survivor).
- HANDOVER §5 "Leaf-backgrounded builds — NEW coverage gap (#897) initial-envelope call-site" (lesson `2026-06-24-18-001` recurrence).

## Size
2 deliverables, tightly same-surface. Well under the >6 split guard.
