envelope_version=1
sender_type=plan
sender_id=rb-lb-81-lb-45-completion
epic=live-blockers
kind=landing
created=2026-10-21T11:31:50Z

## What landed

PLAN-LB-81 (`lb-81-lb-45-completion`) shipped as #1832 (merged); the runtime stamp now carries the measured variant, refreshes at landing, leaves no stale stamp, and the reader is hardened.

guard: present

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-81-lb-45-completion
epic=live-blockers
pr=#1832
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
effort=unknown
plugin_version=unknown
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

## Deliverables

### D1 — the landing carries the measured variant, effort is measured where the harness measures it

- **met** — a single-model OpenCode fixture tree stamps `variant: high` and the producer writes
  `model=deepseek-v4.1-flash/high`; `test_preflight_stamps_variant_and_measured_effort`,
  `TestEmitLandingRuntimeStamp::test_emit_landing_writes_the_variant_form`; order `test-first`;
  `8a449ca83`, `python-2026-10-20-194453.log`; commit `3bfbffe90`.
- **met** — `effort: high` with `effort_source: measured`; `--effort low` does not override;
  `test_opencode_effort_is_the_measured_variant`; order `test-first`; `8a449ca83`,
  `python-2026-10-20-194453.log`; commit `3bfbffe90`.
- **not met as written** — a `mixed` tree writes the distinct `{model}/{variant}` labels: the
  behaviour already held at `137986c61` (the spec's `fails at` label is not borne out), so no
  failing run exists. `test_preflight_stamps_the_mixed_model_labels`,
  `TestEmitLandingRuntimeStamp::test_emit_landing_writes_the_mixed_list`; order `none`; commits
  `3bfbffe90`, `ad340c414`. Kept as the regression control.

### D2 — the stamp is refreshed at landing time

- **met** — a tree that gained a second model lands `model=mixed` with both labels;
  `test_refresh_stamps_a_mixed_tree_after_a_model_switch`; order `test-first`; `8a449ca83`,
  `python-2026-10-20-195335.log`; commit `1ecb1049e`.
- **met** — an unreachable landing read keeps the start value and records `measured_at_start`;
  `test_refresh_keeps_the_start_value_when_the_database_is_unreachable`; order `test-first`;
  `8a449ca83`, `python-2026-10-20-195335.log`; commit `1ecb1049e`.
- **met** — an unchanged tree yields the same value; `test_refresh_over_an_unchanged_tree_keeps_the_value`;
  order `none` (the spec labels this clause `holds at 137986c61`); commit `1ecb1049e`.

### D3 — a failed preflight leaves no stale stamp, and a failed stamp is visible

- **met** — a failed collector after a successful stamp leaves the runtime keys absent;
  `test_failed_collector_clears_a_previous_runtime_stamp`; order `test-first`; `8a449ca83`,
  `python-2026-10-20-195637.log`; commit `1ecb1049e`.
- **met** — `metadata_stamped: false` with `degraded: false` warns;
  `TestPhase1InitRuntimeStampBranch`, `test_unstamped_metadata_without_degradation_is_reported`;
  order `test-first`; `8a449ca83`, `python-2026-10-20-195958.log` (the script half held at base);
  commits `1ecb1049e`, `25c5571b7`.
- **met** — an OpenCode call without a session id returns the omission reason;
  `test_opencode_without_a_session_reports_the_omission_reason`; order `test-first`; `8a449ca83`,
  `python-2026-10-20-195507.log`; commit `1ecb1049e`.

### D4 — the database reader is robust, and the tests that guard the stamp can fail

- **met** — a database path containing `?` or `%` is read;
  `test_database_path_with_uri_metacharacters_is_read`; order `test-first`; `8a449ca83`,
  `python-2026-10-20-201456.log`; commit `3397327b1`.
- **met** — with `XDG_DATA_HOME` set the default path follows it;
  `test_default_opencode_db_path_follows_xdg_data_home` (+ home fallback control); order
  `test-first`; `8a449ca83`, `python-2026-10-20-201820.log`; commit `3397327b1`.
- **met** — the deployed-layout fixtures yield the deployed bundle's version;
  `test_flat_deployed_tree_reads_its_root_manifest` (order `test-first`; `8a449ca83`,
  `python-2026-10-20-201638.log`), `test_bundle_cache_tree_reads_the_deployed_manifest` (order
  `none`, held at base); commit `3397327b1`.
- **met** — each replaced test fails under a mutation of the code it names; order `mutation-after`;
  logs `python-2026-10-20-203107.log` (percent-encoding), `-203251.log` (XDG), `-203438.log`
  (root manifest), `-203747.log` (preflight argv), `-213255.log` (`build_version` emission),
  `-213427.log` (`executor_version` fallback); commit `3397327b1`.

`test-compile` ran against every pushed head: `3bfbffe90`, `1ecb1049e`, `3397327b1`, `ad340c414`,
`8681fcd30`, `25c5571b7`, `1715a7f13`, `9a62ed1c4`.

## Personas and skills

- Production code: `plan-marshall:persona-implementer`. Tests: `plan-marshall:persona-module-tester`.
  Every self-review round and every PR-comment triage: `plan-marshall:persona-code-reviewer`.
- Per deliverable, spec-declared skills: `pm-plugin-development:plugin-architecture`,
  `pm-plugin-development:plugin-script-architecture`, `pm-dev-python:python-core`,
  `plan-marshall:ref-code-quality`, `pm-dev-python:pytest-testing`,
  `plan-marshall:persona-module-tester`.
- Files outside the spec's Expected Surface, all load-bearing: `plan-orchestrator/SKILL.md`
  (canonical invocation for the new verb), `plan-orchestrator/workflow/preflight.md` (stamp
  contract), `platform-runtime/standards/runtime-info.md` (field docs),
  `test/plan-marshall/phase-1-init/test_phase_1_init.py` (D3 doc-contract test).
  `skills added: none` (same declared domains).

## Hypotheses

- `HYPOTHESIS` the collector reports the variant as a separate field — **confirmed**,
  `runtime_info.py` `measure_opencode_model` (the single-model branch returns `variant`/`provider`).
- `HYPOTHESIS` `emit-landing` reads only `status.metadata` and never re-measures — **confirmed**,
  `phase-6-finalize/standards/emit-landing.md` Step 1 item 5 before this change.
- Verify-first decisions recorded: the landing-time re-read lives in `emit-landing` (the last moment
  the run can be measured) rather than in a separate finalize step; no measured/self-reported
  mismatch field, because on OpenCode the measured variant wins.

## Findings

- Self-review round 1: 12 findings. Blocking: `measured_at_start` relabelled a self-reported source
  (fixed with a provenance guard + test); D1's mixed clause not met as written (reported, not
  fixed); D4's missing mutations (ran the `build_version` and `executor_version` mutations).
  Advisories fixed: stale `model_omission_reason`, mixed-effort/doc claim, stale key lists, a
  too-strong consequence, the metadata-map decline, a test disjunction, an under-constrained clear
  test. Commit `ad340c414`.
