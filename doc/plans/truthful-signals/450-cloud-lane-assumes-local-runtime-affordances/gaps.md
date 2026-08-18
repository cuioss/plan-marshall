# Gaps — 450-cloud-lane-assumes-local-runtime-affordances

**Source:** verification.md (same directory)   **Open items:** 5

All six deliverables landed in `.claude/skills/cloud-plan-lane/SKILL.md` and survive at HEAD
(`c806e3e1`). The gaps below are two report-accuracy defects, two wording/structure defects against
explicit ⛔ instructions in the plan, and one low-severity record inaccuracy. None of them requires
re-opening a deliverable's substance.

## G1 — Reconcile the report's D0 affordance table with what the run actually did

- **Kind:** stale-statement
- **Severity:** high
- **Where:** `doc/plans/truthful-signals/450-cloud-lane-assumes-local-runtime-affordances/report-01.md:34`,
  `:36`, `:185` — § D0 table rows "Self-wake / polling" and "Auto-merge arming", and the "GitHub access
  path:" line under § Contract check
- **What is wrong:** Line 34 says self-wake was "not probed (**no PR opened**, so no self-wake was
  needed)"; line 36 says arming was "not probed (**no arming this run**)"; line 185 says the GitHub MCP
  server was "**not exercised** for GitHub operations this run (**no PR**)". The same report opens PR
  #1147 (`:3`, `:179`), reads its comment surfaces over MCP (`:120`), and arms auto-merge with squash
  (`:162`). The PR's commit list shows the mechanism: the D0 table landed in `84ad5b0`, whose commit
  message reads "Outcome partial — … PR/merge held for the operator"; the later commits `dae86fd` and
  `b1f10a6` updated the header and contract-check rows 7–8 but never revisited D0.
- **Why it matters:** D0's entire product is that observation table, and the plan made the run its own
  live fixture ("it should report which it actually observed"). Three cells now assert the run observed
  nothing where it in fact observed the affordance directly. Run reports in this epic are the evidence
  corpus later plans mine — plan 450 itself was compiled from four of them — so a false "not probed"
  suppresses evidence a future plan would use, in the one epic named for truthful signals.
- **Fix:** Rewrite the three sites against what the run did. Self-wake: state whether `send_later` /
  `subscribe_pr_activity` were invoked at all and what they returned; if they were never invoked, say
  "not probed — the run drove the cycle by direct read instead", not "no PR opened". Auto-merge arming:
  mark **confirmed here**, since the run armed it, and record what the arm call returned and whether the
  arm was observable afterwards. Line 185: replace with the surfaces actually used (`create_pull_request`,
  `pull_request_read` for comments, `enable_pr_auto_merge`) and drop "(no PR)".
- **Done when:** No statement in `report-01.md` asserting an absence (no PR, no arming, no GitHub
  operation) is contradicted by another statement in the same file, and each D0 "this run" cell reflects
  the run's final state rather than its state at the time the row was written.
- **Module/topic:** `doc/plans/truthful-signals/450-…/report-01.md` (cloud-lane run records)

## G2 — Correct the `sourcery-ai` participation verdict: it reviewed, it was not silent

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `doc/plans/truthful-signals/450-cloud-lane-assumes-local-runtime-affordances/report-01.md:127`
  — § Reviewer participation, the `sourcery-ai` row; and `:157` — § Merge gate condition 2
- **What is wrong:** The row records verdict `silent`, evidenced as "The 'Sourcery review' check-run
  concluded `skipped`; **no comment body**." A live read of PR #1147's review-summary surface
  (`pull_request_read` `method: get_reviews`) returns exactly one review — `sourcery-ai[bot]`, state
  `COMMENTED`, submitted `2026-08-10T20:13:35Z` on commit `fbf14384`, body: *"Sorry @cuioss-oliver, you
  have reached your weekly rate limit of 500000 diff characters."* The bot engaged and reported a quota
  block; its verdict is `rate-limited`, the same as coderabbit's. Consequently condition 2's
  "3 conversation comments … 0 inline review threads. **Satisfied**" was established from two of the
  three comment surfaces, not all of them.
- **Why it matters:** A `silent` verdict and a `rate-limited` verdict tell the operator different things
  — `silent` implies a reviewer that may still be reachable, `rate-limited` names a quota with a reopen
  horizon. The disclosure the run made ("`sourcery-ai` silent (check skipped)") therefore misstates the
  coverage shortfall's cause. It is also the first recorded instance of the review-summary-surface blind
  spot that PR #1184 later closed in the contract, so leaving it uncorrected hides the incident that
  justifies that rule.
