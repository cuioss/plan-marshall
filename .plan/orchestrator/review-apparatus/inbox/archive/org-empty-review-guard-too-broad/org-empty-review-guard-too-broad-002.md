envelope_version=1
sender_type=plan
sender_id=org-empty-review-guard-too-broad
epic=review-apparatus
kind=landing
created=2026-09-28T17:31:42Z

# PLAN-PR-002 landing: org empty-review guard, residual R3 closed

**Plan:** `org-empty-review-guard-too-broad`, delivered entirely in `cuioss/cuioss-organization`. The plan-marshall host diff is empty, so finalize here is bookkeeping only.

## Shipped (verified from PR state and tags)

- **cuioss-organization#297** (merge `f18ae7f`). The `changes` pre-job of `reusable-cuioss-review-bot.yml` now runs `workflow-scripts/classify-review-diff.py` inside the reviewer's pinned PR-Agent digest. The script applies the runner's own settings and `GithubProvider.get_diff_files()` filter chain, and outputs `reviewable`:
  - `false` for zero files (c) or zero survivors (d);
  - `true` with a `::notice::` on any resolution failure (fail-open).
  - The gate step is byte-for-byte unchanged. The `EXCLUDED` block moves (c) and (d) to "skipped upstream by `changes`". `dorny/paths-filter` and `non_plan` are removed.
- **cuioss-organization#298** (`f56f1f9`) prepared the release. **v0.32.0** is tagged (`3e70f35`).
- **22/22 consumer pin-bump PRs are merged** (plan-marshall #1638, API-Sheriff #362, TokenSheriff #764, …). On API-Sheriff #362 both `review / changes` and `review / review` were skipped by the org bot-skip terms.
- **The live check passed** on plan-marshall #1651, run `36423408452`:
  - log line: `classify-review-diff: reviewable=true survivors=65 settings=defaults+global`;
  - no fail-open notice;
  - `review / review` = success.
- **The correct skip was also observed live** on #1639, which changed only `.plan/**` and `uv.lock`: `changes` succeeded and `review` was skipped.

## Spec divergences (operator-approved)

- **Q1: the root-cause claim in the spec was wrong.** API-Sheriff#340 was `.gitignore` plus `.plan/**` files, and `.gitignore` was removed by the runner's invalid-extension filter, not by the `[ignore]` globs. The skip therefore mirrors the runner's full filter chain, not just the `[ignore]` globs.
- **Q2:** the classifier runs the runner's own code inside the pinned image. No filter list is copied.
- **Q3:** the operator dispatched `release.yml` by hand.
- **Q4:** the live check used the next real plan-marshall PR (#1651).

## Findings for the epic (filed as lessons)

- **2026-09-27-07-001:** the transition's mailbox probe reports `not_orchestrated` for this plan's spec-pointer `source_id`, while `inbox detect` reports `orchestrated`.
- **2026-09-27-07-002:** `ci checks logs` returns nothing for successful runs.
- **2026-09-28-17-001:** `ci checks status` omitted the review workflow's nested checks on #1651, which looked like "the reviewer never ran". A read-only `gh` call, authorized by the operator for this one case, was needed to observe the run.
- **2026-09-27-07-003:** the phase-3-outline leaf self-transitions to 4-plan before the Q-Gate and the user review.
- **2026-09-27-07-004:** the strict handshake is unusable while concurrent orchestrator sessions write `.plan/orchestrator/**`.
- **Accepted residual R1 is unchanged:** a `synchronize` run in which every model call failed remains ungated. `handle_push_trigger` is still off.
