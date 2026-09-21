# PLAN-PRQ-02: Retrospective aspects publish a verdict over a population they never read

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-17 at epic creation from three first-party measurements filed by PLAN-TRUTH-166's own
retrospective (PR #1501, merged `e8c3cad5b`) and folded into `truthful-signals` PLAN-TRUTH-152 on
2026-09-17 before this epic existed. ⛔ **Those folds are SUPERSEDED by this spec** — PLAN-TRUTH-152
transferred here as PLAN-PRQ-01, and its 2026-09-17 fold section is the source text for the three items
below; re-read it rather than re-deriving from memory. Source messages, all archived:
`truth-166-architecture-refresh-migration-churn-002.md`, `-004.md`, `-005.md`.

## Objective

**Three registered retrospective aspects publish a confident figure over a population they never read,
and a fourth publishes a coverage number its own documentation calls an upper bound.** Each one reads
healthy — `diff_available: true`, `status: success`, a sibling block naming its population — while the
number beside it is unsupported. The consequence is not a missing measurement but a WRONG one that the
report carries forward into corpus-level roll-ups.

⭐ The epic's instrument applied to its own primary producer: after this lands, every aspect's clean
reading must be a checked negative, never silence.

## Deliverables

Five deliverables. D0 is a gate.

**D0 — GATE: derive the aspect population and classify each of the 17 registered aspects.** For every
aspect in `SECTION_SPEC`, state whether it publishes (a) the population it read, (b) a could-not-look
discriminator, or (c) neither. ⛔ Publish the tally over all 17 — the three known members below were found
one at a time by a landing plan, which is exactly the under-derived-population archetype. The fix set is
whatever D0 returns, not this list. ⛔ **RE-GROUNDED 2026-09-18 (cleanup, `checked_at: 1605831c5`):** the
population moved from 16 to 17 — `retro_sections.SECTION_SPEC` has 19 rows / `valid_aspect_keys()` returns
17 registerable keys (the 16 tabulated at `SKILL.md:184-201` plus `dispatch_boundaries`; the other two
`SECTION_SPEC` rows are underscore-prefixed injections `valid_aspect_keys()` filters structurally). A
fourth member sharing D1-D3's exact shape is also now named in source: `retro_sections.py:42-52` excludes
`manifest-decisions` (`check-manifest-consistency`) from `FOOTPRINT_CONSUMING_ASPECTS` because it
"publishes no footprint-degradation verdict at all" — the roster at `:57-62` covers 4 of 17 aspects, 13
unclassified.

**D1 — `check-manifest-consistency` stops deriving its footprint from a `base_ref` diff.**
`plan-retrospective` is finalize step 17 and `branch-cleanup` (which merges) is step 13, so the diff is
structurally empty by the time it runs: it reported `files_total: 0` with `diff_available: true` and
FAILED its `branch_cleanup_changes` rule for a plan that shipped a 26-path footprint, while two sibling
aspects in the same run resolved 26 paths through the shared footprint resolver. Route through that
resolver; an empty-but-available diff must never assert that no implementation file changed. The skill's
canonical block currently recommends the failing path — correct it in the same act.
⛔ **FOLDED 2026-09-19** (inbox `prq-06-a-lane-override-that-cannot-take-effect-is-005.md`): a second,
independent defect in the same aspect. `check-artifact-consistency`'s `forwarded_to_manifest` flag
downgrades a `status: warn` to `severity: info` on the assumption `check-manifest-consistency` will pick
it up — but `check-manifest-consistency.py` never reads `forwarded_to_manifest` at all (0 hits, vs. the
flag's 4 hits in the producer and 5 across its docs/tests), so the finding is silently dropped rather than
re-routed. On `PLAN-PRQ-06` this dropped a real finding: D6 landed at 50% modification-intent coverage
(below the 70% `fulfilled` bar) with three declared `write-replace` files unshipped. Add a
`declared_vs_realized_set` rule to `check-manifest-consistency` consuming `outline_only[]` /
`references_only[]` (grading non-empty `outline_only` at `warning`, `references_only` at `info`); D4
additionally gets a structural guard — **a `forwarded_to_*` flag with no receiving rule fails a test,
not a plan.**

**D2 — `build_time` publishes its population, or omits the figure.** `analyze-logs` emitted
`total_build_seconds: 0.0, build_count: 0` for a plan whose own fragment reported 28 build calls
(3,975,160 ms). The consumer-side rule already exists in full (`references/plan-efficiency.md`: *"Absent
is not zero"*); move the duty to the producer, as its sibling blocks already do (`cost_rollup` names its
population; `artifact_emission` names a could-not-look reason).

**D3 — `extract-chat-signal` obeys the serialization rule its own sibling contract states.** The
`reduced_transcript` field is emitted with flush-left continuation lines containing colons, which
`parse_toon` re-reads as phantom top-level keys — the exact shape `references/chat-history-analysis.md`
declares a MUST-NOT. Emit a quoted scalar with escaped newlines or hand back a path; make `reduced_bytes`
describe the delivered payload rather than the reduction; and bind the MUST to fragment PRODUCERS, not
only fragment authors. ⛔ **FOLDED 2026-09-19** (inbox `prq-06-a-lane-override-that-cannot-take-effect-is-002.md`
— the THIRD independent report of this exact defect, after the original lesson and this D3 itself): two
additions.
1. A concrete consumer-side guard: publish `reduced_transcript_delivered_bytes` alongside `reduced_bytes`,
   so the truncation mismatch is detectable at the consumer even before the producer is fixed.
2. **The blast radius is at least two aspects, not one.** `permission_prompt_analysis` was corrupted
   downstream of this same truncation on `PLAN-PRQ-06` — it was forced to report an UNMEASURED zero (50 of
   52 operator turns and 3 of 4 gate-decision bodies never delivered to it). D5's matched controls must
   cover both consumers, not only the chat-history aspect.

**D4 — The dispatch audit states the strength of its own coverage claim, and controls.** `ran_inline` is
documented as *"an UPPER BOUND on inline execution, never proof of it"*, and a hand-written `[DISPATCH]`
line CANCELS the missing-seam emission (caller-blindness). Make both visible in the emitted verdict rather
than only in the standard. Plus a matched control per member of D0's fix set: the honest producer must
still report a real figure when the population IS readable.

## Claim Labels

- OBSERVED: `plan-retrospective` registers 16 aspects, keyed authoritatively in
  `scripts/retro_sections.py` `SECTION_SPEC` and tabulated at `SKILL.md:184-201` (inventory sweep,
  2026-09-17).
  - verdict: contradicted | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: yes | evidence: retro_sections.SECTION_SPEC has 19 rows / 17 registerable keys at HEAD (len(valid_aspect_keys())==17), not 16. Extra registerable key is dispatch_boundaries (SECTION_SPEC row 'Phase Dispatch Boundaries'); the other two rows are underscore-prefixed injections filtered by valid_aspect_keys(). D0's population is 17.
- OBSERVED: the three producer defects in D1–D3 were measured first-party by PLAN-TRUTH-166's own
  retrospective and are quoted with their figures in PLAN-TRUTH-152's 2026-09-17 fold section.
- OBSERVED: `standards/execution-context-dispatch-audit.md:154` states `ran_inline` is an upper bound;
  `:46` states a hand-written `[DISPATCH]` line cancels the missing-seam emission (inventory sweep).
- ⚠ HYPOTHESIS: the three known members are not the whole population — other aspects share the shape.
  ⛔ Explicitly unmeasured; D0 owns the derivation and may return a larger or smaller set
  (verify-at-outline).
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: A fourth member is now named in source: retro_sections.py:42-52 excludes manifest-decisions (check-manifest-consistency) from FOOTPRINT_CONSUMING_ASPECTS because it publishes no footprint-degradation verdict at all -- the exact shape, found independently on a fourth producer. Roster at :57-62 is 4 of 17 aspects; 13 unclassified.
- ⚠ HYPOTHESIS: routing `check-manifest-consistency` through the shared footprint resolver is sufficient,
  i.e. the resolver is available at step 17 — confirm/refute at the two sibling aspects that already use
  it (`check-routing-decisions`, `check-outline-vs-shipped`) (verify-at-outline).
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: Resolver available post-branch-cleanup; both siblings call it (check-routing-decisions.py:67, check-outline-vs-shipped.py:69, resolve_footprint at :1045/:315). _footprint_resolver.py:13-51 has 5 tiers, 3 survive worktree removal. But check-manifest-consistency.py still does NOT route through it -- imports only resolve_diff_file_path (:42), still shells git diff (:210), still fails on raw_files_total==0 (:511-530). D1's premise stands; only the message was made honest.
- OBSERVED (folded 2026-09-19, `prq-06-a-lane-override-that-cannot-take-effect-is-005.md`):
  `forwarded_to_manifest` is set by `check-artifact-consistency.py` (4 hits) and documented at
  `references/artifact-consistency.md`, but `check-manifest-consistency.py` never reads it (0 hits) — the
  named receiver never receives. ⚠ Partially verified: the `outline_only|references_only|manifest_present`
  asymmetry (18 hits in the producer vs. 2 in the receiver) corroborates but does not line-by-line prove
  that none of `check-manifest-consistency`'s five checks is a set comparison — re-derive the 2 hits at
  outline (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — the aspect producers (D0–D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/` — the consumer-side rules moving to producers (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/execution-context-dispatch-audit.md` — the coverage-claim strength (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — the canonical block recommending the failing `--base-ref` path (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_footprint_resolver.py` — the
  ACTUAL shared resolver `check-routing-decisions`/`check-outline-vs-shipped` call (`resolve_footprint`) and
  D1 routes through — corrected 2026-09-18 (cleanup): the HYPOTHESIS entry this replaces named
  `manage-references/scripts/_cmd_compute_footprint.py`, which exists but is the CLI command surface, not
  the resolver; `_footprint_resolver.py` reaches `manage-references` only indirectly via
  `_references_core.py` (`compute_plan_branch_diff`, `resolve_base_ref`, `resolve_live_worktree`).
- OBSERVED: `test/plan-marshall/plan-retrospective/` — coverage and the matched controls (D4)

## Dependencies and Sequencing

- Depends on: none.
- ⛔ Never pair with PLAN-PRQ-01 (shared `plan-retrospective/scripts/`).
- ⚠ D1's remedy reads the base-ref resolution that `truthful-signals` PLAN-TRUTH-167 D3 is fixing
  (`_references_core.py`, local `main` vs `origin/main`). **Cross-epic, invisible to both gates** — if 167
  lands first, D1 consumes it; if not, D1 must not re-fix it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-02-retrospective-aspects-publish-a-verdict-over-a-population-they-never-read.md"
```

## ⭐ FOLDED 2026-09-17 — FOUR CORPUS LESSONS THAT ALREADY REPORTED THREE OF THESE, AND ONE THAT GENERALISES THEM

From the 2026-09-17 lessons sweep; all four preserved at
`.plan/local/orchestrator/post-run-quality/lessons/{id}.md`. Expected Surface unchanged — each names a
producer already declared above. ⛔ **Each predates this spec**, so D0's population derivation must treat
them as prior art rather than as new members: three of this spec's four known defects were filed as
lessons and never actioned.

- **`2026-09-13-20-004` — the general rule this whole spec instantiates.** Three retrospective guards
  reported clean *because they could not look*, and the could-not-look discriminator lived in a docstring
  rather than in the payload. ⭐ Adopt its wording as D0's classification test: a discriminator a consumer
  cannot read is not a discriminator.
- **`2026-09-04-08-008` — the WRITER half of D2's `build_time` zero.** Build rows never reach the
  change-ledger at all, so the honest-producer fix in D2 is necessary but not sufficient: publishing the
  population truthfully still reports zero while nothing writes rows. ⛔ D2's scope grows accordingly, and
  the ledger half is `PLAN-PRQ-08` D0's subject — coordinate, do not duplicate.
- **`2026-09-04-08-003` — D3's defect, filed first-party in September.** The TOON round-trip truncates the
  reduced transcript while forwarding the upstream counts intact, which is exactly the
  payload-absent-behind-healthy-discriminators shape D3 fixes.
- **`2026-09-04-08-004` — D1's defect, one tier deeper.** Every footprint-resolving tier is worktree-bound
  and `branch-cleanup` runs first, so **three aspects** go inconclusive post-merge, not just
  `check-manifest-consistency`. D1's remedy must add a landed-commit tier rather than only re-routing one
  aspect — otherwise the other two stay inconclusive and the fix reads as complete.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
