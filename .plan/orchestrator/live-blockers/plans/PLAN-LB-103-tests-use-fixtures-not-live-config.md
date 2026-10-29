# PLAN-LB-103: Tests never read this repository's own project config, and a change to `.plan/marshal.json` alone no longer forces the full verify build

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-103-tests-use-fixtures-not-live-config.md` and is queued as one row file, `queue/PLAN-LB-103.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the operator's instruction on 2026-10-29 after PR 1884 (a five-line `.plan/marshal.json` edit) ran two full verify
> builds of about 30 minutes each, because `.plan/marshal.json` is on the CI workflow's `extra-buildable` list. The operator's
> ruling: a test that reads this project's own live config is always a bug; the fix is fixtures, not a relocated lint. This is
> operator-requested work, staged above the live-blockers focus rule.

## Objective

Three test files read this repository's own committed `.plan/marshal.json` instead of a fixture, so a test result depends on
whatever the project's config says today. That coupling is the only reason the CI workflow forces the full ~27k-test verify build
for a config-only change. This plan makes the tests hermetic (no test reads the live file, and the assertions that did are
re-expressed over fixtures or removed with their reason recorded), and then drops `.plan/marshal.json` from `extra-buildable` so
a config-only change takes the footprint skip like any other non-building path.

## Deliverables

1. **No test reads this repository's own `.plan/marshal.json`.**
   - **Census first.** Run the full `module-tests` once with `.plan/marshal.json` hidden from the worktree and once with it replaced
     by an empty JSON object; the failing tests are the readers. The census is the union of those failures and the three files
     named in Claim Labels. Record the list in the PR.
   - **Convert.** For every reader, the assertion becomes a fixture test (a `tmp_path` config, or the defaults the code ships), or
     it is deleted with the property it protected written in the PR. A live assertion with no fixture equivalent gets one; the
     live read is never kept.
   - `test_branch_prefix_allowlist.py`: drive the prefix check from a fixture config (or the shipped default), not from the
     repository's file. Its helper already falls back to an empty config, so the live read adds nothing.
   - `test_config_defaults.py`: the three tests built on the committed-file constant (canonical top-level key order, every
     orchestrator knob surfaced, round-trip through `save_config` unchanged) are re-expressed over a fixture config; where a fixture
     test already covers the same property (the `save_config` key-order and the orchestrator-knob seed tests), delete the live one.
   - `test_committed_marshal_machine_local_keys.py`: delete the two tests that read the tracked file (`git show HEAD:` and the
     on-disk copy); keep the scanner and its negative control, which already run over fixtures. No replacement check is added.

   *Done when:* the full `module-tests` run is green with `.plan/marshal.json` absent AND green with it replaced by `{}`; at HEAD
   the same two runs are red in the census files. Per converted test the PR names the fixture that now asserts its property, or the
   reason it was removed.

2. **A change to `.plan/marshal.json` alone skips the heavy verify build.**
   - Remove `.plan/marshal.json` from `extra-buildable` in `.github/workflows/python-verify.yml` and rewrite the comment block above
     it so it names only the paths that remain.
   - `test_python_verify_buildable_paths.py`: the required-path set no longer contains `.plan/marshal.json`; the negative controls
     that used it as the example missing path use `.claude/**` instead.
   - Update the two docs that state the list: `CLAUDE.md` (the footprint-gate paragraph under Branch Naming) and
     `doc/developer/build.adoc` (the `skip-on-docs-only` paragraph).

   *Done when:* `test_python_verify_buildable_paths.py` passes on the changed workflow and fails on the old one; the two docs name
   the same three-path list the workflow now carries; and a draft PR from a branch whose only change is to `.plan/marshal.json`
   shows the `verify / gate` job reporting `run=false`, `verify / verify` skipped and `verify / conclusion` green. That draft PR is
   closed unmerged and never enqueued.

Split guard: two deliverables, one theme (a config-only change needs no test run because no test depends on the live config).
Deliverable 2 is unsafe without deliverable 1's census, so they ship together.

## Standing Constraints

- Operator ruling: a test that reads this project's own live config is a bug. Do not relocate the live assertions into a lint, a
  quality-gate step or a separate CI job. The one property that lived only in a live read, no machine-local keys or secrets in the
  tracked file, is dropped by this ruling; the PR records that consequence and whether anything else enforces it.
- Touch only `.plan/marshal.json` in the forced-build list. `.claude/**`, `marketplace/**/*.md` and `test/**/*.md` stay: each is a
  different file set and would need its own census.
- Do not change the lane's footprint classifier (`runbook_lane.py` `_classify_path`). Under this repository's workflow it holds no
  readable non-building rule and classifies `.plan/marshal.json` as buildable whatever the list says, which costs a local build and
  never skips one CI would run.
- A test that reads the real `python-verify.yml` (`test_python_verify_buildable_paths.py`, the D5 cases of `test_runbook_lane.py`)
  reads a workflow file, not the project config. Leave those reads; record them in the PR as an adjacent coupling for the operator.
