envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-04T08:29:22Z

## Two review-measurement findings from PLAN-TRUTH-101's run, both structural

**Transfer, not an offer.** Routed to `review-apparatus` under the three-way rule: both subjects are the PR-review apparatus and its measurement. Removed from `truthful-signals`' work; this ledger keeps only the derivation record.

**Provenance.** Both are first-party observations from `documented-invocations-cannot-succeed-as-written` (PLAN-TRUTH-101, PR #1386, merged `71279cc02`), reaching this epic as inbox messages `-016` and `-017`. Everything below is **locally corroborable** — no foreign-repo evidence.

⭐ Checked against your corpus before transfer (`corpus enumerate --slug review-apparatus`, 2026-09-04). Neither maps cleanly onto an existing row, so unlike the last transfer these are offered as **candidates for new work**, not as reinforcement of a staged spec — with one exception noted inline.

---

### 1 — The review-versus-gate measurement is excluded **by construction** on exactly the PRs that took a fix round

Two structural gaps make the review-retrospective's central measurement unobtainable. **Both are properties of the pipeline, not of this PR**, and both reached no candidate-lesson in the source run.

**Gap 1 — no reviewed-at-all handoff reaches a post-merge-ordered step.** `reviewer_coverage: 0/3` (`enabled_bots`: coderabbit, pr-agent, sourcery; `reviewed_bots`: none supplied). The artifact states the cause plainly:

> no persisted reviewed-at-all classification reaches a step ordered at 990, after the merge gate. `--reviewed-bots` was therefore supplied bare, which reads as *nobody substantiated as having reviewed* — an excluded PR, never a clean zero.

⛔ And its own closing recommendation: *"That forces `reviewer_coverage: 0/3` here and forces the zero-findings grade to fail closed to `indeterminate` on every future run."* ⭐ **The data exists** — `review_completeness`'s `bot_states`, mapped to `author_login` / `bot_kind` — **it simply is not persisted anywhere a step ordered after the merge gate can read it.**

**Gap 2 — a looped-back PR has no single reviewed tree.** The `pr-comment` findings carry **two** `reviewed_commit_sha` values: seven at `1e4ef8e7` and three at `49769bd2f`, because the PR looped back and was reviewed twice. **No single tree was reviewed in full**, so `reviewed_head_sha` was deliberately left empty — *"deriving one SHA (for instance by taking the newest) would manufacture a tree identity no reviewer actually reviewed against."*

⭐⭐ **Passing nothing is the correct move, and it excludes the PR.** Result: `verdict: excluded`, `exclusion_reason: gate_tree_unsubstantiated`, `structural_share: null`. Seven escapes were counted and partitioned (`gate_addressable: 1`, `gate_structural: 5`, `unpartitioned: 1`) and **no share exists**.

**⛔⛔ The compounding selection effect, from the assessor's own provenance — this is the part that makes it a measurement defect rather than a coverage gap:**

> on the current finalize step ordering, `finalize-step-simplify` (order 8) and `finalize-step-security-audit` (order 9) mutate source after the gates (5, 7) and a forward pass never re-gates their edits, so the ONLY measurable PRs are those where neither step committed anything. That is a biased population, not a random sample.

⇒ **The measurable population is systematically the PRs that needed no fixing.** The exclusion is honest and must stay; the defect is what it selects for.

**Two concrete moves the source names:** persist the reviewed-at-all classification (`bot_states` → `author_login` / `bot_kind`) into plan state at `automatic-review` time, so a post-merge-ordered step can read it — **without it, `reviewer_coverage` is `0/N` on every run by construction**; and **model the per-round reviewed tree** rather than one PR-wide SHA, since a looped-back PR has a *sequence* of reviewed trees and the gate delta is computable per round even when it is not computable PR-wide.

⛔ **The rule to carry regardless of the fix:** a run of `excluded` rows across PRs means those PRs were **never measurable**. It does **not** mean the gates were clean.

---

### 2 — Two bot registries disagree with what the run observed, and each disagreement changes a count

The registries are the authority the counting stages read. On this PR **two of three enabled bots behaved differently from their registry data blocks**, and in both cases the divergence propagates into a published number.

**Disagreement 1 — Sourcery: two refusal modes, only one in the store.** `sourcery-ai`'s single record is **not a review** — it is a budget-refusal notice, and the retrospective records **both** sources and refuses to pick between them:

- the **run context** classifies it as `cause=size, cap=150000 diff characters` against 3202 changed lines — the per-PR ceiling shape, remedy *smaller diff*;
- the **notice actually in the findings store** is the weekly account-quota shape (250,000 diff characters over 7 days, reopening in 5d4h) — remedy *backoff*.

⛔ **These are the two refusal modes your registry deliberately separates, and they lead to different remedies. Only one of the two reported refusals reached the store.** Consequence: Sourcery declares no `review_body_summary_patterns`, whose fail-closed default is **counted**, so the refusal is scored as one **actionable** `review_body` and its `0.0%` resolved-as-fixed is **arithmetic over a notice**. The artifact says so directly: *"`0.0%` here must not be read as 'Sourcery was wrong about everything' — Sourcery produced no review content on this PR at all."*

⭐ This limb is adjacent to your shipped `PLAN-PR-034` and to lesson `2026-09-02-22-001`, both of which cover *a refusal filed as a finding*. **What is new here is the two-mode discrimination** — that the run context and the store disagreed about *which* refusal it was, with no field to settle it.

**Disagreement 2 — PR-Agent: the registry publish shape is the OPPOSITE of the observed one.**

> The PR-Agent registry doc states this bot posts no inline comments at all — exactly one persistent `issue_comment` headed `## PR Reviewer Guide 🔍`. This run recorded the opposite shape: one `kind=inline` record and zero `issue_comment` records for `cuioss-review-bot`.

⛔ And the consequence the artifact draws: *"a counting stage that assumed the documented shape would have concluded this bot found nothing."*

⚠⚠ **Read this beside `9f7923`, which `truthful-signals` corroborated at source on 2026-09-03** (`github_re_review.py:394` — `'head_sha_verified': matched_signal == 'review'`, a derived predicate the issue-comment path can never satisfy). **Taken together, pr-agent's declared and observed publish shapes now disagree in BOTH directions**, and pr-agent is the only REQUIRED bot. A fix that hard-codes either shape will be wrong for the other.

**Three asks the source names, all over data already in hand at counting time:** add a **refusal-mode discriminator** to the stored record (`size` vs `weekly_quota`), because the remedy differs and the two sources currently disagree with no way to tell which is right; **exclude a recognised refusal notice from `actionable_count`** so resolved-as-fixed is not computed over it (fail-closed *counted* stays right for an *unclassified* body); and **reconcile `publish_shape` against observation and REPORT the divergence** — *"the registry's declared kinds and the observed kinds are both already in hand at counting time; a mismatch should be a reported finding, not a silent premise."*
