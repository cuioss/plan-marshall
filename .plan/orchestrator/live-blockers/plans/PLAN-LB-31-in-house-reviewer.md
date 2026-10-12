# PLAN-LB-31: In-house reviewer: measure whether it finds anything, decide its place in the roster, then finish the fleet enrolment

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-31-in-house-reviewer.md` and is queued as one row file, `queue/PLAN-LB-31.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-21, PLAN-LB-20, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

`cuioss-review-bot` is a required reviewer whose last measurement showed a canned review 152 times out of 156, and thirteen repositories are still waiting to be enrolled in it. Nothing has been measured since its charter changed, so nobody knows whether it should stay required or whether the enrolment is worth finishing. This plan repeats the measurement with the earlier method, re-runs the reviewer on a fixed set of diffs with known defects, writes the result down, puts the roster question to the operator, and only then, if the answer says so, enrols the thirteen deferred repositories and checks each on its first real pull request. The sources are one plan because the enrolment is gated on the measurement's decision and both report on the same reviewer.

### Carried from PLAN-LB-21: Measure whether the in-house reviewer finds anything, and decide its place in the roster

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

### Carried from PLAN-LB-20: Finish the review-bot fleet rollout — schema first, then the thirteen repositories

The in-house reviewer (`cuioss-review-bot`) is enrolled in 7 of the 20 repositories it was meant to
cover. The other 13 were left unwritten because their `.github/project.yml` fails the organisation's
schema on keys the rollout never touches: `github-automation.auto-merge-build-timeout`, which ten of
them carry and the schema does not admit, and two-part versions such as `2.7-SNAPSHOT`, which fail a
three-part pattern. The three repositories migrated earlier carry the same failures and were merged
on a check of the added block only. All of these verdicts were read by hand, because no validator can
be run locally. This plan settles each failing key at the source in `cuioss/cuioss-organization`,
ships a validator anyone can run, re-validates the three migrated repositories whole-file, and then
enrols the thirteen. Almost all of the work is in other repositories; this repository changes little
or not at all. Carries forward review-apparatus PLAN-PR-078 D1 and D2 (the unfinished part) and the
directive of lesson `2026-10-06-15-001`.

## Deliverables

1. **[PLAN-LB-21 D1]** **A repeat corpus pass with the earlier method, over pull requests opened since the charter
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

2. **[PLAN-LB-21 D2]** **A fixed-diff experiment on pull requests with known defects.** The corpus compares different
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

3. **[PLAN-LB-21 D3]** **A written result in this repository.** A document at `doc/analysis/in-house-reviewer-efficacy.md`,
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

4. **[PLAN-LB-21 D4]** **A recorded operator decision on the required-bot roster.** Put the result to the operator with
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

5. **[PLAN-LB-21 D5]** **The registry's calibration section agrees with the measurement.**
   `automatic-review/standards/cuioss-review-bot.md` § "Signal calibration" describes the
   reviewer's configuration generations and what was measured under each. Add the assembled-charter
   generation with the measured result, or correct the section where the measurement contradicts
   it. No behaviour changes.
   *Done when:* the section names the assembled-charter generation and points at the result
   document; `test/plan-marshall/automatic-review/` passes.

6. **[PLAN-LB-20 D4]** **The thirteen deferred repositories are enrolled.** In this order — first those that pass the
   released schema unchanged, then those that need a version or key correction in the same PR:
   cui-core-ui-model, cui-jsf-components, cui-portal-ui, cui-java-tools, cui-jsf-test-basic,
   cui-portal-core, cui-reference-documentation, cui-test-keycloak-integration, nifi-extensions,
   cui-test-generator, cui-test-juli-logger, cui-test-mockwebserver-junit5, cui-test-value-objects.
   Each PR adds `.github/workflows/cuioss-review-bot.yml` calling the org reusable workflow at the
   current release pin, and a `cuioss-review-bot:` block in `.github/project.yml` with
   `enabled: true`, the confirmed packs from the table below and `additional_rules: []`. Before each
   merge: the validator passes on the PR's whole file, and the repository's release path is checked
   to be guarded so that a merge to the default branch cannot publish. A repository that fails
   either check is reported and left unwritten.
   *Done when:* for each of the thirteen, the default branch carries the caller workflow and the
   block with exactly the confirmed packs, read back after merge; or the report names the
   repository, the check it failed and what is needed. The report states the count enrolled out of
   13 and out of 20 and does not round a partial rollout up.

