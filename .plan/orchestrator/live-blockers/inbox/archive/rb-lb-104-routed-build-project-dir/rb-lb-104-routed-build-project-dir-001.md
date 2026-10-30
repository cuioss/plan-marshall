envelope_version=1
sender_type=plan
sender_id=rb-lb-104-routed-build-project-dir
epic=live-blockers
kind=landing
created=2026-10-30T09:09:00Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-104-routed-build-project-dir
epic=live-blockers
pr=#1893
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2025
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# PLAN-LB-104 — a routed build resolves the tree the caller named

Merged as `42b421ff2bd7d9b88ef480dec15e19e4b0adbaf6` via the merge queue (merge_group run
41027396799, success). PR #1893 is closed and the branch is deleted; the main checkout was
switched and pulled to the merge commit.

## 1. Deliverables

| # | Deliverable | Verdict |
|---|---|---|
| D1 | The submitted command names the tree the caller named, in absolute form | **not fully met** — one clause could not be produced pre-merge (below); every other clause met |
| D2 | A missing wrapper is a named failure, not an opaque `execution_failed` | met |
| D3 | The lane routes every build and never turns the server off for the rest of the run | met |

D1, clause by clause:

- *Both `--project-dir` token forms rewritten, no other token touched, no-flag argv unchanged* —
  **met**. `test_route_submits_the_absolute_project_dir_for_the_separated_form` and
  `…_for_the_equals_form`, `order: test-first`, failing run `b7558e37c`, job log
  `15f0be06155f4b6495b0ed67ab54e682.log`; the pre-existing
  `test_route_ready_submits_reconstructed_command` covers the no-flag argv.
- *Second test through the REAL resolver with a tmp tree holding a `pw`* — **met**.
  `TestRoutedArgvResolvesTheWorktreeWrapper::test_the_submitted_project_dir_resolves_the_worktree_wrapper`,
  `order: test-first`, same failing run — the child re-resolved the relative value to
  `…/plan-x/.plan/local/worktrees/plan-x`. Only the daemon client is stubbed; the resolver and the
  wrapper detection are real.
- *PR records one live routed build from a real lane worktree with the relative form
  (`--project-dir .plan/local/worktrees/{id}`)* — **NOT MET AS WRITTEN**. That value is relative, so
  it forces the main checkout as the working directory, and from there the lane's executor rule
  admits only the main checkout's `.plan/execute-script.py` — the base-commit client, which has no
  fix. The branch's fixed client runs with the worktree as cwd, where that same tree is `.`. The one
  construction that would exercise the literal token with the fixed client
  (`python3 <worktree>/.plan/execute-script.py …`) is refused by the tool-call guard and would prove
  a hybrid no real run produces. Confirmed independently in two review rounds; the operator chose to
  open the PR and report the clause as not met.
  What was recorded instead, and what it shows: the pre-fix reproduction used the LITERAL form from
  the main checkout and failed exactly as the spec describes (inner `[EXEC] pwx compile plan-marshall`,
  `error: execution_failed`, exit -1; rendered `build_failed`, exit 1, duration 0); the live runs
  from the worktree with the relative form `.` — the same tree, named relatively — carried the
  ABSOLUTE tree in the submitted argv with `status: success`, `mechanism=daemon_longpoll` and no
  degradation (job logs `98df90fa71934fb0b83ea4a7c31f9773`, `8665ac2d7c494b90a68ba6c4d55f5c65`,
  `2f78d84de42d4a8ea6f4f5d48d69b92b`, `434e3ce0f6344fc8a004b0f108dc7f66`).
- *Every other path-valued flag proven cwd-independent or normalised* — **met**, recorded in the PR:
  `--plan-id` is mutually exclusive and derives an absolute tree; `--working-dir` / `--env` make a
  build daemon-incompatible so it never reaches the routing seam; `--root` is declared only on
  `discover` and Gradle's `find-project`, so it cannot appear in a routed `run` argv.

D2 evidence: `TestMissingWrapperIsNamedOnBothLegs` — in-process (TOON), JSON projection, log-file
fault, missing-cwd fault, and the routed leg through a stub job whose log holds the inner result —
`order: test-first`, failing run `2bdfbb35f` (with the tests), job log
`1b1bb563b86a47dbb3296c5b1cd1c449.log`; plus the reader-level cases and their matched negative
control in `TestReadLogVerdict`.

D3 evidence: `test_skill_routes_every_build_and_retries_a_launch_fault_once` and
`test_landing_build_server_line_counts_the_builds_per_mechanism`, `order: test-first`, failing run
`39291926f` (with the tests), job log `35de92dd44f54e52bafd9b2a36dceb6c.log`.

