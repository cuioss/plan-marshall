# PLAN-PR-015: A barrier override is not bound to the HEAD it was granted against, so a docs-only ruling authorized a merge containing five production commits

epic: review-apparatus
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — inbox `code-intelligence-substrate-004` § 4, drained 2026-07-30

Forwarded from the PLAN-02 landing on PR **#1067** and removed from that epic's ledger. Its sender calls
this "the single most important finding of the plan"; this epic agrees.

⭐ **Staged rather than folded, over a real temptation to fold into PLAN-PR-013.** Both enforce one
invariant — *an approval is scoped to the HEAD it was established against* — but they govern different
subjects through different code paths: PR-013 governs a **bot's participation credit**, this plan governs
an **operator's authorization**. PR-013 also already sits at the split-guard threshold. ⛔ **If either
plan's D1 finds the two converge on ONE barrier predicate, say so and consolidate rather than shipping
two fixes for one invariant.**

## Objective

The pre-merge review barrier can be overridden by the operator. The override is recorded, but it is
**not bound to a HEAD**. When the HEAD subsequently changes, the authorization silently carries over to
a tree the operator never saw.

⛔ **The operator's reasoning was delta-shaped; the persisted authorization was not.**

## The evidence, and why it is not a near-miss

| Time (UTC) | Event |
|---|---|
| 12:37:07 | Operator **overrides** the barrier. Recorded rationale: unreviewed delta is **docs-only** — 2 ADR files, 542 insertions, **no buildable source**; the production changeset was reviewed at `405b05f06` |
| 13:08:51 | Merge lock acquired — merge is seconds away |
| 13:10:01 | Merge **ABORTED**, for an entirely unrelated reason: upstream `#1066` landed `doc/adr/012` while this plan held its own `doc/adr/012` |
| — | Forced rebase, ADRs renumbered, re-verify, re-push |
| ~13:35 | The re-push re-triggers CodeRabbit, which files **5 genuine defects, 3 Major** |
| 14:30:36 | Barrier re-evaluated at the new HEAD `76c7200b6`. Recorded: *"Merging under the operator ruling recorded earlier"* |
| 14:41:54 | **Merged** |

⛔ **The five defects were not caught by a gate. They were caught by an ADR-number collision.** Had the
numbers not happened to clash, `#1067` merges at ~13:09 carrying:

- a resolver-identity registry admitting a truthy non-`str` id — able to abort **every graph query** on a
  mixed `str`/`int` sort, and to silently collapse two distinct resolvers sharing an id into one producer;
- a `merge_resolver_edges()` dropping self-edges and unknown endpoints **with no `notes[]` entry**, so a
  resolver reports `status: ok`, zero edges, and no suppression reason — ⭐ **a vacuous confident zero,
  inside the plan whose entire stated purpose was anti-vacuity**;
- a `discover_derivation_resolvers()` call outside the `try/except ImportError` guarding the documented
  zero-resolver fallback, turning every graph-family verb into `status: error` on a missing path.

## Deliverables

1. **D1 — GATE (mutates nothing): derive every merge-gate authorization that is not HEAD-scoped.**
   ⛔ **The operator override is a SAMPLE, not the population.** Enumerate every mechanism that can
   satisfy or bypass the pre-merge barrier — operator override, force-done, `barrier_mode: ask`
   dispositions, any recorded ruling — and for each, record whether it captures the HEAD it was granted
   against and whether anything re-checks that HEAD before it is honoured. ⚠ Compare against
   `head_at_completion`, which `phase_steps` **already** records for other steps: the pattern exists in
   this codebase and the override simply does not carry it. **Reuse it; do not invent a second one.**
2. **D2 — an override is bound to its HEAD and LAPSES when the HEAD moves.** Rebase, loop-back, amend,
   force-push — any change. A lapsed override must be re-sought, not silently re-honoured.
   ⛔ **This deliberately moves a merge verdict**, so it ships with D5(c)'s evidence, never on assertion.
3. **D3 — the override records WHAT it was granted over, not merely that it was granted.** The 12:37
   rationale was explicitly *"docs-only, no buildable source"*. A persisted authorization that drops the
   delta-shape cannot be re-evaluated against a later delta by anything, human or code. ⚠ Settle whether
   the re-check is *shape*-based (still docs-only ⇒ still covered) or *identity*-based (any HEAD change
   ⇒ lapse). **Identity is the safe default; shape-based re-checking is an optimization that must not be
   built before D1 shows it is needed.**
