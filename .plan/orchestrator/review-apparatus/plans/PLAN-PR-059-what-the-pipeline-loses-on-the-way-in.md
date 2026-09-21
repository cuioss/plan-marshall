# PLAN-PR-059: What the comment pipeline loses on the way IN

epic: review-apparatus
workstream: WS-03

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-067 (D0/D1/D6/D7/D8/D9/D10 — the whole read path), PLAN-PR-068 (D2 — the transmit half), PLAN-PR-072 (D3 — the marker lifecycle), PLAN-PR-069 (D4/D5 — the contract documents, one owner).
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-029` and `PLAN-PR-040` whole**, under the operator's 2026-09-12
> decision to raise the split guard to **12 deliverables** and group staged work by shared target
> surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text. Follow the pointer; do not retype.
> `PLAN-PR-029`'s body is the cloud-wave audit's text, preserved verbatim there — a retype here would
> destroy the one thing that makes it citable.

## Objective

Stop the ingestion end of the comment pipeline destroying real findings: the noise pre-filter that
discards a finding because of what a bot's prompt block quotes, and the self-response filter that
ingests our own comments as review findings because they do not open with the expected heading.

## Why these were grouped

Derived from `corpus surfaces`: both declare `github_pr.py`, `_github_pr.py`,
`workflow-integration-github/SKILL.md` and `test_github_pr.py` — and both edit the SAME predicate
family, the producer-side pre-filters that decide whether a fetched comment becomes a `pr-comment`
record. `PLAN-PR-029` D1 fixes the filter that drops a REVIEWER's finding; `PLAN-PR-040` fixes the
filter that fails to recognise OUR OWN comment. ⛔ Two filters, one function, opposite directions —
shipped apart, the second lands on a call site the first has just rewritten.

⚠ `PLAN-PR-029` § Re-Grounding carries **six corrections that must be applied before a run starts**,
including a declared surface path that does not exist and a mandatory `070 G1` fold. They bind here
unchanged.

## Deliverables

**D0 — GATE, mutates nothing.** The merged derivation gate. From `PLAN-PR-029` D0: derive the RESPOND
consumer surface, or HALT. From `PLAN-PR-040`: re-derive the count of already-mis-ingested comments in
this repository's findings corpus, and publish it with its population. ⛔ `PLAN-PR-029` § Re-Grounding
item 4 warns the enumeration is materially larger than the source's own lead — **derive it, never
inherit the number.**

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | Stop the pre-filter reading a finding's AI-agent block as an acknowledgment | `PLAN-PR-029` § D1 |
| D2 | A delivered reply is stamped, counted honestly, and never re-sent | `PLAN-PR-029` § D2 |
| D3 | Close and document the marker lifecycle in `manage-findings` | `PLAN-PR-029` § D3 |
| D4 | One actor for the strip, one field for the body | `PLAN-PR-029` § D4 |
| D5 | The RESPOND loop is described once, by its owning table | `PLAN-PR-029` § D5 |
| D6 | Key the self-response filter on author identity, not a heading literal | `PLAN-PR-040` § Deliverables 1 |
| D7 | Keep the heading test as a secondary signal, never the sole one | `PLAN-PR-040` § Deliverables 2 |
| D8 | A test that fails on the current code: self-authored, non-heading body | `PLAN-PR-040` § Deliverables 3 |
| D9 | The filter keys on *"a comment THIS WORKFLOW wrote"*, not author or reply relationship | `PLAN-PR-040` § D-FOLD 2026-09-04 |

⛔ **D2 carries `PLAN-PR-029` § Re-Grounding item 6 — the `070 G1` third requirement — as a binding
amendment.** As written without it, D2's *Done when* certifies a permanently-unresolved thread.

**D10 — A capped fetch reports that it was capped (amendment 2026-09-15, corpus pass).**
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

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/standards/comment-patterns.json`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/standards/comment-patterns.json`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/standards/sonar-rules.json`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/untrusted-ingestion/standards/threat-model.md`
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`
- OBSERVED: `test/plan-marshall/workflow-integration-gitlab/test_gitlab_pr.py`
- OBSERVED: `test/plan-marshall/workflow-integration-sonar/test_fetch_findings.py`
- OBSERVED: `test/plan-marshall/manage-findings/test_findings_store_resolve.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` — D10
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_pr_comments.py` — D10

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-029` § Claim Labels and
  `PLAN-PR-040` § Claim Labels, carried unchanged with their labels. Confirm/refute at those two
  sections — they are the authoritative record and this plan re-states none of them.
- OBSERVED: `PLAN-PR-029` § Re-Grounding lists six pre-run corrections, including a declared surface
  path that does not exist (`test_findings_store.py`) and the mandatory `070 G1` fold. Confirm/refute
  at that section; every one of them binds here.
- HYPOTHESIS: the two pre-filters are the same predicate family and can be corrected in one pass —
  confirm/refute at `github_pr.py` § `_is_obvious_noise` and § the self-response filter
  (verify-at-outline). If they turn out to be independent, D6–D9 split out rather than distorting D1.
- OBSERVED (first-party, 2026-09-15, orchestrator read of `github_ops.py:405-448`): `REVIEW_THREADS_QUERY`
  carries four fixed `first:` caps and no `pageInfo`; `fetch_pr_comments_data` issues it once. Confirm/refute
  at that query and its single `run_graphql` call site.
  - verdict: corroborated | checked_at: 7a028157e | by: review-apparatus/cleanup | rescoped: n/a | evidence: github_ops.py:405-448 REVIEW_THREADS_QUERY has reviewThreads(first:100), comments(first:10), reviews(first:100), comments(first:100), no pageInfo; single run_graphql call at :476
- OBSERVED (corpus pass 2026-09-15, not re-read first-party): `ci pr comments` returned 236 against 237 on
  `cuioss/API-Sheriff#255`, dropping review `5123206655`. Confirm/refute by re-running both instruments on
  that PR.
- OBSERVED (corpus pass 2026-09-15, not re-read first-party): `cuioss-review-bot[bot]` posted 10 inline
  `/improve` suggestions on plan-marshall PRs in the window. Confirm/refute at D0 against the findings
  corpus.

## Dependencies and Sequencing

- ⛔ **Overlaps `PLAN-PR-056`, `PLAN-PR-057`, `PLAN-PR-058` and `PLAN-PR-060`** on the `github_pr`
  family — sequence, never pair.
- ⭐ **`PLAN-PR-060` depends on this plan**: its attribution gate reads a corpus whose denominator this
  plan's D0 and D6 correct. Run this first.
- ⭐ **Internal order: D0 → D6/D7/D9 (whose comment is it) → D1 (whose finding is it) → D2/D3 → D4/D5.**
- Supersedes: `PLAN-PR-029`, `PLAN-PR-040`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-059-what-the-pipeline-loses-on-the-way-in.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
