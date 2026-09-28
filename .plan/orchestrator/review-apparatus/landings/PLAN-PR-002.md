# Landing Analysis: PLAN-PR-002 — org empty-review guard too broad

epic: review-apparatus
workstream: WS-02
pr: cuioss/cuioss-organization#235 — https://github.com/cuioss/cuioss-organization/pull/235

> Landing record written by the `analyze` verb from inbox message
> `org-empty-review-guard-too-broad-001.md` (2026-08-08), after corroborating its claims
> against ground truth. A pasted claim is a lead, never a fact.

## ✅ SHIPPED 2026-09-28: second run, residual R3 closed (inbox `org-empty-review-guard-too-broad-002.md`)

Everything above this section records the FIRST run: #235, which merged 2026-08-09 after that run's lifecycle
ended. This section records the re-scoped second run, which closes #235's residual R3. The spec's
`RE-SCOPED 2026-09-26` block describes that scope.

**Corroborated first-party (2026-09-28), not taken from the message:**

| Claim | Verdict | Evidence |
|---|---|---|
| cuioss-organization#297 merged at `f18ae7f` | corroborated | `ci --project-dir cuioss-organization pr view --pr-number 297`: `state: merged`, merge `f18ae7f6b9b4`, which is an ancestor of `origin/main` |
| #298 prepared the release; v0.32.0 is tagged | corroborated | #298 merged `f56f1f9`; the tag object `3e70f35` points at commit `5fb6e07` ("pin internal action references for v0.32.0"), which is on `origin/main` |
| The `changes` pre-job classifies (c) and (d), fails open, and leaves the gate unchanged | corroborated | `origin/main:.github/workflows/reusable-cuioss-review-bot.yml`: `reviewable` output (c at :156–160, classifier at :190); `review` gated on `needs.changes.outputs.reviewable != 'false'` (fail-open, :232–245); the `EXCLUDED` block moves (c)/(d) to "skipped upstream by `changes`" (:547–563); `exit 1` intact (:590). `workflow-scripts/classify-review-diff.py` is present |
| 22/22 consumer pin-bump PRs merged; live check on plan-marshall #1651 run `36423408452`; live skip on #1639 | unverifiable (not re-read) | The plan's own report. plan-marshall `4af92f73a` ("update cuioss-organization workflows to v0.34.0", #1650) shows consumers have already moved past v0.32.0 |

**Deliverable fidelity vs the re-scoped spec:**

- **R3-D1** is shipped, with an operator-approved divergence: the skip mirrors the runner's FULL diff-file filter
  chain, run inside the pinned image, rather than only the `[ignore]` globs.
- **R3-D2** is shipped: the gate is unchanged and the `EXCLUDED` block is updated.
- **R3-D3** is shipped: tests, docs, release and fan-out.

**⛔ The spec's root-cause claim was WRONG, and the plan caught it (Q1).** API-Sheriff#340's diff was
`.gitignore` plus `.plan/**` files. The runner dropped `.gitignore` through its invalid-extension filter, not
through the `[ignore]` globs. A glob-only skip would therefore have missed the very case that motivated the
plan. This is the epic's recurring *diagnosis-by-paste* archetype: the 2026-09-22 fold corroborated the failure
itself against real logs, but not its mechanism.

**⚠ The landing is prose-only.** `inbox landing-check` reports `complete: false` with all 9 required
`landing-facts` keys missing. It is recorded as an Open Defect below; the drain continues.

**Residual R1 is unchanged** and remains operator-accepted: a `synchronize` run whose every model call failed
stays ungated, and `handle_push_trigger` is still off.

**Lessons the plan filed** (global corpus, routed by the lessons flow, not absorbed here):

- `2026-09-27-07-001`: the transition mailbox probe says `not_orchestrated` where `inbox detect` says
  `orchestrated`.
- `2026-09-27-07-002`: `ci checks logs` returns nothing for successful runs.
- `2026-09-28-17-001`: `ci checks status` omits nested review-workflow checks, so the reviewer looks like it
  never ran.
- `2026-09-27-07-003`: the phase-3-outline leaf self-transitions before the Q-Gate.
- `2026-09-27-07-004`: the strict handshake is unusable under concurrent orchestrator writes.

## ⛔⛔ THIS IS NOT A SHIP — THE DELIVERABLE PR IS OPEN AND UNMERGED

The message is `kind: landing` and reads as a completion report. **Ground truth contradicts the ship
semantics**, and the row was therefore NOT transitioned to `shipped`.

