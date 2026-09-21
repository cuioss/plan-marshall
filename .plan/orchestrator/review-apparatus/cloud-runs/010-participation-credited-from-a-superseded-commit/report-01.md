# Run report — 010-participation-credited-from-a-superseded-commit (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/participation-superseded-commit-uo7k92` (harness-assigned, kept as-is)    **PR:** [#1141](https://github.com/cuioss/plan-marshall/pull/1141) — **MERGED** (squash `50f67ed`, by `cuioss-oliver`, 2026-08-10T16:12:35Z)    **Outcome:** completed — all deliverables complete and verified; PR merged once `verify` went green (auto-merge fired; the `license/cla` check was **not** required)

> **Correction (post-merge, this file amended on a follow-up branch).** An earlier revision of this
> report recorded the outcome as *"partial — merge blocked on the `license/cla` signature."* That was
> **wrong**: the CLA was not a required check, and the PR auto-merged the moment `verify / verify`
> concluded green. See § "Why the CLA was falsely read as a merge blocker" below for how the mistaken
> inference happened. Because PR #1141 was already merged when the correction was made, this amendment
> lands as a fresh change per the merged-PR rule, not as a push to the (merged) PR branch.

## Skills loaded

- `cloud-plan-lane` (the working contract; loaded first)
- `plan-marshall:ref-code-quality` (read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (read from bundle path)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)
- `plan-marshall:persona-implementer` (production-code work identity)

All obtained by the bundle-path route; none unreachable.

## Deliverables

### D0 — site population + anchor per site (GATE)

**Enumeration method (re-runnable).** `Grep` the participation symbols
(`_has_update_movement`, `participation_requires_update`, `reviewed_commit_sha`, `head_sha_verified`,
`participated_stale`/`stale_participation`, `participation_complete`) over `**/*.py` and `**/*.md`;
read the producer→consumer call graph from `github_pr.fetch_findings`'s return keys
(`participated_bots`, `stale_participation_bots`, `refused_bots`) to their consumer
`review_completeness.check_completeness` and its barrier caller in `branch-cleanup.md`; and
`github_re_review.await_fresh_review`'s `head_sha_verified` to its consumer `branch-cleanup-rereview.md`.
The registry (`bot_registry.participation_requires_update`) confirms **PR-Agent is today the sole bot**
subject to the S1 currency test.

**The site table — reported per site, never one global answer:**

| # | Site | Anchor (which commit the credit is compared against) | Idempotent? |
|---|------|------|------|
| S1 | `github_pr.py` `_has_update_movement` + participation loop — the currency test for `participation_requires_update` bots | **NONE.** Observation-history (`observed_keys`) for arm 1 (first presence) + `updated_at != created_at` for arm 2. No SHA is consulted on either arm. | **NO.** The first fetch *consumes* the first-presence arm; a second fetch of the same unedited comment **at the same HEAD** flips `participated`→`participated_stale`. The module's own comment states this design: "the record only ever closes that arm on a LATER fetch." |
| S2 | `github_pr.py` participation loop, non-`requires_update` bots (coderabbit, sourcery) | NONE — presence of a declared evidence kind; no currency test runs at all for these bots. | Idempotent (pure over the comment set), but currency-blind. |
| S3 | `github_re_review.py` `_match_review` (the re-review "obtain" review path) | **HEAD SHA.** `review.commit_sha == head_sha` → `head_sha_verified: true`. | **YES** — pure comparison of `commit_sha`/`submitted_at` against fixed inputs. |
| S4 | `github_re_review.py` `_match_bot_comment` (the re-review "obtain" comment path) | **NONE.** Timestamp vs `trigger_time`; a comment carries no reviewed SHA → `head_sha_verified: false`. | Idempotent (pure), but SHA-blind. |
| S5 | `review_completeness.py` `classify_bot`/`check_completeness` (the quorum consumer) | NONE directly — it trusts the producer's verdict sets. | Idempotent given fixed inputs (pure); but its inputs are produced by S1, which is not. |
| S6 | `branch-cleanup.md` Pre-Merge Review-Completeness Barrier (Predicate 2) | The **live HEAD** — re-runs `fetch_findings` (which re-stamps `reviewed_commit_sha` to the current HEAD) then `review_completeness`. Re-derives per fetch, not per stored record. | Inherits S1's non-idempotence — its `fetch_findings` call *is* S1. |
| S7 | `branch-cleanup-rereview.md` step 3 (trigger-A re-review consumer) — **the "recorded-but-ignored bit"** | Reads `matched` + `timed_out`, **ignores `head_sha_verified`**. A `head_sha_verified: false` comment-only match is credited as "the fresh review is now on the PR." | The read itself is idempotent, but it consumes S4's SHA-blind bit and **discards** the one bit (S3-vs-S4) that names whether the SHA was verified. |
| S8 | `_github_pr.py` / `github_ops.py` `pr wait-for-comments` predicate — the movement arm that is the **input** to S1's currency test | Timestamp/count movement; no SHA. | Idempotent (an await-completion timing signal, not a credit). The contract doc's "Recorded exclusions" already names it as "the *input* to the currency test rather than the classification it feeds." |