Per-head test runs (every pushed head was tested): `fa173cfa3` verify green (32516 tests, job
`d37d9d89b7a0415eb73333bc1dc8c393`); `23b97a172` whole tree green (32521 tests, job
`1ec9be1fbf7d42948993cf60ce3a7544`, serial); `9fb674f51` whole tree green (32574 tests, job
`b565a3cb34924a84bb61be72e0079228`, serial); `d748e6c4e` whole tree green (32574 tests, job
`31866c9c5b3042278ac2c6ee97b7d904`, serial) and CI green (verify/verify 1171 s).

## 2. Personas and skills

- persona-implementer — the shared build-client code (D1, D2).
- persona-module-tester — the unit/module tests (every deliverable).
- persona-documenter — `runbook-lane/SKILL.md`, `build-server-client/SKILL.md`,
  `extension-api/standards/build-execution.md` (D2, D3).
- persona-code-reviewer — the three self-review rounds and every PR-comment triage.

Per deliverable, the spec names no `Skills:` line, so `skills: none named`. No surface drift
occurred: every touched file is inside the spec's Expected Surface or is the result-contract document
the new fields belong to (`extension-api/standards/build-execution.md`), which the spec's D2 wording
implies; no skill was added.

## 3. Hypotheses

- "the rendered result drops the message because the formatter keeps only known fields" —
  **confirmed**: `_build_format.EXTRA_FIELDS` is a whitelist (`_build_format.py:41-58`) and
  `cmd_run_common` rebuilt the execution-failure envelope without the reason
  (`_build_shared.py:752-766` at the base commit).
- "a routed job's inner `execution_failed` is rendered as `build_failed` with exit code 1" —
  **confirmed** by the reproduction (job log `9badd10f8d2344b8bc22b002aa30a34a.log`: inner
  `error: execution_failed`, exit -1; rendered `error: build_failed`, exit 1).
- "no other flag in the routed argv is cwd-sensitive" — **confirmed** (see the D1 table).
- "the lane's 'every later build in-process' is the lane improvising, not a rule" — **confirmed**:
  the pre-change § 4 prescribed `in_process` only for an absent executor slot.
- "the landing template's build-server line sits at § 8 and `inbox landing-check` requires no new
  key" — **confirmed**; the per-mechanism count lives in the landing's prose.
- The Maven hypothesis (another project's lane) — **not settled**: that project's daemon journal is
  outside this repository and was not read. D3's wording is symptom-based (`execution_failed` /
  `log_file_failed`), so it does not describe one cause for two.

## 4. Findings

Self-review round 1: one blocker (D1's live-record clause, above) plus 13 nits (stale doc claims, two
weak guard assertions, missing reader/JSON coverage) — fixed in `67fac3c88`.
Round 2: the blocker confirmed; 5 nits, one of them a claim the previous fix made false (`--root` is
also on Gradle's `find-project`) — fixed in `0452a48c4`.
Round 3: (a)-(e) confirmed closed; 2 remaining doc nits (`reason` / `project_dir` scoping and the
daemon-mode fail-loud wording) — fixed in `a652b5688`. Round limit reached with the D1 evidence
clause still open → `self-review: budget-exhausted`; the operator was asked and chose to proceed.

PR review comments (all handled, every thread resolved):
- CodeRabbit 03:20 on `a652b5688` — 4 minor findings (routing check before the first auto build;
  launch-fault set derivation; log-file fault reason; mechanism-count source) → fixed in `714a50cee`,
  replied and resolved; CodeRabbit marked each "Addressed".
- CodeRabbit 05:16 on `1da24efc7` — 1 inline (base `auto` on the build-time preflight) + 2
  outside-diff (identify the missing path before reporting a missing wrapper; store fallback details
  per build) → fixed in `9fb674f51`, replied and resolved, outside-diff answered in a PR comment.
- CodeRabbit 06:19 on `9fb674f51` — 1 minor (classify missing working directories on Windows) →
  fixed in `d748e6c4e` by checking the cwd on disk instead of the exception, with a real-fault test;
  replied and resolved.
- Sourcery (optional) approved at 03:56 on `23b97a172`, then refused on its 7-day budget; optional, so
  it does not gate.
- One pre-existing guard assertion (`before the first routed build`) was broken by a rewording and
  restored rather than relaxed; a second (`runs in-process otherwise`) likewise.

## 5. Reviewers

| Reviewer | Required | Outcome | Head | History |
|---|---|---|---|---|
| coderabbit | yes (quota-limited) | reviewed, then refused on quota | 9fb674f51 covered (kind=reviewed marker); final push covered by the standing authorization | refused 00:58Z (limit), 90-minute wait, re-triggered 03:07Z → reviewed 03:20Z; refused 03:28Z, 03:55Z, 06:53Z; **standing authorization** applied on `d748e6c4e` (see below) |
| sourcery | no (optional) | approved once, then hard-quota | 23b97a172 | approved 03:56Z; refusals 00:58Z, 06:53Z |

Standing review authorization for CodeRabbit on the merged head `d748e6c4e`: a qualifying review
exists (9fb674f51, `kind=reviewed`, naming its covered commit); every finding from every one of its
four reviews is fixed in a pushed commit and every thread is resolved (CodeRabbit closed them
itself); it was re-triggered once after the last push (06:53:35Z) and the refusal is recorded
(06:53:41Z, review limit reached); and every other gate condition held on `d748e6c4e` — CI green,
the split gate green, Sonar `not_configured`.

## 6. Operator questions

1. Asked at the self-review round limit: "How should I proceed at the self-review round limit with
   D1's live-record clause open?" — options: {open the PR and report D1 not fully met, stop with
   merge_state=open, open the PR and mark D1 met on substitute runs}; **selected**: "Open the PR,
   report D1 not fully met".
   Free-text operator messages: none. No surface/naming error needed a question.

