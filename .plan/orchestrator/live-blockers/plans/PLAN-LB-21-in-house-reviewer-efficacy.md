# PLAN-LB-21: Measure whether the in-house reviewer finds anything, and decide its place in the roster

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-21-in-house-reviewer-efficacy.md` and is queued as one row file,
> `queue/PLAN-LB-21.json`, in the epic ledger. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

This plan is a measurement and a decision, not a code fix. `cuioss-review-bot` is a required
reviewer: a merge waits for it. In the last measurement, over a window of about two weeks, 152 of
its 156 reviews were the same canned table ("No major issues detected", "No security concerns
identified"), and on the 123 pull requests where CodeRabbit reported at least one actionable finding
it reported one on 4. After that measurement the reviewer changed:
its charter is now assembled at run time from a spine and per-domain packs in each repository that
opts in. Nothing has been measured since, so nobody knows whether the change helped, whether the bot
should stay required, or whether enrolling thirteen more repositories is worth the effort. This plan
repeats the measurement with the same method over pull requests opened since the charter change,
re-runs the reviewer on a fixed set of diffs with known defects, writes the result down, and puts the
roster question to the operator. The decision is the operator's; the plan records it and applies only
what the operator chooses. There is no earlier spec; the method is carried forward from
review-apparatus `findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md`, `review-practice.md`
§ 1 and Recommendation B of `findings/2026-08-01-sweep-4day.md`.

## Deliverables

1. **A repeat corpus pass with the earlier method, over pull requests opened since the charter
   change.** Population: every pull request opened after `2026-09-15T09:50:16Z` (the stamp the last
   pass left for its successor) in the repositories that pass covered, plus any repository enrolled
   since; pull requests labelled `skip-bot-review` and Dependabot pull requests are excluded and
   counted, as before. Each repository's population is split at the instant its `cuioss-review-bot`
   block with `enabled: true` reached the default branch, and the two sides are reported separately:
   before (central charter) and after (assembled charter). For each side report: reviews posted;
   canned versus substantive, classified by the earlier pass's structural rule and cross-checked by
   body length; security cell populated; `/improve` suggestions; paired recall against CodeRabbit on
   pull requests where CodeRabbit self-declared at least one actionable finding; the four-outcome
   score of `review-practice.md` § 1 (clean and corroborated, deficit, unassessable for lack of a
   baseline, unassessable because never triggered); and findings the bot reported that CodeRabbit
   did not. A reviewer run is looked up unfiltered by branch, never by the pull request's branch.
   *Done when:* the tables exist for both sides with the population size beside every ratio; the
   classifier is checked by hand on a seeded random sample of at least 30 reviews and the agreement
   is stated; every repository with fewer than 20 reviews on a side is reported as "coverage only,
   no quality claim"; the pass states its own upper-bound instant for the next pass.

2. **A fixed-diff experiment on pull requests with known defects.** The corpus compares different
   diffs under different configurations, so it cannot show what the charter change did. Take a
   fixed set of already-merged pull requests on which another reviewer found a Major defect and the
   bot's review was canned: plan-marshall #1065, #1066, #1068 and API-Sheriff #133 (the set the
   ledger names), plus at least four drawn from the 2026-09-15 pass's deficit rows in repositories
   that now run the assembled charter. Post `/review` once on each, read the result, and score it
   against the known defect: found, found something else real, or canned. Record for each run the
   charter line from the reviewer log ("Assembled review charter (spine; packs: …)" or the central
   charter), so the configuration under test is observed and not assumed. This also answers whether
   `/review` still produces a review on a merged pull request.
   *Done when:* a table with one row per pull request gives the known defect, the earlier review's
   class, the new review's class and the charter line observed; a pull request on which no run
   started is reported as "not triggered" with the run list read, not as a canned review; the
   experiment's comments are listed so they can be found later.

3. **A written result in this repository.** A document at `doc/analysis/in-house-reviewer-efficacy.md`,
   beside the one analysis already there and in its form: the question, the method, what the
   evidence supports, what it does not support, and the decision once made. Following that
   document's precedent and the documentation standards, it carries the durable reasoning and the
   re-run instructions, not dated tables. The dated tables, the appendix and the list of experiment
   comments go into the plan's PR description and its inbox message, where the orchestrator files
   them in the ledger beside the earlier passes.
   *Done when:* the document exists, states for each claim the population it rests on in words
   ("on every repository with the assembled charter" and so on), names the instrument and how to
   re-run it, and has an explicit "not supported" section; the PR description carries the tables of
   deliverables 1 and 2.

4. **A recorded operator decision on the required-bot roster.** Put the result to the operator with
   the options and what each costs: keep `cuioss-review-bot` required as it is; make it optional so
   its silence or canned output no longer holds a merge; keep it required but only where its
   measured yield is above a stated bar; change `/improve` (the only surface that produced
   suggestions last time) from per-repository opt-in to the default; or stop running it. State the
   standing decision this touches — CodeRabbit stays required until the in-house reviewer reaches
   similar quality — and whether the measurement meets that reopen condition. The plan does not
   choose. It records the answer in the result document and in the plan's decision log, applies it
   to this repository's roster in `.plan/marshal.json` only if the answer changes that roster, and
   lists the consumer repositories whose roster the answer implies changing, without editing them.
   *Done when:* the result document's decision section quotes the operator's answer and the date
   is in the PR description; if the roster changed, `.plan/marshal.json` matches the answer and the
   tests that pin the roster pass; the inbox message tells PLAN-LB-20 in one line whether to
   proceed with enrolment.

5. **The registry's calibration section agrees with the measurement.**
   `automatic-review/standards/cuioss-review-bot.md` § "Signal calibration" describes the
   reviewer's configuration generations and what was measured under each. Add the assembled-charter
   generation with the measured result, or correct the section where the measurement contradicts
   it. No behaviour changes.
   *Done when:* the section names the assembled-charter generation and points at the result
   document; `test/plan-marshall/automatic-review/` passes.

## Claim Labels

- OBSERVED: the last pass covered 181 pull requests in four contributing repositories over `2026-08-30T20:16:39Z` to `2026-09-15T09:50:16Z`, found 156 bot reviews of which 152 were the canned table and 4 substantive, a populated security cell on 0 of 156, paired recall of 4 of 123 (9 of 123 counting `/improve`), and 7 distinct findings CodeRabbit did not file — read in the review-apparatus ledger at `findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md` § "Yield", § "Paired recall", § "Delta vs the 2026-08-30 pass"
- OBSERVED: that pass left an explicit lower bound for its successor (`2026-09-15T09:50:16Z`) and persisted its scripts (`collect.py`, `classify.py`, `report.py`, `confound.py`, `adjudicate.py`, `final_tables.py`) but not its raw dumps — read at the same file § header and § "Reproduction", and the directory `findings/2026-09-15-corpus-scripts/` beside it
- OBSERVED: that pass enumerated with `gh pr list --search` and `gh api` because the CI abstraction's `pr list` cannot filter by date or label — read at the same file § "Instrument and validation"
- OBSERVED: that pass states its own limits: CodeRabbit's actionable count is self-declared, the adjudication is our own disposition, no quality claim holds for TokenSheriff or API-Sheriff (15 and 20 reviews), and "drop the bot" does not follow — read at the same file § "What is supportable, and what is NOT"
- OBSERVED: the scoring rule has four outcomes, a deficit is only assessable against a baseline, a reviewer run must be looked up unfiltered by branch because `/review` runs are attributed to `main`, and a refusal that never expires is recorded apart from one that does — read in the ledger at `review-practice.md` § 1
- OBSERVED: the fixed-diff re-run is Recommendation B of the 2026-08-01 sweep, and the set it names is plan-marshall #1065, #1066, #1068 and API-Sheriff #133 — read in the ledger at `findings/2026-08-01-sweep-4day.md` § "Recommendations" B. The ledger does not name API-Sheriff #185 or #154 anywhere: cui-http #185 is the one substantive pull request the last pass found never triggered, and cui-http #154 is a retracted classifier error in the 2026-08-30 pass
- OBSERVED: the central charter names nine defect categories, says severity is not a reporting threshold, contests the empty-list answer, sets `num_max_findings = 12`, `temperature = 1.0`, model `vertex_ai/gemini-3.7-flash`, and publishes clean reviews — read at `/Users/oliver/git/cuioss-review-bot/.pr_agent.toml` § `[pr_reviewer]` and § `[config]` (local checkout; last commit there is #66 of 2026-09-24)
- OBSERVED: `/improve` runs only on a labelled pull request or where the caller sets `auto-improve: true` — read at the same file § `[pr_code_suggestions]`
- OBSERVED: the assembled charter replaces the central one only where `.github/project.yml` sets `cuioss-review-bot.enabled: true`; this repository does, with packs `python` and `plugin` — read at `.github/project.yml` and at the pack files under `/Users/oliver/git/cuioss-review-bot/packs/`
- OBSERVED: this repository's roster is `required_bots: cuioss-review-bot,coderabbit`, `optional_bots: sourcery` — read at `.plan/marshal.json` § `plan-marshall:automatic-review`
- OBSERVED: the standing operator decision is that CodeRabbit stays required until the in-house reviewer reaches similar quality, with the reopen condition "measured by the existing comparison protocol" — read in the ledger at `settled.md` § "WATCH CLOSED 2026-09-15 (operator decision)"
- OBSERVED: `doc/analysis/` exists and holds one document, a decision with structural rationale that deliberately leaves out dated absolutes — read at `doc/analysis/uncompressed-output-measurement.md`
- OBSERVED: the registry document for this bot has a § "Signal calibration" that pairs every yield figure with a configuration generation and lists "central spine plus the per-domain packs a repository selects" as the live generation, with no measurement under it — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` § "Signal calibration"
- OBSERVED: seven repositories carry the opt-in, six of them since 2026-10-06 and only one observed running the assembled charter — read in the ledger at `landings/PLAN-PR-078.md` and `epic.md` § Watches
- HYPOTHESIS: this repository has run the assembled charter since plan-marshall #1605 merged (the pilot opt-in), which gives it by far the largest post-change population — confirm/refute by reading the merge time of #1605 and the first reviewer log after it that carries the "Assembled review charter" line (verify-at-outline)
- HYPOTHESIS: the persisted scripts still run against today's API responses and comment formats; the bot's review body or CodeRabbit's summary may have changed shape since — confirm/refute by running `classify.py` on a ten-pull-request sample and reading every classification by hand before the full pass (verify-at-outline)
- HYPOTHESIS: `/review` on a merged pull request still starts a reviewer run and edits the bot's comment in place, so the earlier canned text must be captured before the command is posted — confirm/refute on the first experiment pull request, reading the run list unfiltered (verify-at-outline)
- HYPOTHESIS: the assembled charter is used for a `/review` on an old pull request in a repository that has since opted in, because the block is read from the default branch at run time — confirm/refute at `/Users/oliver/git/cuioss-organization/.github/workflows/reusable-cuioss-review-bot.yml` and by the charter line in the run log (verify-at-outline)
- HYPOTHESIS: the six repositories enrolled on 2026-10-06 have too few pull requests since then to support any quality claim, so the after-change evidence is in effect this repository's and plan-marshall-mcp's — confirm/refute from the pass's own per-repository counts (verify-at-outline)
- Verify-first clause: the pass needs date- and label-filtered enumeration across repositories, which the CI abstraction does not offer and the repository's rules reserve to it. Either get the operator's explicit go-ahead to run the persisted `gh`-based scripts read-only, as the last pass did, or report that the instrument cannot be run under the rules. Do not add a new CI verb inside this plan.
- Verify-first clause: the scripts live in the orchestrator ledger, which this plan may read and may not write. Copy them to `.plan/temp/`, run them there, and commit nothing from them unless the operator asks for a kept instrument; if so, ask where it should live.
- Verify-first clause: the experiment posts `/review` on real, merged pull requests in two repositories and spends reviewer tokens. List the pull requests and get the operator's go-ahead before posting; post each command once.
- Verify-first clause: keep three things apart in every table, as `review-practice.md` § 1 requires: a canned review, a review that was never triggered, and a diff no other reviewer covered. A ratio that mixes them is not reported.
- Verify-first clause: do not attribute a difference between the two sides of deliverable 1 to the charter. The diffs differ, the model ladder may have moved, and the last pass already recorded a before/after drop it could not attribute. Only deliverable 2 holds the diff fixed.