**The contradiction D0 surfaces (D1 must resolve):** **S3** demonstrably *withholds* credit unless the
reviewed SHA equals the merge candidate (SHA-anchored, `head_sha_verified: true`). **S1** demonstrably
*credits* participation with **no SHA consulted**, so a review of an earlier commit satisfies the gate
at a later commit — and it flips on the second look. Two sites, opposite answers, from what should be
one contract. And **S7** computes the deciding S3-vs-S4 bit and then throws it away.

**Data constraint discovered (shapes the D2 fix).** A fetched *comment*
(`github_ops.fetch_pr_comments_data`) carries **no reviewed-SHA** on any kind — only
`created_at`/`updated_at`. Only a *review* (`_github_pr.fetch_pr_reviews_with_commits`) carries
`commit_sha`. The per-finding `reviewed_commit_sha` (the PR HEAD stamped at ingestion) is therefore the
only durable per-comment SHA available to S1, and PR-Agent's contentless Guide is dropped as noise so
it has **no finding** — only a key in the noise-dropped sidecar. D2 therefore extends that sidecar to
carry the stamped SHA.

**Gate verdict: the site population was derived from the tree (grep + call-graph + registry); the plan
proceeds.**

### D1 — the stated rule

**Commit 4e93870.** `bot-participation-contract.md` § "The currency rule" states the single rule
applied at every D0 site: *a participation credit is valid only against the merge candidate — a review
counts iff the commit it reviewed is the merge candidate's HEAD, and the verdict is a pure comparison
that consumes no observation state, so it is identical however many times it is evaluated.* The
contradiction D0 surfaced (S1 credits with no SHA; S3 withholds unless the reviewed SHA equals the
merge candidate) is resolved toward S3's behaviour: S1 is re-keyed onto the SHA comparison. The
derivation settled cleanly, so no "alternatives" proposal was needed.

### D2 — re-key the currency test onto HEAD SHA

**Commit 4e93870.** `github_pr.py`: `_has_update_movement` (observation-history + `updated_at`)
replaced by `_reviewed_at_merge_candidate` (SHA currency arm + edit-movement arm, no `observed_keys`).
The merge-candidate SHA (`fetch_pr_head_sha`) is fetched before the participation loop; the reviewed
SHA per comment is the union of `_existing_pr_comment_shas` (stored-finding stamps) and
`_recorded_dropped_comment_shas` (the noise sidecar, extended to carry `reviewed_commit_sha`). The
verdict is now idempotent and SHA-anchored. Verified by test + the explicit pre-fix mutation proof
(below).

### D3 — `declined` state, excluded from quorum

**Commit 4e93870.** `review_completeness.py`: new `STATE_DECLINED` in `_UNPROVEN_STATES`, a
`--declined-bots` input, classified after the refusal branches and before `participated_stale`. The
incremental-review decline is recognized at the trigger-A consumer (`branch-cleanup-rereview.md` now
honors `head_sha_verified` — a `matched: true` / `head_sha_verified: false` is a decline, not a
review) and forwarded to the pre-merge barrier's Predicate 2 (`branch-cleanup.md` passes
`--declined-bots`). Documented in `bot-participation-contract.md` § "Detecting a decline" (taxonomy
grew seven → eight; the closure-count and blocking-count contract tests were updated in lock-step, and
the derivation tests carry the new member automatically). **Boundary (honest):** the `declined`
observation is populated end-to-end only on the trigger-A (post-rebase) path; a decline observed on
the FIND-step trigger-B loop-back is not yet wired into `--declined-bots` — see Residue.

### D4 — mutation-proven tests

**Commit 4e93870.** New/updated tests:

- **Idempotence at an unchanged HEAD** (`test_second_fetch_at_the_same_head_stays_participated`,
  stored path; `test_second_fetch_of_an_unchanged_guide_at_the_same_head_stays_credited`, drop path).
  These replace the two tests that *pinned the observer-effect bug* (both asserted the second same-HEAD
  fetch flips to stale). **Mutation-proven:** a standalone emulation of the pre-fix
  first-presence-consumed predicate flips `participated → []` on the second same-HEAD fetch, so these
  tests FAIL pre-fix — captured in the Findings section.
