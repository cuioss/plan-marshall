envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=landing
created=2026-09-07T09:44:35Z

# Landing — PLAN-TRUTH-099

`queue --add-row` shipped. The orchestrator's epic queue now has a safe single-row append.

- **PR**: #1434, merged as `3ca7e2c8f8a1eb0d86e681f34b1933aed164106b`
- **Plan id**: `the-ledger-has-no-safe-single-row-append`
- **Branch**: `feature/the-ledger-has-no-safe-single-row-append` (deleted)
- **Verify**: green, 24598 tests
- **Superseded PR**: #1424, closed unmerged (see Review below)

## What landed

**D1 — `queue --add-row`.** Appends one row inside the same shared `rmw_json` critical section the existing write forms use, with the duplicate-id check evaluated against the fresh in-lock queue rather than a pre-lock snapshot. Refuses a duplicate `PLAN-NN` (`duplicate_plan_id`) rather than appending a second row for the same logical plan, since `--transition` and `--set-row` both locate by id. Carries a three-valued spec-presence probe holding `absent` (a measured negative) apart from `unlistable` (no observation), and a three-valued status-document probe holding an absent `plans` key (seeded) apart from a present non-list value (`invalid_status_document`, nothing written).

**D2 — a matched concurrency control.** Both arms share one harness: each writer takes its own pre-lock read, blocks on a `threading.Barrier` until its peers have read, then commits. The arms differ in exactly one dimension — the safe arm calls the production `_append_plan_row`, the unsafe arm commits `[*stale, row]` through the same critical section. A serialized harness fails at the barrier rather than passing green.

**D3** — the canonical invocation surface in `plan-orchestrator/SKILL.md`.

**D4** — the three-write-form boundary across `orchestration-model.md`, `workflow/analyze.md` and `templates/landing-analysis.md`: bulk seed at `decompose`, single append at stage, single mutate at reconcile.

## Two spec premises refuted at HEAD

Both were operator-resolved during outline, not worked around silently:

- The spec asked for the boundary "alongside the existing `--set-row` boundary sentence" in `orchestration-model.md`. A complete-coverage sweep found no `--set-row` mention there; the real carriers were `analyze.md` and `landing-analysis.md`. Resolution: new subsection in the standard **plus** both real carriers.
- The spec's D4 ledger-append item was already satisfied (`specs_without_row_count: 0`) **and** prohibited by the Ledger Write-Boundary. Dropped.

## Residual defects for the epic — NOT fixed here

Four items found during this run that belong to other components:

1. **`github_re_review.py` — a review that happened is disposed as declined.** `_references_head_sha` is called only at `github_re_review.py:571`, in the review branch. A bot that publishes its reviewed SHA in the **comment body** — `cuioss-review-bot`'s `Review updated until commit <sha>` line is a stable structured form — can therefore never reach `head_sha_verified: true`, and every such re-review disposes as `declined`. For a required bot the only remedies are demotion to `optional_bots` or an operator merge-authorization, so a real review gets waived. Symptom already documented at `workflow-integration-github/SKILL.md:39`. Remedy: declare a body-side SHA pattern in `automatic-review/standards/cuioss-review-bot.md` and apply the predicate on the comment path.

2. **`coderabbit.md` — an ETA that is stated is reported as absent.** None of the three `rate_limit_eta_patterns` (coderabbit.md:75-78) matches the live wording `Next included review available in N minutes`; all require `before requesting another review` or `limit resets`. The producer emits `eta: ""` for a notice that plainly states one, and the contract then tells callers to read the empty result as "no ETA stated".

3. **`triage.md` documents a value the validator rejects.** `triage.md:191` prescribes `deliverable: 0` for fix tasks; `_tasks_core.py:759` rejects it for any non-`holistic` origin as "Missing required field" — a falsy-vs-absent bug. This run only proceeded by ignoring the documented value.

4. **The queue-write boundary is prose-enforced, not code-enforced.** A generic `manage-status update-field --field plans` remains reachable by any caller. Raised by CodeRabbit on **both** PRs (`45310f`, `4f0716`) and held `taken_into_account` both times — the wide remedy contradicts the boundary this plan settles (the bulk write is sanctioned for `decompose`'s seed-from-nothing) and would add a `manage-status` API verb reaching `decompose`. Held twice now without a home; this is the epic's own enforce-in-code archetype (cf. `d94c92858`) and needs an epic item rather than a third hold.

## Review

CodeRabbit reviewed three times and raised 7 actionable findings; 6 were fixed, 1 held (item 4 above). `cuioss-review-bot` participated on every head, always empty-finding. `sourcery` is optional and hard-quota'd.

Two things worth carrying forward:

- **4 of the 6 findings on #1434 were second-order** — defects in this plan's own repairs of its #1424 findings. `1f08b2` re-introduced, one level above, the exact absent-vs-present state-fold that `b339df`'s fix removed one level below.
- **PR #1424 stalled and had to be replaced.** Six explicit `@coderabbitai review` triggers over ~12 hours and five 90-minute waits produced no further review; every trigger re-armed the rate window. Closing it and opening #1434 obtained a full review in under 15 minutes. ⚠ The tempting explanation — free-OSS tier on #1424 vs Team plan on #1434 — is **refuted**: all three persisted review envelopes on both PRs record `Plan: Team` with the same `0 remain after this review` footer. The mechanism is not identified; only the remedy is known.

## Cost

3h54m worked / 41h50m wall / 5.2M dispatched tokens / 138M billing-weighted.

⚠ **Finalize was the cost centre, not execute**: 3.60M of 5.22M dispatched tokens (69%), against 0.41M for execute. Three loop-backs drove it. The `single_module+feature` anchor is 1.6M.
