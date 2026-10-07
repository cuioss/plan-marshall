# WS-07: Landed-Corpus Remediation

epic: code-intelligence-substrate

> Charter document for one workstream. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

This workstream discharges the defect corpus produced by auditing the epic's own landed output. In
August 2026, 36 staged specs were exported to `doc/plans/code-intelligence-substrate/`, executed in
cloud sessions, and every one of them landed. Each landing was then independently audited against
the tree it left behind, and each audit was attacked by a second reviewer that had not produced it.
The result is **473 recorded gaps — 46 high, 217 medium, 210 low** — and eight fix plans derived
from them.

The workstream closes when those eight plans have landed and the gap corpus is discharged. It is a
remediation wave, not a new capability: **every deliverable in it corrects shipped behaviour or a
shipped self-description that is false.**

⭐ **The wave exists because the audit found one shape repeating across the whole epic**: *a
confident verdict published over a population the instrument never examined*, enabled by *a guard
that cannot fire*. The epic's own instruments carry it. Several plans reproduced it **inside the
fix built to remove it**.

## Scope

- **In scope**: the 473 gap entries from the 2026-08 landed-corpus audit, each assigned to exactly
  one of the eight `5xx` plans; the plans' own `## Gap coverage` sections are the authority for
  which gap belongs where.
- **Out of scope**: new capability on any tier-ladder surface (that stays with WS-01 through
  WS-03); the measurement work still blocked on corpus availability (that stays with WS-04 and
  WS-06, where the blocked deliverables already live).

⚠ **Workstream membership does NOT drive pairing.** Serialization classes are derived from
**surfaces**, per `epic.md` § "Serialization classes are derived from surfaces". These seven plans
sit in one workstream for charter and provenance only; the disjointness check reads each spec's
`## Expected surface`.

## Plans

| Plan | Status | Gaps | High | Notes |
|------|--------|-----:|-----:|-------|
| PLAN-CIS-048-lsp-and-derivation-resolver-correctness | shipped | 28 | 10 | Landed as #1321. The wave's first plan; post-run audited during the 2026-08-22 ingest, not by the original audit. |
| PLAN-CIS-051-detector-and-auditor-integrity | staged | 36 | 11 | Highest high-severity density in the wave. |
| PLAN-CIS-052-finalize-dispatch-and-blocking-boundary-observability | staged | 24 | 6 | Preferably before `053`. |
| PLAN-CIS-049-architecture-store-query-truthfulness | staged | 59 | 5 | |
| PLAN-CIS-050-measurement-and-cost-integrity | staged | 64 | 9 | |
| PLAN-CIS-053-test-suite-anti-vacuity | staged | 73 | 2 | Groups by **failure shape**, not by source plan — deliberately. |
| PLAN-CIS-055-cloud-plan-lane-contract-proposals | staged | 32 | 0 | Records proposals for the operator; ships no contract amendment. |
| PLAN-CIS-054-documentation-surface-truthfulness | staged | 156 | 3 | **LAST** — it corrects descriptions of behaviour the other seven change. |

## Sequencing and Surface Notes

Recorded by the audit, and binding where stated:

- **`052` (`540`) preferably before `053` (`550`)** — `053` widens the finalize seam sweep, which is
  red while `052`'s two unmigrated dispatch sites remain, so landing `052` first gets there in one
  step. ⚠ **This is a preference, not a prerequisite.** `053` is order-independent by construction:
  its D1 prerequisite probe holds each such item with its test body recorded when the sibling has
  not landed. **Do not hold `053` for it.**
- **`054` (`560`) LAST** — it corrects descriptions of behaviour the other seven plans change.
  Running it early guarantees re-work.
- **`050`, `051` and `053` must not run concurrently against `audit.py`.**
- **`049`, `052` and `053` overlap on the architecture and finalize surfaces.**

These last two are **conflict-avoidance constraints, not prerequisites** — they bound which pairs
may be emitted together, not which order the work must take.

⛔ **Two cautions carry into any run that picks these up**, both from the audit:

1. **Where a gap entry and its adversarial review disagree, the review wins.** It is the later,
   evidence-bearing pass, and the fix plans already carry its corrections.
2. **Any figure derived from a duration or throughput is a lead, not a fact.** The audit ran many
   agents concurrently in one tree, and at least one timing-based finding was proven to be
   contention rather than a real property. Re-measure before acting.

The full per-plan evidence — `plan.md`, `report-01.md`, `verification.md`, `gaps.md` for all 36
landed plans plus the audit's own records — is archived under `cloud-runs/`. The `5xx`
plans restate what a run needs and cite those files as corroboration rather than as required
reading.