- **Advanced-HEAD staleness** (`test_review_predating_the_merge_candidate_is_stale`,
  `test_dropped_guide_goes_stale_once_head_advances`) — the matched control proving the credit is
  genuinely anchored to the commit, not "always participated".
- **Edit-arm after a HEAD advance** (`test_in_place_edit_credits_participation_after_a_head_advance`,
  `test_guide_edited_after_head_advance_credits_participation_again`) — a genuine in-place re-review is
  still credited when the SHA arm misses.
- **D4(d) population-derivation** — `test_currency_anchor_is_derived_from_both_sha_sources` (both SHA
  sources are the SUT's own readers), plus the registry-derived, non-empty `_UPDATE_REQUIRING_BOTS`
  sweep and the existing `_DERIVED_NON_PARTICIPATION` / `_scan_invocation_sites` derivations (extended
  for `declined` / `--declined-bots`).
- **D3 quorum tests** — `declined` blocks like `absent`; both refusal shapes excluded;
  refusal-outranks-decline and proven-outranks-decline ordering; a `declined` required bot blocks the
  pre-merge barrier byte-identically to `absent` (widened-member parity).
- **D3 consumer doc test** — `test_rereview_consumer_honors_head_sha_verified_as_a_decline` asserts
  the trigger-A consumer reads `head_sha_verified` and the barrier forwards `--declined-bots`.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** (`github_pr.py`,
`review_completeness.py`, and test files), so the full `./pw verify` ran. Result: **`=== verify:
SUCCESS ===`, 18689 passed, 14 skipped** — including `test_real_marketplace_quality_gate_has_zero_findings`.
The per-commit `./pw quality-gate` also reported `total_issues: 0`, `status: pass` (one ruff C420 and
one historical-prose finding were fixed before the commit).

## Findings

- **Pre-fix mutation proof (D4).** A standalone harness reinstated the pre-fix
  first-presence-consumed predicate and re-ran the same-HEAD scenario: the second fetch flipped
  `participated → []` for the sole `participation_requires_update` bot (pr-agent), confirming the new
  idempotence tests correctly FAIL against the pre-fix code. Disposition: recorded as the mutation
  evidence; the scratch harness lives outside the repo (disposable).
- **Ruff C420** on the new sidecar-record dict-comprehension → replaced with `dict.fromkeys(...)`.
  Disposition: fixed.
- **plugin-doctor `analyze_historical_prose_in_skills` (1)** — "an earlier commit" in
  `bot-participation-contract.md` tripped the earlier-proposal family → rephrased to "a commit that is
  not the merge candidate". Disposition: fixed.
### Verification sub-agent (Step 6)

An independent `general-purpose` sub-agent verified the diff against the plan (read-only). It confirmed
D2/D3/D4 implemented as specified, out-of-scope compliance clean, and the same-HEAD idempotence test as
genuine mutation discrimination. Three findings, all dispositioned:

1. **[Medium] Stale "seven-member" taxonomy text.** `automatic-review/SKILL.md` (×2) still said
   "seven-member" / enumerated seven members omitting `declined`. The grep sweep surfaced two more the
   agent didn't reach: `review_completeness.py:125` comment and `phase-6-finalize/workflow/create-pr.md:201`.
   **Disposition: fixed** (commit d194d60) — all four now say eight and enumerate `declined`; the
   "ninth member" complement wording corrected.
2. **[Low] Empty merge-candidate-SHA path was non-idempotent.** A failed `fetch_pr_head_sha` (empty
   string) let the first fetch credit and the second go stale — a flip on the one path the SHA is
   absent (toward *more* blocking, the safe direction, but contradicting the unqualified idempotence
   claim). **Disposition: fixed** (commit d194d60) — the first-observation arm is now guarded on a
   non-empty merge-candidate SHA, so the empty-SHA case fails closed on both fetches; pinned by
   `test_unresolvable_head_sha_fails_closed_and_stays_idempotent`.
3. **[Low, already disclosed] `declined` wired end-to-end only on the trigger-A path.** The FIND-step
   trigger-B loop-back does not populate `--declined-bots`. **Disposition: accepted as residue** (see
   Residue) — the plan's D3 concrete defect is the trigger-A `head_sha_verified` bit, which is closed.
   The agent also noted the `head_sha_verified` consumer is a markdown workflow step, so its test
   verifies instruction text rather than an executed code path — inherent to the architecture, not a
   defect.

The agent could not run the build (per instruction) and could not independently observe the mutation
harness; both were verified by this run (build: `./pw verify` SUCCESS; mutation: the harness output is
recorded above).

### PR review findings (Step 7)

4. **[Real, fixed] PR-Agent (`cuioss-review-bot`, the required bot) — "Bypassed SHA Currency Check".**
   The edit-movement arm was keyed on `updated_at != created_at`, a permanent "was ever edited" flag:
   once a `participation_requires_update` comment is edited at commit N, it was credited at N+1, N+2, …
   without re-review — the exact false-positive class this plan closes, on the edit path. **Disposition:
   fixed** — the noise sidecar became a proper **currency ledger** recording
   `(reviewed_commit_sha, updated_at)` per credited comment, refreshed on each credit; the edit arm now
   measures a *fresh* edit against the recorded `updated_at` ("edited since last credited"), so an edit
   at N credits N only. `_reviewed_at_merge_candidate` reads the single ledger (dropping the
   findings-SHA source, which could not carry `updated_at`), so stored and dropped comments are treated
   identically. Pinned by `test_edit_at_one_commit_does_not_credit_a_later_commit`; the mutation proof
   and all idempotence/staleness tests still hold. This was a genuine defect the plan's Goal demands
   closed, found by the required reviewer — the exact case the pre-merge barrier exists to surface.

## Reviewer participation

Population derived from the registry `author_login` of each
`automatic-review/standards/{bot_kind}.md`: `coderabbit`→`coderabbitai`, `pr-agent`→`cuioss-review-bot`,
`sourcery`→`sourcery-ai`. This repo's settled config makes **`pr-agent` the sole REQUIRED bot**
(`coderabbit`, `sourcery` optional). Verdicts from the stored comment bodies on PR #1141:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` (pr-agent, **required**) | `reviewed` | Posted "PR Reviewer Guide 🔍" with a real finding ("Bypassed SHA Currency Check") — a review artifact against the diff. |
| `coderabbitai` (coderabbit, optional) | `rate-limited` | Posted only "Review limit reached … Next review available in 33 minutes" (awaitable window). |
| `sourcery-ai` (sourcery, optional) | `rate-limited` | Posted only "you have reached your weekly rate limit of 500000 diff characters" (weekly quota). |

**Coverage: 1 of 3 reviewed; the REQUIRED bot (`pr-agent`) reviewed, so the required quorum is
satisfied.** The two optional bots are rate-limited (routine, outside our control; optional silence
does not block). PR-Agent's real finding ("Bypassed SHA Currency Check") was fixed in `ddd486c` and
acknowledged on the thread; the operator then merged the PR once `verify` went green, so no further
re-review round was required.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not expose
  a per-run token total to the model).
