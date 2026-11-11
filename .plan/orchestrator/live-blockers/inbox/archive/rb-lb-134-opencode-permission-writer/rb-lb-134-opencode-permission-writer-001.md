envelope_version=1
sender_type=plan
sender_id=rb-lb-134-opencode-permission-writer
epic=live-blockers
kind=landing
created=2026-11-10T18:22:58Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-134-opencode-permission-writer
epic=live-blockers
pr=#1954
merge_state=open
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:pending,merge:pending
unresolved_review_threads=0
review_body_findings_total=0
review_body_findings_handled=0
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# Landing — PLAN-LB-134 (OpenCode 2 permission writer)

Stopped before the merge: the PR is open, CI is green, and the required reviewer has not reviewed. The blocker is CodeRabbit's own review quota (details under Reviewers); no merge was attempted.

## Deliverables

| # | Deliverable | Verdict | Order | Test(s) | Failing run |
|---|---|---|---|---|---|
| D1 | The rule writer keeps the effect it reports and knows OpenCode 2's tool name | met | mutation-after | `test_ensure_refuses_to_override_a_more_specific_later_deny` (ask + allow params), `test_the_bare_shell_tool_names_the_shell_catch_all`, `test_an_opencode1_map_write_maps_subagent_to_task`, `test_ensure_maps_subagent_to_task`, `test_configure_maps_subagent_to_the_map_task_key`, `test_fix_remove_maps_subagent_to_the_map_task_key`, `test_the_action_wildcard_decides_the_effective_effect` | `7adc28b93` + mutation, `plan-marshall/python-2026-11-10-091615.log` (22 failed) |
| D1 | wildcard-action question carries a recorded source and version | met | none | recorded in the PR body and the progress file: OpenCode 2 permission documentation read against the installed `opencode v2.2.6`, corroborated by `opencode api GET /api/agent` | — |
| D2 | A failed write and an unreadable input are reported | met | mutation-after | `test_an_unparsable_config_is_reported_and_left_untouched`, `test_ensure_reports_an_unparsable_project_file`, `test_ensure_executor_reports_an_unparsable_project_file`, `test_a_non_utf8_config_returns_the_loader_error`, `test_ensure_defaults_reports_a_failed_save`, `test_project_initial_setup_reports_an_unparsable_config`, `test_ensure_wildcards_does_not_wrap_a_failed_result`, `test_add_and_remove_work_on_an_opencode2_list`, `test_add_and_remove_work_on_an_opencode1_map`, `test_a_failed_version_probe_is_not_checkable` | same run |
| D3 | The two deny readers agree | met | mutation-after | `test_both_deny_readers_report_the_same_hybrid_deny_set`, `test_both_deny_readers_report_an_agent_scoped_deny` | same run |
| D4 | The emitted catch-alls cannot override a global deny | met | mutation-after | `test_emitted_agent_permissions_evaluate_like_the_source_tool_grants`, `test_known_tools_map_to_permissions`, `test_target_absent_tool_alongside_mapped_tools_emits_only_mapped`, `test_a_new_skeleton_carries_no_shell_catch_all`, `test_new_skeleton_is_opencode2_shaped` | `7adc28b93` + mutation, `plan-marshall/python-2026-11-10-091615.log` and `marketplace/targets/opencode/python-2026-11-10-093334.log` |
| D4 | evaluation order carries a recorded source and version | met | none | recorded in the PR body and the progress file (same source + `opencode v2.2.6`) | — |

The "holds at the base" clauses still hold: `test_a_requested_deny_outranks_a_broader_earlier_allow` and `test_a_bare_task_grant_on_a_map_file_writes_task` are green at the head.

Per-head test runs: `module-tests plan-marshall` green at `92d3381e4`, `6dd7ed230`, `3fef2d158` and `03a35cf11`; `module-tests marketplace/targets/opencode` green at `6dd7ed230`; `verify` green at `6dd7ed230` and `03a35cf11`.

## Personas and skills

