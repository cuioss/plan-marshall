# Landing Analysis: PLAN-LB-30 — Organisation CI release

epic: live-blockers
workstream: WS-04
pr: #1722 (https://github.com/cuioss/plan-marshall/pull/1722)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-30.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `plan-lb-30-org-ci-release-001.md` (kind `landing`, `landing-check`
`complete: true`). Checked against:

- `ci pr queue-state --pr-number 1722`: `pr_state: merged`,
  `merge_commit_sha: 2cb0f8c3f4f42f06b0cf4074ef7de9e45a0cf24e`, merge-group run `success`.
- `git show 2cb0f8c3f`: 5 files, 366 insertions, 4 deletions. All five were read in full
  (the two test modules at HEAD, the three other hunks from the commit).
- The local `cuioss-organization` checkout after a fetch: `git log v0.37.0..v0.40.0`; at
  `v0.39.0` the reusable verify workflow, the validator script and its test module read in
  full; from `1b9d705` (#315) the hunks of `schema.json`, `README.adoc`,
  `docs/project-yml-schema.adoc` and `update-github-actions.md`.
- The released validator run against the default branches of API-Sheriff, TokenSheriff and
  cui-http (`pw validate --repo …` in the organisation checkout; schema and validator are
  unchanged between `v0.39.0` and that checkout's HEAD). Each repository's `project.yml` was
  also read at `origin/main`.
- `ci checks status` for the two PRs that merged after this one, #1727 and #1728.
- `ci pr comments --pr-number 1722`: 15 comments, 4 review threads, read as leads and
  checked against the test code.

Not read: the plan's own archived artifacts and report (moved out of this repository), and
the foreign `test_pyprojectx_gate.py` and `test_read_config.py`.

## Deliverable Fidelity vs Spec

Deliverables are named by their source tag in the spec.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| PLAN-LB-16 D1 — contract test: no machine-local key in the tracked `marshal.json` | shipped, wider than specified, with two overclaims in its docstring | `test_committed_marshal_machine_local_keys.py` forbids `runtime` and `project_dir` plus six more top-level keys, reads both `HEAD:.plan/marshal.json` and the file on disk, and has a negative control per class including `{'runtime': {'target': …}}`. The docstring says it catches `C:/` paths and `token` keys; the path pattern has no drive-letter form and the key pattern matches only compound token names. Both were raised in review and answered "accepted" with no code change |
| PLAN-LB-20 D1 — whole-file `project.yml` validator in `cuioss-organization` | shipped-as-specified | `validate-project-config.py` validates the whole file against `schema.json` (Draft 2020-12), prints one line per violation with key path and rule, exits non-zero, has a `--repo` mode that reads the default branch through `gh`, runs through `./pw validate`, and is documented in `docs/project-yml-schema.adoc` § Validation. Tests reject an unknown `github-automation` key and a malformed version with the key path named, and pass a valid file. The spec's "reproduces the hand-read table for the 20 repositories" is answered only by the foreign PR's claim that all 24 local checkouts validate; not re-run here |
| PLAN-LB-20 D2 — one decision per failing key, applied and released | shipped; the cross-file test is weaker than specified | `auto-merge-build-timeout` is admitted as a deprecated, ignored integer; both version patterns are widened to two or three parts, and `current-version` also admits a number. Each decision is a NOTE in `docs/project-yml-schema.adoc` with its reason; the rejected alternative is implied, not named. Released as `v0.39.0`. The test that should check the four files "state the same thing" only asserts that each contains the string `auto-merge-build-timeout`, and there is no such test for the version decision |
| PLAN-LB-20 D3 — the three migrated repositories validate whole-file | done, all three pass unchanged | validator output: `remote:API-Sheriff: OK`, `remote:TokenSheriff: OK`, `remote:cui-http: OK`. All three still carry `auto-merge-build-timeout`; cui-http carries `current-version: 3.2` and `next-version: 3.3-SNAPSHOT`. They pass because the schema was widened, so no fixing PR was needed |
| PLAN-LB-16 D2 — the gate builds when a test-input path changes | shipped-as-specified; observed live for two of the three cases | `python-verify.yml` pins `@47273b80…` (the `v0.39.0` tag commit; the pin moved in #1720, not in this PR) and passes `.plan/marshal.json .claude/** marketplace/**/*.md test/**/*.md`. The reusable workflow evaluates them in a second, positive filter group and fails open on a filter error. Live: #1728 (ledger files under `.plan/orchestrator/` only) shows `verify / verify` skipped and `verify / conclusion` green on both of its runs; #1727 (one `.adoc` and two `marketplace/**/*.md` files, which the gate skipped before) shows `verify / verify` executed on both of its runs. No `marshal.json`-only PR has merged since, so that exact case is not observed. The PR body does not record the observations the spec asked for |
| PLAN-LB-16 D3 — structural test pins the caller's buildable set | shipped-as-specified, with one loose assertion | `test_python_verify_buildable_paths.py` requires `.plan/marshal.json` and `.claude/**` by exact token while `skip-on-docs-only` is true, passes when it is false or absent, and has negative controls for a missing input and for each missing path. The two Markdown globs are checked by substring, so `marketplace/**/*.mdx` would satisfy the check. Raised in review, answered "accepted", not changed |
| PLAN-LB-16 D4 — workflow comment and project instructions state what the gate does | shipped-as-specified | the workflow comment, `CLAUDE.md` § Branch Naming and `doc/developer/build.adoc` § CI each say the skip applies to `pull_request` and `merge_group` runs and list the same four paths the input passes; `build.adoc` names the same pin as the workflow |

Realized surface against the declared one: all five changed files are declared. Declared
and untouched: `.github/project.yml`, `platform-runtime/scripts/antigravity_runtime.py`,
`platform-runtime/scripts/runtime_base.py`, `test_config_defaults.py` and
`test_merge_group_trigger.py`. The two runtime files were the place to settle the spec's
first hypothesis (docstrings that still say `project_initial_setup` seeds `marshal.json`
with `runtime.target`); they are unchanged, so those docstrings stand as they were.

## Metrics and Anomalies

- Tokens: the landing facts carry `total_tokens=0`. A plan with seven deliverables and twenty
  finalize steps did not cost nothing, so this is a metrics read that returned no data, not a
  measurement. The plan ran on the Antigravity harness on a second machine.
- Duration: 4,411 seconds wall time (about 74 minutes).
- All twenty finalize steps report `done`; none reports a loop-back.
- `cleanup_owed=false`.
- The message's Residue section says `none`; this plan sent no finding and no
  candidate-lesson message.

## Routing and Merge Behavior

- Review: CodeRabbit, Sourcery and cuioss-review-bot all reviewed. Four inline findings (two
  Sourcery, two CodeRabbit), every one answered "Accepted" with a reason and no code change,
  and all four threads resolved. CodeRabbit withdrew one and repeated its objection on the
  substring check, which is correct as read here. Its closing summary still says "fix these
  checks before merging".
- CI/merge: merged through the merge queue; the merge-group run concluded `success`.
- Collisions with plans in flight: none. No file in `2cb0f8c3f` is declared by PLAN-LB-23,
  24 or 29.
- Consequence for the queue: the organisation release PLAN-LB-31 waits for exists
  (`v0.39.0`; `v0.40.0` has followed it).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-30 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-30 --field pr --value 1722`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-30 --field landing --value landings/PLAN-LB-30.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-30 --field plan_marshall_plan_id --value plan-lb-30-org-ci-release`
- [x] epic.md narrative reconciled against the queue rows (queue annotations)
- [x] Watch added: the zero token figure
- [x] Open Defect added: the contract test's two overclaims and the substring check
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated and committed with the row change

## Follow-Ups

- The contract test's docstring promises two detections its patterns do not perform, and
  the structural test checks the Markdown globs by substring. Small; recorded as an Open
  Defect, not staged.
- The foreign cross-file consistency test checks presence of a string, not agreement.
  Belongs to `cuioss-organization`; PLAN-LB-31 works in that repository next.
- The two `platform-runtime` docstrings the spec's first hypothesis names were not corrected.
