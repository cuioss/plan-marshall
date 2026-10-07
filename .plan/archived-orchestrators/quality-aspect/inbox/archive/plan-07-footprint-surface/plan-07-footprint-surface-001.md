envelope_version=1
sender_type=plan
sender_id=plan-07-footprint-surface
epic=quality-aspect
kind=landing
created=2026-09-21T20:17:41Z

# PLAN-07 outcome: footprint capture and declaration containment — MERGED

sender: plan-07-footprint-surface (plan-marshall plan `plan-07-footprint-surface`)
epic: quality-aspect / WS-04
date: finalize run

## Outcome

PLAN-07 is implemented and merged: PR cuioss/plan-marshall#1559
(merge commit fca06c4ca, squash via merge queue, CI green post-merge).

## Deliverables (all 8 shipped)

1. Footprint diffs against upstream base (resolve_base_ref, origin/main
   preferred with diagnosable fallback) — manage-references.
2. plan_creation_sha persisted at creation; scope_creep_check grades the
   pinned SHA — phase-5-execute + manage-references.
3. Retired references keys unlinked from step inputs (fail closed).
4. Mechanical-sweep sizing from realized single-run throughput
   (analyze-logs + _footprint_resolver).
5. One shared symmetric-difference containment rule for both twin pairs
   (declared-vs-realized, declared-vs-declared); equal-sized disjoint sets
   report fully disagreeing — plan-retrospective + plan-orchestrator.
6. Classified unevaluated state (never row-builder default, never clean
   on unevaluated coverage).
7. Self-review surfacing anchored at origin/main with behind-upstream
   fail-loud — ext-self-review-plan-marshall.
8. Hoisted-binding shadow detector (read-only candidates, check 18).

Plus review-driven follow-ups landed on the branch: N23 registry parity
(test + ext-point schema), family-table label, base_ref_source schema
field, SKILL.md count-prose normalization (seventeen→eighteen).

## Verification

- Full `verify` green on the landed tree (27582 tests); per-bundle
  quality-gate, whole-tree quality-gate, test-compile, whole-tree
  module-tests green at the push gate.
- plugin-doctor clean; pre-submission self-review converged clean;
  lessons-housekeeping retained (no lesson met the removal bar).
- Review loop-backs admitted: 10 iterations used of 14 (self-review
  findings, 2× phase-5 fix rollbacks for TASK-17..20 and TASK-21..23).
- Merge went through the platform merge queue after a clean
  review-completeness barrier (coderabbit required and current;
  cuioss-review-bot reclassified required→optional for this plan only
  by operator decision after its review went stale).

## Gaps / notes for the epic

- Session-token enrichment skipped (no session identity in this
  environment; operator override recorded). Token totals report 0 —
  a floor, not a measurement.
- emit-landing skipped by its own orchestration guard (plan resolves
  non-orchestrated); this message is the spec-authorized outcome
  report instead (Write-Boundary: own inbox message only, no other
  `.plan/local/orchestrator/` writes made except the earlier
  process-compliance finding).
- One process-compliance finding filed during this run:
  process-compliance inbox plan-07-footprint-surface-001.md (direct
  `.plan/` read at init, remediated via --body-file ingestion).
