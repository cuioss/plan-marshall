envelope_version=1
sender_type=plan
sender_id=rb-lb-152-review-gate-single-read-cleanup
epic=live-blockers
kind=landing
created=2026-11-15T15:23:00Z

guard: present on this harness (opencode); the guard-log entries for this run's four sessions are listed in §7.

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-152-review-gate-single-read-cleanup
epic=live-blockers
pr=#1992
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2133
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=1
review_body_findings_handled=1
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

# PLAN-LB-152 — review-gate single-read cleanup

Merged as `637b5048d8426bb67e5e09f0ca1f3f3c6a003bfc` (PR #1992), branch
`fix/lb-152-review-gate-single-read-cleanup`, base `06e5da77a`.

## 1. Deliverables

### D1 — the contract and the verdict code describe only the single in-process read — met

- Behaviour clause (status-failed / `complete` false / non-GitHub project each answer
  `undecidable_read`): met. Tests `test_a_failed_read_refuses_the_merge`,
  `test_a_truncated_read_refuses_the_merge`,
  `test_a_project_that_does_not_route_to_github_is_never_read`; `order: none` (the clause says
  "hold", and these held before and after).
- `a read with no complete key answers undecidable_read and not a traceback`: met.
  `test_a_read_without_a_coverage_signal_is_undecidable`; `order: test-first`; failing run
  `06e5da77a` (the branch head was still exactly the base commit — only the test file was modified)
  `/home/oliver/.plan-marshall/marshalld/job-logs/a13830eea7864997a5e2ac2fbbd8686d.log`
  (`assert 'coverage_unavailable' == 'undecidable_read'`); passed at `9fcb684f2`.
- `a test fails if the SKILL.md reason list names a reason runbook_lane.py can no longer return`:
  met. `test_the_lane_text_names_no_reason_the_verdict_cannot_return`; `order: mutation-after`;
  mutation re-added the retired reason to the lane text, red at `9fcb684f2`
  `/home/oliver/.plan-marshall/marshalld/job-logs/4b3354fbac604fa782378f9ac768c1b3.log`
  (`named in the lane text but unreachable: ['coverage_unavailable']`); green at `9fcb684f2`.
- Commit `9fcb684f2`.

**Correction recorded against the spec:** the Done-when lists "a read with no `complete` key answers
`undecidable_read`" among the behaviours that "hold at `2bf7cd83d`". It does not — at base that read
answered `coverage_unavailable`, which is the red run above. The Standing Constraint "the only new
verdict is `undecidable_read` where there was a traceback" is therefore wrong too: a second
`undecidable_read` replaces `coverage_unavailable`. Neither input is reachable by a real read, so no
verdict a real read can produce changed.

### D2 — a failing flatten is classified, the import placement is pinned — met

- Non-dict comment entry answers `undecidable_read` through `review-gate`:
  `test_a_comment_entry_that_cannot_be_flattened_is_undecidable`; `order: test-first`; failing run
  `9fcb684f2` (D1 committed; D1 does not touch the flatten path)
  `/home/oliver/.plan-marshall/marshalld/job-logs/d01854192054480dafe161da94aa6e94.log`
  (`TypeError: 'str' object is not a mapping` escaping `_review_gate_verdict` with no verdict);
  green at `e4edfa599`. The test also pins the guard's own `display form` detail.
- Import-placement pin: `test_the_read_classifies_an_unimportable_provider_module`;
  `order: mutation-after`; mutation hoisted the two imports above the `try` at `e4edfa599`
  `/home/oliver/.plan-marshall/marshalld/job-logs/f47c8b784bcc4d9db029566415d03909.log`
  (`ModuleNotFoundError: import of ci_base halted; None in sys.modules` escaped); green at
  `e4edfa599`.
- Commit `e4edfa599`.

### D3 — the tests own the machine state — **not met as written** (one sub-clause)

- `the review-gate and shape-table tests pass from a temporary directory with no .plan/marshal.json
  above it`: met. `test_the_gate_fetches_the_surface_once_and_spawns_no_cli` and
  `test_the_lane_column_does_not_depend_on_a_project_configuration`; `order: mutation-after`;
  removing each provider fixture at `a548c6818`:
  `/home/oliver/.plan-marshall/marshalld/job-logs/fd1ccd9a2fad4bfe983de91235d57a65.log`
  (`assert [] == [7]` — the gate stopped at `undecidable_read` before the fetch) and
  `/home/oliver/.plan-marshall/marshalld/job-logs/cc3180c71dfa4f05b15434015f4e7fe3.log`
  (`assert False is True`); green at `a548c6818`.
- `a second read routed through run_cli fails the single-fetch pin`: met.
  `test_the_no_cli_pin_trips_for_a_read_routed_through_run_cli`; `order: mutation-after`; with the
  pin reverted to `raise AssertionError` at `a548c6818`
  `/home/oliver/.plan-marshall/marshalld/job-logs/39bf9bc5d96b4f829ad635d33376298d.log`
  (`Failed: DID NOT RAISE Failed`); green at `a548c6818`.
- `ci_base.get_default_cwd() is the same value before and after the whole review-gate test module`:
  **not met as written, `order: none`.** No failing run exists and none can be produced:
  `test/conftest.py::_reset_ci_default_cwd` (autouse, function-scoped) clears that value on both
  sides of every test, and the mutation that removed `restore_default_cwd` from the leaking test
  stayed green
  (`/home/oliver/.plan-marshall/marshalld/job-logs/14a227d5587647c49d784d724fe7b21e.log`). The
  criterion was neither narrowed nor reworded; it is reported not met, so this deliverable does not
  count. D3's per-test `restore_default_cwd` bullet is implemented as written.
- `the quoted-marker shape table and its matched control keep their verdicts`: holds; both green.
- Commit `a548c6818`.

### D4 — the wording is current-state only — met

`order: none` (the clause says "holds at `2bf7cd83d`", not "fails at"). The named docstrings —
`github_re_review.py` (refusal record), `_github_pr.py` (`review_coverage_names_commit`), the
single-fetch test, `test_finished_review_one_reader.py` — each state their rule in the present tense,
as does a fifth paragraph in the same `github_re_review.py` region. The existing documentation pins
in `test/plan-marshall/automatic-review/test_review_complete_after_handling_docs.py` pass. Commit
`c3179ea0f`, extended by the self-review and CodeRabbit wording corrections in `6331a962f` and
`4a35735f4`.

### Per-head test runs

`module-tests plan-marshall` (plus `verify` where noted) ran at every pushed head:
`9fcb684f2`, `e4edfa599`, `a548c6818`, `c3179ea0f`, `6331a962f`, `7819315da`, `4a35735f4` — all
green. `verify` ran at `c3179ea0f`, `7819315da`, `4a35735f4` — all green
(`.../job-logs/5a35cd5764314c87a570552f619a8195.log`, `.../b57678e9978a40d98b0c92535270d072.log`).

## 2. Personas and skills

| Step | Persona | Domain skills |
|---|---|---|
| D1 | `persona-implementer` | `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`, `pm-plugin-development:plugin-architecture` |
| D2 | `persona-implementer` | `pm-dev-python:python-core`, `pm-dev-python:pytest-testing` |
| D3 | `persona-module-tester` | `pm-dev-python:pytest-testing`, `plan-marshall:persona-module-tester` |
| D4 | `persona-documenter` | `pm-documents:ref-documentation` |
| every self-review round, every PR-comment triage | `persona-code-reviewer` | — |

`skills added: none, reason: the run touched no module the Expected Surface did not name.`

## 3. Hypotheses

- **`coverage_unavailable` in the `manage-tasks` freshness scripts is their own reason, not a read of
  `review-gate`** — **confirmed**: `_freshness_crosscheck.py:1447` is its own keyword argument and
  `_cmd_pre_commit_verify_freshness.py:792` passes its own `coverage_reason`; no consumer of the
  gate's reason exists outside the lane and its test.
- **`forbid_run` (`AssertionError`) does not trip for a read routed through `ci_base.run_cli`** —
  **confirmed**: `ci_base.py:915` catches every `Exception` and returns a failure tuple, so the pin
  now raises `pytest.fail`, and a companion test pins that escape.
- **The two `manage-tasks` scripts move only if that hypothesis is refuted** — not moved.

## 4. Findings

- **Self-review round 1** (9 findings): fixed the unfalsifiable module-scope cwd fixture, the
  "one seam" statements, both directory-independence docstrings, the refusal-record paragraph, and
  the missing `disposition_unparsable`; accepted as reporting-only the D1 base-claim correction and
  the explicit `mutation-after` statement; accepted that D3 is not met as written; refuted the
  `PLAN_MARSHALL_HOME` clause (no such fixture exists in any conftest, and the new tests touch no
  machine-global state). Commit `6331a962f`.
- **Self-review round 2** (3 findings): both hand-rolled temp-directory fixtures deleted in favour of
  conftest's `outside_repo_dir`; the seam sentences quantify the noun; the flatten test pins the
  guard's own detail string. Commit `7819315da`.
- **Self-review round 3**: nothing open.
- **CodeRabbit** (1 inline thread, `Minor · Functional Correctness`): the refusal-record sentence
  overstates — the authorship, head-reference and trigger-time tests run ahead of the refusal test,
  so a review they drop is skipped with no record. Accepted as a documentation defect: the code order
  is untouched (reordering would add refusal records the envelope does not carry today, which the
  Standing Constraints forbid) and both sentences now bound what the record covers. Fixed in
  `4a35735f4`; thread `PRRT_kwDOQ3xasM63qDEr` replied and resolved.
- **Sourcery**: refused on quota (250,000 diff characters over the last 7 days; next allowed in
  3d13h). Optional reviewer, no findings, does not gate the merge.
- **CI**: green on both heads (`7819315da`, `4a35735f4`).

## 5. Reviewers

| Reviewer | Required | Outcome | Head reviewed | History |
|---|---|---|---|---|
| `coderabbit` | yes | reviewed; 1 finding, handled | `7819315da` (marker `kind=reviewed` naming that head) | triggered once at PR open; refused a second review ("Already reviewed the last commit"), which `review_complete_after_handling` + the handled finding make unnecessary — no trigger posted for `4a35735f4`, and its CI check reports NEUTRAL on that head |
| `sourcery` | no | refused | — | triggered once at PR open; quota refusal, recorded; not re-triggered |

The merge gate's review condition was satisfied by **done** for `coderabbit`:
`review-gate --required-reviewer coderabbit` answered `merge_allowed: true` / `all_handled`, with
the finding handled and its thread resolved.

## 6. Operator questions

**None asked.** No question-tool call was made in this run; no operator free-text messages either.
No model or effort switch occurred.

## 7. Rule check

- **Guard:** present on this harness. `{guard_log}` is `.plan/temp/guard.log`; this run's session tree
  is four sessions (the lane's own plus three self-review sub-agents), and the log carries five
  entries for them:
  - the lane's session, R1: one `git commit` whose message contained parentheses — refused, the
    command was re-issued without them and succeeded;
  - round-2 sub-agent, R5: one `python3 -c` (inline Python) — refused;
  - round-2 sub-agent, R1: one `git ls-files … | head` — refused;
  - round-3 sub-agent, R1: one `git rev-parse …; git status` — refused;
  - round-3 sub-agent, R4: one direct `.pyprojectx/venvs/.../bin/python -m pytest` call — refused.

  Section 5 of the contract makes a sub-agent's rule break the lane's, so all five are the run's.
- **Self-detected, not in the guard log:** one shell `grep -c … .plan/temp/guard.log`. The Shell rule
  requires the file tools for reading and searching; the guard does not enforce that particular
  clause, so it recorded nothing. The search was re-issued through the file-search tool.
- **Deviation from the base-sha recipe:** the Evidence rule names a detached `{plan}-base` worktree as
  the way to prove a "fails at `{sha}`" clause. This run did not create one; it captured the failing
  runs on the branch's own working tree before the fix was applied, and reported each by commit and
  log path. For D1 that is the base commit exactly (`06e5da77a`, test file only modified). For D2's
  flatten red it is base + D1 (`9fcb684f2`), and D1 does not touch the flatten path. The D3 clauses
  are `mutation-after`, which the rule defines as mutating the committed fix and for which no base
  tree applies. No `git clone`, no raw `worktree add` and no hand-run generator was used.
- **No restarts, no killed sub-agents.** Three self-review dispatches; the second was a fresh session
  because the attempt to continue the round-1 session was rejected for a missing argument, and it
  re-ran the review from scratch.
- **Builds:** 31 routed builds, all `mechanism=daemon_longpoll`, no in-process fallback, no launch
  fault, no `killed` job. One build (`quality-gate` before the round-2 fixes) returned `error` because
  ruff auto-reformatted blank lines and asked for a re-run; it was re-run green, and that is recorded
  as a red build, not a routing event.
- **Spec read:** `spec_source` was `ledger_worktree` at both resolve calls, and no `spec_differ`
  marker was returned, so no older copy was read silently.
- **Executor skew:** `not_applicable` (a source checkout — the executor maps this checkout's own
  scripts, so the lane text cannot name a verb the mapped script lacks). Answered, recorded, never
  asked about.
- **Model/effort switches:** none.

## 8. Build server

- Setup preflight on the worktree: `ready` (registered). The project's own state at resolve was also
  `ready`.
- Per-mechanism count over the run: `daemon_longpoll: 31`, `in_process_fallback: 0`.
- Fallbacks and retries: **none** — no `degraded` result, no `executor_absent_from_worktree`, no
  launch-fault retry. The worktree carried its own executor (`executor_in_worktree: present`) and
  `build-routing` answered `auto` before every routed build.
- Killed jobs: none.
- Several builds waited in the daemon queue (`queued_seconds` up to 107) and four returned a live
  `running` status that was re-attached with a bounded `wait` in the same call — never backgrounded.
- `runtime_stamp_reason`: absent — every stamp fact was measurable.

## 9. Residue

- The three out-of-scope items the spec names remain untouched and are stated in the PR: the
  CAUTION-shape review-body parser defect; the hex-word placeholders that still pass
  `review_coverage_names_commit`; `Path.resolve()` in `resolve_ci_provider` following symlinks.
- The refusal-record ordering CodeRabbit found is documented and deliberately not reordered in this
  plan; it is a candidate for the parser-defect follow-up.
- No base worktree, no leftover worktree and no un-pruned ref: `cleanup_owed=false`.
