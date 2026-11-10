# Landing Analysis: PLAN-LB-106 — review-bot evidence is read from what the provider says about the head

epic: live-blockers
workstream: WS-05
pr: #1912

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-106.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `5fd240a5e993bcac32afe93043e52fb97da13b54`, a squash commit with ONE parent, `3806ca897c28c6bedd9bffcd25a22f0e32275460` (the ledger land of PR 1917; read with git before the leaf prompt named it). The leaf found `git diff b09d230fc 5fd240a5e` empty, so the squash tree equals the final PR head. Landing message `rb-lb-106-review-bot-evidence-truth-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; `unknown` is an unobserved fact and not a zero; out of scope under the focus rule); its surface delta is `unmeasured` (neither a declared nor a realized set was supplied), so the surface was read from the diff instead: 29 files, +1765/−189 (`git diff --stat 3806ca897 5fd240a5e`). The lane reports 5 of 5 deliverables done, `self-review: clear`, with a spec read from the ledger copy (`spec_differ=true`: the main checkout's copy carries four deliverables).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a summary comment is credited from the head its own marker names | shipped-modified | `_github_pr.py` parses the HTML-comment marker (`sourceCommitId`, `coveredCommitId`, `kind`). A present-but-unreadable marker yields "never credit", where the spec's D1 line says "no verdict": a spec defect, since the spec's own fail-closed constraint contradicts it and the lane chose the constraint (leaf). |
| D2 — a finished review of the head outranks an older quota refusal; a thread reply is never evidence | shipped-modified | The inline rule at `github_pr.py:2111-2118` and the placement at `github_ops.py:686-714`. It holds for a thread reply. For a comment's placement it is wrong in production (L3-1), so the D2 outcome fails open on real data. |
| D3 — a cut body keeps its conclusion and says it was cut | shipped-modified | `validate_struct.py` and `_findings_ingest.py` keep head and tail and mark the elision (leaf). The cut upstream at quarantine is head-only (`_findings_core.py:181-182`, re-read) so a body over 64 KiB loses its tail before ingest sees it (L3-4). |
| D4 — a second review's inline comments are filed | shipped-as-specified, lead stays live | The test injects records after the fetch, so it cannot refute a fetch-layer cause of the lead (L2-2). The lane records the surviving lead as the documented resolved-thread skip. |
| D5 — a Sourcery review body is filed | shipped-as-specified | `sourcery.md` declares the footer markers; `test_only_sourcery_declares_footer_markers` enumerates the registry (leaf). The footer strip is per line (L3-3). |
| not a deliverable | not measurable | `landing-check` surface delta `unmeasured`. 29 files realized against the spec's 26 declared entries (`corpus surfaces`); the diff is read, not compared path by path. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing; the orchestrator re-read the points marked `re-read` at their `file:line` in the merged tree. It was a reading only: no build, no test run, no write. The leaf had no Grep and used `architecture search --content`; it also read the live PR 1912 comment data.

- **Dispatch:** one read-only leaf per landing — the read crosses 29 files and must not share context with any other landing.
- **Verdict:** layer 1 findings (two minor); layer 2 findings (minor and info); layer 3 findings (**two major**, minor, info), no blocker.
- **Orchestrator re-read:** L3-1 (code and live data), L3-4 (code). Every other row is a lead the leaf checked and I did not re-read.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 (minor, not re-read) | The marker name, `coveredCommitId`, `sourceCommitId`, `kind` and `reviewed` are code literals and the parser applies to every bot's body, against the standing constraint that everything CodeRabbit-specific is registry data. The lane decides by body content, where D2 says the registry selects which bots' named evidence disables the fresh-edit arm. An old-format summary still credits through the fresh-edit arm. | checked | `_github_pr.py` ~L383-400 |
| L1-2 (minor, not re-read) | The lane text credits a marker naming "one of this PR's heads" and points at `review_coverage_verdict`, which compares against a single head; the prose rule and the cited parser disagree. | checked | `runbook-lane/SKILL.md` L699-704 |
| spec defect (leaf) | D1's "no verdict when the marker is absent or unreadable" contradicts the standing fail-closed constraint. The shipped "never credit" is right; the spec line is to be corrected so a later round does not restore the fall-through. | corroborated | spec D1; `review_coverage_verdict` returns `False` for unreadable fields |

**Layer 1 verdict:** findings — 2 minor and one spec defect of mine.

### Layer 2 — Implemented

- **L2-1 (minor, not re-read):** the runbook-lane guard checks `'kind'` and `'reviewed'`, which occur in any prose, and its field list is test-local rather than read from `_github_pr`; a parser field rename would not fail it (`test_runbook_lane.py`).
- **L2-2 (minor, not re-read):** the D4 test injects records after `fetch_pr_comments_data`, so it cannot refute a fetch-layer cause of #512, and `count_skipped_noise >= 1` is loose. The lead stays live: PR 1912 shows CodeRabbit nitpicks and outside-diff findings inside review bodies (`test_comments_stage_fetch.py`).
- **L2-3 (minor, not re-read):** `_REVIEW_COVERAGE_PATTERN` `\{.*?\}` parses a nested JSON payload as unreadable (fail closed), and `search` takes the first opener, so a review body quoting a fixture marker overrides the provider's `commit_id` with False (`_github_pr.py`).
- **L2-4 (info, not re-read):** the `_ELISION_TEMPLATE` comment justifies a no-newline marker by line-oriented transport, but the kept head and tail contain newlines (`validate_struct.py`).
- **L2-5 (info, not re-read):** `{**payload, **_truncation_fields(clamps)}` is always overwritten by the merged block, and no consumer outside ingest and tests reads `truncated`, so triage never sees the cut flag (`_findings_ingest.py`).
- **L2-6 (info, not re-read):** `test_a_finished_head_review_outranks_an_older_quota_refusal` asserts the classifier, not `pre_merge_gate merge`; the barrier claim rests on inference from `pre_merge_gate.py:727-744`.
- Red-first runs (`5c1e70ab4`, `f973dab28`) and every per-head test run are `not_shown_by_reading`; the leaf confirmed only that the shas exist and the branch order (tests, then D1/D2, then D3/D5). The lane's hypothesis that the marker is an HTML comment was confirmed by the leaf from the live PR summary (flat JSON `final_review_risk_coverage`), not from the runbook-lane's cited API-Sheriff copy the spec's verify-first clause asked for; every test fixture is synthetic.

**Layer 2 verdict:** findings — 6 (minor and info).

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read, one callee not read) | `github_ops.py:705-709` (`_inline_comment_placement`), `github_pr.py:2111-2118` | A CodeRabbit inline review comment opening a thread, posted at an older head, on a line that is still in the diff at the merge candidate; a refusal for the head observed in the same fetch | The placement reads the comment's own `commit` first and the review's commit only as a fallback. GitHub reports the comment's `commit` at the newest head while the line stays in the diff, so an old comment is placed at the merge candidate. The inline rule then sets `_named_verdict` from `_reported_commit_matches_candidate`, credits the bot, and the credit outranks the refusal at `classify_bot` (`review_completeness.py:884-895`, leaf; `pre_merge_gate.py:727-744`, leaf). Live proof on PR 1912: CodeRabbit comment `PRRC_kwDOQ3xasM8AAAABCyVDVA`, created 2026-11-05 14:52:35, opening its thread, resolved, reports `commit_id b09d230fc…`, the final head, while CodeRabbit's own summary says "Latest commit, not reviewed: b09d230". The false green of PLAN-LB-26 / #515 is back on main, and before this change the same comment had `commit_id ''` and could not credit beside a refusal. (Effect read from the code and the live data; I did not read `_reported_commit_matches_candidate` or run the barrier.) | major |
| L3-2 (leaf, inferred, not re-read) | `github_pr.py:2093`; `_is_refusal_notice` not read | The real CodeRabbit shape: the "Review limit reached" block sits inside the same summary comment that carries the coverage marker | That pattern is a registered `refusal_pattern`, so the whole summary is skipped as a refusal and its marker is never read; the finished review earns no credit and #537 persists. Untested: the D2 fixture puts the refusal and the summary in separate comments. Whether CodeRabbit keeps the limit block after finishing a review is unknown. | major (lead) |
| L3-3 (leaf, not re-read) | `github_pr.py` `_strip_footer_markers` / `_is_obvious_noise`; `sourcery.md:22-25` | A clean Sourcery "looks great" body plus the footer; a footer spread over several lines | The footer used to drop any Sourcery comment, dropping clean bodies as a side effect; Sourcery declares no `contentless_review_markers`, so such a body is now filed as a `pr-comment` finding needing triage, and a multi-line footer leaves markup behind so a footer-only body is filed. No real Sourcery body was seen. | minor |
| L3-4 (re-read) | `_findings_core.py:181-182`; `validate_struct.py` `_clamp_string_with_elision` | A review body over 64 KiB | The quarantine cuts head-only at the byte cap and appends `[truncated]`; ingest then keeps the "tail" of that head, so the conclusion is gone, and `original_length` reports about 65.5k, not the true length. A body of exactly 8000 characters is promoted byte-identical; 8001 is clamped (leaf, correct). | minor |
| L3-5 (leaf, not re-read) | `github_pr.py:2111-2116`, `:2236-2243` | A thread-reply-only bot | It is now reported stale, not absent, so the remedy shifts from escalation to re-trigger, and the reply-covered arm can lift such a bot, so the credit rests on the bot's own "Already reviewed the last commit" claim. | info |
| L3-6 (leaf, not re-read) | `github_pr.py:2111` | `cuioss-review-bot`, which declares `inline` evidence | The inline rule is bot-agnostic and ignores `_requires_update`, so the bot the spec said to leave alone is also governed; four suites had to add `commit_id` / `thread_reply` to stay green. | minor |
| L3-7 (leaf) | GraphQL fragment | `replyTo`, `commit` or `pullRequestReview` absent | Null-safe by isinstance checks; no new connection, so no rate-limit cost; the thread-position fallback is ORed in always, the conservative direction. | info |
| L3-8 (leaf, not re-read) | `test_participation_site_population_*` | an unseeded AST candidate | The guard is not vacuous (it forced the `_REVIEW_COVERAGE_REVIEWED_KIND` exclusion and the runbook-lane `SiteExpectation`), but its AST walk covers producer, private helper and registry only: the new placement site is outside the population, and the three files are identical triplicates. | info |

**Layer 3 verdict:** findings — two major (L3-1 confirmed, L3-2 a lead), L3-3 and L3-6 minor, L3-4 minor, the rest info.

## Reviews and Merge

CodeRabbit (required) reviewed `dabb78c06`, `c27312d21`, `d9be145ce`, `3084d75df` and `ea5f80545`, and refused on quota for later heads; the lane used the standing authorization for the final head `b09d230fc` (`coveredCommitId=ea5f80545`, `kind=reviewed`, re-triggered once and refused on quota). The leaf read CodeRabbit's summary as "Review limit reached" and "Latest commit, not reviewed: b09d230", which agrees with the lane. Sourcery (optional) refused for size (150,000 diff characters). Review history was the lane's claim: I read no review body and not the PR body that records D4. CI `verify` was green on every pushed head per the lane; I did not re-read it. The merge went through the queue to `5fd240a5e`.

The L3-1 defect is in code that reads evidence for the NEXT PR: the barrier that ran for this merge was the pre-change one, where the same inline comment carried `commit_id ''`. By the lane's account this PR merged on the standing authorization with a qualifying review on `ea5f80545`; I did not re-read the barrier's output for it.

## Residue and Watches

- Spec defect of mine: D1's "no verdict" line contradicts the fail-closed constraint; correct it in the spec if the spec is re-used.
- L3-1 is a live fail-open in the merge gate and wants a fix plan (surface: `github_ops.py`, `github_pr.py`, the participation tests). Staged on the operator's word only.
- L3-2 is a lead to settle first at that plan's outline: does CodeRabbit keep the limit block after a finished review?
- The lane's coverage-marker evidence was the runbook-lane's own fixture, not a verbatim API-Sheriff copy (the spec's verify-first clause); the live PR 1912 summary now supplies the verbatim shape.
- The `landing-check` gap on `total_tokens` is out of scope.
- Owed from earlier: the executor regeneration owed by PLAN-LB-112, and parked PLAN-LB-46 sequences after this landing.