- **Wall-clock:** ~1h from branch-publish to PR-open, plus the review cycle.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  per-task billing boundary — a boundary this interactive session does not share. No comparable figure
  is available, so none is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — six skills named above, all via the bundle-path route. |
| 2 Branch | Done — harness-assigned `claude/participation-superseded-commit-uo7k92`, kept as-is, on `origin`. **Branch form: harness-assigned.** |
| 3 Plan directory | Done — `doc/plans/review-apparatus/010-.../plan.md` exists and opens with the first-instruction block (present on arrival; no repair needed). |
| 4 Implement | Done — deliverables addressed; every commit carries the `Co-Authored-By: Claude` trailer, no "Generated with" footer. |
| 4 Per-commit gate | Done — every source-touching commit was preceded by a `total_issues: 0` `./pw quality-gate`. |
| 4 Pushed | Done — no unpushed commit (each commit pushed immediately). |
| 5 Build gate | Done — `*.py` changed → full `./pw verify` → SUCCESS, 18689 passed / 14 skipped (re-verified after each finding fix). |
| 6 Verification sub-agent | Done — findings + dispositions recorded (§ Findings). |
| 7 PR cycle | Done — PR #1141; both comment surfaces read; PR-Agent's finding fixed + replied; inline review-thread surface empty. |
| 8 Merge gate | **MERGED** — auto-merge (armed `--squash`) fired when `verify / verify` concluded green; confirmed `state: MERGED`, `merged_by: cuioss-oliver`, squash commit `50f67ed`. The `license/cla` check was **not** required (see the correction note); an earlier revision wrongly recorded this row as blocked. |
| 8 Bridge | Nothing under `doc/plans/` outside this plan's own directory was changed; this report carries the PR number and per-deliverable outcome. |
| 9 This check | Appended here. |
| 9 What have we learned | Below. |

**GitHub access path:** the GitHub MCP server (the cloud path). **Branch form:** harness-assigned.
**Local sync owed:** yes — this plan edited `marketplace/bundles/**`, so a local `/sync-plugin-cache`
is owed for whoever picks the work up locally (the cloud lane cannot sync: it reads the git-ignored
`target/` and writes `~/.claude/`, neither of which it has).

