# PLAN-PR-002: Org empty-review guard asserts a precondition its own config denies

> ⛔⛔ **RE-SCOPED 2026-09-26 (orchestrator re-grounding against `cuioss-organization` `origin/main` @ `2a2fa2e`).
> This section supersedes § Objective and § Deliverables below; everything else stays as evidence.**
>
> **What already shipped:** cuioss-organization#235 (merged 2026-08-09, `06e2591`), read first-party. It
> narrowed the guard to the runner's reviewed actions (`opened` / `reopened` / `ready_for_review` /
> `review_requested`), kept `exit 1` byte-for-byte, enumerated the excluded populations in-file, and fanned out
> through the normal pin bump. Original D1 is done within its accepted residual R1, and so are D3 and most of D2.
> The file has since been renamed to `.github/workflows/reusable-cuioss-review-bot.yml` (#288), and the guard now
> reads `steps.review_assembled.outputs.review || steps.review_central.outputs.review`.
>
> **What is still open (the ONLY scope of this plan): #235's residual R3.** The in-file `EXCLUDED` block's
> populations **(c) a PR with no files** and **(d) an empty diff after filtering** sit on *retained* actions,
> so the gate still fails them. That is a live false failure. It was observed 2026-09-22 on
> `cuioss/API-Sheriff#340` (runs `35709715234`, `35716363715`): every changed file matched the reviewer's
> `[ignore]` globs, `pr_reviewer` logged `Empty diff for PR`, `REVIEW_OUTPUT` came out empty, and the
> "Verify the reviewer actually produced a review" step failed. #235 declared R3 unclosable because the runner
> exposes no state that tells the cases apart. ⭐ **That premise is now REFUTED by the tree's own precedent:**
> #280's `changes` job already computes the diff against a path filter **before** the `review` job runs,
> and skips the whole job for a `.plan/**`-only diff. The discriminator can be computed from the PR's file list,
> not read from runner state.
>
> **Re-scoped deliverables:**
>
> - **R3-D1:** Generalise the `changes` pre-job so that "no files" (c), and "every changed file matches the
>   reviewer's effective `[ignore]` globs" (d), skip the `review` job the way `.plan`-only already does. Read
>   the globs from the same source the runner uses (the central `cuioss-review-bot` settings plus repo
>   overrides), never from a second hand-maintained list. If the effective globs cannot be resolved,
>   **FAIL OPEN** into the review, as `non_plan` already does, so that an unresolvable filter never skips a
>   real review.
> - **R3-D2:** The gate step itself stays untouched: `exit 1` on empty output on every run that reaches it.
>   ⛔ The prohibited remedy (downgrading to `::warning`) still binds. Update the `EXCLUDED` block so (c)
>   and (d) move from "retained, gated" to "skipped upstream by `changes`", and state why.
> - **R3-D3:** Regression tests in `test/workflow/` that pin: an ignore-only diff skips `review`; a mixed diff
>   runs it; an unresolvable glob source fails open; the gate's `exit 1` is intact. Use API-Sheriff#340's
>   file list as the positive fixture. Update `docs/Workflows.adoc` in lockstep, then release and fan out
>   by the normal pin bump (~21 consumers, blast radius stated in the PR body).
>
> **Stale preconditions below, corrected:** there IS a local checkout (`/Users/oliver/git/cuioss-organization`,
> so `references.json`'s `local_checkout: null` is out of date); the `synchronize`-trigger framing is moot
> (`#1048` reverted); R1 remains operator-accepted. **Not affected by the PM-MCP supersession (2026-09-26):**
> the surface is foreign org CI, which PM-MCP does not replace.

epic: review-apparatus
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`cuioss-organization`'s `reusable-pr-agent-review.yml` fails the review job when `REVIEW_OUTPUT`
is empty. That guard exists for a real and important reason — the runner exits 0 when every model
call fails, so without it "reviewed, found nothing" is indistinguishable from "never reviewed", an
ambiguity that already produced a real misread on plan-marshall#1024. But the runner ALSO
legitimately produces no output on unchanged-SHA, merge-commit and bot-commit pushes. The guard
therefore fires on cases its own configuration creates. Narrow it so it distinguishes those two
populations, keeping it fail-closed for the population it was written for.

This must land BEFORE `handle_push_trigger` is enabled, not after: a broad guard plus push
triggers fans a wall of false job failures across ~21 consumer repos.

## Provenance — this spec absorbed `truthful-signals` PLAN-116 Defect B

PLAN-116 was released to this epic on 2026-07-30 and **split**; its Defect B is this plan. Three
things fold in that are NOT in the handover summary:

- ⚠ **Do NOT scope against the reverted framing.** PLAN-116 records that `#1048` was **REVERTED by
  `#1053`**, so the specific synchronize-trigger framing of this defect is MOOT. The underlying
  observation — a guard asserting a precondition its own configuration cannot satisfy — is retained
  and **must be re-established at HEAD before scoping**. A plan that scopes against the reverted
  framing implements against a world that no longer exists.
- **The legitimately-empty population has a named source**: the runner returns no output on
  unchanged-SHA, merge-commit and bot-commit pushes at `github_action_runner.py:128-146` (line
  reference OBSERVED as supplied; **verify by symbol**, it is a pinned-image file).
- **The full ordered objective is two steps, not one**: narrow the guard to the events pr-agent
  actually reviews, **THEN** set `handle_push_trigger` + `push_commands = ["/review"]`. Enabling the
  trigger first reproduces the failure on a subset instead of on all of them — which is worse, because
  a partial reproduction reads as a partial success.
- **Sibling slices of the same split** (do not absorb them): PLAN-PR-001 (Defect A), PLAN-PR-005
  (C+E), PLAN-PR-006 (D), PLAN-PR-007 (F).

## Deliverables

1. The empty-`REVIEW_OUTPUT` condition distinguishes "the runner had nothing to review" (skip /
   neutral) from "the runner attempted a review and produced nothing" (fail, unchanged). The
   discriminator is derived from observable runner state, not from re-deriving the push reason.
2. The legitimately-empty population is enumerated in the workflow itself with its reasoning, so a
   later reader does not re-broaden the guard: at minimum unchanged-SHA pushes, merge commits,
   bot-authored commits, **and a PR whose entire diff resolves to files the reviewer's own `ignore`
   config filters out** (2026-09-22 fold, evidence below) — `_get_diff_files` legitimately returns
   zero files, `pr_reviewer._prepare_prediction` logs `Empty diff for PR` at WARNING, and
   `REVIEW_OUTPUT` is empty through no failure of the runner at all.
3. Consumer release fan-out handled per the org's normal release path, with the ~21-repo blast
   radius acknowledged explicitly in the PR body.

## Claim Labels

- OBSERVED: the guard exists and fails the job on empty `REVIEW_OUTPUT`, and the runner produces
  nothing on unchanged-SHA / merge-commit / bot-commit pushes. Recorded at epic init from the live
  org workflow.
- OBSERVED: a change here fans out to ~21 consumer repos through an org release tag — unlike the
  two config repos, which take effect on the next review with no release step
  (`pr-agent-settings` is fetched per invocation in CI mode, with no 15-minute webhook cache).
- OBSERVED: the org skip rules live as job-level `if:` guards in THIS file, because
  `ignore_pr_labels` / `_authors` / `_title` / `_{source,target}_branches` are dead config in
  GitHub Action mode — they are consumed only by `should_process_pr_logic()`, which exists in the
  webhook servers and not in `github_action_runner.py`. Any narrowing implemented via
  `ignore_pr_*` would silently do nothing.
- HYPOTHESIS: `handle_push_trigger` is currently DISABLED — confirm/refute by reading the trigger
  block of `.github/workflows/reusable-pr-agent-review.yml` at the org default branch
  (verify-at-outline). This is an asserted-absence claim and carries the higher risk: if push
  triggers are already live, the false-failure fan-out is not a future risk but a present one, and
  the plan's urgency and rollout order both change.
- OBSERVED (folded, provenance above): `#1048` was reverted by `#1053`, so the synchronize-trigger
  framing is moot and the defect must be re-established at HEAD. ⚠ **This is the one claim in this
  spec most likely to mislead if taken at face value** — it is a statement about what is NO LONGER
  true, and the ~21-repo blast radius makes scoping against a stale framing expensive.
- HYPOTHESIS: the runner exposes enough state to discriminate the two empty populations without
  re-deriving the push reason in YAML — confirm/refute against the runner's own output/exit
  contract in the pinned PR-Agent image (verify-at-outline). If refuted, the discriminator must be
  designed rather than read, and this plan should be re-scoped before implementation.
- Verify-first clause: the org repo has NO local checkout (see Dependencies). Every claim above was
  recorded from a live read at epic init and MUST be re-read against the org default branch at
  outline — a workflow file is the kind of artifact that changes without anyone telling this epic.
- OBSERVED (2026-09-22 fold, corroborated against real logs, not the pasted diagnosis): a
  same-day parallel-session paste claimed `cuioss/API-Sheriff` PR #340's `review / review` job
  failed org-wide with `google-github-actions/auth produced no credentials file path` /
  `organization variable GCP_PROJECT_ID is not set`. **That diagnosis is CONTRADICTED by the actual
  run logs** (`ci checks logs --run-id 35709715234` and `--run-id 35716363715`, fetched against the
  real `cuioss/API-Sheriff` checkout): both runs show `Created credentials file at ...` followed by
  normal `pr_agent` execution through `Applying repo settings` and into `Reviewing PR: ...` — the
  quoted `::error::` lines are the `##[group]Run ...` step SOURCE echo GitHub Actions always prints
  before executing a `run:` block, not raised errors; auth and `GCP_PROJECT_ID` both succeeded in
  both runs. The REAL failure in both is `Empty diff for PR: https://api.github.com/repos/cuioss/API-Sheriff/pulls/340`
  at `pr_reviewer.py:211` — PR #340's changed files were entirely `.gitignore`/ignore-pattern
  entries (see `_get_diff_files` `Filtered out [ignore] files`), so `_prepare_prediction` legitimately
  produced no prediction, `REVIEW_OUTPUT` came out empty, and the workflow's own "Verify the reviewer
  actually produced a review" step failed loud — this epic's own guard-too-broad defect, a NEW
  instance of the same population this plan already targets, not an org Vertex/GCP outage. Confirmed
  via `.github/workflows/pr-agent.yml` in the local `API-Sheriff` checkout: it `uses:
  cuioss/cuioss-organization/.github/workflows/reusable-pr-agent-review.yml@...` — the SAME file
  this spec's Expected Surface already names, so this fold adds NO new surface. Do not re-open a
  GCP org-variable investigation on the strength of the paste alone; the org-variable claim is
  refuted, not merely unverified.

## Expected Surface

- OBSERVED: `cuioss-organization` → `.github/workflows/reusable-pr-agent-review.yml` — the
  empty-`REVIEW_OUTPUT` guard step and the job-level `if:` guards.
- HYPOTHESIS: `cuioss-organization` → `docs/automatic-review/pr-agent.md` — a doc update if that
  document states the guard's semantics (verify-at-outline).
- OBSERVED (absence): NO file inside `plan-marshall` is touched by this plan. This is what makes it
  the one candidate second stream if `parallelization_scope` is ever raised above 1.

## Dependencies and Sequencing

- Depends on: none in-epic. ⚠ **But it has a setup precondition no other plan in this epic has:**
  `references.json` records `local_checkout: null` for `cuioss-organization`. The plan's first act
  is obtaining a checkout; it cannot assume a tree exists.
- Overlaps with: nothing. Disjoint by construction from every plan-marshall file and from both
  config repos.
- Adjacent to: `pr-agent-settings` (WS-03). The two are frequently confused because the skip rules
  a reader expects to find in `pr-agent-settings` actually live in this workflow. Do not move them.
- ⛔ **PROHIBITED remedy** — do not narrow the guard by downgrading empty-review to a warning. The
  runner exits 0 when every model call fails; this guard is the only thing separating "reviewed,
  found nothing" from "never reviewed". Downgrading it re-creates the exact ambiguity that cost a
  real misread on plan-marshall#1024.
- Use `git -C {checkout}` and the CI abstraction's `--project-dir` for this repo — it is not
  covered by plan-marshall's `.plan/` tooling, and `gh` is never called directly.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-002-org-empty-review-guard-too-broad.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