7. **[PLAN-LB-20 D5]** **Each newly enrolled repository is checked on its first real pull request, or listed as
   unchecked.** For each repository enrolled by deliverable 6 of this spec (deliverable 4 of PLAN-LB-20) and for the six enrolled earlier and
   never observed (API-Sheriff, TokenSheriff, cui-http, cui-java-module-template, cui-open-rewrite,
   playwright-test-artifacts), read the reviewer run on the first pull request opened after
   enrolment and confirm the log line "Assembled review charter (spine; packs: …)" names the
   confirmed packs. No probe pull request is opened and no `/review` comment is posted for this
   purpose. Why both reviewer jobs were skipped on API-Sheriff #400 is established or stated as
   unknown.
   *Done when:* the report has one row per enrolled repository with the pull request and run read
   and the charter line found, or the reason no observation was possible.

## Claim Labels

Carried in source order: bullets 1 to 24 from PLAN-LB-21; bullets 25 to 34 from PLAN-LB-20; bullets 35 to 36 added at the regrouping.

- OBSERVED: the last pass covered 181 pull requests in four contributing repositories over `2026-08-30T20:16:39Z` to `2026-09-15T09:50:16Z`, found 156 bot reviews of which 152 were the canned table and 4 substantive, a populated security cell on 0 of 156, paired recall of 4 of 123 (9 of 123 counting `/improve`), and 7 distinct findings CodeRabbit did not file — read in the review-apparatus ledger at `findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md` § "Yield", § "Paired recall", § "Delta vs the 2026-08-30 pass"
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717 1e556f15d moved archive to telemetry); read at 1e556f15d^ review-apparatus/findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md: L3 window, L49 181, L130 0 of 156, L136 152 of 156, L152-153 4 and 9 of 123, L280 7 distinct
- OBSERVED: that pass left an explicit lower bound for its successor (`2026-09-15T09:50:16Z`) and persisted its scripts (`collect.py`, `classify.py`, `report.py`, `confound.py`, `adjudicate.py`, `final_tables.py`) but not its raw dumps — read at the same file § header and § "Reproduction", and the directory `findings/2026-09-15-corpus-scripts/` beside it
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717); read at 1e556f15d^ same file: L5 STAMP 2026-09-15T09:50:16Z, L331 Reproduction says raw dumps NOT persisted; git ls-tree shows findings/2026-09-15-corpus-scripts/ with the six named scripts plus collect_other.py and cmp.py
- OBSERVED: that pass enumerated with `gh pr list --search` and `gh api` because the CI abstraction's `pr list` cannot filter by date or label — read at the same file § "Instrument and validation"
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717); read at 1e556f15d^ same file, Instrument and validation L11-13: gh pr list --search and GET-only gh api; 'ci pr list --help offers only --head, --state and --limit. It cannot filter by date or label'
- OBSERVED: that pass states its own limits: CodeRabbit's actionable count is self-declared, the adjudication is our own disposition, no quality claim holds for TokenSheriff or API-Sheriff (15 and 20 reviews), and "drop the bot" does not follow — read at the same file § "What is supportable, and what is NOT"
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717); read at 1e556f15d^ same file, What is supportable and what is NOT: L138 and L277 self-declared 665, L206 'our own disposition', L301 no quality claim for TokenSheriff or API-Sheriff (15 and 20 guides), L303 'Drop pr-agent does not follow'
- OBSERVED: the scoring rule has four outcomes, a deficit is only assessable against a baseline, a reviewer run must be looked up unfiltered by branch because `/review` runs are attributed to `main`, and a refusal that never expires is recorded apart from one that does — read in the ledger at `review-practice.md` § 1
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717); read at 1e556f15d^ review-apparatus/review-practice.md section 1: L60-63 issue_comment runs get head_branch main, query UNFILTERED; L68 deficit only assessable against a baseline; L72-79 four outcomes; L81-82 never-expiring refusal recorded apart
- OBSERVED: the fixed-diff re-run is Recommendation B of the 2026-08-01 sweep, and the set it names is plan-marshall #1065, #1066, #1068 and API-Sheriff #133 — read in the ledger at `findings/2026-08-01-sweep-4day.md` § "Recommendations" B. The ledger does not name API-Sheriff #185 or #154 anywhere: cui-http #185 is the one substantive pull request the last pass found never triggered, and cui-http #154 is a retracted classifier error in the 2026-08-30 pass — ⛔ RE-SCOPED 2026-10-09 at `4ed67e228`: the second sentence is wrong. Recommendation B's set holds, but the ledger does name the two pull requests: `inbox/archive/generic-charter-language-specific-defect/generic-charter-language-specific-defect-013.md` line 50 lists "`API-Sheriff#185` (26 inline items) or `#154` (47)" as a re-review check. The fixed-diff re-run may therefore use them as that message intends. The ledger is no longer in this repository (moved by #1717 to plan-marshall-telemetry); it was read from git history at `1e556f15d^`
  - verdict: contradicted | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: yes | evidence: Rec B part holds (1e556f15d^ findings/2026-08-01-sweep-4day.md L244-248: #1065, #1066, #1068, API-Sheriff #133). But the ledger DOES name them: inbox/archive/generic-charter-language-specific-defect/...-013.md L50 has 'API-Sheriff#185 (26 inline items) or #154 (47)'
- OBSERVED: the central charter names nine defect categories, says severity is not a reporting threshold, contests the empty-list answer, sets `num_max_findings = 12`, `temperature = 1.0`, model `vertex_ai/gemini-3.7-flash`, and publishes clean reviews — read at `/Users/oliver/git/cuioss-review-bot/.pr_agent.toml` § `[pr_reviewer]` and § `[config]` (local checkout; last commit there is #66 of 2026-09-24)
  - verdict: unverifiable | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: No cuioss-review-bot checkout under /home/oliver/git (24 repos listed, none by that name); the cited .pr_agent.toml cannot be read. Only a stale temp copy from 2026-09-01 exists under plan-marshall .plan/temp/gen-check/pr-agent, which is not the cited file
- OBSERVED: `/improve` runs only on a labelled pull request or where the caller sets `auto-improve: true` — read at the same file § `[pr_code_suggestions]`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Cited .pr_agent.toml absent here; behaviour read in cuioss-organization local checkout f47083a (v0.37.0, lags v0.40.0) reusable-cuioss-review-bot.yml L506 and L523: auto_improve = inputs.auto-improve or label cuioss-review-bot-improve
- OBSERVED: the assembled charter replaces the central one only where `.github/project.yml` sets `cuioss-review-bot.enabled: true`; this repository does, with packs `python` and `plugin` — read at `.github/project.yml` and at the pack files under `/Users/oliver/git/cuioss-review-bot/packs/`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: plan-marshall .github/project.yml L24-30: cuioss-review-bot enabled true, packs python and plugin. Org workflow (local f47083a, v0.37.0) L459 and L514 switch on charter-source == assembled. Pack files unread: cuioss-review-bot repo not checked out
- OBSERVED: this repository's roster is `required_bots: cuioss-review-bot,coderabbit`, `optional_bots: sourcery` — read at `.plan/marshal.json` § `plan-marshall:automatic-review`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: plan-marshall HEAD .plan/marshal.json L116-128, step plan-marshall:automatic-review: required_bots 'cuioss-review-bot,coderabbit', optional_bots 'sourcery', bot_lists_provenance answered
- OBSERVED: the standing operator decision is that CodeRabbit stays required until the in-house reviewer reaches similar quality, with the reopen condition "measured by the existing comparison protocol" — read in the ledger at `settled.md` § "WATCH CLOSED 2026-09-15 (operator decision)"
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717); read at 1e556f15d^ review-apparatus/settled.md L1116-1129 'WATCH CLOSED 2026-09-15 (operator decision)': CodeRabbit stays REQUIRED until pr-agent achieves similar review quality; reopen 'measured by the existing comparison protocol'
- OBSERVED: `doc/analysis/` exists and holds one document, a decision with structural rationale that deliberately leaves out dated absolutes — read at `doc/analysis/uncompressed-output-measurement.md`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: git ls-files doc/analysis lists only uncompressed-output-measurement.md; L1 titles it a decision, L9-12 say the snapshot absolutes are 'not reproduced here' and the decision rests on structural facts, L25 Decision, L29 Rationale (structural, not snapshot)
- OBSERVED: the registry document for this bot has a § "Signal calibration" that pairs every yield figure with a configuration generation and lists "central spine plus the per-domain packs a repository selects" as the live generation, with no measurement under it — read at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` § "Signal calibration"
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: automatic-review/standards/cuioss-review-bot.md: L484 Signal calibration, L486 every yield figure stated with its configuration generation, L513 G2 'central spine plus the per-domain packs a repository selects', L689 'No G2 yield figure exists yet'
- OBSERVED: seven repositories carry the opt-in, six of them since 2026-10-06 and only one observed running the assembled charter — read in the ledger at `landings/PLAN-PR-078.md` and `epic.md` § Watches — ⛔ RE-SCOPED 2026-10-08 at `726ca857a`: wrong split. The ledger records all seven in-scope repositories as enrolled by PLAN-PR-078 on 2026-10-06, not six of them; six is the number never observed running the assembled charter, and plan-marshall-mcp is the one that was. plan-marshall itself, the earlier pilot, is an eighth repository outside that count. The list of six unobserved repositories in PLAN-LB-20 D5 is unaffected; for PLAN-LB-21 D1 every one of the seven splits at its own 2026-10-06 merge instant, and this repository splits at its pilot opt-in
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Judged on the RE-SCOPED note. 1e556f15d^ landings/PLAN-PR-078.md L14, L45-47 and epic.md L2224: 7 of 20 via PLAN-PR-078, live 1 of 7 (plan-marshall-mcp #34). Local merge commits of #399, #782, #273, #190, #33 all dated 2026-10-06; two checkouts lag
- HYPOTHESIS: this repository has run the assembled charter since plan-marshall #1605 merged (the pilot opt-in), which gives it by far the largest post-change population — confirm/refute by reading the merge time of #1605 and the first reviewer log after it that carries the "Assembled review charter" line (verify-at-outline)
- HYPOTHESIS: the persisted scripts still run against today's API responses and comment formats; the bot's review body or CodeRabbit's summary may have changed shape since — confirm/refute by running `classify.py` on a ten-pull-request sample and reading every classification by hand before the full pass (verify-at-outline)
- HYPOTHESIS: `/review` on a merged pull request still starts a reviewer run and edits the bot's comment in place, so the earlier canned text must be captured before the command is posted — confirm/refute on the first experiment pull request, reading the run list unfiltered (verify-at-outline)
- HYPOTHESIS: the assembled charter is used for a `/review` on an old pull request in a repository that has since opted in, because the block is read from the default branch at run time — confirm/refute at `/Users/oliver/git/cuioss-organization/.github/workflows/reusable-cuioss-review-bot.yml` and by the charter line in the run log (verify-at-outline)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: cuioss-organization local checkout f47083a (v0.37.0, lags v0.40.0) reusable-cuioss-review-bot.yml L339-374, step 'Read the review declaration from the default branch': contents API with ref=$DEFAULT_BRANCH on every run. Run-log half needs gh
- HYPOTHESIS: the six repositories enrolled on 2026-10-06 have too few pull requests since then to support any quality claim, so the after-change evidence is in effect this repository's and plan-marshall-mcp's — confirm/refute from the pass's own per-repository counts (verify-at-outline)
- Verify-first clause: the pass needs date- and label-filtered enumeration across repositories, which the CI abstraction does not offer and the repository's rules reserve to it. Either get the operator's explicit go-ahead to run the persisted `gh`-based scripts read-only, as the last pass did, or report that the instrument cannot be run under the rules. Do not add a new CI verb inside this plan.
- Verify-first clause: the scripts live in the orchestrator ledger, which this plan may read and may not write. Copy them to `.plan/temp/`, run them there, and commit nothing from them unless the operator asks for a kept instrument; if so, ask where it should live.
- Verify-first clause: the experiment posts `/review` on real, merged pull requests in two repositories and spends reviewer tokens. List the pull requests and get the operator's go-ahead before posting; post each command once.
- Verify-first clause: keep three things apart in every table, as `review-practice.md` § 1 requires: a canned review, a review that was never triggered, and a diff no other reviewer covered. A ratio that mixes them is not reported.
- Verify-first clause: do not attribute a difference between the two sides of deliverable 1 to the charter. The diffs differ, the model ladder may have moved, and the last pass already recorded a before/after drop it could not attribute. Only deliverable 2 holds the diff fixed.
- OBSERVED: the schema's top level is `additionalProperties: true`, and its `cuioss-review-bot` block admits `enabled`, `packs` and `additional_rules` only — read at the same file
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: cuioss-organization local checkout f47083a (v0.37.0) schema.json: L313 top-level additionalProperties true; L125-152 cuioss-review-bot has enabled, packs, additional_rules, additionalProperties false. v0.39.0/v0.40.0 schema is NOT on this machine (no such tags)
- OBSERVED: in the local checkouts, ten of the thirteen deferred repositories carry `auto-merge-build-timeout` (all but cui-java-tools, cui-test-generator and cui-test-juli-logger), and seven carry a two-part version (cui-java-tools `2.7-SNAPSHOT`, cui-jsf-test-basic `4.4-SNAPSHOT`, cui-portal-core `1.5-SNAPSHOT`, cui-test-generator `3.1-SNAPSHOT`, cui-test-juli-logger `2.2-SNAPSHOT`, cui-test-mockwebserver-junit5 `1.6` and `1.7-SNAPSHOT`, cui-test-value-objects `2.1-SNAPSHOT`). This matches the hand-read table of the earlier rollout — read at `/Users/oliver/git/<repo>/.github/project.yml` for each; local checkouts may lag the default branch
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Read .github/project.yml in all 13 /home/oliver/git checkouts: auto-merge-build-timeout: 300 in 10 (absent in cui-java-tools, cui-test-generator, cui-test-juli-logger); the seven two-part versions match exactly. Per PLAN-LB-30 landing these no longer fail since v0.39.0
- OBSERVED: the operator decision is "fix schema first": the thirteen repositories stay unwritten until the schema is settled, and a failing repository is reported, never force-written — recorded in the review-apparatus ledger at `epic.md` § "2026-10-07: `PLAN-PR-078` SHIPPED (#1704), but the fleet rollout is 7 of 20", `landings/PLAN-PR-078.md` § Verdict, and inbox message `plan-pr-078-review-bot-fleet-opt-in-011.md` § Residue
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717); read at 1e556f15d^ review-apparatus: epic.md L515-526, landings/PLAN-PR-078.md L12-17, inbox -011.md Residue L37: fix the schema first; 'reported, never force-written'. Schema since settled (landings/PLAN-LB-30.md L43)
- OBSERVED: the confirmed packs per deferred repository — java for all thirteen; additionally javascript for cui-jsf-components and nifi-extensions; additionally docs for cui-reference-documentation — recorded in inbox message `plan-pr-078-review-bot-fleet-opt-in-001.md` § "The 13 deferred repositories"
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: Gone from HEAD (#1717); read at 1e556f15d^ inbox/archive/plan-pr-078-review-bot-fleet-opt-in/...-001.md L61-79 'The 13 deferred repositories': java for all 13; java, javascript for cui-jsf-components and nifi-extensions; java, docs for cui-reference-documentation
- OBSERVED: the seven enrolled repositories pin the caller to `reusable-cuioss-review-bot.yml` at org release v0.36.0, and only plan-marshall-mcp was observed running the assembled charter — recorded in the same message § "The 7 repositories carrying the opt-in" — ⛔ RE-SCOPED 2026-10-09 at `4ed67e228`: the pin is stale. In the local checkouts API-Sheriff (#418) and TokenSheriff (#793) now pin the caller at `8e6a0c7` (v0.40.0) and cui-http at v0.37.0; cui-open-rewrite and plan-marshall-mcp still show v0.36.0. The enrolment pull requests of deliverable 6 use the current organisation release, not v0.36.0, and the observation pass of deliverable 7 records the pin each repository actually runs. Related: `cuioss-organization` v0.39.0 admits `auto-merge-build-timeout` and two-part versions, so the keys that made the thirteen repositories fail are still in their files but reportedly no longer fail; re-run `./pw validate --repo` on each before assuming a correction is needed
  - verdict: contradicted | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: yes | evidence: Message -001 L45 still records b2de4107 v0.36.0, but pins moved: local API-Sheriff (#418) and TokenSheriff (#793) cuioss-review-bot.yml L46 pin 8e6a0c7 v0.40.0, cui-http pins v0.37.0; cui-open-rewrite and plan-marshall-mcp checkouts still show v0.36.0
- HYPOTHESIS: the default-branch `project.yml` of each of the 20 repositories equals its local checkout for the failing keys — confirm/refute by running deliverable 1's remote mode, which reads the default branch (verify-at-outline)
- HYPOTHESIS: all thirteen deferred repositories have a guarded release path at the current org pin, as the seven enrolled ones had — confirm/refute per repository at its default-branch `.github/workflows/release.yml` and the reusable workflow it pins (verify-at-outline)
- HYPOTHESIS: nifi-extensions' plan configuration still lists the retired `pr-agent` bot name and four repositories have no required bot at all, so enrolling the reviewer there does not by itself make it gate a merge — confirm/refute at `.plan/marshal.json` in each consumer checkout; fixing it is out of this plan's scope (verify-at-outline)
- Verify-first clause: before deliverable 4, read PLAN-LB-21's recorded decision. If no result exists yet, stop after deliverable 3 and report; do not enrol thirteen more repositories in a reviewer whose usefulness is unmeasured, unless the operator explicitly says to proceed.
- Verify-first clause: every count in the final report ("N of 13", "N of 20") is computed from a read of each repository's default branch after the last merge, with the list of repositories read printed beside it.
- Verify-first clause: the carried claims name foreign checkouts as `/Users/oliver/git/<repo>`. Resolve the same repository names under the checkout root of the machine the plan runs on.
- Verify-first clause: PLAN-LB-20 D1 to D3, the whole-file validator, the two schema decisions with their organisation release, and the re-validation of the three migrated repositories, are not in this plan. They moved to PLAN-LB-30. Carried text that speaks of "the validator" or "the released schema" refers to what that plan ships.

## Expected Surface

- HYPOTHESIS: `doc/analysis/in-house-reviewer-efficacy.md` — the written result; a new file in an existing directory (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` — § "Signal calibration", the assembled-charter generation
- HYPOTHESIS: `.plan/marshal.json` — `required_bots` / `optional_bots` of `plan-marshall:automatic-review`, only if the operator's decision changes this repository's roster (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/automatic-review/test_bot_participation_contract_config.py` — pins on the configured roster, only if the roster changes (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-30 for the two enrolment deliverables only (PLAN-LB-20 D4 and D5 in the carried numbering): they need the released schema and the validator. The five measurement and decision deliverables depend on nothing and start at once.
- Stop point: after the recorded operator decision. If the decision is not to proceed, or PLAN-LB-30 has not released the schema, the plan reports and ends there with the enrolment deliverables recorded as not done; it does not enrol against an unsettled schema.
- Overlaps with: none. If the operator's decision changes `.plan/marshal.json`, that change is a config-only pull request of the kind PLAN-LB-30 fixes the verify gate for: land it after PLAN-LB-30, or make sure it gets a real build.
- May run together with: every other plan of this epic.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-21:

- Depends on: none. It reads pull requests and posts review commands; it needs no other plan's change.
- Overlaps with: PLAN-LB-18 and PLAN-LB-19 on nothing they edit — they change `coderabbit.md`, `sourcery.md` and the contract, this plan changes `cuioss-review-bot.md` § "Signal calibration" only. If the operator's decision changes `.plan/marshal.json`, land that as its own small PR: a config-only PR is exactly what PLAN-LB-16 is fixing the verify gate for, so wait for PLAN-LB-16 or make sure the PR gets a real build.
- Order relative to PLAN-LB-20: this plan's result should exist before PLAN-LB-20 enrols the thirteen remaining repositories. Enrolment adds a reviewer run and its token cost to every pull request there and, where the bot is listed as required, a wait at every merge; the last measurement says that run returns a canned table 97 times in 100. The thirteen are mostly quiet library repositories, so enrolling them first would add little evidence to this measurement — this repository alone has far more pull requests under the assembled charter than they would produce in a month. PLAN-LB-20's schema decision, validator and re-validation of the three migrated repositories do not depend on this result and can run in parallel with it.
- Adjacent to: `.claude/skills/finalize-step-review-retrospective/` — it computes per-PR reviewer metrics at finalize. It is the per-run instrument; this plan is the cross-repository one. Not edited. If the result shows the per-run instrument could have answered the question, say so in the result document as a follow-up, not as a change here.
- Foreign-repo work, read and comment only: `/review` comments on the experiment pull requests in `cuioss/plan-marshall` and `cuioss/API-Sheriff` (and any other repository the drawn set includes); read-only API calls against the repositories in the population. No file in `cuioss/cuioss-review-bot` or `cuioss/cuioss-organization` is edited: a charter or pack change that the result suggests is a separate plan, measured on the same fixed set before and after.
- Left out on purpose: changing the charter, the packs or the model ladder; fixing the reviewer's missing re-review on push and its missed-open-event gap; changing consumer repositories' rosters; adding date filters to the CI abstraction; an independent adjudication of CodeRabbit's findings (the comparison stays "our own disposition", stated as such).
- Operator decisions needed: go-ahead to run the `gh`-based instrument; go-ahead for the experiment's `/review` comments; the roster decision of deliverable 4, which is the point of the plan.

From PLAN-LB-20:

- Depends on: PLAN-LB-21 (in-house reviewer efficacy) for deliverables 4 and 5 only. Deliverables 1 to 3 do not depend on it and should run first: a validator and a truthful schema are worth having whatever the reviewer turns out to be worth, and the three migrated repositories already run it.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` — the `ci repo file read` and `ci checks logs --scope --match --job` verbs this plan uses to read foreign default branches and reviewer logs. They are used as they are. The known gap that `ci checks status` can omit a reusable workflow's nested checks (cui-http #274) is worked around by reading the run list, not fixed here.
- Foreign-repo work, the thirteen deferred repositories (`/Users/oliver/git/<repo>` for each name in deliverable 4): `.github/project.yml` (add the block; correct failing keys if deliverable 2 chose correction) and a new `.github/workflows/cuioss-review-bot.yml`.
- Order: (1) validator against the current schema, to turn the hand-read verdicts into derived ones; (2) the two key decisions, schema and docs, org release; (3) re-validate and, where needed, fix the three migrated repositories; (4) enrol the thirteen, passing repositories first; (5) observe.
- Left out on purpose: making `project.yml` schema validation a required CI check in every repository (a fleet-wide policy change); the bot rosters in consumer plan configurations (retired `pr-agent` name, missing `required_bots`); re-review after a push and the missed-open-event gap in the reviewer workflow; the leftover local `feature/plan-pr-078-review-bot-fleet-opt-in` branches in the foreign checkouts.
- Operator decisions needed: the two schema decisions of deliverable 2; cutting the org release; and whether to enrol before PLAN-LB-21 reports.
- Reporting: if the host PR is empty, the plan reports through its inbox message alone, with the per-repository table of deliverables 3 to 5 as the body and one line per foreign PR with its merge commit.

### Id map

| Id before the regrouping | Now |
|---|---|
| PLAN-LB-01 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-02 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-03 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-04 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05 | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-12 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-14 | unchanged, still PLAN-LB-14 |
| PLAN-LB-15 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16 | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-18 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20 | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21 | PLAN-LB-31 (all deliverables) |

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-31-in-house-reviewer.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
