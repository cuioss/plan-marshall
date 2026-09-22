# PLAN-PR-054: The foreign-PR gate — `540a`, the first half of PLAN-PR-028's mandatory split

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-064` — do NOT emit this spec.** ⭐ **The split this file
> implements is RETIRED because its stated cause is gone**: `PLAN-PR-028` was cut into `540a` / `540b`
> only because ten deliverables broke the ~6 guard, and the operator raised that guard to 12. The whole
> of `PLAN-PR-028` is restored as one plan, carrying this half's D4/D5 and D6 `020` items. ⛔ **This
> file is NOT dead and is NOT deleted**: it records why the split existed and what it scoped. The
> authoritative deliverable text was always `PLAN-PR-028`'s, and `PLAN-PR-064` points there.

epic: review-apparatus
workstream: WS-04

> ⛔⛔ **SPLIT SPEC. This is `540a` of the mandatory `540a` / `540b` split recorded in
> `PLAN-PR-028-a-landing-message-that-cannot-outrun-its-merge.md` § "MANDATORY SPLIT".** Performed by
> the 2026-09-08 `cleanup` pass (A5, redistribution).
>
> ⛔ **The deliverable BODIES are NOT retyped here.** `PLAN-PR-028` stays on disk as the audit record
> and remains the authoritative text for every deliverable this spec carries. The implementing plan
> **READS them from that file** — a deterministic file read, never a reconstruction from this summary.
> Retyping them would be exactly the drift this epic forbids at every other hand-off surface.
>
> `PLAN-PR-028` itself is now **superseded by this spec and `PLAN-PR-055`**, and is never emitted whole.

## Objective

Close the foreign-PR gate's defects: its blocking population, its branch passing, its root anchoring,
its timeouts, its provider check, its row discriminator — and Branch F's unreachable recovery path.

⭐ **This is the stronger half and it is READY.** PLAN-PR-028's own re-grounding records that the `020`
half **re-grounds cleanly and its defects are live**, and that `540a`'s surface **was untouched by
either #1338 or #1344** — so unlike `540b` it does not have to re-derive its line references at outline.

## Deliverables carried

| From `PLAN-PR-028` | Subject |
|---|---|
| **D4** | the foreign gate's blocking population, the published classification status, the pushed/unpushed contract |
| **D5** | Branch F's unreachable recovery; the gate's blocking-set text and `unresolved[]` instruction |
| **D6's `020` items** | the coverage figure's host/foreign split, for the `020` half only |

⛔ **D0 is STRUCK** in the source spec, so this half inherits **no halt gate**. The count derivations
D0 armed its HALT on are stated as facts in PLAN-PR-028 § Re-Grounding rather than as a gate to
re-derive. **Read that section before implementing; do not re-derive what it settles.**

**D0 (this spec) — GATE, mutates nothing.** Read PLAN-PR-028 §§ Re-Grounding, Deliverables D4/D5 and
D6's `020` items, and § Expected Surface, and confirm each named symbol still resolves at HEAD.
**HALT and report** if a named symbol has moved — ⭐ this pass already found that the relayed and
locally-recorded line numbers for `head_sha_verified` had BOTH gone stale while the mechanism held, so
**anchor on symbols, never on line numbers.**

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py`
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py`

⛔ **Epic-tree record, NOT repository source — read input only**, and it reaches no PR diff:
`../cloud-runs/020-a-foreign-task-reports-done-with-no-pr-anywhere/report-01.md` — the D0 single-seam
correction (D5).

## Claim Labels

- OBSERVED: the `540a` / `540b` split is recorded as **settled, not proposed**, in `PLAN-PR-028`
  § "MANDATORY SPLIT", together with the deliverable partition and the surface partition this spec
  implements.
- OBSERVED: `PLAN-PR-028` records `540a`'s surface as **untouched by #1338 and #1344**, so this half
  does not inherit `540b`'s line-reference re-derivation.
- OBSERVED: `PLAN-PR-028`'s D0 is struck, so neither half carries a halt gate from it.
- HYPOTHESIS: every symbol `PLAN-PR-028` § Expected Surface names for D4/D5 still resolves at HEAD —
  confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py`
  § its population-selection and blocking-set functions (verify-at-outline). ⛔ **D0 HALTS on
  refutation**, and anchors on symbols rather than line numbers.

## Dependencies and Sequencing

- ⛔ **`540a` BEFORE `540b`** — PLAN-PR-028's own sequencing note: D5's gate work is independent, and
  D1's mapping table (in `540b` = `PLAN-PR-055`) wants the derived terminal-branch set D4/D5 will
  already have read. **Do not launch `PLAN-PR-055` first.**
- ⛔⛔ **COLLIDES with `PLAN-PR-033`** on `foreign_pr_gate.py`, `phase-6-finalize/SKILL.md` and
  `test_foreign_pr_gate.py`. `PLAN-PR-033` was emitted on 2026-09-08 and carries the two gaps
  `PLAN-PR-028` deliberately left as operator-gated proposals. **Sequence, never pair** — and prefer
  landing `PLAN-PR-033` first, since its operator decisions bound what this plan may implement.
- Adjacent to `PLAN-PR-050` on `phase-6-finalize` docs; disjoint on scripts.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-054-the-foreign-pr-gate-half.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