* production code — `persona-implementer`; unit and module tests — `persona-module-tester` (plus its `testing-methodology` standard); every self-review round and every PR-comment triage — `persona-code-reviewer`.
* The spec declares no `Skills:`/`Persona:` lines: `skills: none named` for all four deliverables.
* `skills added: none` — no deliverable reached a module outside the Expected Surface. One test file the spec did not list, `test/marketplace/targets/opencode/test_opencode2_shape.py`, is the emitter's own shape pin and had to move with the emitted shape.

## Hypotheses

* OBSERVED `_move_rule_to_end`/`_upsert_permission_rule` moved a requested rule past a later, more specific rule — **confirmed** (`opencode_runtime.py:522-565` before the change).
* OBSERVED `to_opencode_grant` had no bare `shell` — **confirmed** (`opencode_runtime.py:336-349`).
* OBSERVED the OpenCode 1 map branches wrote the category without a map-key rename — **confirmed** (`opencode_runtime.py:1560-1576`, `1770-1774`, `1800`; `permission_fix.py:454-474`).
* HYPOTHESIS "OpenCode 2 evaluates a wildcard `action`" — **confirmed**. Source: the published OpenCode 2 permission documentation (`https://opencode.ai/docs/permissions`), read against the installed binary `opencode v2.2.6`; "Actions and resources use simple whole-value wildcards", and every agent's ruleset as returned by `opencode api GET /api/agent` starts with `{action:"*", resource:"*", effect:"allow"}`. Consequence implemented: the effective-effect computation treats the wildcard action as a match.
* HYPOTHESIS "global rules are evaluated before agent rules, so an emitted agent catch-all overrides a global deny" — **confirmed**. Same source: "lower-priority configuration is loaded first, global rules are appended next, and agent rules are appended last"; "Agent rules are appended after global rules". Same record settles that agent-markdown frontmatter permissions and `opencode.json` `agents.*` land in one effective ruleset (`GET /api/agent` shows the frontmatter-declared allows and the config-level denies for the same agent).

## Findings

Self-review: four rounds (round 4 authorized by the operator after the 3-round limit).

* Round 1 — 10 findings, 7 fixed in `92d3381e4`: the wildcard behaviour was not pinned; `_rule_exists`/`_remove_permission_rule` ignored the wildcard action; `contract.md` still described the old deny reader; two adoc sentences still claimed catch-all-first; the OpenCode 1 map remove deleted a whole category; the conflict restore was conditional; two docstrings described behaviour the code no longer had. Three kept deliberately and justified: `project_initial_setup` fails closed, `ensure` materialises an explicit rule, the skeleton exists before the read.
* Round 2 — 9 findings, all fixed in `6dd7ed230`: runtime map `remove`/`ensure` destroyed a pattern map; conflict envelopes claimed "nothing was written" after the settings path may have created a file; a failed save reported `added`; a dead branch; a false docstring; a blocked sibling was silent; ensure-defaults reported additions on its error path; the insert-point docstring; the docs' error table.
* Round 3 — 5 new findings plus one partial, fixed in `3fef2d158`: a category-wide grant replaced a pattern map in three sibling writers; a wildcard-action rule was treated as broader in every dimension; a successful removal was refused when a sibling was blocked; the conflict scan missed rules before the insert point; the partial failed-save report.
* Round 4 (operator-authorized) — round-3 findings confirmed closed; two pre-existing defects reported. **A**, "remove ignores the requested effect and can delete an `ask` row", fixed in `03a35cf11` because it is the same promise class D1 owns. **B**, "a category-wide `permission.bash` scalar is replaced by an empty map by six writers", left as residue (see Residue).

CI: green on the head (verify, gate, SonarCloud, dependency-review, generate-check). No PR review comments: both review bots refused on quota before producing anything.

## Reviewers

| Reviewer | Required | Result | Head | History |
|---|---|---|---|---|
| coderabbit | yes (`quota_limited: true`) | **refused** — no review exists | `03a35cf11` | triggered 16:21Z (`@coderabbitai review`) → refused on quota ("next included review available in 37 minutes"); re-triggered 18:20Z after the mandated 90-minute wait → refused again; escalated trigger `@coderabbitai full review` posted at 18:22Z. Attempts spent: 3 of 10. `ci pr reviews` reports 0 reviews, so the standing authorization does not apply. |
| sourcery | no (`quota_limited: true`) | **refused** — optional, does not gate | `03a35cf11` | triggered 16:21Z → "used your own review budget of 250,000 diff characters for the last 7 days ... request another review in 1 day and 9 hours" |