4. **D4 — the barrier's second evaluation must GATE on the gap it reports, or state that it is not
   gating.** ⭐ The 14:30 log entry is **exemplary**: it records that Sourcery still refuses and that
   *"Required bot pr-agent has not re-reviewed this exact HEAD."* **It states the gap and merges anyway.**
   ⛔ **The defect is not in the recording — it is that a correctly-recorded caveat gated nothing, and in
   the log it reads exactly like a gate that passed.** Either it blocks, or it says in terms that it is
   proceeding despite an open gap under a named authorization.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) An override granted at HEAD A does not satisfy the
   barrier at HEAD B. (b) A re-sought override at HEAD B does. (c) ⭐ A regression pinning the `#1067`
   shape end-to-end: override at a docs-only HEAD → rebase introducing production commits → barrier
   refuses to honour the stale override. (d) The authorization population D1 derives is **derived**,
   non-empty, and every member asserted — copy `test/_shared/_dispatch_roster.py`.

## Claim Labels

- OBSERVED (orchestrator-verified via the GitHub API): `#1067` merged at **14:41:54Z**, merge commit
  `c6b501e6`, head `76c7200b`; CodeRabbit's review is timestamped **13:35:43Z** carrying 5 actionable
  findings; the three fix commits are `14d4e3dc` / `c4ff2273` / `76c7200b` at 14:03:46–14:04:05Z.
- ⚠ **CORRECTED from the forwarded message**: it records the merge at **15:02:32** and the CodeRabbit
  re-trigger at **13:40:11**. The API says **14:41:54Z** and **13:35:43Z**. The discrepancy is unexplained
  (possibly a differing clock in the plan's own decision log) and **does not affect the finding** — the
  override still spans the rebase either way. ⛔ **Use the API times; re-derive rather than citing the
  message's.**
- OBSERVED (forwarded, from the plan's own `logs/decision.log`, not independently read by this epic — the
  plan directory is outside the orchestrator's carve-out): the 12:37:07 override and its docs-only
  rationale, the 13:10:01 abort on the ADR-012 collision, and the 14:30:36 re-evaluation wording.
  **Confirm/refute artifact**: that plan's `logs/decision.log` at those three timestamps. ⚠ The wording of
  the 14:30 entry is load-bearing for D4 — read it verbatim before scoping.
- ⭐ OBSERVED (operator self-report, trusted narrative): *"I applied your 'merge anyway' authorization,
  given against a docs-only delta, to a state that later included five production commits that didn't
  exist when you granted it. I should have re-asked."* ⛔ **The human half is already owned and needs no
  remedy from this plan. The tooling half is that nothing made re-asking necessary** — build for that,
  and do not add process ceremony aimed at the human.
- HYPOTHESIS: the override's persisted form has no HEAD field at all (rather than an unchecked one) —
  confirm/refute at D1. The two have different fixes: a missing field is an addition, an unchecked field
  is a predicate bug.
- HYPOTHESIS (an asserted absence — **verify it, do not assume**): no existing mechanism already lapses an
  override on HEAD change. ⚠ **This epic asserted an absence without checking once already today and was
  wrong** (`review_rate_window_await` was shipped all along). **`grep` before concluding this one.**

## ⛔ Prohibited remedies

- **Do NOT fix this by removing the override.** It is the sanctioned escape, and PLAN-PR-008 exists
  because a previous fix removed the only escape without replacing it. ⛔ **Do not reproduce that.**
- **Do NOT fix it by re-prompting the operator on every HEAD change regardless of delta.** That trains
  reflexive approval, which is a worse failure than the one being fixed.
- ⚠ **Do NOT treat the honest 14:30 log entry as the defect.** The recording was right; the gating was
  absent. A remedy that makes the log quieter has fixed nothing and destroyed the audit trail.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` —
  the barrier's override path and its second evaluation (verify-at-outline; shared with PR-008/009/013/014
  — see Sequencing).
- HYPOTHESIS: wherever the override is persisted — plausibly `manage-status` `phase_steps` beside
  `head_at_completion` (verify-at-outline).
- HYPOTHESIS: `.../automatic-review/SKILL.md` § force-done, if force-done proves to be a second member of
  D1's population (verify-at-outline).
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` and the finalize
  barrier tests.

## Dependencies and Sequencing

- ⭐ **Ranked immediately after PLAN-PR-014.** Both are "the gate did not gate" with confirmed live
  instances; PR-014's is a crash, this one's is a scope leak. Neither is blocked by the taxonomy work.
- ⛔ **Overlaps `branch-cleanup.md` with PLAN-PR-014, -008, -009 and -013 — FIVE plans now share that
  file. Sequence, never pair any two.**
- ⭐ **Shares ONE invariant with PLAN-PR-013** — *approval is scoped to the HEAD it was established
  against*; PR-013 applies it to bot participation, this plan to operator authorization. **If D1 shows
  both resolve to a single barrier predicate, consolidate and say so** rather than shipping two fixes.
- ⚠ **Feeds PLAN-PR-008's D3.** That plan owes an operator decision on accepted coverage gaps; this one
  establishes that an accepted gap must be re-consented when the artifact changes. Landing this first
  gives D3 a HEAD-scoped notion of "accepted" to build on.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-015-a-barrier-override-is-not-bound-to-the-head-it-was-granted-against.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