## Expected Surface

- HYPOTHESIS: `doc/analysis/in-house-reviewer-efficacy.md` — the written result; a new file in an existing directory (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` — § "Signal calibration", the assembled-charter generation
- HYPOTHESIS: `.plan/marshal.json` — `required_bots` / `optional_bots` of `plan-marshall:automatic-review`, only if the operator's decision changes this repository's roster (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/automatic-review/test_bot_participation_contract_config.py` — pins on the configured roster, only if the roster changes (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. It reads pull requests and posts review commands; it needs no other plan's change.
- Overlaps with: PLAN-LB-18 and PLAN-LB-19 on nothing they edit — they change `coderabbit.md`, `sourcery.md` and the contract, this plan changes `cuioss-review-bot.md` § "Signal calibration" only. If the operator's decision changes `.plan/marshal.json`, land that as its own small PR: a config-only PR is exactly what PLAN-LB-16 is fixing the verify gate for, so wait for PLAN-LB-16 or make sure the PR gets a real build.
- Order relative to PLAN-LB-20: this plan's result should exist before PLAN-LB-20 enrols the thirteen remaining repositories. Enrolment adds a reviewer run and its token cost to every pull request there and, where the bot is listed as required, a wait at every merge; the last measurement says that run returns a canned table 97 times in 100. The thirteen are mostly quiet library repositories, so enrolling them first would add little evidence to this measurement — this repository alone has far more pull requests under the assembled charter than they would produce in a month. PLAN-LB-20's schema decision, validator and re-validation of the three migrated repositories do not depend on this result and can run in parallel with it.
- Adjacent to: `.claude/skills/finalize-step-review-retrospective/` — it computes per-PR reviewer metrics at finalize. It is the per-run instrument; this plan is the cross-repository one. Not edited. If the result shows the per-run instrument could have answered the question, say so in the result document as a follow-up, not as a change here.
- Foreign-repo work, read and comment only: `/review` comments on the experiment pull requests in `cuioss/plan-marshall` and `cuioss/API-Sheriff` (and any other repository the drawn set includes); read-only API calls against the repositories in the population. No file in `cuioss/cuioss-review-bot` or `cuioss/cuioss-organization` is edited: a charter or pack change that the result suggests is a separate plan, measured on the same fixed set before and after.
- Left out on purpose: changing the charter, the packs or the model ladder; fixing the reviewer's missing re-review on push and its missed-open-event gap; changing consumer repositories' rosters; adding date filters to the CI abstraction; an independent adjudication of CodeRabbit's findings (the comparison stays "our own disposition", stated as such).
- Operator decisions needed: go-ahead to run the `gh`-based instrument; go-ahead for the experiment's `/review` comments; the roster decision of deliverable 4, which is the point of the plan.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-21-in-house-reviewer-efficacy.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
