# Landing Analysis: PLAN-01 — manifest-compose-gaps

epic: plan-optimization
workstream: WS-01
pr: #926 (squash-merged to main — commit `09915b14c`)

> Landing record for one shipped plan. Verified against ground truth: the squash-merge
> commit on main (`09915b14c fix(manifest): wire request_aspect and extend orchestrator-tier
> guard (#926)`) and the presence of `_read_request_aspect` in `_manifest_decide.py` +
> `manage-execution-manifest.py` + SKILL.md. Operator narrative corroborated.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — wire `request_aspect` into compose-time aspect-step-drop | shipped-as-specified (consumer-side, the PREFERRED option (a)) | `_read_request_aspect(plan_id)` added to `_manifest_decide.py` mirroring `_read_recipe_source`; or-fallback at composer aspect read site; compose-level + unit tests. Symbol confirmed in source. Producer-side `--aspect` forwarding deliberately rejected (as the spec allowed either half). |
| D2 — extend `execution_tier=orchestrator` guard to the INITIAL phase-5 envelope (#897 gap) | shipped-modified — re-grounded to NO behavior change | Cross-surface tracing at outline established the gap is ALREADY closed by total compose-time `step_execution_tier` stamping. D2 became a regression test locking the totality invariant + retired a stale "gap-is-open" marker in `phase-5-execute/SKILL.md`. |

**Absorbs contract (HONORED — critical for this epic's orphan-pile history):** both absorbed items
accounted for explicitly, neither silently dropped. D1 shipped the "docs-only plans STILL build"
fix (P4-C1 wiring survivor). D2's "#897 initial-envelope guard gap" was found already-closed and
LOCKED with a regression test + stale-marker retire — the exact "say so explicitly and re-home"
discipline the wave-2 `Absorbs`-as-contract rule demands.

## Metrics and Anomalies

- Tokens: 2.9M total.
- Duration: 7h19m wall — of which ~4h44m (~65%) was CI + merge-queue wait, not active work.
- Anomalies:
  - **Aspect-classifier false positive at init** — flagged `drops_build_steps=true` because
    "docs-only" appeared in the narrative *describing the D1 bug*; operator overrode to
    implementation (plan changes code + tests). Meta: the classifier matched narrative-about-a-bug,
    not a request-to-skip-build. → new watch.
  - **Light lane correctly escalated to deep** when D2 needed cross-surface grounding — expected
    ratchet behavior, not a defect.
  - **Harness kills** on orchestrator-tier verify/coverage builds (external, not our bug) — no
    blind retry; whole-tree quality-gate stamped freshness; `verify / verify` CI was the
    authoritative behavioral gate (green). Consistent with the BK #912 mitigation posture.

## Routing and Merge Behavior

- Review: CodeRabbit found one genuine doc-consistency issue (docs claimed the aspect drop was
  "role-driven"; actually a full-list clear) → fixed. Gemini's `read_json` suggestion declined
  (code mirrors `_read_recipe_source`'s try-except precedent). Self-review + CodeRabbit drove a
  bounded re-settle that converged with 0 new findings.
- CI/merge: `verify / verify` green; squash merge queue; single squash commit on main
  (`09915b14c`). No rebase conflict with in-flight PLAN-02/PLAN-03 (surfaces stayed disjoint —
  disjointness prediction HELD).

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-01 → status=shipped, pr="926", landing="landings/PLAN-01.md"
- [x] epic.md queue row reconciled from status.json
- [x] Open Defects: "docs-only plans still build" (P4-C1 survivor) + "#897 initial-envelope guard gap" retired — absorbed by PLAN-01 D1/D2
- [x] Watch added: aspect-classifier matches narrative-about-a-bug (false positive at init)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **Disjointness prediction held** — PLAN-01 (manifest surface) did not collide with in-flight
  PLAN-02 (finalize) or PLAN-03 (execution-context). No pairing-collision to record.
- **New lessons filed by the plan** (native IDs, not folded here): `2026-07-18-05-001`
  (automatic-review D3 loop_back misfire), `2026-07-18-05-002` (sweep mirrored-contract prose in
  one pass). These are the plan's own corpus entries — not epic-ledger items.
- **New watch** (below in epic.md): aspect-classifier false positive on narrative that *describes*
  a docs/build concern rather than *requests* one. n=1 (#926). Plan-worthy on recurrence — candidate
  fold into a future manifest/classifier plan or the P7 docs-contract family if it recurs.
