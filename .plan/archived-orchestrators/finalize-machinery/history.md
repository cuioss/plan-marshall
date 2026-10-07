# History: Finalize machinery — retire the recurring phase-6 defects

slug: finalize-machinery
closed: 2026-09-18
phase at close: orchestrating → closed

> Frozen record of the closed epic. The tree remains on disk as the audit record;
> nothing here mutates. Successor epics: process-compliance (rule-following),
> quality-aspect (measurement integrity). Sibling reference: operator-ux (origin).

## Vision as pursued

Opened 2026-09-03 at operator decision during an operator-ux analyze drain, to stop
that epic acting as the finalize lane's defect inbox. Goal: retirement, not
observation — landed fixes letting corpus lessons be retired, plus confirmation runs.
Two anticipated themes (COST, INVOCATION SURFACES) held; the run added MERGE-GATE and
LEDGER-PIPELINE workstreams plus a seventh plan (session-identity) staged mid-life
from inbox findings.

## Queue outcome (7 shipped, 0 parked, 0 dropped)

| Plan | PR | Landing |
|------|----|---------|
| PLAN-01 head-rearm (WS-01) | 1505 (66733bef) | landings/PLAN-01.md |
| PLAN-02 invocation-surfaces (WS-02) | 1507 (e2e745c) | landings/PLAN-02.md |
| PLAN-03 review-currency (WS-03) | 1510 (dd16f521) | landings/PLAN-03.md |
| PLAN-04 git-branch-mechanics (WS-03) | 1509 (f8b0fa40) | landings/PLAN-04.md |
| PLAN-05 lessons-pipeline (WS-04) | 1527 (6e239a13) | landings/PLAN-05.md |
| PLAN-06 anchors-and-mutex (WS-04) | 1525 (1605831c) | landings/PLAN-06.md |
| PLAN-07 session-identity (WS-04) | 1530 (ba0317c) | landings/PLAN-07.md |

PLAN-01 and PLAN-02 were implemented outside the plan lifecycle (direct checkout
edits, admitted in inbox findings, remediated to branches); the operator accepted
inline verification for PLAN-01. All seven merged via merge queue except where noted
in their landing reports. Machine-persisted re-grounding verdicts were stamped for
PLAN-06 (5 claims) and PLAN-07 (4 claims) pre-transition.

## Decision record (abridged — full log in logs/decision.log)

- Epic opened at operator decision (operator-ux drain, 2026-09-03).
- Decomposed 2026-09-16: 4 workstreams, 6 staged plans, scope N=2.
- Standing Execution Contract rule (opencode + Muse Spark 1.3): every spec carries
  mandatory process-compliance section; emitted commands stay bare file pointers
  (phase-1-init pointer detection is syntax-only).
- Standing routing rule: rule-following findings drain to the process-compliance
  epic's inbox (agreement + 2 forwarded findings filed there).
- Corpus move + purge 2026-09-17: 68 lessons copied to epic `lessons/` with
  `index.md`; 15 retired (12 completely_covered with clause+input, 3 redundant);
  corpus 186→171. Layout variance (new `lessons/` dir) recorded.
- Operator-owed cleanup: delete stray `lessons/2026-09-08-25-09-012.md` (filename
  typo duplicate).

## Carried-forward leads (not dropped, not owned)

1. **Defect 2 — PLAN-06 narrative-only landing.** Machine facts (tokens, wall time,
   steps) unrecoverable by design (unenriched floor). Accept as residual, or retire
   on operator confirmation nothing is owed.
2. **cuioss-review-bot demoted to optional** (operator order, PLAN-05). Re-promote
   when responsive; silence pattern in the archived plan.
3. **process-compliance overlap watch.** Staged-vs-staged surface adjacency
   (PLAN-03/02/07 pairs); coordinate launch timing while that epic runs.
4. **Epic-lesson copies retained in corpus** (~50 open/staged subjects). Retire via
   future lessons-housekeeping sweeps as owning plans ship — quality-aspect inherits
   the measurement/ledger subset.
5. **Sourcery retirement confirmation.** Representative 08-25-09-012 retained pending
   one independent confirmation run (fixed by operator-ux PLAN-10).

## Closing rationale

All staged work shipped; inbox drained (0 queued); no live rows. Remaining items are
residuals, standing notes, or owned elsewhere (process-compliance, quality-aspect).
Closed at operator direction 2026-09-18; archive opt-in follows.