## What have we learned (Step 9)

> **Mitigated by plan `450-cloud-lane-assumes-local-runtime-affordances`.** The lesson recorded here and
> in § "Why the CLA was falsely read as a merge blocker" — derive a blocked PR's blocker from
> (required checks ∩ non-green checks), and never promote a visible-but-non-required pending status to
> "the blocker" in an operator disclosure — is now written into Step 8 condition 1 by that plan's **D3**.
> (The required-vs-decorative distinction the run also relied on had already landed via plan `030`.)

**One candidate refinement, with evidence from this run — recorded, not shipped.** The evidence is the
mistake in § "Why the CLA was falsely read as a merge blocker": this run read a PR's
`mergeable_state: blocked` and attributed it to a *salient but non-required* pending check (`license/cla`)
rather than to the actually-required `verify / verify` that was still running. The lane's Step 8 says
"all checks are green — verify against actual check state," but it does not say to derive *which* check
blocks from **(repo required checks) ∩ (non-green checks)**, nor does it warn against promoting a visible
non-required pending status to "the blocker" in an operator disclosure. Adding that one sentence to Step
8 would have prevented the wrong "partial — blocked on CLA" outcome. It is **recorded, not shipped**: a
contract amendment needs operator approval and its own `chore/` PR, and the earlier
candidate-refinement (a "required check blocked on a human action") was itself premised on the same false
belief and is withdrawn. The honest, run-produced lesson is the required∩non-green derivation above.

## Why the CLA was falsely read as a merge blocker

The error and its correction, recorded because a misread merge gate is exactly the kind of
"claim not read back from the source" this lane exists to prevent.

**What I claimed:** the run was "partial — merge blocked on `license/cla` (`not_signed`), an operator
signature this session cannot perform," and I armed auto-merge as a hand-off.

**What was actually true:** the `license/cla` status is **informational, not a required check** on this
repository. The PR's `mergeable_state: blocked` was caused by the **still-running `verify / verify`**
(the one genuinely-required check), not by the CLA. When `verify / verify` concluded green at
15:59, the PR auto-merged immediately — the CLA still showing `not_signed` and not blocking anything.

**How the mistaken inference happened — three compounding mistakes:**

1. **I equated `mergeable_state: blocked` with a specific named blocker without reading the repo's
   required-checks configuration.** `blocked` only says *something* required is unsatisfied; it does not
   say *which*. The correct move was to enumerate the repo's *required* status checks and intersect
   with the non-green ones — I did not.
2. **I let the most *salient* pending status stand in for the *required* one.** The CLA posted a
   prominent "not signed" comment and a `pending` commit status; `verify / verify` was quietly
   `in_progress`. I reached for the loud signal (CLA) over the quiet one (verify), which is precisely
   backwards — a `pending` non-required check is cosmetic, an `in_progress` required check is the gate.
3. **I treated a plausible inference as a confirmed fact in an operator-facing disclosure.** The lane's
   own rule — "a claim is not an outcome; merge state and check state are read back from the actual
   source" — applies to *why* a merge is blocked just as much as to *whether* it merged. I asserted the
   CLA was the blocker without the read that would have refuted it.

**The lesson (also fed to Step 9's "what have we learned"):** when a PR is `blocked`, derive the
blocker from the intersection of (repo required checks) ∩ (non-green checks), and never promote a
visible-but-non-required pending status to "the blocker" in an operator disclosure. The one real
follow-up item below stands; the CLA "block" was never real.

## Residue

- **Local `/sync-plugin-cache` owed** (bundle edits; see Contract check). This is the only open item:
  the merge landed on `main`, but the cloud lane cannot sync the plugin cache (it reads the git-ignored
  `target/` and writes `~/.claude/`), so whoever picks the work up locally runs `/sync-plugin-cache`.
- **D3 trigger-B wiring** — the `declined` observation is populated end-to-end only on the trigger-A
  (post-rebase) path; a FIND-step trigger-B loop-back decline is not yet fed into `--declined-bots`.
  Disclosed as a bounded follow-up, not a gap in the plan's D3 concrete defect (the trigger-A
  `head_sha_verified` bit, which is closed).
- **PR-Agent re-review of the fix commit** — at report finalization, PR-Agent had not yet re-reviewed
  `ddd486c` (its Guide still reflects the pre-fix HEAD). The fix is covered by the new regression test
  and the local + PR CI; a fresh PR-Agent pass, if it lands, is monitored via the auto-merge arming.