- **Fix:** Change the `sourcery-ai` row's verdict to `rate-limited`, quote the actual review-summary body
  as its evidence, and note that the "Sourcery review" **check-run** concluding `skipped` is not evidence
  of silence — the finding lived on the review-summary surface, which this run did not read (the contract
  at run time named only two comment surfaces; `get_reviews` was added by PR #1184). Add a line to
  § Merge gate condition 2 recording that the surface was unread at the time and what it in fact held.
- **Done when:** `report-01.md` records `sourcery-ai` as `rate-limited` with the quoted body, and states
  that condition 2 was established over two surfaces with the third read only retrospectively.
- **Module/topic:** `doc/plans/truthful-signals/450-…/report-01.md` (reviewer-participation records)

## G3 — Hedge the three affordance rows the run never probed

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:53` (GitHub access), `:55` (Ruleset-config API),
  `:56` (Auto-merge arming) — § Cloud session affordances
- **What is wrong:** The plan's D0 gate carries an explicit ⛔: *state "is gated" only where this run
  confirmed it, and "may be gated (reported)" otherwise.* The run applied it to one row only — Self-wake
  correctly reads "may be **approval-gated**". Three rows its own D0 table marks *reported-only / not
  probed* are stated as flat, confirmed fact: "There is **no `gh` CLI**, and Bash cannot reach
  `api.github.com` (egress-blocked — direct calls return `403`)"; "**Not reachable** — the MCP server
  exposes no branch-protection / ruleset tool"; "arming auto-merge … **queues the PR at once**".
- **Why it matters:** These rows exist so a future run reuses the fact instead of re-deriving it — which
  is exactly why an unhedged one is costly: a session that *does* have `gh`, or a server build that *does*
  expose a ruleset tool, is told authoritatively that it does not. § GitHub access (`:995`) still says
  "Never assume a tool is present — check", so the contract half-contradicts itself on the same page.
- **Fix:** Reword the three cells to carry their evidence grade, matching the Self-wake row's form. E.g.
  GitHub access: "In every cloud session observed so far there was **no `gh` CLI** and Bash could not
  reach `api.github.com` (`403`); check rather than assume." Ruleset-config API: "**Observed unreachable**
  — no server build seen so far exposes a branch-protection / ruleset tool, and direct API access returned
  `403`." Auto-merge arming: "**Observed:** arming while the required checks are green queues the PR at
  once." Leave the operational instruction that follows each fact unchanged.
- **Done when:** Every row in § Cloud session affordances either states a fact confirmed by a named
  artifact in this repository (`python-verify.yml`, a quoted run report) or is phrased as an observation
  that the reader is told to re-check, and none asserts an absence the corpus recorded as unprobed.
- **Module/topic:** `.claude/skills/cloud-plan-lane` (§ Cloud session affordances)

## G4 — Make the affordance facts single-sourced, or mark the restatements as pointers

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:55` (affordances "Ruleset-config API" row) vs
  `:1216-1222` (Step 8's MCP field note); and the same index/detail pairing at `:54` vs `:1327-1331`
  (self-wake), `:57` vs `:427-439` (`*.py` build), `:60` vs `:38` (sync)
- **What is wrong:** D1's done-when required that "the affordance facts appear in exactly one place (no
  restatement that can drift)". They do not — each fact is stated in the affordances table **and** in its
  operative step. The run recorded this itself (report finding #5, disposed "Accepted, no change") and
  named it a "mild drift risk" in § What have we learned. The drift has since occurred: the affordances
  row still says "Read required-ness from `mergeStateStatus`", while `SKILL.md:1216-1222` establishes that
  the MCP `get` payload has **no `mergeStateStatus` key** and the field is `mergeable_state` (lowercase).
  A reader who takes the affordances section at its word — which is what the section is for — looks for a
  field that is not in the response.
- **Why it matters:** The section was added specifically so a run reads the facts once instead of
  re-deriving them. A table that has already gone stale against its own detail section is worse than no
  table: it is a confident wrong answer at the point a run is least likely to double-check.
- **Fix:** Two changes. (1) Correct the "Ruleset-config API" row to name both spellings, as the mapping
  row at `:72` already does — "read required-ness from GitHub's merge-state field (`mergeStateStatus` in
  `gh`, `mergeable_state` on the MCP path)". (2) Make the index/detail relationship explicit at the head
  of the affordance table: state that each row is a pointer whose authoritative wording is the linked `§`,
  so any future edit to a fact is made in the step and only summarized here. That satisfies the intent of
  "exactly one place" — one *authoritative* place — without deleting the index the section exists to be.
- **Done when:** No affordance row names a field, tool, or trigger that its linked section contradicts,
  and the table states which of the two is authoritative when they differ.
- **Module/topic:** `.claude/skills/cloud-plan-lane` (§ Cloud session affordances ↔ Steps 5 / 8)

## G5 — List all of the run's commits, not three of them

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/450-cloud-lane-assumes-local-runtime-affordances/report-01.md:20-21`
  — § Deliverables preamble
- **What is wrong:** "Run commits on the branch: `8b0c455` (plan setup), `92620f4` (D1–D5
  implementation), `9f192df` (verification fixes)." PR #1147 carries **10** commits, seven of them from
  this session: those three plus `84ad5b0` (report-01), `fbf1438` (the four sibling-report annotations),
  `dae86fd` (record PR number), `b1f10a6` (finalize at the merge gate). The claim as worded is about
  commits *on the branch*, and it under-reports by four.
- **Why it matters:** `fbf1438` is the commit that carries the Bridge-rule excursion the report elsewhere
  declares; a reader auditing that excursion from this list would not find it. The sentence also asserts
  the trailer/footer property "each carries the trailer" over a set smaller than the one it names.
- **Fix:** List all seven session commits with a one-phrase role each, or reword to "Deliverable commits"
  and add a separate line naming the record commits (`84ad5b0`, `dae86fd`, `b1f10a6`) and the
  operator-directed annotation commit (`fbf1438`).
- **Done when:** Every commit the run made on the branch is named in `report-01.md`, or the list is
  explicitly scoped to deliverable commits with the remainder named separately.
- **Module/topic:** `doc/plans/truthful-signals/450-…/report-01.md` (cloud-lane run records)
