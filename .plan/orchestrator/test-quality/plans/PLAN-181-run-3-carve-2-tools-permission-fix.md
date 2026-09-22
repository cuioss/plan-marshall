# PLAN-181: Run 3 Carve 2 — tools-permission-fix Source

epic: test-quality
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-181-run-3-carve-2-tools-permission-fix.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
>
> ⛔ **Scope is exactly one B0 source: `test/plan-marshall/tools-permission-fix/`.**
> Second carve of PLAN-140 run 3 (slice 060), nominated by the run-3 plan's ordered
> 12-source list (drain II) for direct pattern transfer from carve 1
> (manage-providers, #1552): smallest remaining source, densest repeated setup per
> file, same permission-domain family as carve 3 (tools-permission-doctor) so the
> two read as a pair. Deliberately excluded: the other 11 B0 sources (each its
> own carve, staged just-in-time), B1–B4 cluster splits (staged after B0 lands),
> any production-code change (test-only carve).

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode): process compliance is mandatory, not advisory.

## Objective

Reduce the `tools-permission-fix` source to the 400-line module budget (B1) without
losing a single assertion, mirroring carve 1's fixture-hoist shape: hoist repeated
`monkeypatch`/setup into per-source fixtures, split over-budget modules into
`test_*` collection units, and prove fidelity mechanically. Done when the doctor
reports zero over-budget modules in this source, pytest is green both orders, and
the fidelity/dup/banner gates read clean.

## Deliverables

1. **D1 — Re-derive the source scope at dispatch.** The nomination cites 2 files,
   both over budget, with 65 `monkeypatch` + 287 `tmp_path` hits — all LEADS
   (populations move every window). Re-count from the doctor's own sweep before
   sizing; do not adopt the nomination figures.
   *Done when:* the over-budget module list is re-derived at dispatch HEAD and
   matches the nomination shape (small source, setup-dense) or the deviation is
   recorded with cause.
2. **D2 — Fixture hoist + splits, no behavior change.** Mirror carve 1
   (`_providers_fixtures.py` pattern): per-source `_*fixtures.py` outside
   collection, repeated setup replayed statement-for-statement, over-budget
   modules split into `test_*` units. Single PR, far under the 100-file
   reviewer ceiling.
   *Done when:* every module in scope reads ≤400 lines and the diff is
   hoist/split-only.
3. **D3 — Fidelity proof.** `_fidelity_diff` before/after on the carve commits:
   test_identities unchanged, lost=0/gained=0 on all three facets, duplication +
   banner reports attached with introduced=0.
   *Done when:* the three reports are attached to the PR with clean verdicts.
4. **D4 — Green both orders + doctor clean.** `pytest` on the source default
   order + reverse directory order, both green, no new skips; doctor
   `test-conventions` error-0 with the budget count down by exactly the scoped
   modules.
   *Done when:* both pytest runs green at the merge HEAD and the doctor
   figures reconcile.
5. **D5 — Per-PR review logging.** Tier M: `skip-bot-review` label; log label
   y/n, CodeRabbit skipped y/n, Sourcery present y/n + dispositions. Every
   arrived Sourcery comment triaged/handled before merge.
   *Done when:* the D5 log lines are in the landing message.

## Claim Labels

- OBSERVED: carve 1 (manage-providers) landed as #1538-adjacent shape via PR
  #1552 — read at `landings/`-adjacent epic record (3 files, test_configure
  752→713, fidelity 208→208 lost=0, doctor error-0).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: test-quality/cleanup | rescoped: n/a | evidence: re-read PR #1552 via the CI abstraction: state merged, merge_commit_sha 7a94d3e8a32c48c5de17896808b5ae20dfe00d2f, title test(manage-providers): hoist repeated env setup into per-source fixtures. Body confirms test_configure.py 752->713, fidelity test_identities 208 before/208 after lost=0 gained=0, doctor test-conventions error_count=0. Nothing touched since: git log -1 -- test/plan-marshall/manage-providers/ returns 7a94d3e8a (2026-09-20), the merge itself; wc -l test_configure.py reads 713.
- OBSERVED: carve 2 nominated as tools-permission-fix with 2 over-budget files
  — read at the run-3 drain II record (nomination + 12-source order on file).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: test-quality/cleanup | rescoped: n/a | evidence: files resolved: test/plan-marshall/tools-permission-fix/test_permission_fix.py and test_permission_fix_behavior.py. wc -l at HEAD 7d82d5d906c6 reads 1618 and 1587 - identical to the last recording, both still over the 400 budget by 1218 and 1187. No drift: git log -1 --format=%h gives 3103e9d6a (2026-09-13, #1475) for test_permission_fix.py and fe592d2db (2026-09-18, #1528) for test_permission_fix_behavior.py, so fe592d2db remains the most recent touch across the pair and nothing has landed on the source since nomination.
- HYPOTHESIS: the two files and their setup density at dispatch —
  confirm/refute at `test/plan-marshall/tools-permission-fix/` § scoped
  modules (verify-at-outline; populations move every window, so D1 re-derives
  before sizing).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: test-quality/cleanup | rescoped: n/a | evidence: tracks claim 1 exactly, re-confirmed by the same measurement: both files still over budget at 1618 and 1587 (wc -l at HEAD 7d82d5d906c6), both appear as test-module-line-budget findings in the whole-tree sweep. Setup-density remains a D1 lead with no fixed number to check by design; the epic-surface-partition attribution table attributes exactly these 2 findings to PLAN-181, the only non-<not-derivable> bucket at this HEAD.

## Expected Surface

- OBSERVED: `test/plan-marshall/tools-permission-fix/` — the carve scope (single source directory; fixture modules land inside it or in `test/_shared/` alongside carve 1's shape)

## Dependencies and Sequencing

- Depends on: carve 1 landed (#1552 — the mirror pattern); PLAN-105/PLAN-170
  instruments (landed).
- Overlaps with: PLAN-140 run 3 (RUNNING) owns these files until it yields —
  **emission sequences behind the running plan** (N=1 sequential); the gate
  blocks while R=1. Emit only into a free slot or on operator word
  re-assigning the carve from the run to this row.
- Pairs with: carve 3 (tools-permission-doctor) — same permission-domain
  family, staged next just-in-time.
- Carves 3+ (remaining 11 B0 sources + B1–B4): NOT staged here — one carve per
  emission, just-in-time, per the standing anti-over-planning discipline. The
  ordered list lives in the run-3 drain II record.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-181-run-3-carve-2-tools-permission-fix.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. Every carve report carries a
complete `landing-facts` block (all 9 keys); narrative-only landings cost a
hand-recovery drain every time. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