| Claim | Verdict | Evidence |
|---|---|---|
| Shipped as `cuioss/cuioss-organization` PR #235 | **PARTIALLY CORROBORATED** — the PR exists and matches, but is **OPEN** | `ci --project-dir /Users/oliver/git/cuioss-organization pr view --pr-number 235` → `state: open`, `review_decision: none`, `mergeable: unknown`, head `fix/pr-agent-empty-review-guard-scope`, base `main`, title `fix(pr-agent): narrow empty-review guard to the runner's reviewed actions` |
| The plan's own local lifecycle finished | **CORROBORATED** | `manage-status list` no longer carries `org-empty-review-guard-too-broad` |
| No plan-marshall PR exists and none should be expected | **CORROBORATED as consistent** | The host worktree diff was empty by design; no plan-marshall PR was created |

⇒ **The plan lifecycle has ended while its only deliverable sits unmerged in a foreign repo.** The
local lifecycle's completion is NOT evidence that the work landed — the two are decoupled the moment
the deliverable lives outside the host repo. This is the epic's own confident-signal-hides-a-caveat
theme reaching the ledger itself: a `kind: landing` message is the plan's *claim* of completion, and
nothing in the message channel verifies it.

⭐ **Recorded as a method rule for every future cross-repo plan: a landing message from a plan whose
deliverable is in a foreign repo MUST be corroborated against the FOREIGN PR's state.** The local
oracle (absence from `manage-status list`) proves only that the plan stopped running.

## ⛔ Operator decision 2026-08-08 — "merge #235 first, then mark shipped" — BLOCKED at the readiness check

The operator chose to resolve the discrepancy at the source. The orchestrator ran the readiness check
and **did not merge**, because the PR is not merge-ready:

- **All 12 checks green** (`checks status --pr-number 235`: CodeQL, 3× Python Verify jobs ×2 runs,
  dependency-review, license/cla, CodeRabbit).
- **5 unresolved comments, THREE of them actionable CodeRabbit findings on this diff**
  (`pr comments --pr-number 235 --unresolved-only`):
  1. ⛔ **Major** — the `pr_actions` allow-list this PR added duplicates a value that is *configurable*
     from `cuioss/pr-agent-settings` (`.pr_agent.toml` / env). Nothing fails when the two diverge.
     Asks for the contract to be stated and a regression test added.
  2. ⚠ **Minor** — `review_requested` is admitted by the guard and documented, but **no caller trigger
     sends it**: the `docs/Workflows.adoc` Basic Usage template subscribes to `opened`, `reopened`,
     `ready_for_review` only. Either the entry comes out or the template gains it.
  3. ⚠ **Nitpick, and it is a vacuous-guard instance in the very test this PR added** —
     `test_if_allow_lists_every_reviewed_action` asserts **membership, not equality**, so adding
     `"synchronize"` to the workflow keeps the whole suite green. That is exactly the population this
     PR excludes on purpose, so the test cannot fail for the case it exists to protect.
- `sourcery-ai` declined on its weekly 500,000-diff-character quota. **Optional bot, provenance
  `answered` — does not block** (and per `PLAN-PR-021` this must not be reported as a shortfall).

⛔⛔ **Merging now would land a PR with two actionable findings unaddressed behind an all-green check
surface — the exact false-green shape this epic exists to close.** Finding 3 makes it sharper: the
guard test shipped by a plan about a too-broad guard is itself too weak to catch the broadening.

⇒ **Resolving the findings is source work in a foreign repo — plan work, prohibited to the orchestrator
by the prime directive.** The merge is therefore owed to a plan, not to this session. The operator's
decision stands; only its precondition is unmet.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| Narrow the `pull_request` arm of the empty-review guard to the runner's own reviewed actions | shipped-modified, **unmerged** | PR #235, 3 files: `.github/workflows/reusable-pr-agent-review.yml`, `docs/Workflows.adoc`, `test/workflow/test_pr_agent_review_guard.py`; guard now mirrors `GITHUB_ACTION_CONFIG.PR_ACTIONS` via a `contains(fromJSON(...), github.event.action)` allow-list |
| Leave the `issue_comment` + `/review` arm and the `exit 1` step body untouched | shipped-as-specified (per message) | Message states the `exit 1` on empty `REVIEW_OUTPUT` is byte-for-byte unchanged and was never downgraded to a warning (the PROHIBITED remedy) |
| Doc moved in lockstep | shipped-as-specified (per message) | `docs/Workflows.adoc` § PR Agent Review → Verification |
| Enumerate legitimately-empty populations | added-unplanned | A new `EXCLUDED` comment block naming each excluded population and its reason |

⚠ Per-file diff content was NOT re-read by this analysis — the PR's existence, state, branch, title and
file count were corroborated; the *content* verdicts above are the plan's own report. They are
HYPOTHESIS-grade and are settled by reading #235's diff, which is owed if this plan's work is ever
re-scoped.

## Four spec claims the plan REFUTED at outline

Recorded because two of them change the framing for sibling plans:

1. **The defect is LATENT, not live.** No caller subscribes to an action outside the allow-list today,
   so the gate never evaluates on the push population. The spec's sequencing insistence was right; its
   urgency framing was not.
