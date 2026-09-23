# PLAN-08: Scope the Re-Grounding Verdict Field's staleness check to content, not raw HEAD

epic: orchestrator-refactor
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-08-verdict-staleness-scoping.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The Re-Grounding Verdict Field's `stale` flag currently compares a verdict's `checked_at` sha
against the repository's raw current HEAD, with no path or epic scoping. In a repository
running many concurrent orchestrator epics, ledger-only `.plan/orchestrator/**` commits land
on `main` continuously and unrelated to any given claim, so `stale: true` fires almost
immediately after a verdict is stamped and stays true nearly always — the field can no longer
distinguish "this claim's grounding may be outdated" from "something, anything, landed on
main since." Re-derive staleness from content-scoped change — reusing the same declared-surface
technique `phase-6-finalize`'s `verdict_currency classify` already uses for the analogous
problem — so the flag again carries a usable signal, without changing its non-blocking
admission semantics.

## Deliverables

1. **D1 — content-scoped staleness derivation.** For a spec whose Expected Surface resolves
   `declarative` (per `plan-marshall:script-shared`'s `epic_spec_parser`, the section's single
   sanctioned reader), derive `stale` from whether any declared path changed between
   `checked_at` and current HEAD, instead of `_current_head_sha()` raw-equality
   (`orchestrator.py:2111-2120`, consumed at `:2836` and `:3103`).
2. **D2 — explicit, named fallback for the non-`declarative` case.** A spec whose surface is
   `derived` / `prose` / `absent` / `unreadable` has no comparable path set for D1's check to
   use. Decide and document the fallback (today's raw-HEAD comparison is one legitimate
   choice), and publish WHICH basis produced each row's `stale` value in the payload — never a
   bare boolean with no derivation, mirroring the derivation-status disclosure pattern already
   used elsewhere in this script (`corpus surfaces`, `corpus cross-check`).
3. **D3 — tests proving the corrected behavior.** A claim whose declared surface is untouched
   since `checked_at` reports `stale: false` even when unrelated commits — including
   `.plan/orchestrator/**`-only ones from other epics — landed on HEAD in between. A claim
   whose declared surface WAS touched reports `stale: true`. Cover the D2 fallback path too.
4. **D4 — update the staleness prose.** `orchestration-model.md` § Re-Grounding Verdict Field
   is the field's sole normative home; its "Staleness" paragraph currently implies raw-HEAD
   comparison and must describe the content-scoped derivation and the fallback basis instead,
   so the standard and the code stay one definition.

## Non-Goals

- No change to the admission table or to `_admits` (`orchestrator.py:2787-2793`) — `stale`
  is reported, never promoted to blocking, before and after this plan.
- No change to `corpus set-verdict`'s grammar or emitter — the five-key verdict line shape is
  unaffected; this plan changes only how `stale` is DERIVED at read time.

## Claim Labels

- OBSERVED: `orchestrator.py:2836` — `row['stale'] = bool(head) and not
  head.startswith(parsed['checked_at'])` compares the parsed `checked_at` sha against
  `_current_head_sha()` (`:2111-2120`), the raw current HEAD of the whole repository, with no
  path or epic scoping.
- OBSERVED: `orchestrator.py:3103` — `head = _current_head_sha()` is read once per
  `cmd_corpus_verdicts` (`:3072`) invocation and threaded unchanged into every spec's
  `_spec_verdict_rows` call (`:3120`), so every claim in every spec scanned in one call shares
  the identical raw-HEAD staleness basis.
- OBSERVED: `orchestration-model.md:271` states staleness is "reported, never promoted... never
  silently promoted to blocking... nor silently dropped", confirmed against
  `orchestrator.py:2787-2793` (`_admits`), which never reads the `stale` key. This fix changes
  only the derivation of `stale`, not admission — no blocking-consumer is affected.
- OBSERVED: `phase-6-finalize/standards/verdict-currency.md` already establishes the technique
  this plan reuses — a declared-paths glob (`verdict_inputs`) plus a tree-diff against it,
  rather than raw HEAD/SHA identity — for the directly analogous problem of unrelated commits
  spuriously re-triggering a check. This is cited precedent, not a claim requiring separate
  verification.
- OBSERVED: the Expected Surface reader (`epic_spec_parser`, `plan-marshall:script-shared`)
  already resolves each spec's declared paths and derivation status
  (`declarative`/`derived`/`prose`/`absent`/`unreadable`) and is the single sanctioned reader
  of that section (`orchestration-model.md` § The gate's reading contract). This plan consumes
  that existing reader; it does not build a second one.
- HYPOTHESIS: `_verdict_row` (`orchestrator.py:2796-2837`) and `_spec_verdict_rows`
  (`:2840-`) can be extended to accept a resolved surface-path list per spec without materially
  changing their call sites' shape; confirm/refute at `cmd_corpus_verdicts` (`:3072`) whether
  plumbing the Expected Surface resolution through to these two functions is straightforward
  given their current signatures (verify-at-outline).
  - verdict: corroborated | checked_at: b5d0ef7e6922e38caa4cdc8fdaaca31530c9ccd0 | by: orchestrator-refactor/analyze | rescoped: n/a | evidence: Shipped PR #1585 (merge b5d0ef7e6): _verdict_row/_spec_verdict_rows extended cleanly to carry a closed 6-member staleness_basis vocabulary (orchestrator.py:466-502,3214-3248) plumbed straight through cmd_corpus_verdicts (:3538-3597) with no material signature break; 535-line diff, 596+752-line test additions.
- Verify-first clause: re-run every line citation above against HEAD at outline time — every
  other plan in this epic edits `orchestrator.py` concurrently, so exact line numbers will have
  shifted by the time this plan is picked up (the same caveat PLAN-07 already states for the
  same file).
  - verdict: corroborated | checked_at: b5d0ef7e6922e38caa4cdc8fdaaca31530c9ccd0 | by: orchestrator-refactor/analyze | rescoped: n/a | evidence: Shipped diff targets real, current code (orchestrator.py:466-502,2796-2837,2840-,3072,3214-3248,3538-3597 in the shipped tree) rather than the stale research-time citations, so the line-shift re-derivation this clause asked for was performed at outline/execute.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`

## Dependencies and Sequencing

- Depends on: none directly.
- Overlaps with: PLAN-02 (ledger/row-vocabulary work, also in `orchestrator.py`), PLAN-06
  (mechanism intake, also `orchestrator.py`), PLAN-07 (whole-file structural split, sequenced
  last in the epic).
- **Must land before PLAN-07.** This plan changes `stale`'s derivation — a genuine
  output-field semantic change — while PLAN-07 is explicitly behavior-preserving only ("No
  verb, flag, output field, or error code changes. If any does, the plan has failed."). If
  PLAN-07 lands first, its behavior-preservation proof (D3) freezes today's raw-HEAD staleness
  bug into the split instead of checking against corrected semantics.
- Adjacent to: none beyond the above.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-08-verdict-staleness-scoping.md"
```

## Write-Boundary

The plan implementing this spec touches only repository source, standards and tests. It
creates and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
