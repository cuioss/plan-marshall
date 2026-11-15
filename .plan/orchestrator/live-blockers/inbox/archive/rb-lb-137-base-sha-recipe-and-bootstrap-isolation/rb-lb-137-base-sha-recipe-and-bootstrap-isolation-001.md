envelope_version=1
sender_type=plan
sender_id=rb-lb-137-base-sha-recipe-and-bootstrap-isolation
epic=live-blockers
kind=landing
created=2026-11-11T22:05:48Z
revision=1
amended=2026-11-12T10:16:59Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-137-base-sha-recipe-and-bootstrap-isolation
epic=live-blockers
pr=#1963
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=26
review_body_findings_handled=26
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (2 refusals in this session's guard-log lines: R7 edit-in-main-checkout, R5 execute-tool typo)

## Deliverables

All three deliverables are met as written; each Done-when clause ("fails at `9cd644892`")
was proved red at the branch base `280e6c404` (origin/main at branch time — `9cd644892` is its
ancestor and neither contains the fix) or by mutation of the committed fix, as stated.

### D1 — one base-sha evidence recipe — commit `b994fd1dd`

| Done-when | Order | Verdict | Test | Failing run | Green | Commit |
|---|---|---|---|---|---|---|
| doc test: recipe, four forbidden forms, evidence home | test-first | met | `test_the_lane_states_the_one_base_sha_evidence_recipe` | `280e6c404`, log `16f552178324415dbc3374c01a413e25` | `b994fd1dd` | `b994fd1dd` |
| doc test: landing removal/owed-cleanup + tree read first | test-first | met | `test_the_landing_requires_the_base_copy_removal_or_the_owed_fact` | `280e6c404`, log `e62a2797874d4c1dbd66ce5c646015d8` | `b994fd1dd` | `b994fd1dd` |
| `--detach` test: real detached worktree, no branch | test-first | met | `TestWorktreeCreateDetached::test_detach_creates_a_worktree_with_no_branch` | `280e6c404`, log `87181f356b2e451d924d2182e40d1f9f` | log `bdd4a60ed21042a39ebc32a42d2a169f` | `b994fd1dd` |

### D2 — bootstrap write confinement + a named unversioned executor — commit `352bdae23`

| Done-when | Order | Verdict | Test | Failing run | Green | Commit |
|---|---|---|---|---|---|---|
| ancestor `.plan/local` and inherited `PLAN_BASE_DIR` sentinel write nothing outside `project_root` | test-first | met | `TestBootstrapContainment::test_an_ancestor_plan_local_does_not_capture_the_write` + `::test_an_inherited_plan_base_dir_does_not_capture_the_write` | `b994fd1dd`, log `51da55a886654c74a118c064041e0b40` | log `8b09cb44e64e497f90024bcd118c55d5` | `352bdae23` |
| unresolvable version returns `unversioned` | test-first | met | `test_an_unresolvable_version_is_stamped_unversioned` + control `test_a_readable_version_is_stamped_without_a_reason` | `b994fd1dd`, log `95209f901c6941d2a85f9c0fb682a7c0` | log `ae2874a52e264b15ab6c7dce02a91112` | `352bdae23` |
| empty-stamp fixture names the cause | test-first | met | `test_an_empty_stamp_names_the_cause_and_the_remedy` | `b994fd1dd`, log `b6f5972ca8bf46319b862ad3b2ff0665` | log `d2005716a6a4463f8c35a4aab24c648a` | `352bdae23` |

### D3 — the thread reply's prepare flag — commit `c943eb0b6`

| Done-when | Order | Verdict | Test | Failing run | Green | Commit |
|---|---|---|---|---|---|---|
| doc test: `--for thread-reply` + no hand-written body | mutation-after | met | `test_the_lane_names_the_thread_reply_prepare_flag_and_forbids_a_hand_written_body` | `c943eb0b6` mutated, log `909a608e7da54c0b854ffc6646e383cf` (2 failed) | log `1f2eb829276643fca75b2303b79f169d` | `c943eb0b6` |
| `pr-thread-reply` message carries the command | mutation-after | met | `test_body_not_prepared_names_the_prepare_command_for_its_kind[pr-thread-reply]` | `c943eb0b6` mutated, log `909a608e7da54c0b854ffc6646e383cf` | log `e9349405216d4c28b123ce5ad8ae2016` | `c943eb0b6` |
| provider pins updated, not loosened | mutation-after | met | `test_cmd_issue_comment_body_not_prepared` (github + gitlab) | `c943eb0b6` mutated, log `909a608e7da54c0b854ffc6646e383cf` | log `3704a8e08762475eb5666d98b9d2554d` | `c943eb0b6` |

Per-head test runs on pushed heads: `b994fd1dd` (detach log `bdd4a60e…`, tools-script-executor
`b67dcc8c…`, plan-orchestrator `da51dd16…`), `c943eb0b6` (`1f2eb829…`), `58d1039fb` (verify
`d41a60f2…`, quality-gate `f28721b6…`), `3146cfee4` (full module-tests `cee5e5d0…`), `ab5969f71`
(full module-tests `4475c479…`), `b93ba6b57` (full module-tests `197e38d2…`, quality-gate
`f57fc34f…`), `50571c453` (full module-tests `c7d59e22…`, quality-gate `30ec992b…`). CI `verify`
green on `b93ba6b57` and on `50571c453`; the PR merged as `a309ce08`.

## Personas and skills

- Personas applied: `persona-implementer` for the production changes (lane text, generator,
  git-workflow, prepare_execute, ci_base, orchestrator, steward, manage-config, file_ops,
  runtime_info, pin-trap); `persona-module-tester` for every test change; `persona-code-reviewer`
  for the self-review rounds and for triaging every PR comment; `persona-documenter` for the
  reference and skill-doc updates.
- Skills per deliverable: `skills: none named` — the spec declares no `Skills:`/`Persona:` lines.
- Surface drift: none. Every changed file is named by the spec's Expected Surface or is a necessary
  consequence of it (see Residue for the list and the reason).

## Hypotheses

- D1 "a detached worktree can be built and tested through the build seam under a `{plan}-base`
  name" — **confirmed** at `build_server.py:144-162` (an explicit `--project-path` is the
  canonicalised project root; an unenrolled tree answers `disabled` and builds in-process) and
  `git-workflow.py:2472` (creation needs neither a branch nor plan metadata).