## 7. Rule check

- Shell file operations issued by the run: none — every read/search went through the file tools.
  Two `grep`-tool and `read`-tool accesses reached outside the repository
  (`~/.plan-marshall/marshalld/job-logs/…`), which the spec's verify-first clause and the lane's
  "open the `log_file` it names" instruction call for; recorded here rather than hidden.
- Builds: every build was submitted with the default routing. No launch-fault retry was needed; no
  `--execution-mode` flag was ever passed. The one exception is the pre-fix reproduction, which
  failed exactly as the defect describes.
- Routed-build concurrency: one `self-review` sub-agent ran a whole-tree build while this session was
  also building, violating "one daemon-routed build at a time per worktree"; its run came back red on
  two tree-walking guards (pytest 300 s timeout under xdist), which pass in isolation and in the
  serial whole-tree run.
- `git worktree remove` was used without force, as the section prescribes; `git stash`, `git restore`,
  `git checkout -- <path>`, `git rebase` and forced pushes were never used.
- `executor-skew`: `not_applicable` (source checkout) — answered, recorded, never asked about.
- Spec read: `spec_source: ledger_worktree`, no `spec_differ` marker.
- Guard: `present`. The run's serial whole-tree runs exceeded the 3600 s bound twice; both bound
  expiries are recorded and the gate continued with the split form rather than re-submitting the same
  bound.

## 8. Build server

Setup preflight: `ready` (project registered, daemon reachable). Every build in this run was
submitted to the daemon: `builds: daemon_longpoll: 48, in_process_fallback: 0` (48 recorded build
invocations, each reporting `mechanism=daemon_longpoll`). No `degraded` result and no
launch-fault retry occurred, so `fallbacks: none`. Three bound expiries were recorded (the wrapper's
own 330 s floor twice, an explicit 1745 s/2400 s/3600 s bound on the long runs); each was re-run with
a raised bound or the split form, never with the same bound. Running hand-backs from the 300 s client
wait were re-attached in the same tool call, never backgrounded. No `killed` job. No
`runtime_stamp_reason` was carried, so the stamp is fully measured.

Local-environment flakes, none in a module this change touches and each green in isolation: two
tree-walking shape guards hitting pytest's 300 s per-test timeout under xdist (37/37 green alone), a
pyprojectx venv race in a target-tree precondition, four npm run-mode flakes (8/8 green alone), and
one run with `xd` worker crashes (`node down`). CI on GitHub ran the parallel `verify` green on every
head that mattered.

## 9. Residue

- **D1's live-literal-form clause is open by construction**: it needs a post-merge run from `main`
  with `--project-dir .plan/local/worktrees/{id}`, which is now possible and was not before. If the
  epic wants that evidence, one routed build from the merged tree closes it.
- The Maven hypothesis (another project's daemon journal) remains unsettled.
- Sourcery's 7-day budget resets in about four days; the optional reviewer contributed one approval.
- A pre-existing robustness gap noticed but not changed (outside the spec's surface): two
  tree-walking shape guards sit close to pytest's 300 s per-test timeout on a loaded machine, so a
  parallel full-suite run can go red on them. A serial run is the reliable form here.
