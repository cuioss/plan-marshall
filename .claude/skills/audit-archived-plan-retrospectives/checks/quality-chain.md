# Check: quality-chain (cross-plan)

Classifies every `artifacts/findings/*.jsonl` finding across the corpus along two
orthogonal axes — the quality MECHANISM that caught it and the RESOLUTION it
received — builds a per-plan mechanism×resolution matrix plus corpus totals,
flags the chain anti-patterns, and runs a SHIFT-LEFT study of what the PR
auto-review bot caught that the cheaper, earlier mechanisms (build, self-review)
missed. This is a cross-plan check: it emits one aggregate block over the whole
findings corpus, with a per-plan table and a per-finding table nested inside.

The deterministic computation lives in `scripts/audit.py`
(`cross_quality_chain` / `emit_quality_chain_block`); this sub-document is the
interpretation guide. The check reuses the same `read_jsonl` reader over
`artifacts/findings/*.jsonl` that the `quality-verification-report` check uses,
so the two checks read identical inputs and never disagree on what a finding is.

## Inputs the check reads

Per plan, the script globs `artifacts/findings/*.jsonl` and parses every JSONL
finding record. The findings families it classifies:

| Source jsonl | Mechanism | Carries |
|--------------|-----------|---------|
| `test-failure.jsonl`, `build-error.jsonl` | `build` | A build/test/compile failure the build gate surfaced. |
| `qgate-*.jsonl`, `assessments.jsonl`, any record with `source == "qgate"` | `self-review` | A Q-Gate / assessment finding the plan caught itself before opening the PR. |
| `pr-comment.jsonl` whose detail names a bot (`gemini` / `copilot` / `bot` / `automated`) | `auto-review` | A PR-bot comment — the shift-left subject. |
| `pr-comment.jsonl` (human), any record with `source == "user_review"` | `human-review` | A human PR comment. |
| anything else | `other` | Unclassified by the rules above. |

The finding fields the classifier reads: `resolution`, `resolution_detail`,
`promoted`, `source`, `detail`, `title`, `type`.

## Classifications

### Mechanism — which quality gate surfaced the finding

`build` → `self-review` → `auto-review` → `human-review` are ordered by **cost
and lateness**: build is the cheapest and earliest gate, auto-review is the most
expensive (a full PR round-trip), human-review the latest. A finding's mechanism
tells you how far right in the chain the defect slipped before anything caught
it.

### Resolution — what disposition the finding received

Derived from the `resolution` field, refined by a `resolution_detail` regex:

| Bucket | Rule |
|--------|------|
| `lesson` | `promoted` is truthy — the finding became a lesson. (Checked first; overrides any `resolution`.) |
| `direct_fix` | `resolution == fixed` with no rerun/flake detail, OR `taken_into_account` with no loop-back detail. Fixed in place. |
| `loop_back` | `resolution == taken_into_account` whose detail names a follow-up `TASK-` / deliverable. The fix was deferred into a later step. |
| `rerun_flake` | `resolution == fixed` whose detail names a transient / re-run / flake cause. Not a real defect — a flaky precondition. |
| `accepted` | `resolution == accepted`. Acknowledged, not actioned. |
| `suppressed` | `resolution == suppressed`. |
| `pending` | `resolution` is `pending` / `none` / empty — unresolved at archive time. |

## Matrix

For each plan the script builds a `matrix[mechanism][resolution]` count grid over
the five mechanisms × seven resolution buckets, plus a `mech_total` per
mechanism. The corpus block sums every plan's matrix into a single
`corpus_matrix` — the chain's overall shape: how many findings each gate caught
across the whole corpus, and how each gate's findings were resolved. A healthy
chain is build-heavy on the left (cheap gates catch the bulk) and thin on the
right (little reaches auto-review).

## Anti-pattern flags

Per plan, the script flags the chain anti-patterns:

| Flag | Fires when | Means |
|------|-----------|-------|
| `build_pending_pile(N)` | `matrix[build][pending] >= 2` | A backlog of build failures left unresolved at archive time. |
| `auto_review_only(N)` | The plan has auto-review findings but ZERO build AND ZERO self-review findings | The PR bot was the only quality gate that fired — everything shifted right to the most expensive stage. |
| `review_body_duplicate(N)` | The same finding title appears under BOTH self-review and auto-review | The bot re-reported what the plan already caught — duplicated review effort. |
| `no_qgate6` | The plan recorded findings but ZERO self-review findings | The plan reached the PR with no Q-Gate / assessment self-review surface at all. |

## Shift-left tiering

For every `auto-review` finding the script grades how completely the
`ext-self-review-plan-marshall` deterministic surfacer COULD have surfaced it
pre-submission — separating "the pre-submission structural review would have
caught this for free" from "only a cognitive PR review could". The tiers map onto
the surfacer's published candidate categories (regexes, user-facing strings,
markdown sections, symmetric pairs, flag-guard pairs, contract sources,
schema-bearing files — see `ext-self-review-plan-marshall` § "Subcommand:
surface"):

| Tier | Class | Surfacer coverage |
|------|-------|-------------------|
| **Tier 1** | deterministic-surfaceable | The finding names a surfacer candidate category (regex / wording / duplication / symmetric pair / flag guard / contract / schema). A bounded `self_review surface` scan would have flagged the exact line. |
| **Tier 2** | structural-but-cognitive | A structural defect the surfacer anchors but does not auto-flag (naming, docstring/JavaDoc, dead code, import ordering). The surface scan narrows it; the LLM pass confirms. |
| **Tier 3** | semantic | A correctness / logic / behavioral finding no deterministic surface can reach. Only build or a cognitive review catches it. |
| **Tier 4** | unclassified | Body too sparse to tier — a review-process pointer (`see comment`, `left a comment`, `as per comment`) or any body carrying no classifiable structural keyword. A bare "comment" reference is NOT a Tier-2 code-comment defect; only a qualified comment defect (`stale`/`outdated`/`dead`/`TODO` comment) tiers as structural. |

The lower the tier, the stronger the shift-left signal: a **Tier-1
`auto_review_only` finding** is one the project paid a full PR round-trip for that
a pre-submission `self_review surface` pass would have caught for free. The
emitted `shift_left_tiers` summary carries the Tier 1-4 histogram over all
auto-review findings so the read-out shows, at a glance, how much right-shifted
review effort a pre-submission structural surface scan could have reclaimed.

## Emitted columns

```
plans_in_corpus: P
plan_genuine_signal_count: G1
finding_genuine_signal_count: G2
shift_left_tiers: "tier1=N1;tier2=N2;tier3=N3;tier4=N4"
corpus_matrix[5]{mechanism,direct_fix,loop_back,rerun_flake,accepted,suppressed,pending,lesson,total}
plans[P]{plan_id,build,self_review,auto_review,human_review,other,total,flags,severity}
findings[F]{plan_id,mechanism,resolution,source_file,shift_left_tier,title,severity}
```

| Column | Meaning |
|--------|---------|
| `corpus_matrix` rows | One per mechanism; a cell per resolution bucket plus the row `total`. The chain's overall shape. Informational context. |
| `plans` rows | Per-plan mechanism totals + the chain anti-pattern `flags` list. `severity` is `genuine` when the plan carries ≥1 flag. |
| `findings` rows | The per-finding rows. `shift_left_tier` is populated (1-4) only for `auto-review` findings, empty otherwise. `severity` is the D1 column. |
| `severity` | Uniform D1 severity column. A per-finding row is `genuine` when it is an `auto-review` finding (shift-left subject) OR still `pending` (unresolved chain debt); `informational` otherwise. |

`finding_genuine_signal_count` counts the genuine per-finding rows;
`plan_genuine_signal_count` counts the flagged plans.