- Self-review round 2: 1 blocking — a mixed re-read relabelled a self-reported effort (fixed with an
  `effort_source == measured` guard + test); advisories (stale progress file, short comment, no
  full verify at the head) fixed. Commit `8681fcd30`.
- Self-review round 3: clear.
- CI: `verify` green at `3397327b1`, `8681fcd30`, `25c5571b7`, `1715a7f13`, and the merge head
  `9a62ed1c4` (local, 31590 passed; CI run `39586548638`).
- Sourcery on #1831: 6 findings + duplicates. Fixed: environment fallback replacing a session
  measurement (`model_origin`), mixed-tree effort overwritten, uniform effort lost on a mixed tree,
  keyword-only doc tests. Answered with reasons: stale-stamp-on-clear-failure, concurrent status
  RMW, fresh-effort discard, subprocess security (false positive). All 9 threads resolved.
- CodeRabbit on #1832: 4 findings, all fixed in `1715a7f13` (missing `model_origin` in the stamp
  list, mixed-effort wording, refresh-set partition + token constants, hardcoded optional count) and
  all threads resolved.
- Sourcery on #1832: one security-only inline comment (subprocess, false positive) answered and
  resolved.
- The first PR (#1831) was closed unmerged under the quota policy after the retry cycle; #1832
  carries the same branch and merge.

## Reviewers

- **coderabbit** (required, `quota_limited: true`): reviewed #1832 at `25c5571b7` (formal review
  `PRR_kwDOQ3xasM8AAAABTauSBg`, commit id `25c5571b74…`); the current head is `9a62ed1c4`.
  Standing review authorization applies: a qualifying review exists, every finding from it and any
  later one is fixed (`1715a7f13`) or answered, all of its threads are resolved, and it was
  re-triggered after the last push (refused "Review rate limited" at 10:42:58Z). Refusal history:
  22:11Z, 05:42Z, 07:15Z, 07:36Z (escalated trigger), 09:29Z, 10:15Z, 10:42Z.
- **sourcery** (optional): reviewed #1831 at `8681fcd30` (9 threads, all handled) and #1832 at
  `1715a7f13` (security-only, thread handled). Hard-quota refusal since 10:01Z; its check is red
  and does not gate.

## Operator questions

1. Asked: "PLAN-LB-81's spec is not on main: resolve returns invalid_spec… How do you want to
   proceed?" — options: "Land the ledger, then rerun (Recommended)", "Run against the ledger copy",
   "Stop the run". Answer was **free text**: "ledge ris landed". The ledger was verified landed
   (`8a449ca83`) before the run continued; no option was selected.
2. Free text: "retry" after the `wait-for-comments` auth failure. No question-tool call.
No other question was asked.

## Rule check

Guard refusals recorded in `.plan/temp/guard.log` for this run's sessions:

- `2026-10-20T19:39:39Z | session=ses_ea54c046… | rule=R1 | git -C … ls-tree -r --name-only HEAD -- target/opencode | head -20`
- `2026-10-20T21:01:02Z | session=ses_ea54c046… | rule=R2 | cp -a .pyprojectx .plan/local/worktrees/lb-81-lb-45-completion/`
  (refused; not retried; the generated `target/` trees made the precondition moot).
- `2026-10-20T21:10:18Z | session=ses_ea4d9ac73… (self-review sub-agent) | rule=R1 | cd … && git diff origin/main...HEAD --stat`

Everything else in section 1 was kept: all scripts through the executor, all builds in-process,
all CI through `ci`, no `gh`/`glab`, no stash/restore/rebase/force-push, one command per shell call,
temp files under `.plan/temp/`, and no edit under `.plan/` outside the sanctioned slots.

## Residue

- D1's third Done-when is **not met as written** (the mixed path held at base); D1 is therefore not
  fully met, and `deliverables_done` is 3 of 4.
- CodeRabbit never reviewed the final merge head `9a62ed1c4`; the merge rests on the standing review
  authorization for a quota-limited reviewer.
- Sourcery's check is red from its hard quota (optional bot; ~5d20h to reset).
- `effort` and `plugin_version` are `unknown` in this landing: the runbook-lane producer reads them
  from its resolve result, which supplies the harness but not the model variant or bundle version.
- `total_tokens` is `unknown` (not measured for this run).
