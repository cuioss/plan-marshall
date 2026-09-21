# History: Execution-context model provisioning (machine-local)

slug: model-provisioning
closed: 2026-09-16
outcome: all 4 plans shipped, epic done-state proven live

> Frozen record of the closed epic. Written once by the `close` verb; the live
> ledger (`epic.md`, `status.json`, `logs/`) remains on disk untouched as the
> audit record. Reopening is a new epic, never an edit of this file.

## Vision as pursued

Re-establish per-level model provisioning for `execution-context` variants on
open-model-set harnesses: a machine-local effort-to-model map (local models +
provider-routed configs, schema-level kind discriminator), a resolve-chain slot
above the inherit fallback (ADR-021), a marshall-steward step materializing
per-level pins, and an emitter re-enable threading those pins into OpenCode
level variants. Operator invariant throughout: unconfigured pins always resolve
inherit-only.

## Queue outcome

- PLAN-01 schema-resolve-slot (WS-01) — shipped as #1490 (`fb8aadc9`, report `landings/PLAN-01.md`)
- PLAN-02 steward-pin-materialization (WS-02) — shipped as #1499 (`71a08925`, report `landings/PLAN-02.md`)
- PLAN-03 emitter-reenable (WS-02) — shipped as #1500 (`793300a9`, report `landings/PLAN-03.md`)
- PLAN-04 live-verification (WS-03) — shipped as #1503 (`ac981779`, report `landings/PLAN-04.md`)
- Parked/dropped: none. Parallelization scope stayed 1 (strictly sequential) throughout.

## Decision record (condensed; full trail in `epic.md` + `logs/`)

- Epic home is a fresh epic (not a multiplattform/tooling-truthfulness follow-up).
- `parallelization_scope` = 1, operator-set at init.
- Inherit fallback unconditional (operator invariant, mid-PLAN-02; enforced at every landing).
- PLAN-03's ADR-021 one-line cross-reference touch kept (anchor rename, truthful).
- PLAN-04 realized surface narrower than declared (1 of 3 files) — no gate impact, last sequential plan.
- Lessons: 1 promoted to corpus (`2026-09-16-11-001`, OpenCode token-capture gap); 13 inbox candidates discarded (corpus recurrence / in-run-fixed / duplicates).

## Carried-forward leads (not dropped, not resolved here)

- PLAN-02's 2 report-only lesson proposals (compose change-type, argparse-recurrence) in the archived plan's `quality-verification-report.md` — record-or-drop still awaits an operator word; raise in any session and dispose via the lessons-handling mode.

## Closing rationale

Epic done-state proven live by PLAN-04: all 7 levels resolve per kind, unpinned stays inherit-only byte-identical, never-escalate enforced. Queue empty, inbox drained (18 archived), no open defects. Closed 2026-09-16 on operator `close and archive`.