Next permitted trigger for CodeRabbit: not before `2026-11-10T19:50Z` (the last refusal plus 90 minutes, longer than the 34 minutes its notice offers). Steps 2–3 of the quota policy (close and re-open the PR, then ask the operator) have not been reached.

`review-gate` on the head: `merge_allowed: true` (`unresolved_review_threads: 0`, `review_body_findings_total: 0`, `review_body_findings_handled: 0`) — but the reviewer condition of the merge gate is not met, so no merge was attempted.

## Operator questions

1. "The self-review reached its 3-round limit with items still open... How should the run continue?" — options: {Run one more review round (Recommended), Proceed to the PR now, Stop the run here}; selected **"Run one more review round"**. The round was run; its two new defects were handled as described above.

No free-text operator messages. No surface/naming error needed a question.

## Rule check

* Guard: present on this harness. `{guard_log}` holds one refusal inside this run's session tree: `2026-11-10T14:33:18Z | rule=R1 | session=ses_e3a221ec4ffe39iReFI7GRZee9` — the round-4 review sub-agent chained `git diff | grep …`, which R1 refuses. It reran the read with the file tools. No other refusal is attributable to this run's sessions; the other `2026-11-10` lines in the log belong to other session trees (`ses_e3bbd50f…`, `ses_e3bbd82b…`).
* The run's own actions: every script through `python3 .plan/execute-script.py`; every build through the resolved `build` canonicals; every CI action through `ci`; no `gh`/`glab`, no build wrapper, no direct `pytest`/`mypy`/`ruff`; no `python3 -c`; no `sleep`. Files read and searched with the file tools; the only shell redirect-free writes were the `ci` body slots and `.plan/temp/`.
* One deviation from a literal reading: the round-4 sub-agent broke R1 (above); its rule break counts as this run's.
* Restarts: one server restart mid-run. The lane text was re-loaded (same source-checkout text, executor `0.1.2076`) and no completed step was re-run. One build job was re-attached after the restart, one earlier `worktree-create` call timed out after creating the worktree and was re-run, which returned `worktree_exists` with `executor_in_worktree: present`.
* Spec read: `spec_source: ledger_worktree`; no `spec_differ` marker.
* `executor-skew` verdict: `not_applicable` (source checkout; the executor maps the checkout's own scripts) — answered, recorded, not asked about.

## Build server

Setup preflight: `ready`. Every build ran routed (`mechanism=daemon_longpoll`, `requested=auto, resolved=routed`): no in-process fallback, no launch-fault retry, no `killed` job. Several submits were admitted late (a busy machine: the daemon reported `in_flight: 2, queued: 3, max_slots: 2`), and each live result was re-attached with a bounded wait rather than backgrounded. `runtime_stamp_reason` absent.

## Residue

1. **`permission.bash` scalar destroyed by six writers** (pre-existing at the base commit; the `resource == "*"` half is fixed here): `permission fix` ensure/add, `permission configure`, `permission_ensure_defaults`, `cmd_ensure`, `cmd_ensure_wildcards` and `cmd_ensure_executor` replace `{"bash": "deny"}` with a map, while the deny reader still reads it as a category-wide deny. Needs its own plan.
2. **`--dry-run` cannot predict a `permission_conflict` or a blocked removal** — the preview reports counts a real run then refuses.
3. **`contract.md` vs the loader**: a non-object JSON root is documented as fail-closed while `permission_load_settings` returns `{}`, so a writer can save a skeleton over `[1,2,3]`; and `permission configure` / `permission web-apply` return `save_error` while the contract lists `io_error`.
4. **PR not merged**: the required reviewer has not reviewed. The branch and worktree stay in place for the next session, which should resume at the quota policy (next permitted trigger `2026-11-10T19:50Z`).