- Every deleted assertion states what it protected, in the PR.
- Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: `.plan/marshal.json` is on `extra-buildable` and the workflow's own comment says the listed paths "are test inputs in this repository" — read at `.github/workflows/python-verify.yml` L49-58 at HEAD `3ebc134fe`.
- OBSERVED: the reusable workflow's base footprint filter already lists `!.plan/**` as non-building, so removing the path from `extra-buildable` is the whole mechanism — read at `cuioss/cuioss-organization` `.github/workflows/reusable-pyprojectx-verify.yml` at the pinned ref `711571432df351d3c5b08d5d50cb6c331f61abb1`, step "Build paths-filter spec" and step "Decide whether to run".
- OBSERVED: three test files read the real committed file — `test/plan-marshall/manage-config/test_committed_marshal_machine_local_keys.py` L122-153 (`git show HEAD:.plan/marshal.json` and `PROJECT_ROOT/.plan/marshal.json`), `test/plan-marshall/manage-config/test_config_defaults.py` L1855, L1992, L2053 and L2110 (`_COMMITTED_MARSHAL_PATH`), and `test/plan-marshall/manage-config/test_branch_prefix_allowlist.py` L33 and L44-56 (`_MARSHAL_PATH`, which falls back to `{}` when the file is absent).
- OBSERVED: `test/plan-marshall/manage-config/test_python_verify_buildable_paths.py` pins `{'.plan/marshal.json', '.claude/**'}` as the required extra-buildable paths (L27-31) and uses `.plan/marshal.json` as the missing-path negative control (L176-194).
- OBSERVED: the docs that state the list are `CLAUDE.md` L21 and `doc/developer/build.adoc` L195; `runbook-lane/SKILL.md` L568 and `runbook_lane.py` L1714 describe `extra-buildable` generally and name no path that changes.
- OBSERVED: PR 1884 ran `verify / verify` on the PR and in the merge group (1608 s and 1819 s on the PR runs), while the ledger land PR 1885, whose paths sit under `.plan/**` but not `.plan/marshal.json`, skipped the build — read through the `ci` abstraction on 2026-10-29.
- HYPOTHESIS: the three files are the complete set of tests that read the live file — about 129 files mention the path and only about a dozen were opened, the rest assumed to use `tmp_path` fixtures; confirm by the census run in deliverable 1 (verify-at-outline).
- HYPOTHESIS: each live assertion in `test_config_defaults.py` has a fixture-based equivalent already in the file — confirm `test_save_config_emits_canonical_top_level_key_order` (L1871) and `test_get_default_config_seeds_orchestrator_block_with_every_knob` (L1945) cover the key-order and orchestrator-knob properties, and that the round-trip property needs a new fixture test (verify-at-outline).
- HYPOTHESIS: the machine-local-keys property is enforced nowhere else — confirm at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py` and `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py` (verify-at-outline), and record the answer.
- HYPOTHESIS: a `merge_group` entry whose only change is `.plan/marshal.json` is skipped exactly like a pull request, because the reusable workflow applies the same footprint rule to both — confirmed by the workflow text only; no merge-group run can be observed without merging (verify-at-outline).
- Verify-first clause (D1): do the census before editing any test, and add every reader it finds to the Expected Surface below; a reader that cannot be converted without the live file is a finding against this spec, not a licence to keep the read.
- Verify-first clause (D2): read the reusable workflow at the pinned ref again before editing the list; if the pin has moved, the base footprint filter must be re-read at the new ref.

## Expected Surface

- OBSERVED: `.github/workflows/python-verify.yml` — the `extra-buildable` list and its comment (D2)
- OBSERVED: `test/plan-marshall/manage-config/test_committed_marshal_machine_local_keys.py` — the two live-file tests (D1)
- OBSERVED: `test/plan-marshall/manage-config/test_config_defaults.py` — the three committed-file tests (D1)
- OBSERVED: `test/plan-marshall/manage-config/test_branch_prefix_allowlist.py` — the fixture-config loader (D1)
- OBSERVED: `test/plan-marshall/manage-config/test_python_verify_buildable_paths.py` — required-path set and negative controls (D2)
- OBSERVED: `CLAUDE.md` — the footprint-gate paragraph (D2)
- OBSERVED: `doc/developer/build.adoc` — the `skip-on-docs-only` paragraph (D2)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none declared. If the census adds `test/plan-marshall/phase-6-finalize/test_pre_merge_gate.py` (it mentions the path once and PLAN-LB-101 edits that file), sequence this plan after PLAN-LB-101.
- Adjacent to: `runbook_lane.py` `_classify_path` and the D5 cases of `test_runbook_lane.py`, which stay untouched (Standing Constraints); the `.claude/**`, `marketplace/**/*.md` and `test/**/*.md` entries of `extra-buildable`, which stay.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-103-tests-use-fixtures-not-live-config.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
