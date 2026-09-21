# History: tooling-truthfulness

Frozen at close. The live ledger (`epic.md`, `status.json`, landings, logs)
remains on disk as the audit record; this document is the final state.

## Vision as pursued

The orchestration machinery reports what it actually checked. Every member
shared one shape — a could-not-evaluate reported as a clean result — and the
standard applied reflexively: a fix that cannot be shown to fail before it
lands is exactly the vacuous pin this epic existed to remove (ADR-019).

## Queue outcome: 8 shipped, 0 parked, 0 dropped

| Plan | PR | Outcome |
|------|----|---------|
| PLAN-01 script-surface-validation (WS-02) | #1466 | shipped |
| PLAN-02 repo-hygiene-residues (WS-04) | #1468 | shipped |
| PLAN-03 build-path-evidence (WS-03) | #1469 | shipped |
| PLAN-04 gate-comparability (WS-01) | #1472 | shipped |
| PLAN-05 declaration-currency (WS-01) | #1482 | shipped |
| PLAN-06 test-falsifiability-survey (WS-05) | #1476 | shipped |
| PLAN-07 opencode-install-docs (WS-06) | #1484 | shipped, incl. operator-directed split of `doc/user/installation.adoc` into `install-claude.adoc` + `install-opencode.adoc` (11-match / 8-file retarget, zero residual) |
| PLAN-08 slug-semantics-model-compliance (WS-02) | #1487 | shipped — staged by the process-compliance Watch TRIGGER (Muse Spark 1.3 bypass x2 + `model-provisioning` decompose slug mis-fill); D1 decompose Step 5 semantic, D2 duplicate-slug lint, D3 resume-summary shared-slug detector, D4 bypass-enforcement registry; live-verified `shared_slugs_count: 0`, `epic_slug_matches_count: 0` |

Terminal queue state: empty. Inbox at close: 0 queued, 37 archived.

## Decision record (carried in full in `logs/decision.log`)

- Emit form: `/plan-marshall` one-line pointers (operator direction 2026-09-10).
- This epic's existence discharged `multiplattform`'s close precondition.
- `parallelization_scope: 2`, second slot routinely unfilled (overlapping orchestrator surfaces) — normal, not failure.
- Process-compliance Watch TRIGGER FIRED absorbed as Open Defect and retired via staged PLAN-08, mechanism-only.

## Lessons promoted to the corpus

`2026-09-11-19-001` (argparse drift, 5-plan recurrence), `2026-09-11-19-002`,
`2026-09-12-08-001` (+ recurrence), `2026-09-12-17-001`, `2026-09-12-17-002`,
`2026-09-13-09-001`, `2026-09-13-12-012`, `2026-09-13-12-013`,
`2026-09-13-12-014`, trigger-B fold into `2026-09-06-07-003`.

## Carried-forward leads (not silently dropped)

- `model-provisioning` epic scaffolded (scope 1, phase `init`): machine-local
  effort→model map, sequenced after the effort-lever Watch re-check.
- `multiplattform` final verification: 35/35 requirements complete per
  operator rulings (relocation / vacuous-satisfaction / ledger-resident
  inventory / intent-accepted qualifications); record at
  `archive/final-analyzis/` inside the multiplattform ledger.
- One-line follow-up for the multiplattform owner: ingested
  `archive/README.md` links `reference/coupling-inventory.md` relatively into
  a nonexistent `archive/reference/` (stale from the ingest move).

## Closing rationale

Every recorded member either fixed with a red-first guard distinguishing
*checked and clean* from *could not check*, or closed with a positive account
of why it needs no fix. Queue empty, inbox drained, no launched plan
unreconciled. Closed on operator word.
