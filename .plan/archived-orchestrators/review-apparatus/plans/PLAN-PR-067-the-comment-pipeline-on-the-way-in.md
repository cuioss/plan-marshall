# PLAN-PR-067: What the comment pipeline loses on the way IN

epic: review-apparatus
workstream: WS-03

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `workflow-integration-github` read path — `github_pr.py` ingestion filters, `github_ops.py` fetch, `comment-patterns.json`.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Stop the ingestion end of the PR-comment pipeline destroying real findings, and make a capped fetch say it was capped. Every deliverable here edits the READ path; nothing in this plan writes to a provider.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D1 | Stop the pre-filter reading a finding's AI-agent block as an acknowledgment | `PLAN-PR-029` § D1 | `PLAN-PR-059` D1 |
| D2 | Key the self-response filter on author identity, not a heading literal | `PLAN-PR-040` § Deliverables 1 | `PLAN-PR-059` D6 |
| D3 | Keep the heading test as a secondary signal, never the sole one | `PLAN-PR-040` § Deliverables 2 | `PLAN-PR-059` D7 |
| D4 | A test that fails on the current code: self-authored, non-heading body | `PLAN-PR-040` § Deliverables 3 | `PLAN-PR-059` D8 |
| D5 | The filter keys on *"a comment THIS WORKFLOW wrote"*, not author or reply relationship | `PLAN-PR-040` § D-FOLD 2026-09-04 | `PLAN-PR-059` D9 |
| D7 | Exclude a RECOGNISED refusal from `actionable_count` | `PLAN-PR-047` § D3 | `PLAN-PR-061` D10 |
| D8 | A zero fetch reports WHICH zero it is | `PLAN-PR-053` § D1 | `PLAN-PR-058` D1 |

