# API-Sheriff PR #133 — mid-flight, pre-merge

> ⛔⛔ **THIS DOCUMENT'S CENTRAL VERDICT IS REFUTED. Corrected 2026-08-01 by
> [`2026-08-01-sweep-4day.md`](2026-08-01-sweep-4day.md) § 3. Read that section before citing anything
> below.**
>
> **PR-Agent DID review this PR** — comment `2026-07-30T11:23:46Z`, from a successful `issue_comment`
> `/review` run at `11:22:29Z`. The § 2 verdict *"unassessable — required reviewer never triggered"* is
> WRONG, and #133 reclassifies to a **deficit**: the canned no-op plus `🔒 No security concerns
> identified` on a 3349-line security-filter change, against a CodeRabbit baseline of 3 reviews and
> 7 threads.
>
> **Why it was wrong** — the evidence query below,
> `actions/workflows/pr-agent.yml/runs?branch={pr-branch}`, is **structurally blind to the `/review`
> path**: GitHub attributes `issue_comment` runs to `head_branch: main`, never the PR branch. It still
> returns `total_count: 0` today while the review demonstrably exists.
>
> ⚠ **NOT refuted, do not sweep along**: zero `pull_request`-event runs genuinely did exist on that
> branch. The `mergeable_state: dirty` Watch is untouched.
>
> ⛔ **Its Feeds entry for PLAN-PR-007 is withdrawn** — see the corrected entry at the foot of this file.
>
> The document is left otherwise intact as the audit record of what was believed when it was written.

epic: review-apparatus · analysed 2026-07-30 · **cross-repo** (`cuioss/API-Sheriff`), **PR OPEN — not a
post-merge revisit** · evidence: `gh api repos/cuioss/API-Sheriff/{issues/133/comments,pulls/133,pulls/133/reviews,actions/...}`
· 1 issue comment, 2 reviews, 1 workflow run on the branch

> ⚠ **Naming deviates from the `PR-{n}.md` contract deliberately.** `{n}` is a plan-marshall PR number
> throughout this corpus; a bare `PR-133.md` would collide with plan-marshall's own #133. Cross-repo runs
> are `{Repo}-PR-{n}.md`. Recorded in `README.md` § Current corpus rather than left as a silent variance.
>
> ⚠ **This is not a run of the standing practice.** That practice is a *post-merge* revisit over
> *accepted* findings. This PR is open and its findings are untriaged, so § 4 below is **owed, not
> answered** — recording it as answered would manufacture a signal.

## 1. Participation

| Bot | Result | Evidence |
|---|---|---|
| **CodeRabbit** | ✅ Reviewed — walkthrough comment (08:04:11Z, edited 08:12:14Z) + `COMMENTED` review, **3 actionable nitpick comments** (08:12:17Z) | `issues/133/comments`, `pulls/133/reviews` |
| **Sourcery** | ⛔ **Refused — diff-size limit**: "your pull request is larger than the review limit of 150000 diff characters" (`COMMENTED`, 08:03:51Z) | `pulls/133/reviews` |
| **PR-Agent** (`cuioss-review-bot`) | ⛔ **Nothing at all** — 0 comments, 0 reviews | both endpoints |

⭐ **The operator's paste said "4 findings"; the fetched evidence shows 3 actionable nitpicks plus the
walkthrough comment.** Minor, but recorded: the count in a paste is a lead, and 3-plus-a-summary is how a
4 arises.

## 2. Verdict

⛔ **PR-Agent produced no result — but this is NOT a bot defect, and the must-provide-a-result rule does
not reach it.** The rule presumes the bot was *asked*. It was not:

- `actions/workflows/pr-agent.yml/runs?branch=feature/plan-15-security-pipeline-modes` → **`total_count: 0`**.
- The branch has **exactly one workflow run of any kind**: `Maven Build`, event **`push`**, success.
- **Zero `pull_request`-event runs exist for this PR, for any workflow.** `dependency-review.yml` is also
  `pull_request`-triggered and also produced nothing.

⇒ The failure is **PR-wide event suppression, upstream of every reviewer** — not pr-agent, not
`pr-agent.yml`, and not the v0.17.0 pin (which `dependency-review.yml` shares and which reviewed fine on
another branch the evening before).

**Deficit assessment: NOT ASSESSABLE, and for a new reason.** Per `review-practice.md` § 1 a deficit needs
a baseline. A baseline exists here (CodeRabbit's 3) — but the comparison is void because PR-Agent never
ran, so there is nothing to compare. ⚠ **This is a fourth scoring outcome the practice does not yet name**:
not *clean*, not *deficit*, and not the existing *unassessable-because-everyone-else-was-rate-limited*.
Call it **unassessable — required reviewer never triggered**.

⚠ **Sourcery's refusal is a new shape too**: a **size** limit, not a rate limit. It does not expire, so
it is not covered by the retired rate-limiting watch. Folded into PLAN-PR-008.

## 3. Posted answers

**N/A — the PR is open and untriaged.** No finding has been dispositioned yet, so the missing-answer rule
has nothing to bite on. ⛔ Not scored as a pass.

## 4. Could we have found it ourselves?

**OWED — deliberately unanswered.** The 3 CodeRabbit nitpicks are not yet accepted or rejected, and the
back-feed question keys off the **answer posted on the PR**. Re-run this section after #133's triage
lands. ⚠ Do not answer it from the finding bodies alone — that is the "keyed off internal state"
correction `review-practice.md` already records as discarded.

## Feeds

- **PLAN-PR-007** — ⛔⛔ **WITHDRAWN 2026-08-01.** This entry claimed a third taxonomy member,
  `not_triggered`, confirmed because "the bot was never asked". **The bot WAS asked and did answer**
  (see the correction banner at the top). `not_triggered` therefore loses its ONLY confirming instance,
  and D1's population is **not** known to be ≥3 on this evidence.
  ⚠ The member is not thereby disproven as a *concept* — a genuinely never-triggered bot remains
  possible — but it is now an unevidenced hypothesis, and PLAN-PR-007 must be re-scoped against this
  refutation before it is emitted.
- **PLAN-PR-008** — adds a **permanently unrecoverable** refusal to D1's terminal-state sample (size
  limit ≠ rate limit: waiting never clears it, only changing the diff does, which is not a barrier
  action) and strengthens the case that D3's operator-authorized coverage-gap exit is *required*.
- **PLAN-PR-001** — ⭐ **counter-evidence worth keeping**: here `absent` was **factually true**.
  PR-001 fixes a *false* absent; this run is the negative case its fix must not break. A fix that credits
  participation from a persistent-comment `updated_at` must still report absent when there is no comment
  at all.
- **`review-practice.md` § 1** — needs the fourth outcome above, plus the qualifier that the
  must-provide-a-result rule presumes the bot was triggered.
- **Open question (not owned by any staged plan yet)**: does a `pull_request`-triggered workflow run get
  created at all while a PR is `mergeable_state: dirty`? Leading mechanism, not settled — see the epic
  Watch.