- D3 "the GitLab provider's `body_not_prepared` message needs the same mapping" — **confirmed** at
  `gitlab_ops.py:590`: it consumes `BODY_KIND_PR_THREAD_REPLY` through the same
  `ci_base.read_and_consume_body`, and both providers wrap the shared message unchanged, so one
  mapping serves both.

## Findings

- **Self-review round 1** (sub-agent over the diff): 15 findings. 11 fixed in `58d1039fb` (recipe
  named a worktree name where `--project-dir` needs the returned path; `git-workflow worktree-create`
  was not an executable notation; the bundle reference still said branch-required; the sentinel was
  read as a version by the pin-trap and by `system.provisioned_version`; two docstrings; the
  reserved-key refusal lost precedence; no cleanliness precondition on removal; an unconditional
  bootstrap claim; the detach test stubbed the seam without asserting the call). 4 reported with
  reasons (D2(b) test placement; `cleanup_owed` shared field; the intentional argparse change;
  evidence lives in the PR body by the spec's own rule).
- **Self-review round 2**: 10 findings. 7 fixed in `3146cfee4` (`cmd_generate` dropped the version
  fields; the parity arm named the sentinel as a version; steward recovery compared it as one;
  `BODY_PREPARE_COMMANDS` could drift; no symlink/containment check in the bootstrap; `--detach`
  allowed the copy-from-main executor; doc drift). 3 reported as accepted with reasons.
- **Self-review round 3**: 4 findings, reported open at the round limit (see Follow-up: all four
  closed by the operator-directed follow-up PR).
- **CodeRabbit review 1** at `58d1039fb`: 11 actionable facets — 9 inline threads + outside-diff
  (`cmd_generate` forwarding) + nitpick (manage-config fixture proof) + 3 additional (conftest
  symlink, lane reuse rule, orchestrator sentinel arm). All handled in `3146cfee4`; every thread
  replied to naming that commit and resolved.
- **CodeRabbit review 2** at `3146cfee4`: 6 inline + 1 outside-diff (symlinked `.plan` before the
  boundary). Handled in `ab5969f71`; threads replied + resolved.
- **CodeRabbit review 3** at `b93ba6b57`: 5 inline + 1 outside-diff (identity before repair, join the
  split warning, readable-vs-published reason, base-test copy step, worktree-root check, consent
  gate for an importable unversioned executor). Handled in `037cbd2c7` and `50571c453`; threads
  replied + resolved.
- Final `review-gate` on the merge head: `unresolved_review_threads: 0`,
  `review_body_findings_total: 26`, `review_body_findings_handled: 26`, `merge_allowed: true`.

## Reviewers

| Reviewer | Required | Outcome | Heads | History |
|---|---|---|---|---|
| `coderabbit` | yes (`quota_limited`, `review_complete_after_handling`) | reviewed | `58d1039fb` (marker summary), `3146cfee4` (marker summary), `b93ba6b57` (marker summary); `NEUTRAL`/skipping on `50571c453` (its included allowance was spent) | Triggered once with `@coderabbitai review`; its later reviews were automatic. Standing authorization not needed: 0 unresolved threads and 26/26 findings handled at the merge head. |
| `sourcery` | no | refused (quota) | — | `@sourcery-ai review` twice; both answered "review budget of 250,000 diff characters for the last 7 days" with a ~7h24m retry window. Optional reviewer, so no gate impact; recorded, never awaited. |

## Operator questions

1. "Self-review round 3 left 4 items open; follow-up PR?" — options: open a follow-up PR / leave
   them recorded as open. Selected: **"Open a follow-up PR"** (see Follow-up).
2. "PR #1969 cannot obtain its required CodeRabbit review (allowance exhausted; trigger, escalated
   trigger and a fresh PR all refused). How should I proceed?" — options: keep retrying / merge
   without that review (gap named) / stop and leave it open. The answer came as free text: "if there
   was at least one CodeRabbit review merge, otherwise recreate PR and re-check". No CodeRabbit
   review existed on that PR, so no merge was taken on that answer: the PR was recreated (#1969)
   and re-checked, and the review arrived after the allowance reset — the follow-up then merged on
   the ordinary gate, not on that answer.
3. No other questions were asked; no rule was bent; no required reviewer was unobtainable on the
   merged heads. No other free-text operator messages were received.

## Rule check

- **Guard**: `present`; `.plan/temp/guard.log` carries two refusals attributed to this session
  (`ses_e354c1726ffeU9vP0bS6EDHfgY`): `rule=R7` for an `edit` aimed at the main checkout (re-issued
  inside the worktree) and `rule=R5` for an `execute-tool` typo (re-issued through the executor).
- **Run's own rule breaks**, not guard-recorded: one shell file read — `tail -n 60` on a build log —
  before switching to the read tool (the log was then read with the read tool). Recorded in the
  progress file at the time.
- **Spec read**: `resolve` read `spec_source: ledger_worktree`; no `spec_differ` marker was
  reported, so the two copies either agree or the main copy is absent.
- **Executor skew**: `not_applicable` (source checkout) — answered, recorded, never asked about.
- **Builds**: every build used the default routing and resolved `mechanism=daemon_longpoll`; no
  `degraded` fallback, no launch-fault retry, no `killed` job. One explicit-bound expiry: the first
  `verify` hit `timeout_used_seconds=1242, timeout_source=explicit`, recorded, and continued with
  the split form (`quality-gate` + `module-tests`) rather than resubmitting the same bound.
- **Restarts / re-dispatches**: none. The session ran continuously; three self-review sub-agents
  were dispatched and all completed.
- **Commit trailers**: every commit and the merge commits end with
  `Co-Authored-By: plan-marshall <noreply@cuioss.de>`; one amended commit corrected a mistyped
  trailer before it was pushed.

## Build server

- Setup preflight: `ready`.
- Per-mechanism count: every build (≈50 submissions across the plan and its follow-up) resolved
  `daemon_longpoll`; zero in-process fallbacks, zero launch-fault retries, zero killed jobs.
- One bound expiry (the `verify` above), continued with the split form; the split parts were green.
- `runtime_stamp_reason`: none reported by `resolve`.

## Residue

Closed by the operator-directed follow-up (PR #1969, merge `862d6205`):

1. **preflight treated `unversioned` as a readable version** (`generate_executor.py`) — a
   `unversioned` executor plus an unresolvable manifest yielded `marshal_status: fresh` from a
   comparison against an absence. Fixed, with tests on **both** pair sides: `unknown` now, never a
   vacuous `fresh` or a false `stale`.
2. **The recipe's copy step contradicted its cleanliness precondition** — a tracked copy made
   `status --porcelain` dirty forever. Fixed: the original content is saved under `.plan/temp/` and
   copied back (file tools only — no `checkout`/`restore`), and an untracked copy is deleted.
3. **A fresh creation whose `executor_in_worktree` is `absent`** was not covered by the
   non-evidence rule. Fixed: the rule now covers creation and reuse, and forbids running the base
   tests on the assumption that a tree without an executor contains its own bootstrap. The recipe
   also serialises base-tree use through a `.plan/local/base-evidence-owner` marker, now an explicit
   `.plan/` write exception.
4. **One comment attributed an empty stamp to the current generator.** Fixed: it names a
   pre-sentinel executor.

Accepted by design, reported for the record: the sentinel literal lives as three local constants
(each naming its producer, with an identity test for the bootstrap's list); the D2(b) stamp tests
live in the generator test files (the Expected Surface authorises `test_generate_executor_behavior.py`);
`--branch` is deliberately no longer an argparse requirement; `cleanup_owed` remains the landing's
single cleanup fact; `plan-doctor` reports a leftover `{plan}-base` as a dangling worktree (now
stated in the lane text as the owed-cleanup signal).

## Follow-up (operator-directed)

- PR #1969 (`fix/lb-137-followup-round-3`) closed the four round-3 findings above; commits
  `2933c578b`, `3f8d0ed47`, `c401d0729`, `dbd8379a0` (plus merges of `origin/main`), merge commit
  `862d6205`.
- Its own cycle: CodeRabbit refused on quota on the first PR #1966 (twice plus the escalated
  trigger), the PR was closed and recreated as #1969 per the quota policy, and the review arrived
  when the allowance reset. Sourcery reviewed it (4 findings, all handled in `3f8d0ed47`), then
  approved; CodeRabbit's later rounds (2 findings in `c401d0729`, 1 in `dbd8379a0`) were all
  handled; final `review-gate`: 0 unresolved threads, 3/3 findings handled, `merge_allowed: true`.
- Gate on its merge head `04baf6df9`: local full `module-tests` green (log
  `ccae04a6024a44f0866632e8d0fc106f`), `quality-gate` green (log `aa34c6fca790447eab3d9db7635742b2`),
  CI `verify` green. Its worktree was removed and its refs pruned; main is at `862d6205`.
