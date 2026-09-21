# Landing Analysis: PLAN-51 — compile-report returns `success` while silently dropping sections

epic: truthful-signals
workstream: WS-01
pr: #1009 (https://github.com/cuioss/plan-marshall/pull/1009) — merged as `74620b907`

> Landing record. Claims verified against the merged commit and the shipped source at HEAD; the
> finalize narrative was treated as a lead, not a fact.

## Deliverable Fidelity vs Spec

Spec staged four deliverables (D1 gate, D2 loud signal, D3 registry completeness, D4 test); the
landing reports two. **Not a scope reduction — a scope CORRECTION the orchestrator approved.**

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — GATE: trace the omit path, choose the signal shape | shipped-as-specified | Resolved to a *partitioned* discriminator rather than a blanket non-empty check |
| D2 — non-empty omit is not a clean success | shipped-as-specified | `compile-report.py:402` `'status': 'warning' if dropped else 'success'`; `:407-408` emit `sections_omitted` **and** new `sections_dropped` |
| D3 — registry completeness / catch-all | **dropped, correctly** | The catch-all **already existed at HEAD**. The spec had quoted the `:301` comment, which described the *pre-fix* state — a stale-source-quote defect in the orchestrator's own spec, not a gap in the code |
| D4 — regression test | shipped-as-specified | Tests pin the 28th recurrence |
| *(added)* contract-surface alignment | shipped-additional | Misleading `:310` comment removed; `SKILL.md` + `report-structure.md` aligned |

**The partition is the substantive design win.** `_fragment_has_payload` (`:164`) splits one bucket
in two: `sections_omitted` keeps its benign meaning (aspect legitimately produced nothing →
`success`), while `sections_dropped` catches a fragment *present with payload* that rendered nothing
→ `warning`. A blanket "non-empty ⇒ warning" would have fired on every benign omission — i.e. it
would have shipped **exactly the vacuous always-on guard this epic exists to eliminate.** The plan
recognised that and avoided it.

**Review caught two real defects in code this plan introduced** — both worth recording because they
are quality signals, not process noise:

- CodeRabbit: `value not in (None, '', [], {}, False)` treats numeric `0` as empty, since `0 == False`
  in Python. A count of `0` or ratio of `0.0` would have been misclassified as no-payload —
  **silently dropping the very content the discriminator exists to make loud.** Fixed; the shipped
  docstring (`:174-178`) now documents the identity-not-equality rule explicitly.
- CodeRabbit: a doc-contract inaccuracy in the Conditional Rule. **The triage agent checked the
  bot's suggested wording and found the suggestion itself wrong** — it would have broadened the rule
  to all conditional sections when the carve-out is keyed to `chat-history-analysis` — and filed a
  corrected fix rather than applying the bot's text. This is the untrusted-ingestion posture working
  exactly as intended at the plan tier: a bot finding is a lead, its proposed remedy is not authority.

## Metrics and Anomalies

- 2h4m worked / 2.6M tokens; 20/20 finalize steps; two loop-back iterations (both review-driven)
- `pre-submission-self-review` clean (12 candidates); `finalize-step-simplify` 2 edits / 1 dedup finding
- Lesson captured: `2026-07-26-19-001`. `lessons-housekeeping` 0 removed / 136 retained
- Review: 1 reviewer, 2 actionable comments — **again a single-reviewer run** (see PLAN-66's
  quorum watch; the pattern is now consecutive)

## Routing and Merge Behavior

- CI green; merged via queue; branch cleaned; main clean.
- Surface collisions: none. Ran concurrently with PLAN-69 and stayed inside `plan-retrospective`.
- **Three rebase cycles** as main advanced; one 628s re-review await that could not succeed (below).

## Reconciliation Actions

- [x] status.json entry updated — `launched` → `shipped`, `pr=1009`, `landing=landings/PLAN-51.md`
- [x] epic.md queue row reconciled
- [x] **PLAN-75 staged** — composer defects (follow-ups 1 + 2)
- [x] **Follow-up 3 folded into PLAN-71** — re-review trigger + rebase redundancy
- [x] Watch added — PLAN-44's shipped fix is INERT in practice
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

1. ⛔ **`plan-retrospective` never ran, and finalize still reported 20/20 green.** It carries
   `lane: minimal` in `marshal.json` and the auto-posture preview listed it, yet the composed
   manifest omitted it. **No retrospective exists for this plan.** This is the flagship archetype in
   the composer itself: a step silently absent while every signal reads complete. Staged as
   **PLAN-75 D1/D2**.
2. ⛔ **`finalize-step-preference-emitter` ran POST-MERGE — which means PLAN-44's fix (#990) is
   INERT.** Orchestrator-verified at HEAD: the step's frontmatter is correct — `order: 61`,
   `mutates_source: true`
   (`phase-6-finalize/standards/finalize-step-preference-emitter.md`) — exactly what PLAN-44 landed
   (it moved `80 → 61` so the write rides the plan PR). `required-steps.md:33-44` likewise places it
   between `push` and `create-pr`, well before `branch-cleanup`. **Yet the composed manifest
   sequenced it after `branch-cleanup` (70).** So the declared order is right and the composer did
   not honour it. **HYPOTHESIS (verify-at-outline):** `_resolve_step_order`
   (`_manifest_validation.py:314-341`) returned `None` for the `default:`-prefixed id — the
   `_is_external_step` branch (`:338-340`) returns `None` for colon-bearing ids, and a `None` order
   makes `_sort_steps_by_frontmatter_order` (`:344-374`) **pin the entry at its original index**
   instead of sorting it. Confirm/refute at `_is_external_step` against
   `default:finalize-step-preference-emitter`. If confirmed, every `default:`-prefixed step is
   unsortable and the sort's claim to be "the sole ordering authority" (`manage-execution-manifest.py:1743`)
   is false for that whole class. Staged as **PLAN-75 D3**.
   **The plan handled it correctly at runtime**: `mutates_source: true` post-merge would have landed
   a promotion unpushably on main, so it skipped the write and logged the pattern rather than
   mutating main behind the PR. Right call.
3. **Trigger-A re-review cannot succeed on a content-free rebase** — CodeRabbit states it "does not
   re-review already reviewed commits", so a 628s await was spent on a signal that could not arrive,
   and it cost an operator prompt. Second half: with `use_merge_queue: true` the platform re-tests
   against the latest base anyway, so the pre-enqueue rebase is largely redundant — three rebase
   cycles here. **Folded into PLAN-71** (which already owns the re-trigger/await mechanics); its
   rebase-redundancy half may split to a finalize/git plan.

**Cross-cutting note.** Follow-ups 1 and 2 are both `manage-execution-manifest` composition defects
found in a single run, and both have the same shape: **the declared contract is correct and the
composer does not honour it.** That makes PLAN-75 a composer-integrity plan rather than two fixes.
