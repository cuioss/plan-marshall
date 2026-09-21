# Landing Analysis: PLAN-03 — OpenCode emitter re-enable with inherit fallback

epic: model-provisioning
workstream: WS-02
pr: 1500

> Landing record for one shipped plan. Lives at `landings/PLAN-03.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Spec: `plans/PLAN-03-emitter-reenable.md` (4 deliverables).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Variant emission change (pinned variants carry pin, absent stays inherit-only) | shipped-as-specified | `variant_emitter.py` +93/- (pin-present branch + pin-absent inherit copy), PR #1500 diff |
| Frontmatter transform for both entry kinds | shipped-as-specified | `frontmatter.py` (alias→`anthropic/<id>`, qualified pass-through), `test_frontmatter.py` +12 per-kind assertions |
| Lockstep and emitter tests updated | shipped-as-specified | `test_level_table_lockstep.py` +62/- and `test_variant_emitter.py` +197/- asserting pinned-per-kind + byte-identical fallbacks |
| Narrow-but-never-escalate at emit time | shipped-as-specified | emit-time guard in `variant_emitter.py` |
| In-scope doc touch: ADR-021 cross-reference | shipped-modified (one line, keep) | `doc/adr/021-*.adoc` anchor `Inherit-only emission` → `Per-level model pins`; keeps the ADR truthful after the section rename — no action owed |

Operator invariant (unconfigured pins → inherit-only) holds in the landed
shape: the pin-absent path emits the inherit-only copy of the canonical
frontmatter, and the map-silent default is inherit everywhere.

## Metrics and Anomalies

- Tokens: 0 total — session-degraded capture, operator-approved per paste; archived `metrics.md` carries no token population (all `-`)
- Duration: 16h38m wall (init 32m / refine 2m / outline 39m / plan 56m / execute 10h42m / finalize 3h46m); inbox `total_wall_seconds=59922.0` consistent
- Anomalies: none pasted (no loop-backs, no quota waits); all 23 manifest steps `done` except `archive-plan: pending` at facts-emission time — archive corroborated on disk post-landing

## Routing and Merge Behavior

- Review: `pr reviews` shows sourcery COMMENTED, coderabbit COMMENTED ×2 rounds, operator replies — consistent with pasted "automatic-review (2 comments) + unified triage"; no third-party text ingested beyond the operator paste
- CI/merge: green (`ci-verify`), merged via merge queue as `793300a9` — corroborated via `pr view` (`state: merged`, `merge_commit_sha` matches) and `git show --stat` (7 files, +331/-62)
- Collisions: none observed; realized surface adds only test files + the ADR one-liner against the declared 4-file surface. PLAN-04's declared surface (the same test files) overlaps the realized test footprint, but PLAN-04 is sequenced after PLAN-03 by dependency, never concurrent — no gate correction owed

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-03 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-03 --field pr --value 1500`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-03 --field landing --value landings/PLAN-03.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-03 --field plan_marshall_plan_id --value implement-plan-03-emitter-reenable`
- [x] inbox drained 15/15 — landing reconciled, 1 lesson promoted (003), 13 discarded (recurrence / in-run-fixed / duplicates), each with the two-sided record
- [x] epic.md queue reconciled from status.json
- [x] watch retained: PLAN-02's 2 report-only lesson proposals still await operator record-or-drop
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

- PLAN-04 now unblocked (PLAN-02 + PLAN-03 landed) — proactive emit below
- Count variance (non-blocking): paste says lessons-capture delivered "10 inbox msgs", drain enumerated 14 candidate-lessons + 1 landing from the same sender; all 15 consumed, so nothing is outstanding
