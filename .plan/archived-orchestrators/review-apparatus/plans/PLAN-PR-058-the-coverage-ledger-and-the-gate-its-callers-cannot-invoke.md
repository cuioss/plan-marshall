# PLAN-PR-058: The coverage ledger, and the gate its own callers cannot invoke

epic: review-apparatus
workstream: WS-01

> ⛔⛔ **SUPERSEDED 2026-09-18 — RETIRED AT THE COMPONENT RE-CUT. Do not emit this spec.**
>
> Its deliverables were carried, verbatim and as pointer rows, into: PLAN-PR-070 (D0/D3/D4/D6/D7/D8 — the gate, its coverage ledger and its call surface), PLAN-PR-067 (D1 — which zero a zero fetch is), PLAN-PR-072 (D2 — persisting the states), PLAN-PR-074 (D5/D9 — the barrier and the branch-cleanup predicate).
>
> **Why**: the nine theme specs were cut by SUBJECT, and every subject crossed the same components —
> `_findings_core.py` was declared by 7 of 9, `automatic-review/SKILL.md` by 6, `github_pr.py` by 5 — so
> no two could ever run concurrently and five plans would each have re-derived the same file. The re-cut
> is by component; no file is declared by two live plans.
>
> ⭐ **This file is NOT deleted**: it remains the authoritative pointer chain between a successor's
> `Carried from` column and the retired source spec holding each deliverable body, and it holds the
> claim labels the successors deliberately do not restate.

> Composed spec — **absorbs `PLAN-PR-053` and `PLAN-PR-051` whole**, under the operator's 2026-09-12
> decision to raise the split guard to **12 deliverables** and group staged work by shared target
> surface.
>
> ⛔ **Every deliverable body below lives in its SOURCE spec and is NOT restated here.** The sources
> are retired from the queue but remain the authoritative text. Follow the pointer; do not retype.

## Objective

Make the participation ledger record which commit a review **covered** rather than when we last
looked, make a zero finding-fetch say WHICH zero it is, and make the gate that reads all of it
invokable by its own documented callers without a rejection.

## Why these were grouped

Derived from `corpus surfaces`: both sources declare `review_completeness.py`,
`bot-participation-contract.md` and `automatic-review/SKILL.md`. The subject link is tighter than the
file link — `PLAN-PR-053` changes WHAT the gate reads (coverage vs observation), `PLAN-PR-051` changes
whether the gate can be CALLED at all. Shipping the first while the second stands means a corrected
ledger feeding a gate whose callers still get rejected; shipping the second alone hardens a call
surface that is about to change shape.

## Deliverables

**D0 — GATE, mutates nothing.** The merged re-grounding gate. From `PLAN-PR-053` D0: re-ground both
coverage claims at HEAD and derive the set of write sites that would have to split the two facts. From
`PLAN-PR-051` D0: re-ground both malformed-token claims against HEAD. **HALT and report** if either
population no longer reproduces.

⛔⛔ **D0 ALSO OWNS THE UNSAMPLED-MARKER GATE — folded 2026-09-13 from `plan-pr-046-012`, which exists
because the observation was carried only as a trailing aside in a message about the refusal detector
and would otherwise have been drained past.** As shipped on `main` at `77cb2e251`,
`github_pr.py` § `_is_participation_evidence` gates content with a **bare `in` test over the whole
body**: `return not marker or marker in str(comment.get('body') or '')`. Any occurrence of the declared
literal anywhere — inside quoted PR text, a nested block, or a user-authored excerpt the bot echoes —
satisfies it. CodeRabbit raised it twice on #1477 (`b131a3` round 1 Major, `c847ec` round 3 Major,
adding the quoted-PR-text vector); both were resolved `taken_into_account`, **never disputed**.

