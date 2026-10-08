# PLAN-LB-16: Config-only and docs-only PRs skip the test build and turn main red

epic: live-blockers
workstream: WS-04

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-30 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-16-config-only-prs-skip-verify.md` and is queued as one row file,
> `queue/PLAN-LB-16.json`, in the epic ledger. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

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

## Deliverables

1. **Contract test: no machine-local key in the tracked `.plan/marshal.json`.** A test reads the
   committed file and fails when it carries a key whose value belongs to one machine: at least
   top-level `runtime` (with `runtime.target`) and top-level `project_dir` (an absolute path).
   The forbidden set is defined once and the test also asserts, as a matched negative control,
   that the same check fails on a synthetic config carrying `{"runtime": {"target": "opencode"}}`.
   Done when: the test passes at HEAD, and fails when `"runtime": {"target": "opencode"}` is
   added to a copy of the committed file. Independent of the foreign-repo work; lands first.

2. **The gate builds when a test-input path changes.** `python-verify.yml` pins the
   `cuioss-organization` release that carries the new extra-buildable input and passes this
   repository's test-input paths: at minimum `.plan/marshal.json` and `.claude/**`, plus the
   Markdown that tests read (skill and bundle Markdown under `marketplace/`, and Markdown under
   `test/`). Done when: a PR that changes only `.plan/marshal.json` shows the `verify` job
   executed (not skipped) on its `pull_request` run and on its `merge_group` run, and a PR that
   changes only a file under `doc/` still shows `verify` skipped with a green
   `verify / conclusion`. Both observations are recorded in the plan's PR.

3. **A structural test pins the caller's buildable set.** In the manner of
   `test_merge_group_trigger.py`, a test parses `python-verify.yml` and asserts that, while
   `skip-on-docs-only` is `true`, the extra-buildable input is present and names
   `.plan/marshal.json` and `.claude/**`; when `skip-on-docs-only` is `false` or absent the test
   passes without the input (nothing is skipped, so nothing needs forcing). Done when: the test
   fails against the workflow as it stands today (opt-in on, no extra-buildable input) and
   passes after deliverable 2 — or after the interim.

4. **The workflow comment and the project instructions state what the gate does.** The comment
   above `skip-on-docs-only: true` in `python-verify.yml` currently ends "A merge_group run and
   any change touching buildable source still verify", which is false: the footprint skip
   applies to `merge_group` runs too. Rewrite it to say that a docs-only entry is skipped in the
   queue as well, and to name the extra-buildable paths and why they are listed. Check the
   footprint-gate paragraph in `CLAUDE.md` § Branch Naming and the CI text in
   `doc/developer/build.adoc` against the new behaviour and correct either if it disagrees.
   Done when: no sentence in those three files says or implies that a `merge_group` run bypasses
   the footprint skip, and the workflow comment lists the same paths the input passes.

## Claim Labels

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

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

- OBSERVED: `.github/workflows/python-verify.yml` — pin bump, the extra-buildable input, and the corrected `skip-on-docs-only` comment
- OBSERVED: `test/plan-marshall/manage-config/test_config_defaults.py` — home of the existing committed-`marshal.json` contract tests; the machine-local-key test joins them or sits beside them
- HYPOTHESIS: `test/plan-marshall/manage-config/test_committed_marshal_machine_local_keys.py` — new module for deliverable 1 if `test_config_defaults.py` is over the module size budget (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-config/test_merge_group_trigger.py` — existing structural guard over `python-verify.yml`; the buildable-set guard of deliverable 3 follows its parsing approach
- HYPOTHESIS: `test/plan-marshall/manage-config/test_python_verify_buildable_paths.py` — new module for deliverable 3 (verify-at-outline)
- OBSERVED: `CLAUDE.md` — § Branch Naming footprint-gate paragraph, checked and corrected under deliverable 4
- HYPOTHESIS: `doc/developer/build.adoc` — CI description; touched only if it states the gate's behaviour (a search for `merge_group`, `skip-on-docs-only` and `footprint` finds no match at HEAD) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py` — stale docstring "seeds `marshal.json` with `runtime.target`"; touched only if the writer check finds the docstring wrong and the plan corrects it (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — same stale docstring at § `Runtime.project_initial_setup` (verify-at-outline)

## Dependencies and Sequencing

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

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-16-config-only-prs-skip-verify.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