2. ⛔⛔ **The spec's own "synchronize framing is moot" exclusion is WRONG, and any sibling carrying it
   forward must DROP it.** `#1053` reverted a PR, not the mechanism: `handle_push_trigger` is reachable
   ONLY from the `pull_request` branch under `action == "synchronize"`. Honouring the exclusion
   literally would have produced a fix that cannot be enabled.
3. **The runner exposes NO discriminator.** `github_action_output(data, 'review')` is called from
   `PRReviewer._prepare_pr_review()`, reachable only after a successful prediction — so every skip path,
   legitimate or failed, leaves `outputs.review` empty. The discriminator had to come from the runner's
   ACTION ALLOW-LIST, not from runner output.
4. **`docs/automatic-review/pr-agent.md` does not document the guard.** The hypothesised file was out of
   scope.

⭐ The spec's verify-first clause fired exactly as designed on claim 3 — "if refuted, re-scope before
implementation" — and the plan re-scoped rather than proceeding. That is the contract working.

## ⛔⛔ The message's epic-facing finding is REFUTED

The message reported: *"`ci.py` declares NO `--project-dir` and NO `--repo` at any level … the CI
abstraction structurally CANNOT open a PR in a foreign checkout."*

**REFUTED on its central claim.** Corroborated first-party by the orchestrator at this drain, and
independently by sibling epic `truthful-signals` (message `truthful-signals-019`, sent deliberately
*before* this drain so no plan would be staged on the refuted claim):

- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py`:9–21 — the module
  docstring documents `--project-dir PATH` as a top-level flag: *"Run every gh/glab subprocess with
  `cwd=PATH`. Required when invoking from a checkout whose HEAD is not the branch the caller wants to
  operate on."*
- `ci.py`:121–131 — the router consumes it before provider dispatch via `extract_routing_args(argv)`
  and applies it with `set_default_cwd(project_dir)`, under a documented two-state contract with
  `--plan-id` (both together is a hard error).

**This analysis used that flag to corroborate #235**, which is the strongest possible demonstration
that the capability exists.

⭐⭐ **THE TRANSFERABLE LESSON — an absent-flag claim MUST be verified against the ROUTER, not against
the argparse table.** `--project-dir` is a top-level router flag consumed manually, not an
`add_argument` declaration, so a sweep of the argparse table returns zero and looks like a clean
negative. This is the asserted-absence half of the verify-first contract — the higher-risk half,
because an unverified absence produces work against a surface that already exists. Had this drain
staged the proposed "foreign-checkout lane" plan, it would have built a second path to a capability
already shipped.

**What survives:** `--repo` genuinely does not exist, and that is **not** a gap — `gh` resolves the
repo from its cwd and `--project-dir` sets that cwd, so a foreign *checkout* is addressable. The real
limit is narrower: **a foreign repo with no local checkout is not addressable.**

## Reconciliation Actions

- [x] row `pr` stamped — `cuioss-organization#235` (qualified with the repo, since the bare number
      would read as a plan-marshall PR)
- [x] row `landing` stamped — `landings/PLAN-PR-002.md`
- [x] row `plan_marshall_plan_id` stamped — `org-empty-review-guard-too-broad`
- [ ] ⛔ row `status` deliberately LEFT at `launched` — **not** transitioned to `shipped`, because
      #235 is open. The status question is an operator decision (below), not an orchestrator call:
      it changes `R` and therefore what may be emitted at `N=1`.
- [x] epic.md reconciled; Watch opened for #235's merge
- [x] the "no foreign-checkout lane" premise retired from the epic's standing claims

## Follow-Ups

- **The finalize empty-host-PR trap is REAL and unaddressed** — with `finalize_without_asking=true`
  and branch-cleanup's `final_merge_without_asking`, a plan whose diff lands in a foreign repo will
  manufacture an empty PR against the host repo and try to merge it. This plan avoided it only because
  an operator prompt guarded it. ⇒ **Routed OUT to `truthful-signals`** under the three-way rule: it is
  machinery integrity (finalize behaviour), not review-apparatus ground. That epic offered to own it
  and deliberately did not double-stage behind our back.
- **Open residual R1, operator-accepted:** once step (2) lands, a `synchronize` run whose every model
  call failed will be UNGATED, and claim 3 establishes there is no runner state to fix that. The
  `/review` comment path — what automation depends on — stays fully gated, and the workflow documents
  the gap in-file. Recorded as an epic Watch.
- **Step (2) is owed by a follow-up plan in `cuioss-organization`**, not here: set
  `handle_push_trigger` + `push_commands = ["/review"]` in `cuioss/pr-agent-settings` AND add
  `synchronize` to callers' `types:`. ⛔ Do not enable the trigger without re-reading R1.
- **Sibling slices of the PLAN-116 split are unaffected** — PLAN-PR-001 (Defect A), PLAN-PR-005 (C+E),
  PLAN-PR-006 (D), PLAN-PR-007 (F) were not absorbed and are not touched by this work.
