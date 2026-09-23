envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-23T05:48:45Z

# Finding: 4-plan q-gate §2.2 Assessment Coverage unsatisfiable for light-lane plans; leaf over-runs dispatched validator subset

Epic: process-compliance
Plan: implement-opencode-enforcement-parity
Phase observed: 4-plan q-gate-validation dispatch

## Summary

The phase-4-plan q-gate-validation dispatch returned 14 `qgate` findings, ALL of class "Missing assessment for file {path} in deliverable N" from §2.2 Assessment Coverage (`q-gate-validation.md`). The light lane sets `qgate_validation_required: false` for the 3-outline call site (planning-outline.md § lane branch), but phase-4-plan Step 8b signals `qgate_validation_required: true` unconditionally for the 4-plan call site, dispatching q-gate-validation with `validators: [module-mapping-validator, scope-criterion-validator]`. The dispatched leaf then ran the full §2.x battery including §2.2, producing one §2.2 finding per affected file.

## Facet A — Leaf over-ran the dispatched validator subset

`phase-4-plan/SKILL.md` § Step 8b is explicit that this call site runs exactly `module-mapping-validator` and `scope-criterion-validator` (§§ 2.11, 2.12 of `q-gate-validation.md`), and `planning-outline.md` passes `validators: [module-mapping-validator, scope-criterion-validator]` in the dispatch envelope. `q-gate-validation.md` preamble (line 12) states each call site activates a different validator subset via runtime `activation_context` / `validators` parameters. The leaf instead ran §§ 2.1–2.7, 2.11, 2.12, adding §2.2 which was NOT in the dispatched subset — the 14 findings are therefore outside the dispatching call site's declared scope.

## Facet B — §2.2 is structurally unsatisfiable on the light lane (regardless of subset semantics)

Assessments (`CERTAIN_INCLUDE`) are produced ONLY by the deep-lane Complex-Track component analysis in phase-3-outline. The light-lane envelope (`phase-3-outline/workflow/light-lane.md`) folds refine-no-loop + Simple-outline + deliverable-derivation and never writes assessments. Therefore ANY light-lane plan that reaches a call site running §2.2 will flag EVERY affected file, unconditionally and permanently — not because the outline is wrong, but because the assessment store is empty by construction. There is no documented light-lane / `plan_source` exemption for §2.2.

## Suggested fixes

1. Enforce the dispatched `validators` subset as a hard scope in `q-gate-validation.md` Step 4 (the full-coverage guarantee should be read over the subset, not the whole matrix). The 4-plan call site then runs only §§ 2.11/2.12, and §2.2 cannot fire with a 14-finding non-zero block.
2. Add a light-lane carve-out for §2.2 (assessment coverage) — either the light-lane call sites skip §2.2 explicitly, or §2.2 gains an activation condition gated on the outline being deep-lane/Complex-Track derived (e.g., assessment store populated).
3. If enforcement is intended to be universal, the light-lane envelope must gain an assessment-producing step — a much larger change and likely not the intent.

## Evidence

- `phase-4-plan/SKILL.md` § Step 8b (B2 note, lines ~940–943): "What B2 suppresses is precisely the pair this call site activates (`planning-outline.md` → `validators: [module-mapping-validator, scope-criterion-validator]`)."
- `q-gate-validation.md` lines 11–12 (call-site subset semantics), §2.2 (lines 168–182, no activation condition, no lane/plan_source gate), Step 4 full-coverage guarantee (line 152).
- `planning-outline.md` line 51: light lane sets `qgate_validation_required: false` for the 3-outline call site.
- Observed `manage-findings qgate list`: 14 findings, all `source: qgate`, `type: triage`, all §2.2 "Missing assessment" text.