⭐ **The decline was correct and does NOT close it.** Tightening an unanchored match fails **CLOSED**: a
verdict comment that stops matching resolves a clean review `absent`, which BLOCKS a merge — and the
declared `recent_review_start` marker is **absent from CodeRabbit's live summary comment on #1477**, so
the gate is unexercised and its target layout has never been sampled. ⇒ **Sampling is the precondition
for anchoring, and it is this gate's job**: sample the live verdict-comment layout across several real
PRs, publish what was sampled and how many, and only then decide the anchored form. ⛔ Do not anchor
against an unsampled layout, and do not leave the substring test unanchored once the layout IS sampled
— the first blocks merges, the second credits a review that never happened. *Done when:* the sampled
population is published with its size, and the anchoring decision names it.

| # | Deliverable | Body lives at |
|---|---|---|
| D1 | A zero fetch reports WHICH zero it is | `PLAN-PR-053` § D1 |
| D2 | The discrimination already exists; nothing persists it | `PLAN-PR-053` § D1a |
| D3 | `reviewed_commit_sha` records COVERAGE, not observation | `PLAN-PR-053` § D2 |
| D4 | Retire the workaround the bug required | `PLAN-PR-053` § D3 |
| D5 | Make the post-merge catch a pre-merge one | `PLAN-PR-053` § D4 |
| D6 | A `malformed_bot_flag` refusal names the token, the shape, and an example | `PLAN-PR-051` § D1 |
| D7 | Make the pair-shaped flags self-describing at the call site | `PLAN-PR-051` § D2 |
| D8 | Prove the gate against its own documented invocations | `PLAN-PR-051` § D3 |
| D9 | A documented empty-string default the executor makes unreachable | `PLAN-PR-051` § D1a |

Nine deliverables — under the ceiling, with headroom left deliberately: D3 is the epic's most
consumer-heavy change (every reader of `reviewed_commit_sha`), and D0 may widen it.

**Evidence amendment 2026-09-15** (from
[`findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md`](../findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md);
feeds D0 and D5, adds no deliverable):

- ⛔⛔ **A required-reviewer bypass reached `main` — the concrete instance D5 must make impossible.**
  `plan-marshall#1438` merged `2026-09-07T07:58:16Z` with **no labels and ZERO CodeRabbit reviews** (its
  only CodeRabbit artefact is a "Review limit reached" summary), three days after `#1407` made CodeRabbit
  required (`required_bots: "cuioss-review-bot,coderabbit"`). `#1407` itself merged on a CodeRabbit
  **size** refusal, which never expires. D0 derives, for every merged plan-marshall PR since `#1407`,
  whether each required bot actually reviewed — and names each bypass with the path that let it through
  (barrier skipped, barrier mis-read a refusal, or merge outside finalize). ⛔ Do not assume which.
- ⭐ **The marker-gate sample D0 owes has a population to start from.** Across 181 PRs: **74** carry a
  CodeRabbit refusal *inside the summary comment*, **71** of them written as an in-place edit, and
  **54** of those PRs also carry real reviews. Two non-refusal texts sit in the same structural slot
  ("Review skipped: No new commits" ×5, "Review failed: The pull request is closed" ×1), and a
  conversational reply can quote refusal text verbatim (`cui-http#179`, comment `5481669579`). ⇒ The
  anchored form must key on structural markers and the review record, never on the summary body's
  current text alone.

