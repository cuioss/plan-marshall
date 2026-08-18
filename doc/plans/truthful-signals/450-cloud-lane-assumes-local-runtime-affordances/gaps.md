# Gaps — 450-cloud-lane-assumes-local-runtime-affordances

**Source:** verification.md (same directory)   **Open items:** 5 (re-derived under adversarial review —
G1–G5 all upheld, none refuted, none added)

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
  The three cells are not wrong in the same way, and the fix differs per cell: on line 36 and line 185
  the assertion itself is false (the run armed auto-merge, and it did drive GitHub over MCP), whereas on
  line 34 the verdict "not probed" is **accurate** — nothing in the report shows `send_later` or
  `subscribe_pr_activity` ever being invoked — and only its stated reason ("no PR opened") is false.
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
  three comment surfaces, not all of them. The two facts are not in conflict — they are about different
  heads: the review was submitted on `fbf14384`, while the `skipped` "Sourcery review" **check-run**
  (`get_check_runs`, id `93587334538`, completed `20:25:29Z`) belongs to the final head `b1f10a64`. Both
  are true; only the inference "check-run skipped ⇒ nothing was filed" is false.
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
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:54` (GitHub access), `:56` (Ruleset-config API),
  `:57` (Auto-merge arming) — § Cloud session affordances. All three cells are this plan's landed text,
  unchanged since `a3eb36bb` (`git show a3eb36bb -- <path>`); only the Self-wake row was edited later.
- **What is wrong:** The plan's D0 gate carries an explicit ⛔: *state "is gated" only where this run
  confirmed it, and "may be gated (reported)" otherwise.* The run applied it to one row only — Self-wake
  correctly reads "may be **approval-gated**". Three rows whose backing fact its own D0 table marks
  *reported-only / not probed* are stated as flat, confirmed fact: "There is **no `gh` CLI**, and Bash
  cannot reach `api.github.com` (egress-blocked — direct calls return `403`)"; "**Not reachable** — the
  MCP server exposes no branch-protection / ruleset tool"; "arming auto-merge … **queues the PR at
  once**". (The GitHub-access row is the partial case: D0 marks it "Confirmed (partial)" — the MCP
  server's *presence* was confirmed, while "absence of `gh` is reported-only" in D0's own words, and it
  is precisely the absence clause the skill states flatly. The other two D0 rows are marked
  *reported-only* outright.)
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
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:56` (affordances "Ruleset-config API" row) vs
  `:1218-1224` (Step 8's MCP field note); and the same index/detail pairing at `:55` vs `:1331-1334`
  (self-wake), `:59` vs `:427-439` (`*.py` build), `:60` vs `:38` (sync). A fifth pair exists inside the
  mapping table itself: rows `:73-75` (issue comments / review summaries / inline threads → `get_comments`
  / `get_reviews` / `get_review_comments`) are duplicated verbatim in function by Step 7's three-surface
  table at `:1053-1057`
- **What is wrong:** D1's done-when required that "the affordance facts appear in exactly one place (no
  restatement that can drift)". They do not — each fact is stated in the affordances table **and** in its
  operative step. The run recorded this itself (report finding #5, disposed "Accepted, no change") and
  named it a "mild drift risk" in § What have we learned. The drift has since occurred: the affordances
  row still says "Read required-ness from `mergeStateStatus`", while `SKILL.md:1218-1224` establishes that
  the MCP `get` payload has **no `mergeStateStatus` key** and the field is `mergeable_state` (lowercase).
  A reader who takes the affordances **table** at its word looks for a field that is not in the response.
- **Why it matters:** The section was added specifically so a run reads the facts once instead of
  re-deriving them. A table that has gone stale against its own detail section is a confident wrong
  answer at the point a run is least likely to double-check. The harm here is bounded — the mapping row
  at `:72`, sixteen lines below the stale cell and inside the same section, already names both spellings,
  so an attentive reader of the whole section recovers — but the bound is luck, not design: it is exactly
  the drift D1's "exactly one place" clause was written to make impossible, and the same structure now
  carries five index/detail pairs and one whole duplicated sub-table (§ Where).
- **Fix:** Two changes. (1) Correct the "Ruleset-config API" row to name both spellings, as the mapping
  row at `:72` already does — "read required-ness from GitHub's merge-state field (`mergeStateStatus` in
  `gh`, `mergeable_state` on the MCP path)". (2) Make the index/detail relationship explicit at the head
  of the affordance table: state that each row is a pointer whose authoritative wording is the linked `§`,
  so any future edit to a fact is made in the step and only summarized here. That satisfies the intent of
  "exactly one place" — one *authoritative* place — without deleting the index the section exists to be.
  (3) Apply the same pointer rule to the duplicated comment-surface rows: leave the authoritative
  three-surface table at `:1053-1057` and have mapping rows `:73-75` point at it rather than restate its
  prose.
