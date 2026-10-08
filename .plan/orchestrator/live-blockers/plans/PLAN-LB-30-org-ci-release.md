# PLAN-LB-30: Organisation CI release: test-input paths force a verify build, and project.yml validates against a schema that says what it means

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-30-org-ci-release.md` and is queued as one row file, `queue/PLAN-LB-30.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-16, PLAN-LB-20, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

Two faults sit in `cuioss/cuioss-organization` and are paid for in this repository and the consumer fleet. The footprint gate of the reusable verify workflow skips the whole test build for a change that touches only `.plan/**`, `.claude/**` or Markdown, which here is test input, so config-only pull requests reach `main` untested and turn it red. And the `project.yml` schema rejects keys the fleet carries, with no validator anyone can run, which is why the review-bot enrolment stopped at 7 of 20 repositories. This plan adds the extra-buildable input and a whole-file validator, settles each failing key in the schema, ships both in one organisation release, pins it here, and re-validates the three repositories already migrated. The sources are one plan because they need the same foreign repository, one release and one pin bump.

### Carried from PLAN-LB-16: Config-only and docs-only PRs skip the test build and turn main red

`.github/workflows/python-verify.yml` opts in to the organization's footprint gate
(`skip-on-docs-only: true`). That gate classifies `.plan/**`, `.claude/**` and every `*.md`
file as non-building and skips the whole `./pw verify` run for a change that touches only such
paths — on the `pull_request` run and on the `merge_group` run alike — while
`verify / conclusion` still reports green. In this repository those paths are test input: the
suite reads the tracked `.plan/marshal.json`, the project-local skills under `.claude/`, and
skill Markdown. A PR that changes only such a file therefore reaches `main` with no test having
run against it, and the first full run afterwards is red for everyone. Three
`marshal.json`-only PRs (#1666, #1669, #1677) did exactly this in one day and stalled a plan
whose own tests were green for about 18 hours. This plan makes the gate build whenever a
test-input path changes, corrects the workflow comment that claims a `merge_group` run still
verifies, and adds a contract test that keeps machine-local keys out of the tracked
`.plan/marshal.json`. There is no earlier plan spec for this fix; it carries forward the
directive of lesson `2026-10-02-10-001` (component `python-verify-ci`).

### The two candidate remedies

**(a) A caller input on the reusable workflow — RECOMMENDED.** Add an input to
`cuioss-organization` `reusable-pyprojectx-verify.yml` that names extra path globs to treat as
buildable even though the static ignore list covers them; release it; pin the release in
`python-verify.yml` and pass this repository's test-input paths. The gate then gives the right
answer at its source, for `pull_request` and `merge_group` runs both, and the required check
`verify / conclusion` keeps its meaning with no branch-protection change.

**(b) An always-run job in this repository** that runs the config-contract tests regardless of
the gate. Rejected for three reasons. First, the required check is `verify / conclusion`; a new
job blocks nothing until it is added to branch protection, and it must then also report on
`merge_group` or the queue stalls. Second, there is no small set of "config-contract tests" to
run: the incidents failed 160 and 248 tests, the committed `marshal.json` is read from at least
five test modules across three skills, and about fifty test modules read the tracked `.claude/`
tree — a hand-kept selection would drift and miss the next reader. Third, it leaves the gate's
wrong answer in place and adds a second mechanism beside it.

Remedy (a) costs a foreign-repo PR, a release and a pin bump. If that release is not available
when this plan executes, the interim is `skip-on-docs-only: false` (every PR pays the full
verify) — see the verify-first clause on the interim.

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

1. **[PLAN-LB-16 D1]** **Contract test: no machine-local key in the tracked `.plan/marshal.json`.** A test reads the
   committed file and fails when it carries a key whose value belongs to one machine: at least
   top-level `runtime` (with `runtime.target`) and top-level `project_dir` (an absolute path).
   The forbidden set is defined once and the test also asserts, as a matched negative control,
   that the same check fails on a synthetic config carrying `{"runtime": {"target": "opencode"}}`.
   Done when: the test passes at HEAD, and fails when `"runtime": {"target": "opencode"}` is
   added to a copy of the committed file. Independent of the foreign-repo work; lands first.

2. **[PLAN-LB-20 D1]** **A whole-file validator that runs locally and in CI, in `cuioss/cuioss-organization`.** A script
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

3. **[PLAN-LB-20 D2]** **One recorded decision per failing key, applied in the schema and its documentation, and
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

4. **[PLAN-LB-20 D3]** **The three migrated repositories validate whole-file.** Run the validator against the default
   branch of API-Sheriff, TokenSheriff and cui-http at the released schema. Where a file still fails
   — which depends on deliverable 2's decisions; cui-http carries both a two-part version and the
   timeout key — open one PR per repository that fixes only the failing keys.
   *Done when:* the validator exits 0 for all three default branches, and the report lists per
   repository either "passes unchanged" or the PR and merge commit that fixed it.

5. **[PLAN-LB-16 D2]** **The gate builds when a test-input path changes.** `python-verify.yml` pins the
   `cuioss-organization` release that carries the new extra-buildable input and passes this
   repository's test-input paths: at minimum `.plan/marshal.json` and `.claude/**`, plus the
   Markdown that tests read (skill and bundle Markdown under `marketplace/`, and Markdown under
   `test/`). Done when: a PR that changes only `.plan/marshal.json` shows the `verify` job
   executed (not skipped) on its `pull_request` run and on its `merge_group` run, and a PR that
   changes only a file under `doc/` still shows `verify` skipped with a green
   `verify / conclusion`. Both observations are recorded in the plan's PR.

6. **[PLAN-LB-16 D3]** **A structural test pins the caller's buildable set.** In the manner of
   `test_merge_group_trigger.py`, a test parses `python-verify.yml` and asserts that, while
   `skip-on-docs-only` is `true`, the extra-buildable input is present and names
   `.plan/marshal.json` and `.claude/**`; when `skip-on-docs-only` is `false` or absent the test
   passes without the input (nothing is skipped, so nothing needs forcing). Done when: the test
   fails against the workflow as it stands today (opt-in on, no extra-buildable input) and
   passes after deliverable 2 — or after the interim.

7. **[PLAN-LB-16 D4]** **The workflow comment and the project instructions state what the gate does.** The comment
   above `skip-on-docs-only: true` in `python-verify.yml` currently ends "A merge_group run and
   any change touching buildable source still verify", which is false: the footprint skip
   applies to `merge_group` runs too. Rewrite it to say that a docs-only entry is skipped in the
   queue as well, and to name the extra-buildable paths and why they are listed. Check the
   footprint-gate paragraph in `CLAUDE.md` § Branch Naming and the CI text in
   `doc/developer/build.adoc` against the new behaviour and correct either if it disagrees.
   Done when: no sentence in those three files says or implies that a `merge_group` run bypasses
   the footprint skip, and the workflow comment lists the same paths the input passes.

## Claim Labels

Carried in source order: bullets 1 to 21 from PLAN-LB-16; bullets 22 to 38 from PLAN-LB-20; bullets 39 to 41 added at the regrouping.

- OBSERVED: the footprint gate's ignore list is static and includes `'!**/*.md'`, `'!doc/**'`, `'!.plan/**'`, `'!.claude/**'`, `'!.agents/**'`, `'!.opencode/**'`, `'!.github/project.yml'` — read at `/Users/oliver/git/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml:136-158` § step `Build paths-filter spec`
- OBSERVED: the footprint skip applies to `merge_group` runs — the input description says "Also applies to merge_group runs … a docs-only entry skips verify there too and still reports a green conclusion" (`reusable-pyprojectx-verify.yml:58-68`), the filter step passes `merge_group.base_sha`/`head_sha` (`:172-181`), and the decide step emits `run=false` before the "non-push events always run" branch (`:200-220`)
- OBSERVED: a gate-skipped run reports success on the required check — `reusable-pyprojectx-verify.yml:399-406` § job `conclusion`
- OBSERVED: the reusable workflow has no input for extra buildable paths, and its own comment says so ("there is no dynamic `extra` input on this workflow") — `reusable-pyprojectx-verify.yml:6-68` (inputs) and `:127-135`
- OBSERVED: the commit this repository pins already has the `merge_group` footprint skip, and the gate file is unchanged between that commit and the local `cuioss-organization` HEAD — `git grep merge_group b2de4107d3d53a41a7edab7e2513887c309b8237 -- .github/workflows/reusable-pyprojectx-verify.yml` and an empty `git diff --stat b2de4107… HEAD` for that file
- OBSERVED: this repository opts in with `skip-on-docs-only: true` and pins `@b2de4107d3d53a41a7edab7e2513887c309b8237 # v0.36.0` — `.github/workflows/python-verify.yml:43-50`
- OBSERVED: the caller comment claims "A merge_group run and any change touching buildable source still verify" — `.github/workflows/python-verify.yml:48-49`; this contradicts the three claims above
- OBSERVED: tests read the committed `.plan/marshal.json` — `test/plan-marshall/manage-config/test_config_defaults.py:1852` § `_COMMITTED_MARSHAL_PATH` with `test_committed_marshal_json_top_level_keys_already_canonical` (`:1989`), `test_committed_marshal_json_surfaces_every_orchestrator_knob` (`:2050`) and `test_committed_marshal_json_round_trips_through_save_config_unchanged` (`:2107`); also `test/plan-marshall/platform-runtime/test_project_steps_extraction.py:287`, `test/plan-marshall/manage-config/test_branch_prefix_allowlist.py:33`, and `_MARSHAL_JSON` in `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure_cli.py:218`, `test_finalize_orchestration_routing_core.py:77`, `test_finalize_orchestration_routing_errors.py:64`
- OBSERVED: tests read the tracked `.claude/` tree — a search for `PROJECT_ROOT / '.claude'` and `.claude/skills` under `test/` returns about fifty modules, for example `test/pm-plugin-development/cloud-plan-lane/test_build_gate_lockstep.py:70` (reads `.claude/skills/cloud-plan-lane/SKILL.md`, a file matched by both `.claude/**` and `**/*.md`) and `test/sync-harnesses/test_harness_command_parity.py`
- OBSERVED: the tracked `.plan/marshal.json` carries no `runtime` and no `project_dir` key at HEAD — its top-level keys are `plan`, `orchestrator`, `build`, `credentials_config`, `interaction_mode`, `project`, `providers`, `skill_domains`, `system`
- OBSERVED: no test forbids those keys in the tracked file. `runtime` and `project_dir` are members of `CANONICAL_TOP_LEVEL_KEY_ORDER` (`marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py:150-178`), so `test_committed_marshal_json_top_level_keys_already_canonical` passes with either present; the only `runtime.target` test, `test_marshal_json_runtime_target_is_retired_and_ignored` (`test/plan-marshall/script-shared/test_target_context.py:519`), checks that the resolver ignores the key in a synthetic file, not that the committed file lacks it
- OBSERVED: the key was committed twice by "land steward-maintained artifacts" PRs and reverted once by hand — `git log -- .plan/marshal.json` shows `e3e5f8b59` (#1669), `34948cfed` (#1677) and `0eb2b48cc` "revert runtime.target antigravity" (#1679); `test_config_defaults.py:1842-1848` records that "the `runtime` key arrived via a verify-skipped steward landing"
- OBSERVED: the OpenCode `project initial-setup` no longer writes `marshal.json` (`marshal_written: False`) — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py:250-287`; `test/plan-marshall/manage-config/test_config_write_guard.py:233,241` asserts `'runtime' not in` the config after init and after setup
- HYPOTHESIS: no current writer puts `runtime` or `project_dir` into `marshal.json`, so the contract test of deliverable 1 guards against a regression rather than against a live writer — confirm/refute at `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py` and `antigravity_runtime.py` § `project_initial_setup`, whose docstrings (`antigravity_runtime.py:157`, `runtime_base.py:384`) still say the method "seeds `marshal.json` with `runtime.target`" (verify-at-outline)
- HYPOTHESIS: the three red-main PRs were skipped by the footprint gate on both their `pull_request` and their `merge_group` run — the lesson records the red `main` and the offending PRs but not the skipped runs; confirm/refute from the `Python Verify` run list for #1666, #1669 and #1677 (job `verify / verify` conclusion `skipped`) (verify-at-outline)
- HYPOTHESIS: the Markdown that tests read is confined to `marketplace/**/*.md`, `.claude/**` and `test/**/*.md`, so those three globs plus `.plan/marshal.json` are the complete extra-buildable set and `doc/**`, root `*.md` and `*.adoc` stay non-building — confirm/refute by enumerating, from the test tree, every repository path outside `marketplace/`, `test/` and `.claude/` that a test opens (for example `CLAUDE.md`, `README.md`, `doc/`) (verify-at-outline)
- HYPOTHESIS: an all-negation spec evaluated with `predicate-quantifier: 'every'` cannot express "ignore `.plan/**` except `.plan/marshal.json`" in one filter group, so the foreign-repo change needs a second, positive filter group (default quantifier) OR-ed into the decision — confirm/refute at `reusable-pyprojectx-verify.yml:160-181` and the `dorny/paths-filter` v4 quantifier semantics (verify-at-outline)
- Verify-first clause: confirm the foreign-repo release exists before scoping deliverable 2 — read the `inputs:` block of `reusable-pyprojectx-verify.yml` at the newest `cuioss-organization` release tag. If the extra-buildable input is not released, deliverables 1, 3 and 4 still ship, and deliverable 2 becomes the interim below.
- Verify-first clause: the interim needs an operator decision. If the release is not available, the only repository-local way to stop the red-`main` incidents is `skip-on-docs-only: false`, which makes every documentation PR pay the full verify (about ten minutes on the PR and again in the queue). Ask the operator whether to ship that interim or to hold deliverable 2 until the release; do not choose silently.
- Verify-first clause: derive the extra-buildable set, do not assert it. Settle the third hypothesis by enumeration before writing the input value. If the enumeration shows the set covers most of what the gate ignores, report that to the operator: turning the opt-in off is then the simpler equivalent of remedy (a).
- Verify-first clause: confirm the input's value format against the released workflow (space-separated globs, as the sibling `paths-ignore-extra` input uses, or another shape) and its glob-safety rule before writing it; the structural test of deliverable 3 parses that same format.
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
- OBSERVED: this repository's own `.github/project.yml` holds `name`, `sonar.enabled`, `github-automation.auto-merge-build-versions` and a `cuioss-review-bot` block with packs `python` and `plugin`; by reading, it satisfies the schema — read at `.github/project.yml`
- HYPOTHESIS: the default-branch `project.yml` of each of the 20 repositories equals its local checkout for the failing keys — confirm/refute by running deliverable 1's remote mode, which reads the default branch (verify-at-outline)
- HYPOTHESIS: no workflow, script or bot in the organisation reads `auto-merge-build-timeout` from a consumer's file by a path other than the config reader, so admitting or removing the key changes no behaviour — confirm/refute by searching `/Users/oliver/git/cuioss-organization/.github/workflows/` and its scripts for the key and for a generic `github-automation` read (verify-at-outline)
- HYPOTHESIS: the release tooling handles a two-part release version end to end (tag, GitHub release name, propagation to consumers), so widening the pattern is safe — confirm/refute at `/Users/oliver/git/cuioss-organization/.github/workflows/reusable-maven-release.yml` and the propagation script it calls, and against cui-http's last release, which used `3.2` (verify-at-outline)
- Verify-first clause: deliverable 2 is two operator decisions. Present both, each with the count of repositories it touches under either choice (derived by the validator, not copied from this spec), and wait for the answer before editing the schema.
- Verify-first clause: cutting an org release is something a dispatched agent has been refused before ("production deploy"); plan for the operator to cut it, and stop at that point with the release PR ready.
- Verify-first clause: `.github/workflows/python-verify.yml` changed between `6edefac32`, the HEAD the PLAN-LB-16 claims were read at, and `64b573110` (the organisation workflows moved to v0.37.0). The carried claim that the file pins `v0.36.0` is superseded. Re-read the pin and the `inputs:` block of the reusable workflow at the pinned release before scoping; if that release already carries an extra-buildable input, the foreign change reduces to passing it.
- Verify-first clause: the carried claims name foreign checkouts as `/Users/oliver/git/<repo>`. Resolve the same repository names under the checkout root of the machine the plan runs on.
- Verify-first clause: PLAN-LB-20 D4 and D5, the enrolment of the thirteen deferred repositories and its observation, are not in this plan. They moved to PLAN-LB-31. Carried text that mentions "deliverable 4" or "the thirteen" as later work refers to that plan.

## Expected Surface

- OBSERVED: `.github/workflows/python-verify.yml` — pin bump, the extra-buildable input, and the corrected `skip-on-docs-only` comment
- OBSERVED: `test/plan-marshall/manage-config/test_config_defaults.py` — home of the existing committed-`marshal.json` contract tests; the machine-local-key test joins them or sits beside them
- HYPOTHESIS: `test/plan-marshall/manage-config/test_committed_marshal_machine_local_keys.py` — new module for deliverable 1 if `test_config_defaults.py` is over the module size budget (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-config/test_merge_group_trigger.py` — existing structural guard over `python-verify.yml`; the buildable-set guard of deliverable 3 follows its parsing approach
- HYPOTHESIS: `test/plan-marshall/manage-config/test_python_verify_buildable_paths.py` — new module for deliverable 3 (verify-at-outline)
- OBSERVED: `CLAUDE.md` — § Branch Naming footprint-gate paragraph, checked and corrected under deliverable 4
- HYPOTHESIS: `doc/developer/build.adoc` — CI description; touched only if it states the gate's behaviour (a search for `merge_group`, `skip-on-docs-only` and `footprint` finds no match at HEAD) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` — stale docstring "seeds `marshal.json` with `runtime.target`"; touched only if the writer check finds the docstring wrong and the plan corrects it (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — same stale docstring at § `Runtime.project_initial_setup` (verify-at-outline)
- HYPOTHESIS: `.github/project.yml` — this repository's own file is validated whole-file with the new validator and edited only if it fails; by reading, it passes and stays unchanged (verify-at-outline)
- HYPOTHESIS: `.github/workflows/python-verify.yml` — only if the org release of deliverable 2 must be pinned here by hand; normally the org's own pin-update PR does it and this plan does not touch the file (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none inside the epic. The pin bump and the test-input paths of PLAN-LB-16 D2 depend on the organisation release this same plan produces; cutting that release is an operator action, so the plan stops with the release pull request ready and resumes after it.
- Suggested order inside the plan: the machine-local-key contract test first (it needs no foreign work); then the validator against the current schema, the two key decisions, and the extra-buildable input, all in `cuioss-organization` and released together; then the re-validation of the three migrated repositories; then the pin bump, the structural test and the comment correction here.
- Overlaps with: none. No other plan of this epic declares `.github/workflows/python-verify.yml`, `CLAUDE.md` or `test/plan-marshall/manage-config/`.
- Feeds: PLAN-LB-31 enrols the thirteen deferred repositories against the schema this plan releases.
- May run together with: every other plan of this epic.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-16:

- Depends on: none inside the epic. Deliverable 2 depends on foreign-repo work, below.
- Foreign-repo work (repository `cuioss-organization`, checkout at `/Users/oliver/git/cuioss-organization`), to land and be released before deliverable 2:
  - `.github/workflows/reusable-pyprojectx-verify.yml` — a new `workflow_call` input naming extra buildable globs (working name `paths-buildable-extra`; the final name is the org repo's to choose), applied in the `gate` job on every event the footprint filter runs on, `merge_group` included, and failing open like the existing filter. The `skip-on-docs-only` description and the comment at `:127-135` ("there is no dynamic `extra` input") change with it.
  - `.github/actions/build-paths-filter-spec/` (`action.yml`, `build_paths_filter_spec.py`) — only if the org repo chooses to build the new spec through the shared action; today the action accepts extra *ignore* patterns only.
  - `.github/actions/read-project-config/` (`action.yml`, `read-config.py`, `schema.json`) — only if the input is also made settable from `project.yml`, as the other `pyprojectx-*` inputs are.
  - `test/workflow/test_pyprojectx_gate.py` and `docs/Workflows.adoc` (§ footprint skip, around lines 121-128 and 982-990) — the gate's own test and documentation.
  - A release, then the pin in this repository. Other consumers are unaffected: the input defaults to empty.
- Overlaps with: none. No other `live-blockers` plan lists `.github/workflows/python-verify.yml` or `test/plan-marshall/manage-config/`.
- Adjacent to: PLAN-LB-20 (`PLAN-LB-20-review-bot-fleet-rollout.md`) — also needs a `cuioss-organization` change (the `project.yml` schema) and a release. The two foreign changes touch different files; if both are ready together, one release and one pin bump here serve both.
- Adjacent to: the push-dedup skip in the same reusable workflow (`reusable-pyprojectx-verify.yml:225-241`), which can report `verify / conclusion` green on a push run for a PR that never received a `pull_request` run. A different skip reason with a different fix; left out on purpose.
- Adjacent to: the `cloud-plan-lane` build gate (`.claude/skills/cloud-plan-lane/SKILL.md` § Step 5), which keys on `*.py` only and so has the same blind spot for a `marshal.json`-only lane plan. Left out on purpose; `test/pm-plugin-development/cloud-plan-lane/test_build_gate_lockstep.py` pins that vocabulary and would need to move with it.
- Left out on purpose: retiring `runtime` and `project_dir` from `CANONICAL_TOP_LEVEL_KEY_ORDER`. Consumer projects may still carry the keys from an older seed, and `normalize-keys` would then report them as stray; the contract test of deliverable 1 constrains this repository's tracked file only.
- Left out on purpose: a guard in the steward's "land steward-maintained artifacts" flow that refuses to stage a machine-local key. Deliverable 1 catches the key in CI once deliverable 2 makes CI run for that file; a write-time guard is a second line, not the blocker.

From PLAN-LB-20:

- Overlaps with: PLAN-LB-16 on `cuioss/cuioss-organization` (it changes the reusable verify workflow there) and on `.github/workflows/python-verify.yml` here. The two org changes touch different files; if both need an org release, ship them in one release and bump the pin once. No other `live-blockers` plan touches this plan's surface.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/` — the `ci repo file read` and `ci checks logs --scope --match --job` verbs this plan uses to read foreign default branches and reviewer logs. They are used as they are. The known gap that `ci checks status` can omit a reusable workflow's nested checks (cui-http #274) is worked around by reading the run list, not fixed here.
- Foreign-repo work, `cuioss/cuioss-organization` (`/Users/oliver/git/cuioss-organization`): `.github/actions/read-project-config/schema.json`; a new validator script in the same directory; `.github/actions/read-project-config/README.adoc`; `docs/project-yml-schema.adoc`; `.claude/commands/update-github-actions.md`; `test/workflow/` (new validator tests, and `test_read_config.py` if the timeout key is re-admitted to the reader); then a release.
- Foreign-repo work, the three migrated repositories (`/Users/oliver/git/API-Sheriff`, `/Users/oliver/git/TokenSheriff`, `/Users/oliver/git/cui-http`): `.github/project.yml`, only where the released schema still rejects it.
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
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-30-org-ci-release.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