⭐ **Recurrence (lesson `2026-09-20-00-001`, drained 2026-09-22 via `lessons-handling-26-09-22-01`):**
`github_pr fetch_findings` still stores a CodeRabbit control-flow acknowledgement ("Already reviewed
the last commit...") as a first-class pending pr-comment finding — the same AI-agent-block-as-ack
defect D1 already owns. No new deliverable; folds as a second occurrence on D1.

**D0 — GATE, mutates nothing.** The merged derivation gate. From `PLAN-PR-029` D0: derive the RESPOND
consumer surface, or HALT. From `PLAN-PR-040`: re-derive the count of already-mis-ingested comments in
this repository's findings corpus, and publish it with its population. ⛔ `PLAN-PR-029` § Re-Grounding
item 4 warns the enumeration is materially larger than the source's own lead — **derive it, never
inherit the number.**

*(Carried verbatim from `PLAN-PR-059` D0 at the 2026-09-18 component re-cut.)*

**D6 — A capped fetch reports that it was capped (amendment 2026-09-15, corpus pass).**
`REVIEW_THREADS_QUERY` in `github_ops.py` requests `reviewThreads(first: 100)`, `reviews(first: 100)`,
`comments(first: 100)` and `comments(first: 10)` per thread, with **no `pageInfo`, no pagination and no
truncation field**, and `fetch_pr_comments_data` returns `status: success` over the clipped set — the
same data path `fetch_findings` ingests from. Either paginate every connection to completion, or — where
a cap is kept — report per connection that it was reached, so a clipped population is never published as
a complete one (ADR-019). *Done when:* a test with a 101st review (and an 11th comment in a thread) fails
on the current code and passes after, and the result names each connection's observed count against its
cap. ⛔ Do not solve it by raising the literal `100` — that moves the cliff, it does not report it.

**Evidence amendment 2026-09-15** (from
[`findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md`](../findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md);
feeds D0's populations, adds no deliverable):

- `cuioss-review-bot[bot]` now posts **inline `/improve` suggestions** (10 in the window, all commitable
  `**Suggestion:**` bodies). They are a finding surface; D0 must confirm the pipeline ingests them as
  findings attributed to that bot, not as noise.
- The observed truncation instance: `cuioss/API-Sheriff#255`, `ci pr comments` 236 records against `gh
  api`'s 237 — review `5123206655`, the 101st of 109, dropped. 1 of 351 dumped PRs exceeded a cap, so
  the loss is **latent**, not absent.

Ten deliverables, under the ceiling. The remaining headroom is deliberate: D0's enumeration is known to
be larger than its source estimated.

*(Carried verbatim from `PLAN-PR-059` D10 at the 2026-09-18 component re-cut.)*

**D9 — `pr merge-queue` reports an ATTEMPT as an OBSERVATION (lesson `2026-09-06-16-001`, absorbed
2026-09-18).** `_github_pr.py:2332-2339` returns `'enqueued': True` with `enqueue_corroboration` set
from the branch rule being active — never from a post-condition read of the PR itself. `isInMergeQueue`
and `mergeQueueEntry` occur in ZERO files across the `tools-integration-ci` and
`workflow-integration-github` script surfaces, so nothing in the tree can currently observe queue
membership. ⚠ `PLAN-PR-009` (#1087) fixed `cmd_pr_merge` and left this verb's corroboration untouched,
by its own landing record. *Done when:* `enqueued: true` is returned only on a read of the PR's own
queue state, and an unobservable state reports `indeterminate` rather than `true`. ⭐ The repo-level
GraphQL `mergeQueue.entries` read is the known-good membership query; `mergeStateStatus` reads `CLEAN`
while genuinely queued and is NOT a substitute.

**D3 amendment 2026-09-18 (lesson `2026-09-04-17-001`).** `pr_intent_section.py` is already on this
spec's Expected Surface for its `OSError`/exit-code collapse; the absorbed lesson adds a second defect
on the same file — the renderer **clips the PR Intent section at a byte offset**, and three properties
compose into a trap: the author is forbidden to size the draft, the renderer appends rather than
replaces, and `ci pr view` does not return the body, so the only repair is a full `ci pr edit` rewrite.
D3 additionally reports an overflow instead of truncating mid-sentence.

Nine deliverables, under the ceiling.

*(Carried verbatim from `PLAN-PR-064` D8 (via `PLAN-PR-073`) at the 2026-09-18 component re-cut.)*

10 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/standards/comment-patterns.json`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_pr_comments.py`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural claim (every deliverable body lives in its Carried-from theme spec, none restated here). Verified by reading this spec at HEAD: the Deliverables table carries only pointers, and the bodies added inline (D6, D9, D3-amendment) are explicitly marked as folds with their provenance. No git diff bears on it.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping; RE-SCOPED 2026-09-22):
  this plan's declared surface is disjoint from every other live plan's in this epic **except
  `PLAN-PR-068`, which shares three declared files** (`github_pr.py`, `workflow-integration-github/SKILL.md`,
  `test_github_pr.py`) — sequenced, never paired, per the "Runs BEFORE `PLAN-PR-068`" entry below.
  Confirm/refute with `orchestrator corpus cross-check --slug review-apparatus` — non-determinate at
  HEAD (see the claim's verdict).
  - verdict: contradicted | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: yes | evidence: DISJOINTNESS IS FALSE, derived by membership over corpus surfaces declared paths. PLAN-PR-067 and PLAN-PR-068 both declare THREE files: workflow-integration-github/scripts/github_pr.py, workflow-integration-github/SKILL.md, and test/plan-marshall/workflow-integration-github/test_github_pr.py. The spec header claim that the cut is by component so no file is declared by two live plans does not hold for this pair. RE-SCOPE: the claim should read that 067 and 068 share three declared files and must be SEQUENCED, never paired - which both specs own Dependencies sections already say (Runs BEFORE PLAN-PR-068). corpus cross-check cannot be used to confirm this at HEAD: it reports 5628 file-overlap matches and candidate_comparison_determinate false, because the live/archived epic split made review-apparatus-26-09-21 its own sibling-epic candidate.
- OBSERVED (first-party, 2026-09-15, `github_ops.py:405-448`): `REVIEW_THREADS_QUERY` carries four
  fixed `first:` caps and no `pageInfo`, and `fetch_pr_comments_data` issues it once, returning
  `status: success` over the clipped set. Confirm/refute at that query and its `run_graphql` call site.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded FIRST-PARTY at HEAD. github_ops.py is UNMOVED in 7a028157e..HEAD (the workflow-integration-github diff lists only _github_checks.py, _github_ci.py, _github_pr.py, github_pr.py), so REVIEW_THREADS_QUERY four fixed first caps, the absent pageInfo and fetch_pr_comments_data single issuance are unchanged. The cited 405-448 coordinates are undisturbed because the file did not move. This is the same premise as PLAN-PR-059 claim 3 and both now agree.
- OBSERVED (corpus pass 2026-09-15): `ci pr comments` returned 236 records against `gh api`'s 237 on
  `cuioss/API-Sheriff#255` (review `5123206655`, the 101st of 109). 1 of 351 PRs exceeded a cap, so
  the loss is latent, not absent.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: FOREIGN observation (cuioss/API-Sheriff#255: ci pr comments 236 vs gh api 237, review 5123206655 the 101st of 109; 1 of 351 dumped PRs over a cap). A foreign-repo measurement over an external population; no plan-marshall git diff reaches it, and it was not re-sampled this pass. Latent, not absent - unchanged.
- OBSERVED (corpus pass 2026-09-15): `cuioss-review-bot[bot]` posts inline `/improve` suggestions (10
  in the window). D0 confirms the pipeline ingests them as findings attributed to that bot.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: FOREIGN observation (cuioss-review-bot[bot] posting 10 inline improve suggestions in the corpus window). An external behavioural sample, not a property of this tree; not re-sampled this pass. D0 must re-derive it rather than inherit it.

## Dependencies and Sequencing

- ⛔ **Runs BEFORE `PLAN-PR-068`**: D1 rewrites the pre-filter whose output D068/D1 transmits over.
- ⭐ D7 (carried from `PLAN-PR-061` D10) and D1's 2026-09-13 fold are the SAME symbol
  (`review_body_summary_patterns` → `actionable_count`): D1 carries the measured cost, D7 carries the
  matched positive control. They land together, in this plan, or the classifier is graded against a
  predicate the sibling is replacing.
- ⭐ D9 is the merge-queue corroboration read: same file as D1-D5 (`_github_pr.py`), disjoint function
  (`cmd_pr_merge_queue`). `PLAN-PR-073` D1 consumes its verdict.
- ⚠ D8 (`count_stored` three-way zero) READS the persisted state `PLAN-PR-072` D2 produces — if 072
  has not landed, D8 derives the state locally and says so rather than re-inferring it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-067-the-comment-pipeline-on-the-way-in.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