- **Done when:** No affordance row names a field, tool, or trigger that its linked section contradicts,
  the table states which of the two is authoritative when they differ, and mapping rows `:73-75` no
  longer restate the body of the `:1053-1057` table.
- **Module/topic:** `.claude/skills/cloud-plan-lane` (§ Cloud session affordances ↔ Steps 5 / 8)

## G5 — List all of the run's commits, not three of them

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/450-cloud-lane-assumes-local-runtime-affordances/report-01.md:23-24`
  — § Deliverables preamble
- **What is wrong:** "Run commits on the branch: `8b0c455` (plan setup), `92620f4` (D1–D5
  implementation), `9f192df` (verification fixes)." PR #1147 carries **10** commits (`get_commits`,
  re-derived), seven of them from the execution session: those three plus `84ad5b0` (report-01),
  `fbf1438` (the four sibling-report annotations), `dae86fd` (record PR number), `b1f10a6` (finalize at
  the merge gate); the remaining three (`780c737`, `7172419`, `af2eaed`) are the earlier plan-authoring
  commits on the same branch. The claim as worded is about commits *on the branch*, so it under-reports
  by **seven** against that set and by **four** against the execution session's own commits — under
  either reading it is wrong.
- **Why it matters:** `fbf1438` is the commit that carries the Bridge-rule excursion the report elsewhere
  declares; a reader auditing that excursion from this list would not find it. The sentence also asserts
  the trailer/footer property "each carries the trailer" over a set smaller than the one it names.
- **Fix:** List all seven session commits with a one-phrase role each, or reword to "Deliverable commits"
  and add a separate line naming the record commits (`84ad5b0`, `dae86fd`, `b1f10a6`) and the
  operator-directed annotation commit (`fbf1438`).
- **Done when:** Every commit the run made on the branch is named in `report-01.md`, or the list is
  explicitly scoped to deliverable commits with the remainder named separately.
- **Module/topic:** `doc/plans/truthful-signals/450-…/report-01.md` (cloud-lane run records)

## Refuted during adversarial review

**None of G1–G5 was refuted.** Each was re-checked independently against the tree and the live PR — not
by re-reading `verification.md` — and each survived; the corrections above are to their line references,
their scope, and their precision, not to their substance. Evidence per gap is in `verification.md`
§ Adversarial review.

Two further candidate gaps were **considered and deliberately not filed**, recorded here so a third
reviewer does not spend the same effort:

- **"D0's mandated probes were never performed."** The plan's D0 ⛔ asks the run to answer, for its own
  environment, *is `gh` present here? are the self-wake tools gated here? does the config API `403`
  here?* The run answered none of the three by probing (`report-01.md:33-36`). This is real, and it is
  the root cause of G3 — but it has **no actionable fix**: the session is gone and the probes cannot be
  re-run retrospectively. Its only reachable remedy is G3's (make the skill's wording carry the evidence
  grade the run actually had), so filing it separately would be a second row for one fix.
- **"The run applied the `*.py`-only gate before it landed."** `report-01.md`'s § Build gate records that
  the contract *as it stood at run start* triggered the per-commit gate on `.claude/skills/**`, and that
  the run took the skip path anyway on the operator's live ruling — while `plan.md`'s ⚠⚠ block requires
  the run to execute its own cycle "against the contract **as it currently stands**." The deviation is
  real and is a departure from an explicit plan instruction, but it is **disclosed in the report, not
  concealed**, it was operator-authorized, and the change it skipped a local lint on was verified in full
  by the merge queue's `merge_group` run before landing. There is no change an implementer could now
  make, so it is an observation rather than a gap.
