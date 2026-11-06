envelope_version=1
sender_type=plan
sender_id=rb-lb-117-execute-handback-fix
epic=live-blockers
kind=landing
created=2026-11-06T05:04:19Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-117-execute-handback-fix
epic=live-blockers
pr=#1918
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2062
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# PLAN-LB-117 — landing report

PR #1918 merged as `c394a95fb63fb2ea151db569fcf7368465ef3b39`.

## 1. Deliverables

All five deliverables are fully met.

**D1 — a stall beside a hand-back is still decided, and the hand-back's step ids are checked — met.**
- *"a fixture with one hand-back on an owed task and one stalled non-owed task is classified `error` with the decision line written (red against the code at `051fda6a0`)"* — met, order **test-first**; test `TestTheHandbackExemptionCoversOnlyTheOwedTaskItNames::test_a_stall_beside_a_handback_is_classified_error`; failing run base `29f3b5417`, build log `70adb1abb78a4665abeb546797e6ea52` (base returned `verification_handback`); commit `0c12cf317`. The decision line is the orchestrator's (`execution.md` § B7, `classification_reason: no_progress_predicate_holds_beside_handback`), as the workflow prescribes.
- *"a fixture with the hand-back alone stays `verification_handback`"* — met (control, green at base); `…::test_a_handback_alone_stays_the_handback_cause`; commit `0c12cf317`.
- *"a hand-back naming a step id outside the manifest's list does not exempt (red at base)"* — met, order **test-first**; `…::test_a_handback_naming_a_step_outside_the_manifest_does_not_exempt`; failing run `29f3b5417`, build log `70adb1abb78a4665abeb546797e6ea52`; commit `0c12cf317`.
- *"the spec's two statements are reconciled in the code's order and in `execution.md:242`"* — met; `execution.md` § B7 now states the scoped exemption and the two-case trigger, and `phase-5-execute/SKILL.md` points at it. Commits `0c12cf317`, `1163e4145`, `640013e69`.

**D2 — `completed_tasks_delta` has a source, and an absent input is not zero — met.**
- *"a fixture shows a dispatch that completed tasks and consumed more than 50,000 tokens beside a non-owed in-progress task is not `error` when the delta is supplied (red at base for the unsourced `0`)"* — met, order **test-first** for the red half; `TestCompletedTasksDeltaHasAStatedSourceAndNoZeroDefault::test_a_supplied_delta_keeps_a_progressing_dispatch_out_of_error` (control, green at base because the supplied path already short-circuits the second conjunct); the red-at-base evidence is the unsourced-`0` pair below; commit `0c12cf317`.
- *"`--consumed-tokens` alone returns the named error"* — met, order **test-first**; `…::test_consumed_tokens_without_the_delta_is_a_named_error` and `…::test_the_delta_without_consumed_tokens_is_the_same_named_error` (`status: error, error: no_progress_not_decidable`, queue verdict preserved as `queue_status`, added in `a5d23e4ed`); failing run `29f3b5417`, build log `2b8f357173134b40a9fcce9eeeacd68c`; commit `0c12cf317`.
- *"the `execution.md` line names a source that exists in the row or the call"* — met, order **none** (doc read); the row carries no done count (`manage-metrics/standards/data-format.md` § Per-Dispatch Context-Load Attribution, ten columns), so the source named is the call's `done_count`; lines read: `execution.md:239-241`, `manage-tasks/SKILL.md` § Loop-Exit Guard; commit `0c12cf317`, refined in `a5d23e4ed`.

**D3 — the owed rung is defined once, and the unmeasured arm is tested on the leaf side — met.**
- *"the definition appears once and the other texts point at it"* — met, order **none** (doc read); `manage-execution-manifest/SKILL.md` § "The owed rung — one definition." (command, per-task hold, per-arm table); `execute-task/SKILL.md` Step 5(b) reads the stamp and cites it; `TestTheContractIsDefinedOnceAndTheLeafPointsAtIt` pins both; commit `ead1c5681`.
- *"the leaf-side fixture fails against a stub that puts the hold on a single task"* — met, order **mutation-after**; `TestTheUnmeasuredArmHoldsOnEveryTaskOfTheGroup` vs `TestTheMeasuredOverCeilingArmDefersToTheChainTail`; failing run by mutating the leaf to hold only a `chain_tail` task, commit `ead1c5681`, build log `2361539bea5b4844ae54eda95d2c6ac0`; commit `ead1c5681`.
- *"the unmeasured-key read is shown in the PR as confirmed or refuted, and a refutation drops the third bullet"* — **confirmed** (so the bullet stands): `_cmd_client_build.py:400` compared the stamp without `measured`, and on a target whose ceiling sits below the engine floor every unmeasured stamp lands above it. Fixed by making `exceeds_bash_ceiling` state a measured stamp's relation to the ceiling; order **mutation-after**; `test_unmeasured_never_claims_a_ceiling_overflow`; failing run by reverting the gate, commit `ead1c5681`, build log `894ddc16ab5b48c0b2b786e883e1e80b`; commit `ead1c5681`.

