# PLAN-07: The orchestrator script is one module per command group

epic: orchestrator-refactor
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-07-orchestrator-script-decomposition.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.
>
> **Lowest confidence in this epic's corpus.** Listed last because it has no external forcing
> function — nothing breaks if it is deferred or dropped — and because it collides with
> essentially every other plan in the epic. Operator discretion to keep, defer, or drop at
> `next`-time.

## Objective

Split `orchestrator.py` along its existing command-group seams so each group is an
independently readable, independently testable module, matching the split
`_orchestrator_inbox.py` already demonstrates. Behaviour-preserving throughout: no verb, flag,
output field or error code changes.

## Deliverables

1. **D0 — the split plan**, derived from the measured line attribution, naming each new module
   and what moves into it. `corpus` is the first and largest.
2. **D1 — `corpus` extracted**, behaviour-identical, with its argparse group.
3. **D2 — the remaining groups**, each behind its own gate.
4. **D3 — a behaviour-preservation proof**: every verb's TOON output compared before and after,
   field by field, against a fixture epic.

## Non-Goals

- No verb, flag, output field, or error code changes. If any does, the plan has failed.

## Claim Labels

- OBSERVED — `orchestrator.py` is 4,919 lines / 227,505 bytes; `_orchestrator_inbox.py` is
  2,420 lines / 112,955 bytes; 7,339 lines in two files (measured at research time).
- OBSERVED (derived by AST walk of top-level definitions, line ranges inclusive, at research
  time — re-derive at outline since PLAN-01/-02/-05/-06 will have edited this file first):
  header + constants 1-576 (11.7%); shared helpers 577-1062 (9.9%); `scaffold` 1063-1087
  (0.5%); `queue` 1090-1332 (4.9%); `resume-summary` 1335-1745 (8.4%); `archive` 1748-1807
  (1.2%); **`corpus` 1810-3447 (1,638 lines, 33.3%)**; `cleanup` 3450-3676 (4.6%);
  `compact` 3679-4109 (8.8%); `preflight` 4112-4364 (5.1%); argparse 4367-4908 (11.0%);
  `main` 4912-4915.
- OBSERVED — the split precedent exists in the same directory: the 9 `inbox` verbs already
  live in `_orchestrator_inbox.py` and are imported at `orchestrator.py:133-150`, with their
  argparse group (`_add_inbox_group`) still in the parent (228 lines).
- OBSERVED — `corpus` alone has 7 verbs and, at research time, 1,638 lines; its argparse group
  (`_add_corpus_group`) is a further ~146 lines.
- HYPOTHESIS — each group's argparse builder should move with its group, leaving the parent a
  dispatcher; confirm/refute at `_build_arg_parser` against the existing `_add_inbox_group`
  precedent, which did NOT move its builder (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: precedent holds exactly: architecture search --content "_add_inbox_group|_add_corpus_group|def _build_arg_parser" returns 5 matches in plan-orchestrator/scripts/orchestrator.py and zero in _orchestrator_inbox.py - the inbox split left its argparse builder in the parent, as claimed. The should-move normative half remains an unbuilt design choice.
- Verify-first clause: this plan MUST be sequenced last, after every other plan in this epic
  has landed. Re-derive the line attribution against the actual HEAD at outline time — every
  other plan in this epic edits `orchestrator.py`, so the research-time figures above will be
  stale by the time this plan runs.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: the staleness it predicts has already occurred: orchestrator.py 5470 lines (recorded 4919, +551/+11.2%), _orchestrator_inbox.py 3351 (recorded 2420, +931/+38.5%) - 8821 lines in two files, not 7339. Every cited range shifted (cmd_archive now at :1958, _spec_paths now at :2021). Sequencing precondition unmet: PLAN-02/03/05/06 all staged, only PLAN-01/PLAN-04 shipped, PLAN-07 itself parked.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`

## Dependencies and Sequencing

- Depends on: PLAN-01, PLAN-02, PLAN-05, and PLAN-06 (all edit `orchestrator.py`). This plan
  is sequenced STRICTLY LAST in the epic, after every other plan has landed — it collides with
  nearly every other candidate in this corpus and has no forcing function of its own.
- Overlaps with: PLAN-01, PLAN-02, PLAN-05, PLAN-06 (all touch `orchestrator.py`).
- Adjacent to: none beyond the above.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-07-orchestrator-script-decomposition.md"
```

## Write-Boundary

The plan implementing this spec touches only repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other
ledger write — and reports its outcome through its PR and its inbox message. The inbox
exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