**Lesson amendment 2026-09-18 (`2026-09-08-22-003`, absorbed; body in `archive/lessons/`).** The
`--measured-diff-size` **crash half is shipped** — verified at HEAD, `review_completeness.py:1955-1970`
declares `nargs='?', const='', default=''` with a comment reciting the deadlock, and the usage line
reads `[--measured-diff-size [<s>]]`. It landed **undeclared** in `PLAN-PR-033` (#1473). ⇒ D0 records it
as discharged rather than re-deriving it. **What is NOT shipped, and D7 carries**: widening the SKILL.md
empty-argument guarantee from *"every list flag"* to every flag that can receive an empty producer
value, and the derived sweep of that block for other such scalars. ⚠ A second absorbed lesson
(`2026-09-13-20-006`) names this same surface: the marker-shape gap on `bot_registry.py` was narrowed
rather than closed and billed two rate-limited review rounds — D0's anchoring decision is where that
debt is settled, per `review-practice.md` § 9.

⚠⚠ **D6–D9 MAY BE PARTLY SHIPPED — D0 must settle this before any of them is implemented.**
`PLAN-PR-033` (#1473, merged `38af136ed`) landed a `--measured-diff-size` **bare-flag crash** fix in
`review_completeness.py`, with a 404-line failing-first test
(`test/plan-marshall/automatic-review/test_measured_diff_size_bare_flag.py`), under an operator-directed
in-PR scope expansion that the PR **never declared** — its `references.affected_files` recorded 14 of
the 28 files that landed. A bare flag crashing the verb is precisely the shape `PLAN-PR-051` D1a names
(a documented default the executor makes unreachable) and sits on the surface D7 rewrites. ⛔ **Derive
what remains; do not assume either that it is done or that it is not.** D0 re-grounds D6–D9 against
`38af136ed` and reports each as discharged, partly discharged, or untouched — with the symbol that
settles it. ⭐ The same landing also shipped `github_re_review.py`'s `head_sha_verified` fix, which
discharged `PLAN-PR-056` D6; assume nothing about this epic's surface at that commit without reading
it.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`
- OBSERVED: `test/plan-marshall/workflow-integration-github/`
- OBSERVED: `test/plan-marshall/manage-findings/`
- OBSERVED: `test/plan-marshall/automatic-review/`
- OBSERVED: `test/plan-marshall/phase-6-finalize/`

## Claim Labels

- OBSERVED: this plan's claim set is exactly the union of `PLAN-PR-053` § Claim Labels and
  `PLAN-PR-051` § Claim Labels, carried unchanged with their labels. Confirm/refute at those two
  sections — they are the authoritative record and this plan re-states none of them.
- OBSERVED: `coveredCommitId` — the field D3 sources coverage from — occurs in ZERO files under
  `marketplace/`, and `cmd_bot_completion` reads only `gh pr checks`. Confirm/refute at
  `workflow-integration-github/scripts/github_pr.py` § `cmd_bot_completion`. Re-read first-party at
  `356973d80` during the 2026-09-11 inbox drain.
- HYPOTHESIS: the coverage/observation split is confined to the write sites D0 enumerates — confirm at
  D0 (verify-at-outline). ⛔ Every consumer that reads `reviewed_commit_sha` as coverage is in scope;
  D0 derives that set rather than assuming it.
- OBSERVED (first-party, 2026-09-15, orchestrator `gh api` read): `plan-marshall#1438` merged
  `2026-09-07T07:58:16Z`, carries no labels, and has zero reviews authored by `coderabbitai[bot]`.
  Confirm/refute at `repos/cuioss/plan-marshall/pulls/1438` and its `/reviews`.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: review-apparatus/cleanup | rescoped: n/a | evidence: Immutable historical GitHub record (plan-marshall#1438 merged 2026-09-07T07:58:16Z, no labels, zero coderabbitai[bot] reviews); no commit in this window can disturb it. Only declared path that moved is branch-cleanup.md, whose sole change is the ADR duplicate-number gate - a landing-time ADR check, unrelated to whether a required bot reviewed #1438. Corroborated as a historical record; the gh api read is not re-run this pass.
- OBSERVED (corpus pass 2026-09-15, not re-read first-party): 74 of 181 PRs carry a CodeRabbit refusal
  inside the summary comment, 71 as in-place edits, 54 alongside real reviews. Confirm/refute by
  re-sampling at D0 — this figure is the starting population, not the sample D0 publishes.

## Dependencies and Sequencing

- ⛔ **Overlaps `PLAN-PR-056`, `PLAN-PR-057` and `PLAN-PR-059`** on the `automatic-review` and
  `github_pr` families — sequence, never pair.
- ⚠ **Nearest launched neighbour is `PLAN-PR-046`** (a clean review in an uncredited shape). Whatever
  it leaves of the coverage half lands in D3 — re-check this spec against its landing before emitting.
- ⭐ **Internal order: D0 → D1/D2 (say which zero) → D3 (split the fact) → D4/D5 → D6–D9.** The gate's
  call surface is hardened last, against the shape D3 leaves.
- Supersedes: `PLAN-PR-053`, `PLAN-PR-051`.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-058-the-coverage-ledger-and-the-gate-its-callers-cannot-invoke.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