**D4 — the manifest keeps one tail command per deliverable — met.**
- *"a two-module deliverable fixture keeps the first command in `owed_rung_command` and exactly one `chain_tail`"* — met, order **mutation-after**; `TestTheManifestKeepsOneTailCommandPerDeliverable::test_a_second_rung_command_does_not_overwrite_the_first`; failing run `ead1c5681`, build log `2361539bea5b4844ae54eda95d2c6ac0`; commit `ead1c5681`.
- *"a re-measured module B does not clear module A's stamps"* — met, order **mutation-after**; `…::test_a_remeasured_module_clears_only_its_own_stamps`; same failing run; commit `ead1c5681`.
- *"a group whose task depends on an outside task puts the tail after it"* — met, order **mutation-after**; `…::test_a_group_ordered_through_an_outside_task_puts_the_tail_last`; same failing run; commit `ead1c5681`.
- *"a record with `verification: null` is read without error"* — met, order **mutation-after**; `test_a_record_with_null_verification_is_read_without_error`; failing run `ead1c5681`, build log `3a75c93c16ea4759857f9a72254d4ed5`; commit `ead1c5681`.

**D5 — the documentation lines that contradict each other agree — met.**
Order **none** (doc read; corroborated by doc-contract tests). Lines read:
- `execution.md:207-208` — the `voluntary_checkpoint` row now covers the `verification_handback: true` + empty-list shape that previously matched no row, and the hand-back row states the scoped exemption and the B7 override (commit `0c12cf317`, refined in `d1499d8fa`).
- `phase-5-execute/SKILL.md:1394` — "These two are the only yields that are NOT error handling", naming all four TASK-boundary points and no longer calling the other two error paths (commit `02c17353b`, refined in `640013e69`).
- `phase-6-finalize/SKILL.md:925` — states the DECISION log the marker is read from, as current behaviour (`02c17353b`).
- `phase-6-finalize/SKILL.md:929` — the cross-surface alignment claim removed; the retrospective reads `script-execution.log` and carries no copy of the marker (`02c17353b`).
- `_signal_scan.py:15` — the transitional class-3 paragraph rewritten as current state (`02c17353b`).
- `manage-metrics.py:126` — the `verification_handback` comment states the behaviour, not its history (`02c17353b`).

Per-head test runs against pushed heads: `module-tests` 32,761 tests green on `02c17353b`; full `module-tests` on `7bfd4c38e18849da886508115202c447` failed only on the plugin-doctor historical-prose rule (fixed in `277023ac5`); `verify` green on `10e9c11d4` (log `f41fd3425d9f4182a03facdfa8b74682`), on `d1499d8fa` (log `5a9baacc7aa54da5998eb6a706a5839f`), on the merged tree `f2ac8d61a` (log `9ea50098c537460b91cc3d30ea917d96`) and on `a5d23e4ed` (log `58b20248f4cb4345a2810d639bb666d1`).

## 2. Personas and skills

