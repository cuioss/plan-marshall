envelope_version=1
sender_type=plan
sender_id=rb-lb-53-halt-conflict-and-phase-time
epic=live-blockers
kind=landing
created=2026-10-25T01:13:23Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-53-halt-conflict-and-phase-time
epic=live-blockers
pr=#1857
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2004
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=0
step.sonar-roundtrip.open_issue_rules=none
```

guard: present (`.plan/temp/guard.log`; one R5 refusal in this run's session — see § Rule check).

## Deliverables

### D1 — a recorded halt ends the step

| Done-when (as written) | Verdict | Test | order | Commit |
|---|---|---|---|---|
| a test records a halted create-pr step and reads a refusal for a re-run that is not a named continuation | met | `test_a_halted_step_refuses_a_re_run_that_is_not_a_named_continuation` | none | 7eb2cfd20 |
| a named continuation passes | met | `test_a_named_continuation_passes` (all three, parametrized) | none | 7eb2cfd20 |
| a step resolution recorded after an `escalate_ask` without a logged operator answer is refused | met | `test_a_resolution_after_an_escalate_ask_without_an_answer_is_refused` (+ the positive control once `halt answer` lands) | none | 7eb2cfd20 |

Supporting guards added in the same deliverable: retry bound (required / not-documented / exhausted), escalation narrowing, malformed-store refusal, failed-outcome stamping without clobbering an escalation, key canonicalization, `escalation_open`/`replace-escalation`, offered-label matching, and the override-answer gate (no failing-first output was captured, so the order is `none` throughout).

### D2 — `needs_user` becomes a stated conflict question

| Done-when (as written) | Verdict | Test | order | Commit |
|---|---|---|---|---|
| a test feeds `overlap_with_content_conflict` / `needs_user` into branch-cleanup and reads a question naming the conflicting files and no merge-queue wait | met | `test_a_content_conflict_becomes_a_question_naming_the_files_and_the_base` + `test_the_content_conflict_gate_forbids_a_merge_queue_wait` (positive control: the authorizing option is offered) + the doc-dispatch assertion | none | 2bbaa4a73 |
| a test reads the force-push refused when the operator's answer did not authorize it | met | `test_the_force_push_is_refused_when_the_answer_names_no_action` + `test_free_text_authorizes_nothing` (positive control: the named label is accepted) | none | 2bbaa4a73 |

### Per-head test runs against pushed heads

| Head | Run | Result |
|---|---|---|
| 91c2aaa8b | module-tests, whole tree | 32108 passed |
| 3a86098c6 | module-tests (plan-marshall tree) + quality-gate | 27132 / green |
| 9982e91e8 | module-tests, whole tree | 32190 passed, 2 × `test_harness_shape_guards` pytest-timeout (>300 s AST walk); both pass in isolation at the same head (37 tests) — environment, not code |
| ac06d4bd3 | module-tests (plan-marshall tree) + quality-gate + CI `verify` | 27126 / green / CI success |

## Personas and skills

- Implementation (both deliverables): `persona-implementer`.
- Tests: `persona-module-tester`.
- Documentation edits (SKILL bodies, standards, references, the adoc and the SVG): `persona-documenter`.
- Every self-review round and every PR-comment triage: `persona-code-reviewer`.
- Domain skills: `skills: none named` — the spec's two deliverables carry empty `Skills:`/`Persona:` rows. No surface drift, so nothing was added.

## Hypotheses

- **HYPOTHESIS (Claim Labels): the classifier's verdict is available to branch-cleanup through its "one-stop read"** — **confirmed that the verdict is available, refuted that it arrives via the step-params one-stop read.** `branch-cleanup.md:230-254` dispatches `baseline-reconcile --no-emit` itself and parses `classification` from that TOON; the one-stop `step-params get` supplies `auto_rebase_threshold` and its siblings only.
- **Expected-surface hypotheses** (`branch-cleanup.md`, `phase-6-finalize/scripts/`, `manage-status/scripts/`, `test/plan-marshall/phase-6-finalize/`) — all four were real surfaces; the halt-refusal decision lives in `phase-6-finalize/scripts/halt_continuation.py` and the halt state in `manage-status/scripts/_cmd_halt.py`, as the surface predicted.

## Findings

**Self-review, three rounds** (`self-review: budget-exhausted` — three rounds used, none reported nothing open):

- Round 1: 12 findings + 8 doc-falsity sites. Fixed the real defects — the override-basis bypass, the unwired continuation check, the unvalidated answer, the empty-step message, the self-declared retry bound, the un-stamped `failed` halt, the uncanonicalized key, the malformed-record fail-open, a contradictory conflict verdict, an uncheckable merged authorization — plus every stale doc. Commits 63725aec5, a74ae4f28.
- Round 2: all round-1 items closed or closed-with-residue; 13 new defects (N1–N13). Fixed: roster/help/docstring falsities, merged-path routing keyed on the label, the stop site no longer passing a token that names nothing, `escalation_open`, `options_missing`, container-level unreadable detection, `operator_answer_without_override`, `--option` without `--escalate-ask`, plus the row-shape and positive-path tests. Commits 4de538533, 7f27afd57.
- Round 3: release-blocking none; two recommended items fixed (the false item-7a claim in the roster, the unhandled `escalation_open` at 7a) in 61fa17148.
- Residual preferences, reported as open and not fixed: `queue_wait: forbidden` on the merged path is conservative rather than load-bearing; `RESOLUTION_OUTCOMES` lives in the halt module while `mark-step-done` consumes it; a non-override handshake row carries `override_basis=operator` by default; `--attempt 0` is not rejected; D1's "the option the operator selected is executed as worded" remains a prose rule — no mechanism compares the chosen label to the continuation taken.

**CodeRabbit, four reviews** (11 actionable threads + 1 outside-diff finding; every one replied to and resolved; the outside-diff finding fixed and answered by PR comment):

- 91c2aaa8b (6): option populations split by classification; item 1 reads the halt store on re-entry; `unclassified` admitted for the two classifier-bypass paths; `queue_wait: forbidden` consumed by the merge route; unknown override bases rejected; the retrospective fixture schema derived from `HANDSHAKE_FIELDS`. Fixed in 71f990bc0 / d1d104d8b.
- d1d104d8b (2): stop with `halt_unreadable` when the re-entry read is unparseable; log `n/a` rather than interpolate classifier metrics on bypass paths. Fixed in 3a86098c6.
- 9982e91e8 (3 + 1 outside-diff): the `loop_back_reentry` marker must have the shape `cmd_set_phase` writes; item 1 distinguishes the four halt-read outcomes so the rate-window wait still re-dispatches; `queue_wait: forbidden` overrides the merge-queue skip itself so the authorized rebase runs; merged-state gate inputs bound explicitly. Fixed in ac06d4bd3.
- ac06d4bd3: re-triggered after the last push and **rate-limited** ("Review rate limited", 2026-10-25T00:01:36Z).

**Sourcery** (optional): refused on every trigger — "larger than the review limit of 150,000 diff characters". Not gating.

**CI**: two infrastructure-shaped failures on the way, both resolved without a code change. A `test-compile` freshness guard tripped on a warm mypy cache (211 files/s over the 200 ceiling) and passed on rerun; two `test_harness_shape_guards` pytest-timeouts under host load passed in isolation.

## Reviewers

| Reviewer | Required? | Result | Head reviewed | History |
|---|---|---|---|---|
| coderabbit | yes (`quota_limited: true`) | **reviewed** 91c2aaa8b, d1d104d8b, 9982e91e8; **refused on quota** for ac06d4bd3 | 9982e91e8 (`final_review_risk_coverage` marker, `kind=reviewed`, low risk) | triggered at 19:29, 20:45, 21:24 (rate-limited 21:25), 23:05, 23:59 (rate-limited 2026-10-25T00:01:36) |
| sourcery | no (optional) | **refused** on size, every trigger | — | triggered 19:29 and with the first batch; "larger than the review limit of 150,000 diff characters" |

**Standing review authorization (coderabbit, quota-limited):** a qualifying review exists on this PR's head `9982e91e8` (marker-bearing summary comment, `coveredCommitId=9982e91e8`, `kind=reviewed`); every finding from every review was fixed in a pushed commit or answered, and every thread is resolved; it was re-triggered once after the last push (`ac06d4bd3`) and the refusal is recorded above; every other gate condition holds on `ac06d4bd3` (CI verify green, quality-gate green, Sonar merge-allowed, every comment handled).

## Operator questions

1. "The executor-skew pre-check returned `could_not_check` …" — options: proceed with the run / regenerate the executor / stop. **Selected: "Proceed with the run".**
2. "`quality-gate` is green except 3 `ARGUMENT_NAMING_NOTATION_INVALID` errors …" — options: regenerate the worktree executor / keep the stale executor and record the red / stop. **Selected: "Regenerate the worktree executor".**
3. "I cannot reach github.com from this host … How should I proceed?" — options: retry the push now / park the run / keep polling. **Selected: "Retry the push now".** The retry succeeded.

Free-text operator messages: none.

## Rule check

- **Guard: present.** One refusal in this run's own session tree: an R5 rejection of `python3 -c "print(1)"` at the start (a probe of the interpreter, before the lane's shape was settled). It was not worked around; every later script call used `python3 .plan/execute-script.py`. No other guard line belongs to this run.
- **Shell rules**: one command per call throughout; no `&&`, pipes, loops or heredocs; files read with the file tools; all temp files under `.plan/temp/`; every repository edit inside the worktree.
- **Git rules**: nothing staged wholesale; no stash, restore, checkout-of-path, rebase or forced push. The one `--amend` was on an unpushed commit of this run. `uv.lock` was committed rather than restored, because it was clean at run start and `git checkout --` is forbidden here; its content was already byte-identical to `origin/main`, so it carries no dependency change.
- **Executor rules**: every build through the resolved canonicals; every CI action through `plan-marshall:tools-integration-ci:ci`; `gh`/`glab` never invoked directly. One deliberate deviation from the routed default: the whole-tree builds ran with `--execution-mode in_process` after the daemon's supervisory bound expired twice on the same suite (recorded below).
- **Restarts**: two server restarts interrupted work and are recorded in the progress file; the lane text was re-read in full after each, and the interrupted whole-tree run was re-run rather than resumed. No sub-agent was killed.
- **Executor regeneration**: the worktree's `.plan/execute-script.py` was regenerated once, on the operator's selection, because the embedded notation table predated the two new scripts. It is a generated, git-ignored artifact.

## Build server

- Setup preflight: **ready** (project enrolled, daemon reachable).
- Routing: `build-routing` answered `auto`. Routed builds were used first; two of them hit the daemon's own bound on the whole-tree suite (`timeout`, `timeout_used_seconds` 1032 learned then 1290 explicit), so the split form ran with `--execution-mode in_process` for the whole-tree runs thereafter. Every other build was routed or in-process as the table below records.
- One environmental note worth carrying: a routed build re-runs the worktree's executor with the `--project-dir` it is given, and a RELATIVE `--project-dir` resolves against the daemon's own cwd, not the caller's — the inner run then falls back to `pwx`, which is absent, and the job fails with `execution_failed`. Absolute `--project-dir` values work.
- No `killed` job occurred.
- `runtime_stamp_reason`: absent — every stamp fact was measurable at landing time.

## Residue

- **`test_harness_shape_guards`** times out (>300 s, an AST walk over shared temp trees) in whole-tree runs under load; it passes in isolation at the same head. Reported, not fixed: it is a harness-shape guard in `test/_shared`, untouched by this plan.
- **`test_compile` freshness guard** tripped once on a warm mypy cache and passed on rerun. Untouched by this plan.
- **Self-review preferences** listed under Findings, and **D1's "selected option executed as worded"** remains prose-only — a follow-up seam (`check --answer` with an option→continuation mapping) would make it mechanical.
- **Sourcery** cannot review a diff this size; the optional reviewer will stay silent on large PRs.
- `test/plan-marshall/plan-retrospective/_plan_retrospective_fixtures.py` now derives its field list from `HANDSHAKE_FIELDS`; the wider retrospective fixture population still uses hand-built rows where it always did.
