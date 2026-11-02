envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-30T07:06:43Z

# Candidate lesson: two landings in a row carry `effort=unknown`, so `landing-check` reports `complete: false` and the run's effort level is lost (plan-marshall runtime stamp / emit-landing `landing-facts`)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, landings plan-v02-51-lane-conditional-guards (PR cuioss/API-Sheriff#538, inbox message -005) and plan-v02-07-threat-classification (PR cuioss/API-Sheriff#537, inbox message -001).

RELATED: none found in lessons-routing (searched for `effort` with `unknown`).

- `inbox landing-check` returned `complete: false` with `missing_keys: [effort]` for both landings. Every other required fact drained. Both carried `effort=unknown`, `harness=claude`, `model=claude-sonnet-5-5`.
- The earlier landing in the same epic (plan-v02-50-enumeration-detection-substrate, PR #532) carried `effort=medium`, so this is intermittent, not a missing feature. Plugin and executor versions were 0.1.2028 for V02-51 and 0.1.2032 for V02-07.
- The V02-07 landing states the cause in its Residue section: "`model` is self-reported at plan start (landing-time refresh could not measure it: reason model_unknown); no effort was stamped, so `effort=unknown` is a recorded gap."
- Effect on the orchestrator: an Open Defect per landing (the `complete: false` branch of the analyze verb requires one), and a metrics line in the landing report that cannot say what effort the run used, which blocks comparing token and wall-time cost across plans.

Suggested direction: find out why the plan-start stamp sometimes records no effort (and why the landing-time refresh could not measure the model), and either stamp the effort the harness reports at plan start or make the landing facts carry the configured `plan.effort` value when a measurement is unavailable, marked as configured rather than measured.

Evidence: API-Sheriff orchestrator ledger `landings/PLAN-V02-51.md` and `landings/PLAN-V02-07.md` (Metrics sections), `inbox landing-check` results on 2026-10-30, epic Open Defect 18.
