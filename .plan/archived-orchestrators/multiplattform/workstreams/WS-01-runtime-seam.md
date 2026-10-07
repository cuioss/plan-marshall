# WS-01: The runtime seam is target-opaque

epic: multiplattform

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-runtime-seam.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the `platform-runtime` seam: the `Runtime` ABC, its router, the two concrete runtimes, and every
general script that reaches a runtime capability. The workstream closes when a third-target
implementer can read `runtime_base.py` alone and either implement or honestly decline every
operation — no target vocabulary in the contract, no argument or return value carrying one target's
grammar, and no general script binding a concrete runtime by name.

## Scope

- **In scope:** `platform-runtime/scripts/**` (ABC, router, both runtimes), `platform-runtime/standards/contract.md`, `platform-runtime/SKILL.md`, the permission skills that consume runtime operations (`tools-permission-doctor`, `tools-permission-fix`, `workflow-permission-web`), and their `test/` subtrees.
- **Out of scope:** the build-target machinery under `marketplace/targets/**` (WS-02); Claude literals in bundle prose and non-runtime scripts (WS-03); the developer deploy loop (WS-04).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-runtime-seam-neutrality | landed | Target-opaque install op, neutral ABC docstrings, consolidated registration, parameterized OpenCode dispatch. PR #1291. |
| PLAN-08-permission-skills-through-the-registry | landed | The permission skills state intent and route through the registry instead of importing `claude_runtime` by name. PR #1393, `landings/PLAN-08.md`. |
| PLAN-09-runtime-seam-completeness | landed | Close the Goal-vs-criteria gap PLAN-01 left: decline vocabulary for four ops, the OpenCode metrics fabricated-success violation, the residual target enumeration, single-sourced registration, and the SKILL.md op table. PR #1405, `landings/PLAN-09.md`. |
| PLAN-14-permission-web-and-rule-pack-class | landed | `permission_web.py`'s WebFetch-grammar render and raw settings I/O, plus `permission_doctor.py` + the three permission standards docs as rule-pack-class material. PR #1408, `landings/PLAN-14.md`. |

## Status: COMPLETE

⭐ **Every plan in WS-01 has landed** — PLAN-01 (#1291), PLAN-08 (#1393), PLAN-09 (#1405),
PLAN-14 (#1408). The strictly-sequential chain below was executed in order and no member ever ran
beside another.

⛔ **Two things this workstream did NOT close, recorded here so its completion is not read as
closing them:**

1. **The `permission_fix.py` permission-DSL residue is still open and now UNCLAIMED.** PLAN-08 owned
   the coupling-inventory row and landed without touching the file; PLAN-14 excluded it by name as
   "PLAN-08's surface". No further chain member exists to pick it up — it needs its own spec.
2. **`permission_doctor`'s direct-script `detect-*` route reports a false zero on a non-Claude
   target.** PLAN-14 declared the rule-pack class but the declaration is structural, not a dispatch
   path, so enforcement remains open. Also unclaimed.

Both are recorded in `epic.md` § Open Defects.

## Sequencing and Surface Notes

- **PLAN-08 → PLAN-09 → PLAN-14 is strictly sequential.** All three edit `platform-runtime/scripts/**`; PLAN-09's decline-vocabulary work also lands on `contract.md`, which PLAN-08 changes first. Nothing in this workstream may run beside another member of it.
- PLAN-08 runs after PLAN-01 and PLAN-03 (both landed) — it starts from the shape PLAN-03 established and closes the residue PLAN-03 registered.
- PLAN-14 runs after PLAN-08 because the semantic vocabulary PLAN-08 D2 builds is what `permission_web.py` must consume; building it twice is the coupling inverted rather than removed.
- **Cross-workstream collisions:** PLAN-06 and PLAN-07 (WS-03) both conditionally touch `platform-runtime/standards/contract.md`. Every member of this workstream is therefore sequenced against those two, not run beside them.
- PLAN-04 (WS-04) is disjoint from every plan here and is the standing concurrency partner under `parallelization_scope: 2`.