- Production code (D1, D2, D4 scripts; D3's `_cmd_client_build.py` change): `persona-implementer`.
- Unit and module tests (all fixture work): `persona-module-tester`.
- Documentation (D5, and every doc sweep in the review rounds): `persona-documenter`.
- Self-review rounds and every PR-comment triage: `persona-code-reviewer`.
- Each deliverable: `skills: none named` — the spec declares no `Skills:`/`Persona:` lines.
- No skill was added for surface drift; the spec's Expected Surface covered every touched module.

## 3. Hypotheses

- *"the row `record-dispatch-boundary` writes carries no done count"* — **confirmed**. `manage-metrics/standards/data-format.md` § Per-Dispatch Context-Load Attribution lists ten columns (`timestamp`, `termination_cause`, `total_tokens`, `tool_uses`, `duration_ms`, four context-load columns, `step_id`); none is a done count. D2's source is the `done_count` field the `loop-exit-guard` call reports.
- *"a configured, unmeasured key can reach `exceeds_bash_ceiling` above the ceiling"* — **confirmed**. `_cmd_client_build.py:400` compared `bash_timeout_seconds > ceiling` without consulting `measured`, so any target whose engine floor plus buffer exceeds its ceiling (the OpenCode 120 s ceiling is below every pyproject floor) reports `true` for an unmeasured command; the chain-tail deferral keys on exactly that flag.
- *"the chain order ignores dependencies through outside tasks and a `verification: null` record occurs"* — **confirmed for the ordering defect** (`_chain_order` consulted only dependencies inside the group set, at the pre-fix line `manage-execution-manifest.py:1250`), and the `null` record is **handled without needing to occur**: the pre-fix read `task.get('verification', {}).get('owed_rung')` raises `AttributeError` on a `null` record, so the guard is now defensive (`_cmd_step.py:149-151`).
- *"`phase-5-execute/SKILL.md:136,1373` and `phase-6-finalize/SKILL.md:929` read as the report says"* — **confirmed**; the four-point statement at `:136`, the three-terminal-outcome text at `:1373` and the "keeps consistent with the retrospective" claim at `:929` were all present as described.

## 4. Findings

**Self-review (four rounds, operator-approved fourth).**
- Round 1: 1 blocker (the B7 trigger did not cover hand-back returns, so D1's behaviour could not fire end-to-end), 2 defects (a missing D2 fixture; the two hand counts against the standing constraint), 9 documentation defects (the blanket-exemption claim still stated in five files, "error-path" wording, a false test docstring, `pyproject-impl.md`, the missing `done_count`/`verification_handback_unknown_steps` contract), 3 preferences (one accepted as a design decision: `exceeds_bash_ceiling` redefinition; two fixed), 4 info (two files outside Expected Surface — both genuinely required; two notes recorded). All fixed in `1163e4145` except the design decision and the info items.
- Round 2: 1 blocker (the widened trigger would have reclassified a legitimate `budget_yield` as `voluntary_checkpoint`), 1 defect (stale command-inventory row), 4 preferences — all fixed in `640013e69`.
- Round 3: 2 defects (a residual "every non-error return" sentence; a false "every field zero-valued" clause) — fixed in `10e9c11d4` after the round limit.
- Round 4 (operator-approved): `NO FINDINGS OPEN` → **self-review: clear**.

**PR review — CodeRabbit.**
- Review of `10e9c11d4`: 1 actionable inline (`_signal_scan.py:20` — the marker and its log type were asserted separately, so a B7 section could move the marker to another subcommand and still pass) and 2 nitpicks (`_int_arg` accepting `bool`; the hand-back row not naming the B7→`error` override). All three fixed in `d1499d8fa`; the inline thread replied to and resolved.
- Review of `f2ac8d61a`: 1 outside-diff finding (`execution.md:240` — the `0` substitution for `consumed_tokens` conflicts with the not-decidable contract) and 2 nitpicks (a not-decidable refusal overwrites the queue verdict; the broad `except Exception` in the manifest read). All three fixed in `a5d23e4ed`: the asymmetry is now stated with its reason (a `0` token figure can only suppress a reclassification, never manufacture one), the refusal reports `queue_status`, and the read catches the resolver's own errors.

**CI.** One red run: the plugin-doctor whole-tree rule (historical prose in `manage-execution-manifest/SKILL.md`) — fixed in `277023ac5`. Everything else green.

## 5. Reviewers

| Reviewer | Role | Outcome | Head reviewed | Trigger / wait history |
|---|---|---|---|---|
| coderabbit | required (`quota_limited: true`) | reviewed | `10e9c11d4` (02:22Z), `f2ac8d61a` (03:28Z) | triggered 22:39Z (refused, "next available in 38 min"); re-triggered 00:22Z as the escalated `@coderabbitai full review` (refused, "next in 11 min"); waited the 90-minute policy window and re-triggered 02:17Z (accepted → review of `10e9c11d4`); refused on `d1499d8fa` (02:32Z) and on `a5d23e4ed` (03:59Z, after the base merge and the finding fixes) |
| sourcery | optional (`quota_limited: true`) | refused | — | triggered 22:40Z; own review budget of 250,000 diff characters exhausted for 7 days |

**Standing review authorization (quota-limited reviewer, § 7).** Applied for the final head `a5d23e4ed`:
1. **qualifying review exists** — the summary comment's `final_review_risk_coverage` marker for the `f2ac8d61a` review reads `{"sourceCommitId":"f2ac8d61aeefdeef4cccd32993428bc8fd1befab","coveredCommitId":"f2ac8d61aeefdeef4cccd32993428bc8fd1befab","kind":"reviewed"}`, and `f2ac8d61a` is one of this PR's heads. (The marker is owned by `_github_pr.review_coverage_verdict`; this project's executor surface exposes no CLI verb for that reader, so it was read verbatim from the comment — the field values are quoted above.)
2. **every finding handled** — all six findings from the two reviews are fixed in pushed commits (`d1499d8fa`, `a5d23e4ed`), and the reviewer's one thread is replied to and resolved.
3. **re-triggered once after the last push** — triggered on `a5d23e4ed` at 03:59Z; refused; recorded.
4. **every other gate condition holds on the current head** — `verify` green, CI green, Sonar not configured, no unresolved thread, no other required reviewer.

## 6. Operator questions

1. **"The self-review has used its three rounds. Round 3 reported two editorial findings … I have fixed both, but no fourth pass has verified them. How should the run proceed?"** — options: *Run a 4th review round* / *Proceed, report budget-exhausted*; **selected: "Run a 4th review round"** (round 4 returned `NO FINDINGS OPEN`).

No free-text operator messages were received in this run.

## 7. Rule check

- **Guard state:** `guard: present` on this harness; the audit log is `.plan/temp/guard.log`. Two refusals are attributed to this run's session (`ses_e53512e42ffeaAUp1QachsU1SX`) and were self-corrected:
  - `R5` (17:21Z) — an executor call issued with the shell in the ledger worktree instead of the main checkout; re-issued from the main checkout in the required relative form.
  - `R7` (17:34Z) — an edit attempted against the main checkout's test file; re-issued against the plan worktree.
- **Own rule breaks counted by the run, not only by the guard:**
  - `git add -A` was used once (before the `640013e69` commit). It staged only that round's tracked modifications — no untracked file was collected — but it is the "never stage everything at once" rule, and it is reported as broken.
  - Three argparse rejections came from this run's own invocations, not from a stale surface: two `--filter` values containing spaces were split by the shell into separate arguments, and one `build_server wait` carried `--project-path`, which that verb does not declare (its own error named the accepted flags). Each was diagnosed as a caller error and re-issued correctly; no source was changed to silence any of them, and no operator question was raised because nothing pointed at a stale executor.
  - Read-class shell file operations issued by the run: `tail` on five build logs (the section-4 instruction to open the named `log_file`) and `wc -l` on the guard log. Both are shell file operations; they are listed here because the rule counts the run's own actions.
- **Routed builds:** every build in this run was daemon-routed (`mechanism=daemon_longpoll`); none fell back in-process, none was backgrounded, and no two were in flight for the worktree at once.
- **Restarts / re-dispatches:** no session restart; one sub-agent (the self-review reviewer) was continued across four rounds rather than re-dispatched.
- **Spec read:** `spec_source: ledger_worktree`, no `spec_differ` marker at setup and none at the landing-time re-resolve.
- **Executor skew:** `not_applicable` — a source checkout whose executor maps its own scripts; recorded, not asked about.
- **Model switches:** none; the run used `deepseek-v4.1-flash/high` throughout.

## 8. Build server

- Setup preflight: `ready` (registered project, daemon reachable).
- Per-mechanism counts: `daemon_longpoll`: every build of this run; `in_process_fallback`: 0.
- Fallbacks: none — every build was submitted with the default routing; no launch-fault retry was needed, and no build was degraded. One `--filter` invocation returned exit 2 from argparse (a caller error, re-issued) rather than a build fault.
- One routed `module-tests` returned a live `running` status and was re-attached with bounded `wait` calls (twice); no killed job.
- `runtime_stamp_reason`: absent — every runtime fact was measurable.

## 9. Residue

- **Harness sync is owed outside this plan, operator-run** (as the spec's Dependencies section states): the bundle edits land in `marketplace/bundles/` and reach Claude/OpenCode/Antigravity only through `/sync-harnesses`.
- **Executor regeneration is not owed** — no script verb or flag was added; `loop-exit-guard` gained result fields and a named error, not a new surface.
- **Accepted design decision (not a defect, recorded for the reviewer):** the unmeasured arm is stopped from deferring by redefining `exceeds_bash_ceiling` to state a MEASURED stamp's relation to the ceiling, rather than by adding a `measured` field to the resolve TOON and gating the deferral on it. The redefinition matches the contract `resolve-command.md` already stated for that field, and the only production consumer is the deferral itself; CodeRabbit flagged it as a preference in two rounds and it was not changed.
- The two bundles' pre-existing historical comments outside this plan's citations (e.g. the `baseline_drift` rationale in `manage-metrics.py`) were left untouched.
