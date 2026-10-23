envelope_version=1
sender_type=plan
sender_id=rb-lb-85-lane-sonar-issues
epic=live-blockers
kind=landing
created=2026-10-22T23:50:26Z
revision=1
amended=2026-10-22T23:51:17Z

Revision 2 — one added residue item, the facts block and report otherwise unchanged.

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-85-lane-sonar-issues
epic=live-blockers
pr=#1839
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.1986
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=unknown
step.sonar-roundtrip.open_issue_rules=unknown
```

guard: present

# Landing report — PLAN-LB-85, the lane reads and gates on the pull request's open Sonar issues

PR #1839, merge commit `e40f50aa1aa2a0a54291f05ae5b840fd1bfb9ca5`, base `main`.
The Sonar figure this plan exists to measure is `unknown`: the read was not taken on this run (see
§ Findings and § Operator questions — the new verbs were unreachable through the executor before the
merge, and the only bootstrap route was refused by the tool-call guard). This is a failed read, not a
clean pull request; the first landing WITH a measured figure is still to come.

## 1. Deliverables

D1 — **met**, all four Done-when clauses. Tests: `TestReadPersistsNothing`,
`TestConfirmedRead`, `TestUndecidableRead`, `TestUnconfigured`, `TestPlanlessDismissal`
(`test/plan-marshall/workflow-integration-sonar/test_read_open_issues.py`). Order **test-first**: the
suite was written and run before the verb existed, and it failed at `8c45ecd39` with
`AttributeError: module 'sonar_mod' has no attribute 'cmd_read_open_issues'`
(`.plan/local/plans/NO_PLAN/build-results/plan-marshall/workflow-integration-sonar/test_read_open_issues.py/python-2026-10-22-152054.log`).
Commit `f96d775b0`, extended by `cf467adf0`, `07b101f4a`, `142c25649`.
- read with no plan directory leaves no file behind — met (`test_read_without_a_plan_directory_leaves_no_file_behind`, before/after snapshot of the sandbox).
- open issues return count and rules with `confirmed` — met (`test_open_issues_return_their_count_and_rules`, `test_a_settled_analysis_with_no_issue_is_a_confirmed_zero`).
- unsettled analysis and rejected credential → `null` + `undecidable` + reason, not `0` — met (`test_an_analysis_that_never_settles_is_undecidable`, `test_a_rejected_credential_on_the_ce_poll_is_undecidable`, `test_a_rejected_credential_on_the_issue_fetch_is_undecidable`, plus `test_a_truncated_page_is_undecidable_not_a_short_count`, `test_a_response_without_a_usable_total_is_undecidable`).
- no Sonar configuration → `unconfigured`, not a count — met (`test_an_unconfigured_project_is_unconfigured_not_a_count`).
Evidence order note: the four clauses share one test-first red at `8c45ecd39` (the whole module
failed to import before the verb existed).

D2 — **met**, all three Done-when clauses. Tests: `test_runbook_lane_sonar.py`, `test_runbook_lane.py`.
Order **mutation-after**: the failing output came from mutating the committed fix `fdd1b70f4`
(`undecidable` admitted the merge; `resolve` reported `not_configured`) —
`.plan/local/plans/NO_PLAN/build-results/plan-marshall/runbook-lane/test_runbook_lane_sonar.py/python-2026-10-22-153436.log`.
Commit `fdd1b70f4`, extended by `1e2fb32e7`, `bd6568a26`, `07b101f4a`, `142c25649`, `f605ab49c`.
- `resolve` returns `configured` with the project key, and `not_configured` without — met (`test_resolve_reports_configured_with_the_project_key`, `test_resolve_reports_not_configured_without_a_sonar_block`; fail-closed `sonar_config_unreadable` / `sonar_config_incomplete` also pinned).
- the lane text carries the § 6 read step and the § 7 merge condition, and a test drives the resolve result through both states — met (`test_the_read_step_names_the_provider_read_and_the_gate`, `test_the_merge_condition_binds_the_merge_to_the_gate_verdict`, `test_the_gate_reads_both_states_from_a_resolve_result`; the last feeds `configured['sonar']` and `plain['sonar']` into the gate, so the text-presence test is not the whole evidence).
- a read that returns `undecidable` does not reach the merge — met at the decision the lane's § 7 binds the merge to (`test_an_undecidable_read_does_not_admit_the_merge`, `test_the_gate_verb_is_reachable_through_its_cli_surface`). The lane is prose; the mechanised verdict refuses, and § 7 makes that verdict the condition.

D3 — **not fully met as written**. Clauses 1 and 2 met; clause 3 is **not met as written**.
Tests: `test_runbook_lane_sonar_landing.py`. Order **mutation-after**: mutation of `3c8311480`
(`undecidable` and `not_configured` both rendered `0`/`none`) —
`.plan/local/plans/NO_PLAN/build-results/plan-marshall/runbook-lane/test_runbook_lane_sonar_landing.py/python-2026-10-22-154038.log`.
Commit `3c8311480`, extended by `1e2fb32e7`, `bd6568a26`, `142c25649`.
- a confirmed count carries the fact with that count — met (`test_a_confirmed_count_carries_the_measured_figure`, `test_the_facts_follow_the_resolve_state_for_a_configured_project`, `test_a_landing_carrying_the_confirmed_fact_is_complete`).
- an `undecidable` read carries `unknown` and `inbox landing-check` still reports `complete: true` — met (`test_an_undecidable_read_carries_unknown_and_never_zero`, `test_a_landing_carrying_the_unknown_fact_is_complete`, plus `test_an_unconfigured_read_carries_unknown_not_zero`).
- `inbox landing-check` reports an unchanged required-key set — **not met as written**: the clause is a preservation claim that already holds at `9a23d41e9` (`_orchestrator_inbox.py` is untouched by the diff), so its "fails at" label can never be seen failing. The property itself is pinned by `test_the_required_landing_key_set_is_unchanged` (the tuple is asserted exactly, and a Sonar key would turn it red), but under the lane's evidence rule a clause whose "fails at" was never observed leaves its deliverable not fully met.

D4 — **met**. Tests: `test_plan_spec_template_contract.py` (4 tests, section-scoped).
Order **mutation-after**: mutation of `825933926` (the phrases removed from the template) —
`.plan/local/plans/NO_PLAN/build-results/plan-marshall/plan-orchestrator/test_plan_spec_template_contract.py/python-2026-10-22-154348.log`.
Commit `825933926`.
- the template requires the Sonar line, and carries none at `9a23d41e9` — met (`test_the_deliverables_section_requires_the_sonar_open_issue_read`, `test_the_standing_constraints_section_states_how_a_dismissal_is_recorded`).
- the template requires the consumer-visible-set line, absent at `9a23d41e9` — met (`test_the_deliverables_section_requires_the_consumer_visible_set`, `test_the_template_asks_both_obligations_of_a_deliverable`).

Per-head test runs (`module-tests`, whole tree): `825933926` 31829 green · `142c25649` 31848 green ·
`5a58a69e0` 31848 green · `f605ab49c` CI verify green (1612s) and the touched modules green locally
(150 runbook-lane, 99 sonar). `bd6568a26` 31837 green. `verify` locally bound-expired once on
`bd6568a26` (1776s, `timeout_source: explicit`), so the split form ran (`quality-gate` +
`module-tests`); CI's `verify / verify` job passed on every pushed head after it.

## 2. Personas and skills

| Step | Persona applied |
|---|---|
| D1, D2, D3 (production code) | `plan-marshall:persona-implementer` (declared) |
| tests written with each deliverable | `plan-marshall:persona-module-tester` (declared) |
| D4 (documentation/template) | `plan-marshall:persona-documenter` (declared) |
| self-review rounds 1–3, and every PR comment triaged | `persona-code-reviewer` (loaded as a standard) |

Per deliverable, the domain skills the spec named — all loaded: D1/D2/D3
`pm-plugin-development:plugin-architecture`, `pm-plugin-development:plugin-script-architecture`,
`pm-dev-python:python-core`, `plan-marshall:ref-code-quality`, `pm-dev-python:pytest-testing`,
`plan-marshall:persona-module-tester`; D4 `pm-plugin-development:plugin-architecture`,
`pm-documents:ref-documentation`.

skills added: `pm-plugin-development:plugin-architecture` (already loaded) against the
`ref-workflow-architecture` and `extension-api` standards, reason: surface drift — D1's own statement
that "the provider contract is stated as two verbs" made
`ref-workflow-architecture/standards/findings-pipeline.md` and
`extension-api/standards/ext-point-triage.md` false; both now name the third verb.

## 3. Hypotheses

- `_wait_for_ce_ready` / `_fetch_issues` need no plan id and no manifest — **confirmed**
  (`sonar.py:250` signature `(project, pr, timeout)`; `sonar.py:411` signature
  `(project, pr, severities, types)`).
- `resolve` can derive `configured` / `not_configured` from `marshal.json` without a network call —
  **confirmed** (`_sonar_credential_missing`, `sonar.py:389-403`, is a credential-FILE check). The
  state itself is read from `credentials_config.workflow-integration-sonar`; a missing token surfaces
  at read time as `unconfigured` and blocks.
- the lane cannot dismiss through `post_responses` — **confirmed** (`sonar.py:718-731` queries the
  plan-scoped finding store by `plan_id`). Mechanism chosen: `sonar_rest transition --issue-key`
  (`sonar_rest.py:98-128`), already plan-less, so the provider change stayed at one verb.
- the `step.sonar-roundtrip.{fact_key}` channel is parsed for a runbook landing as for a lifecycle
  one — **confirmed** (`parse_landing_facts` reads every `key=value` line; completeness consults only
  `LANDING_REQUIRED_KEYS`, `_orchestrator_inbox.py:1500-1581`). Channel reused, no new key.

## 4. Findings

Self-review, 3 rounds (all findings fixed and re-verified except where noted):
- round 1: dismissal path untested; `_resolve_sonar` silently reported `not_configured` for a
  block with no project key; `sonar-facts` rejected `unconfigured`; docs overstated the read's
  scope; `none` sentinel undocumented; § 8 `Values` bullet contradicted the new `n/a`; two provider
  "two verbs" statements stale. Fixed in `cf467adf0`. One assertion dropped deliberately:
  `test_resolve_reports_not_configured_for_a_block_without_a_project_key` was inverted to
  `sonar_config_incomplete` (fail-closed), because the original expectation was the round-1 defect.
- round 2: D2's "both resolve states" leg was not driven by a resolve result; `sonar-facts`
  canonical block stale; `none` emitted for a non-zero count; no lane instruction for the
  `unconfigured` read. Fixed in `1e2fb32e7`.
- round 3: gate synopsis vs its new refusal; `sonar-facts` not symmetric; one-directional zero
  guard; grammar. Fixed in `bd6568a26`. **self-review: budget-exhausted** — the operator accepted the
  three-round limit with those fixes verified only by the run's own test and gate runs.

PR comments (CodeRabbit), two review rounds plus a follow-up:
- duplicate keys satisfied the key-count guard → distinct-key guard (`07b101f4a`).
- "step 7" named both a § 6 sub-step and § 7 → references qualified (`07b101f4a`).
- the CE wait could outlive the Bash ceiling → `sonar_ce_wait_timeout_seconds` resolved from
  `harness bash-timeout-ceiling` (`07b101f4a`).
- a >500-issue page was reported as a confirmed count → `paging.total` + truncation →
  `undecidable` (`07b101f4a`, tightened to "total must equal the page" in `142c25649`).
- follow-up: the unreadable-ceiling fallback still handed a 120s harness 600s →
  `sonar_ce_ceiling_unreadable`, resolved only for a configured project (`142c25649`).
- outside-diff: `--open-count 0 --open-keys K1` merged → `confirmed_zero_with_open_keys`
  (`142c25649`).
- nitpick: the CE-budget test accepted any value ≤ 540 → forced Claude target, asserts 540
  (`f605ab49c`).
SkillSpector P6/AE1 notes in the review are scanner artifacts of a skill that quotes its own
contract; no prompt or system instruction is exposed, and CodeRabbit accepted that reading.
Sourcery: quota refusal only, no findings (optional bot).

CI: green on `bd6568a26`, `07b101f4a`, `142c25649`, `5a58a69e0`, `f605ab49c`.

## 5. Reviewers

| Reviewer | Role | Result | Head(s) reviewed | History |
|---|---|---|---|---|
| coderabbit | required, `quota_limited: true` | reviewed | `bd6568a26`, `07b101f4a`, `5a58a69e0` | triggered 19:25Z, 20:36Z, 22:07Z; refused on quota at 21:26Z and 22:51Z ("Review limit reached"), recorded; standing review authorization applied on the final head |
| sourcery | optional, `quota_limited: true` | refused (quota) | — | triggered 19:25Z, refused ("review budget … 5 days and 3 hours"); optional, never gated |

Standing review authorization, per quota-limited required reviewer (coderabbit): qualifying reviews
exist on `bd6568a26`, `07b101f4a` and `5a58a69e0` with their commit ids; every finding from those
reviews is fixed in a pushed commit and every one of its threads is resolved; it was re-triggered once
after the last push (`f605ab49c`) and refused on quota at 22:51Z, recorded; every other gate
condition held on `f605ab49c` (all comments handled, build gate green, CI green).

## 6. Operator questions

1. Asked: the new verbs are unreachable through the executor (the main checkout's executor predates
   the change; the worktree has none) — how to proceed? Options: regenerate the worktree executor and
   use it; skip the read; regenerate the main executor. **Selected:** "Regenerate the worktree
   executor and use it (Recommended)".
2. Asked after the guard refused that route (R5, direct interpreter call): proceed without the read
   and record `unknown`, or stop with the PR open? Options: proceed without the read (record
   `unknown`); stop the run and leave the PR open. **Selected:** "Proceed without the read; record
   unknown (Recommended)".
3. Asked at the self-review round limit (only low/nit items left, all fixed but unverified): run a
   fourth verification round, or accept as closed? Options: run one verification round; accept as
   closed and report `budget-exhausted`. **Selected:** "Accept as closed; report budget-exhausted".

No free-text operator messages. No question was needed about the quota policy: a qualifying review
already existed, so the standing authorization governed instead of § 6 step 7.

## 7. Rule check

Guard: present. `.plan/temp/guard.log` carries four refusal lines for this run — two mine and two from
this run's self-review sub-agents:

1. `2026-10-22T16:08:08Z | R1 | ses_e9ba2d812…` (self-review round 1) — a `grep … | head` pipeline.
2. `2026-10-22T16:35:56Z | R5 | ses_e9bd2646…` (me) — `python3 …/generate_executor.py generate
   --marketplace-root {worktree}`, the operator-approved worktree bootstrap. Not retried and not
   worked around; the operator then chose to proceed without the read.
3. `2026-10-22T17:05:49Z | R1 | ses_e9b6d9f35…` (self-review round 2) — `test -f … && echo present`.
4. `2026-10-22T17:32:22Z | R1 | ses_e9bd2646…` (me) — a commit message containing backticks, read as
   command substitution. Re-issued without backticks.

Breaches I know of beyond the guard log, all reported rather than hidden:
- **Repository files edited in the main checkout** (rule: only inside the worktree). Early in D1 I
  applied the `sonar.py` edits to the main checkout by mistake, then reverted every hunk with the
  edit tool and confirmed `git status --porcelain` clean before continuing; the worktree received the
  same edits. No main-checkout change survived.
- **Shell file reads** (rule: read with the file tools): `ls` twice for directory listings and `tail`
  a few times to read build logs, plus one `wc -l`. The build-log reads were the `log_file` the build
  result names; the directory listings were avoidable.
- Every mutation used to produce a `mutation-after` failing run was reverted with the edit tool (never
  `git restore`/`stash`/`checkout --`), and `git status` confirmed a clean tree each time.
- Every script ran through the executor, every build through the resolved `build` map, every CI action
  through `ci`. No `gh`/`glab`, no direct `pytest`/`ruff`/`mypy`, no `sleep`.

## 8. Build server

Setup preflight: `ready` (registered, daemon version 1). Every build used `--execution-mode
in_process` with mechanism `in_process_fallback`, because the worktree carried no
`.plan/execute-script.py` for a daemon-routed job to re-run (`executor_absent_from_worktree`, recorded
at setup). No `killed` job. One `timeout`: `verify` at `bd6568a26` hit its 1776s bound
(`timeout_used_seconds: 1776`, `timeout_source: explicit`); recorded and replaced by the split form
(`quality-gate`, `module-tests`), not re-submitted at the same bound. No `degraded` result was
reported by any build. No `runtime_stamp_reason` was carried at landing time.

## 9. Residue

- **The Sonar figure is `unknown` for this run.** The read was never taken: the new verbs were
  unreachable through the pre-merge executor, and the worktree-executor bootstrap was refused by the
  guard. The operator authorised proceeding. Now that the change is on `main`, the next run (and the
  next `finalize-step-sync-plugin-cache` / preflight) regenerates the executor and the read works —
  `resolve` on the merged tree already reports `sonar: configured`, `sonar_project_key:
  cuioss_plan-marshall`, `sonar_ce_wait_timeout_seconds: 60`.
- **`inbox landing-check` reports this landing `complete: false`, missing only `total_tokens`.** That
  is a contract collision, not a producer gap: the lane's § 8 template prescribes
  `total_tokens=unknown` because a runbook-lane run measures no token total, and the check rejects
  `unknown` at every required key. Every runbook-lane landing is therefore incomplete on that key
  until either the lane measures tokens or the check treats the lane's honest `unknown` as its
  documented state. Worth a defect on the landing contract rather than a defect on this run.
- **Executable bootstrap gap.** A plan whose own lane text calls a verb it introduces cannot run that
  verb until the executor is regenerated; the only route that writes a worktree executor needs a
  direct `python3` call, which the guard refuses in this repo. Worth a defect: either the guard should
  permit the generator verb, or worktree creation should generate the per-tree executor.
- **`fetch_findings` keeps the >500-issue page behaviour** (it reports the page length). Only the new
  read was hardened; the producer path is unchanged.
- **`sonar_ce_wait_timeout_seconds` is pinned to the Claude target** in its resolve-level test; the
  OpenCode value (60) is covered only by the unit-level seam test, not by a resolve-level run.
- D3 clause 3 rides as **not met as written** (preservation claim), so `deliverables_done` is 3 of 4.