## How the orchestrator interprets the rows

EVERY emitted row is adjudicated with a stated verdict and cited evidence; a row
may be dismissed as informational/expected ONLY with a cited reason.

- **`auto_review_only` plan flag** — highest-priority chain signal. The PR bot was
  the sole gate; cross-read the plan's `findings` rows and their
  `shift_left_tier`. A cluster of **Tier-1** auto-review findings under an
  `auto_review_only` plan is a missing-pre-submission-review signal worth a
  lesson: the project is paying PR round-trips for defects a `self_review surface`
  pass would catch.
- **`build_pending_pile` plan flag** — a build-failure backlog. Inspect the
  `findings` rows with `mechanism=build, resolution=pending`; a real pile (not a
  single transient) is an unresolved-chain-debt signal.
- **`review_body_duplicate` plan flag** — wasted review effort. The bot
  re-surfaced what self-review already caught. Usually a workflow-shape signal
  (the self-review finding was not marked resolved before the PR opened), not a
  defect on its own.
- **`no_qgate6` plan flag** — the plan reached the PR with no self-review surface.
  Cross-read against the execution-context-manifest check: a `docs_only` /
  `tests_only` manifest legitimately omits Q-Gate-6, so `no_qgate6` is expected
  for those rule keys (cite the manifest rule). For an implementation plan it is a
  genuine gap.
- **per-finding `auto-review` rows** — each is a shift-left candidate. The
  `shift_left_tier` grades whether a deterministic surface scan could have caught
  it. Tier 1 → file (or, on Gate-1 dedup, extend) a lesson keyed to the surfacer
  category the finding belongs to. Tier 3 (semantic) → expected to slip past the
  structural surface; dismiss as informational with the tier as the cited reason.
- **`corpus_matrix` / totals** — informational summary only; a healthy chain is
  build-heavy on the left and thin on the right. A right-heavy corpus (auto-review
  rivaling build) is itself a prompt to widen the shift-left lens.

## Methodology constraint: walk every finding, never sample

This check emits a per-finding table precisely so the orchestrator can adjudicate
**every finding step-by-step**. The orchestrator MUST walk each `findings` row
individually — read its mechanism, resolution, and (for auto-review) its
shift-left tier — and state a per-row verdict with cited evidence. Sampling a
subset of finding rows and generalizing a verdict to the rest is a contract
violation, the same violation the SKILL.md Step-3 contract forbids corpus-wide.

This walk-every-finding constraint adjudicates against **lesson
`2026-06-01-13-001`**: an audit that spot-checks a handful of findings and
declares the chain "healthy" produces a fabricated all-clear — the genuine
shift-left signal (a Tier-1 `auto_review_only` cluster) hides in the rows the
sampler skipped. The per-finding `severity` column and the
`finding_genuine_signal_count` are the precision aids: every `genuine` finding row
demands a full verdict-plus-evidence treatment, every `informational` row a
one-line cited dismissal. A blanket "all findings resolved cleanly" not grounded
in a per-row walk is the exact failure the lesson catalogues.

## Critical rules

- The script is the single source of truth for the parsed corpus, the mechanism /
  resolution classifications, the matrix, the anti-pattern flags, and the
  shift-left tiers. Do not re-grep the findings or re-derive a classification in
  chat.
- The classification regexes (`_QC_RERUN_RE`, `_QC_LOOPBACK_RE`, `_QC_BOT_RE`) and
  the shift-left tier regexes (`_QC_TIER1_RE` … `_QC_TIER3_RE`) live in
  `scripts/audit.py`. If a classification changes, edit the script rather than
  substituting a different reading.
- The prototype seeds `.plan/temp/quality_chain.py` and
  `.plan/temp/findings_taxonomy.py` are READ-ONLY references that informed this
  check's design; the check does not import or invoke them.
- This check is read-only; it never edits `.plan/` files.
