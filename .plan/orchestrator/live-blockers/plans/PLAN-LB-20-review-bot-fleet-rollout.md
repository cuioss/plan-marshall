# PLAN-LB-20: Finish the review-bot fleet rollout — schema first, then the thirteen repositories

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-20-review-bot-fleet-rollout.md` and is queued as one row file,
> `queue/PLAN-LB-20.json`, in the epic ledger. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

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

1. **A whole-file validator that runs locally and in CI, in `cuioss/cuioss-organization`.** A script
   beside the schema (`.github/actions/read-project-config/`) takes a path to a `project.yml` and
   validates the whole file against `schema.json`, printing one line per violation with the key path
   and the rule broken, and exiting non-zero on any. It runs through that repository's own `./pw`
   environment, so it needs nothing installed under the system Python. A second mode takes a list of
   repository names and validates each one's default-branch file read through `gh`. The script is
   covered by tests in `test/workflow/` and documented in `docs/project-yml-schema.adoc` § Validation,
   which today offers only a `yq` syntax check.
   *Done when:* the validator, run against the local checkouts of the 20 in-scope repositories at
   the current schema, reproduces the hand-read table in this spec (or the plan reports each cell
   that differs and why); a test feeds one file with an unknown `github-automation` key and one with
   a two-part version and asserts both are rejected with the key path named; a valid file exits 0.

2. **One recorded decision per failing key, applied in the schema and its documentation, and
   released.** For `github-automation.auto-merge-build-timeout`: the config reader no longer reads
   it (only `auto-merge-build-versions` is in its field registry, and a test asserts the timeout is
   not emitted), yet the action README still documents it and the org's own
   `update-github-actions` command template still writes it. Choose between admitting it in the
   schema as a deprecated, ignored key, and removing it from the template, the README and every
   repository that carries it. For the version patterns: Maven accepts a two-part version and the
   release workflow passes `next-version` straight to `-DdevelopmentVersion`, so choose between
   widening both patterns to admit two parts and correcting the affected repositories to three.
   Each decision is written into `docs/project-yml-schema.adoc` with the alternative that was
   rejected, the schema, README and command template are made to agree, and the change ships in an
   org release.
   *Done when:* the validator's tests encode both decisions (a fixture per key that passes or fails
   as decided); `schema.json`, `README.adoc`, `docs/project-yml-schema.adoc` and
   `.claude/commands/update-github-actions.md` state the same thing about each key, checked by a
   test that reads all four; an org release containing the change exists and its tag is named in the
   plan's report.

3. **The three migrated repositories validate whole-file.** Run the validator against the default
   branch of API-Sheriff, TokenSheriff and cui-http at the released schema. Where a file still fails
   — which depends on deliverable 2's decisions; cui-http carries both a two-part version and the
   timeout key — open one PR per repository that fixes only the failing keys.
   *Done when:* the validator exits 0 for all three default branches, and the report lists per
   repository either "passes unchanged" or the PR and merge commit that fixed it.

4. **The thirteen deferred repositories are enrolled.** In this order — first those that pass the
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

5. **Each newly enrolled repository is checked on its first real pull request, or listed as
   unchecked.** For each repository enrolled by deliverable 4 and for the six enrolled earlier and
   never observed (API-Sheriff, TokenSheriff, cui-http, cui-java-module-template, cui-open-rewrite,
   playwright-test-artifacts), read the reviewer run on the first pull request opened after
   enrolment and confirm the log line "Assembled review charter (spine; packs: …)" names the
   confirmed packs. No probe pull request is opened and no `/review` comment is posted for this
   purpose. Why both reviewer jobs were skipped on API-Sheriff #400 is established or stated as
   unknown.
   *Done when:* the report has one row per enrolled repository with the pull request and run read
   and the charter line found, or the reason no observation was possible.

## Claim Labels

- OBSERVED: the schema's `github-automation` object admits `auto-merge-build-versions` and `dependabot-automerge` only, with `additionalProperties: false` — read at `/Users/oliver/git/cuioss-organization/.github/actions/read-project-config/schema.json` § `properties.github-automation`
- OBSERVED: `release.current-version` requires `^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$` and `release.next-version` requires `^[0-9]+\.[0-9]+\.[0-9]+(-SNAPSHOT)?$`; both reject a two-part version — read at the same file § `properties.release`
- OBSERVED: the schema's top level is `additionalProperties: true`, and its `cuioss-review-bot` block admits `enabled`, `packs` and `additional_rules` only — read at the same file
- OBSERVED: the config reader's field registry reads `github-automation.auto-merge-build-versions` and no timeout key, and a test asserts `auto-merge-build-timeout` is absent from the reader's output — read at `/Users/oliver/git/cuioss-organization/.github/actions/read-project-config/read-config.py` § `FIELD_REGISTRY` and `/Users/oliver/git/cuioss-organization/test/workflow/test_read_config.py` § `TestGitHubAutomationSection.test_default_auto_merge_values`
- OBSERVED: the same key is still documented as an output with default `'300'` and is still written by the org's workflow-update command template — read at `/Users/oliver/git/cuioss-organization/.github/actions/read-project-config/README.adoc` § "GitHub Automation Section" and `/Users/oliver/git/cuioss-organization/.claude/commands/update-github-actions.md`
- OBSERVED: nothing in `cuioss-organization` validates a `project.yml` against the schema: the reader imports no JSON-schema library, and the schema is referenced only by the reader's README, the schema doc (as an editor hint), and one test — searched for `schema.json` and `jsonschema` across the checkout
- OBSERVED: the schema doc's § Validation offers a `yq` syntax check only — read at `/Users/oliver/git/cuioss-organization/docs/project-yml-schema.adoc` § "Validation"
- OBSERVED: the release workflow passes `next-version` to Maven as `-DdevelopmentVersion` unchanged — read at `/Users/oliver/git/cuioss-organization/.github/workflows/reusable-maven-release.yml`
- OBSERVED: in the local checkouts, ten of the thirteen deferred repositories carry `auto-merge-build-timeout` (all but cui-java-tools, cui-test-generator and cui-test-juli-logger), and seven carry a two-part version (cui-java-tools `2.7-SNAPSHOT`, cui-jsf-test-basic `4.4-SNAPSHOT`, cui-portal-core `1.5-SNAPSHOT`, cui-test-generator `3.1-SNAPSHOT`, cui-test-juli-logger `2.2-SNAPSHOT`, cui-test-mockwebserver-junit5 `1.6` and `1.7-SNAPSHOT`, cui-test-value-objects `2.1-SNAPSHOT`). This matches the hand-read table of the earlier rollout — read at `/Users/oliver/git/<repo>/.github/project.yml` for each; local checkouts may lag the default branch
- OBSERVED: API-Sheriff, TokenSheriff and cui-http carry `auto-merge-build-timeout` beside an enabled `cuioss-review-bot` block, and cui-http also carries `current-version: 3.2` and `next-version: 3.3-SNAPSHOT` — read at `/Users/oliver/git/API-Sheriff/.github/project.yml`, `/Users/oliver/git/TokenSheriff/.github/project.yml`, `/Users/oliver/git/cui-http/.github/project.yml`
- OBSERVED: the operator decision is "fix schema first": the thirteen repositories stay unwritten until the schema is settled, and a failing repository is reported, never force-written — recorded in the review-apparatus ledger at `epic.md` § "2026-10-07: `PLAN-PR-078` SHIPPED (#1704), but the fleet rollout is 7 of 20", `landings/PLAN-PR-078.md` § Verdict, and inbox message `plan-pr-078-review-bot-fleet-opt-in-011.md` § Residue
- OBSERVED: the confirmed packs per deferred repository — java for all thirteen; additionally javascript for cui-jsf-components and nifi-extensions; additionally docs for cui-reference-documentation — recorded in inbox message `plan-pr-078-review-bot-fleet-opt-in-001.md` § "The 13 deferred repositories"
- OBSERVED: the seven enrolled repositories pin the caller to `reusable-cuioss-review-bot.yml` at org release v0.36.0, and only plan-marshall-mcp was observed running the assembled charter — recorded in the same message § "The 7 repositories carrying the opt-in"
- OBSERVED: this repository's own `.github/project.yml` holds `name`, `sonar.enabled`, `github-automation.auto-merge-build-versions` and a `cuioss-review-bot` block with packs `python` and `plugin`; by reading, it satisfies the schema — read at `.github/project.yml`
- HYPOTHESIS: the default-branch `project.yml` of each of the 20 repositories equals its local checkout for the failing keys — confirm/refute by running deliverable 1's remote mode, which reads the default branch (verify-at-outline)
- HYPOTHESIS: no workflow, script or bot in the organisation reads `auto-merge-build-timeout` from a consumer's file by a path other than the config reader, so admitting or removing the key changes no behaviour — confirm/refute by searching `/Users/oliver/git/cuioss-organization/.github/workflows/` and its scripts for the key and for a generic `github-automation` read (verify-at-outline)
- HYPOTHESIS: the release tooling handles a two-part release version end to end (tag, GitHub release name, propagation to consumers), so widening the pattern is safe — confirm/refute at `/Users/oliver/git/cuioss-organization/.github/workflows/reusable-maven-release.yml` and the propagation script it calls, and against cui-http's last release, which used `3.2` (verify-at-outline)
- HYPOTHESIS: all thirteen deferred repositories have a guarded release path at the current org pin, as the seven enrolled ones had — confirm/refute per repository at its default-branch `.github/workflows/release.yml` and the reusable workflow it pins (verify-at-outline)
- HYPOTHESIS: nifi-extensions' plan configuration still lists the retired `pr-agent` bot name and four repositories have no required bot at all, so enrolling the reviewer there does not by itself make it gate a merge — confirm/refute at `.plan/marshal.json` in each consumer checkout; fixing it is out of this plan's scope (verify-at-outline)
- Verify-first clause: deliverable 2 is two operator decisions. Present both, each with the count of repositories it touches under either choice (derived by the validator, not copied from this spec), and wait for the answer before editing the schema.
- Verify-first clause: cutting an org release is something a dispatched agent has been refused before ("production deploy"); plan for the operator to cut it, and stop at that point with the release PR ready.
- Verify-first clause: before deliverable 4, read PLAN-LB-21's recorded decision. If no result exists yet, stop after deliverable 3 and report; do not enrol thirteen more repositories in a reviewer whose usefulness is unmeasured, unless the operator explicitly says to proceed.
- Verify-first clause: every count in the final report ("N of 13", "N of 20") is computed from a read of each repository's default branch after the last merge, with the list of repositories read printed beside it.

## Expected Surface

- HYPOTHESIS: `.github/project.yml` — this repository's own file is validated whole-file with the new validator and edited only if it fails; by reading, it passes and stays unchanged (verify-at-outline)
- HYPOTHESIS: `.github/workflows/python-verify.yml` — only if the org release of deliverable 2 must be pinned here by hand; normally the org's own pin-update PR does it and this plan does not touch the file (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-21 (in-house reviewer efficacy) for deliverables 4 and 5 only. Deliverables 1 to 3 do not depend on it and should run first: a validator and a truthful schema are worth having whatever the reviewer turns out to be worth, and the three migrated repositories already run it.
- Overlaps with: PLAN-LB-16 on `cuioss/cuioss-organization` (it changes the reusable verify workflow there) and on `.github/workflows/python-verify.yml` here. The two org changes touch different files; if both need an org release, ship them in one release and bump the pin once. No other `live-blockers` plan touches this plan's surface.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` — the `ci repo file read` and `ci checks logs --scope --match --job` verbs this plan uses to read foreign default branches and reviewer logs. They are used as they are. The known gap that `ci checks status` can omit a reusable workflow's nested checks (cui-http #274) is worked around by reading the run list, not fixed here.
- Foreign-repo work, `cuioss/cuioss-organization` (`/Users/oliver/git/cuioss-organization`): `.github/actions/read-project-config/schema.json`; a new validator script in the same directory; `.github/actions/read-project-config/README.adoc`; `docs/project-yml-schema.adoc`; `.claude/commands/update-github-actions.md`; `test/workflow/` (new validator tests, and `test_read_config.py` if the timeout key is re-admitted to the reader); then a release.
- Foreign-repo work, the three migrated repositories (`/Users/oliver/git/API-Sheriff`, `/Users/oliver/git/TokenSheriff`, `/Users/oliver/git/cui-http`): `.github/project.yml`, only where the released schema still rejects it.
- Foreign-repo work, the thirteen deferred repositories (`/Users/oliver/git/<repo>` for each name in deliverable 4): `.github/project.yml` (add the block; correct failing keys if deliverable 2 chose correction) and a new `.github/workflows/cuioss-review-bot.yml`.
- Order: (1) validator against the current schema, to turn the hand-read verdicts into derived ones; (2) the two key decisions, schema and docs, org release; (3) re-validate and, where needed, fix the three migrated repositories; (4) enrol the thirteen, passing repositories first; (5) observe.
- Left out on purpose: making `project.yml` schema validation a required CI check in every repository (a fleet-wide policy change); the bot rosters in consumer plan configurations (retired `pr-agent` name, missing `required_bots`); re-review after a push and the missed-open-event gap in the reviewer workflow; the leftover local `feature/plan-pr-078-review-bot-fleet-opt-in` branches in the foreign checkouts.
- Operator decisions needed: the two schema decisions of deliverable 2; cutting the org release; and whether to enrol before PLAN-LB-21 reports.
- Reporting: if the host PR is empty, the plan reports through its inbox message alone, with the per-repository table of deliverables 3 to 5 as the body and one line per foreign PR with its merge commit.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-20-review-bot-fleet-rollout.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
