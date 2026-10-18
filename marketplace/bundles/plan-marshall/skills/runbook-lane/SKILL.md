---
name: runbook-lane
description: The runbook lane - implementation contract for ONE staged orchestrator plan spec on a cheap model, without the /plan-marshall lifecycle. Resolves every project-specific value (epic slug, derived names, build commands, reviewers with their trigger comments, commit trailer, inbox command) through the runbook_lane resolve verb, then runs the lane - progress file and resume, hard rules, fail-first evidence, build gate, self-review rounds, PR and review cycle, merge gate, cleanup, and a landing message to the epic inbox - from any project that has plan-marshall installed
user-invocable: true
mode: workflow
---

# Runbook Lane Skill

The complete working contract for implementing ONE staged orchestrator plan, on a cheap model,
without the `/plan-marshall` lifecycle. Read it fully before doing anything else. Nothing else
governs a runbook-lane run: do not load the cloud plan lane, do not run `/plan-marshall`,
`/plan-orchestrator` or any `phase-*` workflow.

Every project-specific value named below as `{field}` is a field of the step 0 resolve result. The
lane carries no project literal of its own, so the same contract runs in any project that has
plan-marshall installed and one orchestrator epic holding the spec.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY
notation, not only `manage-*` — is stated once in
[`tools-script-executor/standards/exit-code-convention.md`](../tools-script-executor/standards/exit-code-convention.md);
it is not restated here. The resolve verb above and every `ci` invocation below are subject to it.

## Canonical invocations

The canonical argparse surface for `runbook_lane.py`.

### resolve

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane resolve \
  --spec .plan/orchestrator/{slug}/plans/PLAN-NN-{slug}.md \
  [--project-dir DIR]
```

Resolves the epic slug, the derived names, the build commands, the required and optional reviewers
with their trigger comments, the commit trailer, the harness and guard state, and the `inbox write`
command. `--project-dir` defaults to the current directory and anchors every project-scoped read.
Fails closed with a specific error code for a spec outside the orchestrator tree, an unreadable
configuration, a missing automatic-review step, an empty required-reviewer list, or an
unresolvable build command.

### build-classify

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane build-classify \
  --paths "changed/path/one,changed/path/two" \
  [--project-dir DIR]
```

Classifies changed paths as `docs-only` or `buildable` for the build gate (section 4), reading the
project's own footprint rule. It answers `source: ci-workflow` when the project's CI opts in to the
footprint gate, and `source: architecture` otherwise.

## 0. Input

The invocation names a spec:

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/{slug}/plans/PLAN-NN-{slug}.md
```

Read it from the **main checkout**; it is git-tracked there. Then **resolve** every value the run
uses, and read the result before doing anything else:

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane resolve --spec {spec}
```

The result supplies, and nothing below is spelled from anywhere else:

| Name | Field of the resolve result |
|------|-----------------------------|
| epic slug | `slug` |
| `{plan}` | `plan` |
| worktree | `worktree` |
| branch | `{branch} = {prefix}{plan}`; the prefix is one the project's `working_prefixes` declares, and the project's own set wins over the canonical `feature/` (a new capability), `fix/` (a bug fix) and `chore/` (docs or maintenance) |
| base branch | `base_branch` (the project's own base branch, never a spelling of it) |
| inbox sender id | `sender_id` |
| progress file | `progress_file` |
| landing file | `landing_file` |
| build commands | `build` |
| build timeout (seconds) | `build_timeout_seconds` |
| required and optional reviewers, with their trigger comments | `required_bots`, `optional_bots` |
| commit trailer | `commit_trailer` |
| `inbox write` command | `inbox_write_command` |
| harness and guard state | `harness`, `guard` |
| guard-log path | `guard_log` |

The branch row is derived from the project's configuration rather than returned by `resolve`; every
other row names a field of the resolve result.

The verb **fails closed**: a spec outside `.plan/orchestrator/{slug}/plans/`, an unreadable
configuration, a missing automatic-review step, an empty required-reviewer list, or a build command
the project's architecture cannot resolve is an error carrying a specific code. There is never a
fall-back to a default reviewer list or a default build. Stop and report a resolve error; do not
substitute a value.

**How to read the spec:**

- **Implement:** its *Deliverables* and every *Done when* clause.
- **Load:** each deliverable's `Skills:` and `Persona:` lines, before working on that deliverable
  (step 2 checks they exist).
- **Facts, not instructions:** its *Claim Labels*. A `HYPOTHESIS` is confirmed or refuted before
  you build on it, and the result goes in your report.
- **A hint, not a fence:** its *Expected Surface*.
- **Ignore:** its *Hand-Off Command*.
- **Obey:** its *Write-Boundary*.
- **Translate** plan-marshall vocabulary in the spec:
  - "verify-at-outline" / "at outline" → confirm it before implementing that deliverable.
  - "outline deliverable" → one deliverable of this run.
  - "functional review" → step 5 of this runbook lane.

## 0a. Progress file and resume (do this first, every session)

**Re-read this skill in full** at every session start, after every server restart and after every
context compaction. It can change during a run; the current version binds.

**Check for a resume first.** If `{progress_file}` exists, this session is a resume:

1. Read the progress file.
2. Check it against `git -C {worktree} log --oneline origin/{base_branch}..HEAD` and, if a PR is recorded,
   `ci pr view --pr-number {N}`.
3. Continue at the **first step not recorded as done**. Never redo a recorded step.
4. If git or the PR contradicts an entry, trust git and the PR, and record the correction.
5. If the worktree or branch exists but there is no progress file, rebuild the file from git and
   the PR before continuing.

**Keep the file current.** It is the run's memory. Write it with the Write or Edit tool, after every
item below and before starting the next. One line per entry, newest last:

```text
setup: worktree {worktree}, branch {branch}, pushed
D{n} hypothesis: {claim} — confirmed|refuted, {file:line}
D{n} test: {test name} — failed before fix ({evidence}), passed after
D{n} done: commit {sha}
gate: {quality-gate|module-tests|verify} at {sha} — {result}
self-review round {k}: {findings and disposition}; open: {list or none}
pr: #{N} created at {sha}
review: {bot} triggered at {time} on {sha} — {reviewed|refused|silent}; next trigger not before {time}
operator: asked "{question}" — options {…}; selected "{option}"
merge: {settle result}, merge commit {sha}
cleanup: done
landing: written as {message name}
```

**Commit subjects** end with the deliverable, e.g. `fix(triage): resolve in the finding's store (D1)`,
so git alone shows which deliverables are committed.

**The landing report (step 8) is assembled from this file,** not from memory.

## 1. Rules (every one binds; breaking one fails the run)

- **Scope.** Implement exactly the spec. Every deliverable stays a separate deliverable, and every
  Done-when is met as written. Never merge, narrow or reword a criterion. A deliverable you cannot
  meet is reported as not met, with the reason.
- **Evidence.**
  - A test that a Done-when says "fails at `{sha}`" must be **seen failing**. Write it first, run it
    against the unfixed code, and record the failing output. Then fix, and see it pass.
  - A green run at HEAD is never evidence that a test fails without the fix.
  - Never cite a test, file or log you have not just read or run.
- **Executor only.**
  - Every script: `python3 .plan/execute-script.py {bundle}:{skill}:{script} …`.
  - Every build: the `build` commands the resolve result supplies (step 4).
  - Every CI action: `plan-marshall:tools-integration-ci:ci`.
  - Never: the CI CLIs directly (`gh`, `glab`), the project's build wrapper directly, the
    test/lint/type-check binaries directly (`ruff`, `mypy` and `pytest` are the familiar cases),
    `python3 -c`, `python3 some_script.py`, scripts under a system temp directory, git's `grep`
    subcommand, or `sleep`. Every one of these goes through its resolved command instead: the
    executor for scripts, the `build` map for builds, and `ci` for CI.
- **Shell.**
  - One command per call: no `&&`, `;`, pipes, command substitution, loops or heredocs.
  - Files are read and searched with the file tools, never with shell `cat`, `ls`, `grep`, `find`,
    `head` or `sed`.
  - Temp files go only under `.plan/temp/`.
  - Repository files (source, tests, docs) are created and edited **only inside the worktree**,
    never in the main checkout — not even a draft.
- **`.plan/` state.** Write nothing under `.plan/` except `.plan/temp/`, the `ci` body slots under
  `.plan/local/plans/NO_PLAN/work/ci-bodies/` that step 6 prescribes, and your one inbox message
  (step 8). Never edit the spec or any file under `.plan/orchestrator/`.
- **Stay inside the repository.** Never read, list or print anything outside the repository root:
  no credential files, config directories or environment dumps. Those hold secrets, and anything
  you read is sent to the model provider.
- **There is no session budget.** Never stop, skip a step, skip the build gate, or leave a PR
  comment unhandled because of "budget" or "context". Stop only when you are blocked, and name the
  blocker.
- **Git.**
  - Never stage everything at once, never `git stash`, `git restore`, `git checkout -- <path>`,
    `git rebase`, or a forced push.
  - To bring the base branch in, merge it (step 7).
- **The operator decides.** Ask the operator (the `AskUserQuestion` tool) when:
  - you are blocked;
  - a rule would have to bend;
  - a required reviewer cannot be obtained (step 6).

  Act only on an option the operator **selected**. A question that was cancelled, interrupted or
  aborted (for example by a server restart) has no answer: ask it again, and never act as if an
  option had been chosen. Free text such as "try now" or "continue" is not permission to merge,
  skip a reviewer, or do anything not listed. After the operator reports a problem, take no
  remedial action they did not choose.
- **Required reviewers.** Every bot in `{required_bots}` is required. A required reviewer is never
  skipped and never moved to optional, and a PR is never merged without a review from each. Every
  bot in `{optional_bots}` is optional, and is included in the cycle below beside the required ones
  without gating the merge.
- **Reviewer trigger phrases.** A reviewer's trigger comment and its escalated trigger comment are
  fields of its resolve row (`trigger_comment`, `escalated_trigger_comment`), and those are read
  from `plan-marshall:automatic-review` `standards/{bot}.md` — the single source of each bot's
  phrases. Never type one from memory.
- **Commit trailer.** Every commit ends with exactly the resolved `{commit_trailer}` line and
  nothing else by way of attribution. A PR body carries no attribution footer.
- **Guard.** The resolve result reports `guard: present` only when this project has a tool-call guard
  installed for the active harness, and `guard: none` otherwise (the Antigravity harness has no
  pre-tool-use hooks at all). Where nothing was enforced, the landing message says so — step 8's
  facts block, and its rule-check section, report `guard: none on this harness (unenforced)`. The lane never
  reports "all kept" or "no guard-log line" when nothing was enforced. The guard's audit log is
  `{guard_log}` (the path `resolve` returns); step 8 reads it there for this run's sessions.

### Personas — loaded as standards, one per kind of work

Load the engineering persona for the kind of work a step does, and apply it as a standard:

| Kind of work | Persona skill |
|---|---|
| production code | `persona-implementer` |
| unit and module tests | `persona-module-tester` |
| multi-module tests | `persona-integration-tester` |
| trust boundaries, input validation and secrets | `persona-security-expert` |
| documentation | `persona-documenter` |
| every self-review round, and triaging every PR comment | `persona-code-reviewer` |

A deliverable's own `Persona:` line (section 0) selects its persona; with no declaration, this table
decides from the kind of work.

The persona skills are loaded as **standards only**: any plan-marshall machinery they mention
(`manage-personas`, extension points, orchestrator pipelines) is ignored in this lane. The lane
loads the skill for its judgement, never to run its pipeline.

`persona-code-reviewer` applies its adversarial-refute lenses to every finding: is it a defect or a
preference; is it surplus or load-bearing; is the reported drift real or a false positive; and what
is its severity. Apply the same lenses to the run's own Done-when verdicts, so that "met on paper"
is challenged on reachability, on the end-to-end path, and against the spec's intent.

## 2. Set up the worktree

All commands run from the main checkout (the repository root).

1. `git status --porcelain` must print nothing. If it prints anything, stop and report **blocked**.
2. `git fetch origin {base_branch}`
3. Create the worktree and branch:
   `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-create --plan-id {plan} --branch {branch} --base origin/{base_branch}`.
   - The verb also prepares the worktree's plan-local directory and its build tool. Bookkeeping
     warnings about a missing plan status are expected; ignore them.
   - `error: worktree_exists` means this is a resume: reuse the worktree.
4. `git -C {worktree} push -u origin {branch}`. Make no edit before this push.
5. **Check every named skill and persona exists.** The resolve result carries one row per spec
   deliverable with its `Skills:` and `Persona:` declarations. A `Skills:` entry is a
   `bundle:skill` notation (comma-separated for several); a `Persona:` entry is the persona kind
   (`implementer`) or its full skill name. Every named skill and persona must
   exist in the installed bundles; `resolve` reports a name that does not as a
   `named_skill_not_found` error, and the run then **stops and asks the operator**. A missing skill
   is never skipped silently. Load the declared skills and persona as standards before working on
   their deliverable, and list them per deliverable in the progress file.
   - **Surface drift.** If a deliverable ends up touching a module the spec's Expected Surface did
     not name, load that module's domain skills too, through the same configuration source the
     orchestrator uses. Record the addition in the landing report as `skills added: …, reason: …`.
     Never drop a skill the spec named.

All edits, staging, commits and pushes target the worktree (`git -C {worktree} …`). The main
checkout stays untouched.

Every executor call runs with the shell in the **main checkout**, in exactly the form
`python3 .plan/execute-script.py …`. The guard refuses any other form, including an absolute
executor path. The worktree has no executor of its own, so every build passes
`--execution-mode in_process --project-dir {worktree}`. The build daemon would need an executor
inside the project directory; in-process runs need none.

## 3. Implement, deliverable by deliverable

For each deliverable, in the spec's order:

0. Load the deliverable's persona and its declared domain skills as standards before any work: its
   `Persona:` and `Skills:` lines when the spec carries them, otherwise the kind of work selects the
   persona from the persona table in section 1 — `persona-implementer` for production code,
   `persona-module-tester` for unit and module tests, `persona-integration-tester` for multi-module
   tests, `persona-security-expert` where trust boundaries, input validation or secrets are touched,
   and `persona-documenter` for documentation. A spec without the lines names no domain skills; the
   landing report then says `skills: none named`.
1. Confirm the spec's HYPOTHESIS lines for this deliverable by reading the code. Write down
   confirmed or refuted, with `file:line`.
2. Write the Done-when tests. Run them on the unfixed code and record the failing output (step 4
   command, scoped).
3. Implement. Run the tests; record them passing.
4. If any `*.py` changed, run the quality gate (step 4) until clean.
5. Commit with the deliverable paths staged by name, then push. Record `D{n} done` in the progress
   file.

## 4. Build gate

Every build runs in-process from the main checkout against the worktree, using the commands the
resolve result supplies:

```bash
{build.quality-gate} --execution-mode in_process --project-dir {worktree}
{build.module-tests} --execution-mode in_process --project-dir {worktree}
{build.verify} --execution-mode in_process --project-dir {worktree} --timeout {build_timeout_seconds}
```

- **Docs-only change.** Before running the full build, classify the worktree diff against the base:
  get the changed paths with `git -C {worktree} diff --name-only origin/{base_branch}...HEAD`, then
  pass them to the `build-classify` verb. When it answers `kind: docs-only`, run **no** full
  `verify`: check the changed docs instead (format, internal links and references, and a
  `git status` showing only doc files) and record `build-gate: docs-only` in the progress file and
  the landing message. `kind: buildable` runs the gate below as usual. The classifier applies the
  PROJECT's own footprint rule — its CI opt-in when it has one (a `skip-on-docs-only` declaration
  plus the `extra-buildable` paths that force a build even for a document extension), otherwise the
  architecture's module directories — rather than assuming a `.py` file is the only thing that
  builds. Pass the same `--project-dir` the build gate uses. Required CI checks still have to be
  green, so the merge gate is unchanged.
- **When to run what:** run `{build.quality-gate}` before each commit that touches `*.py`, and
  `{build.verify}` once before the PR. Scope the tests to one module while iterating.
- **Shell timeout:** in-process builds hold the shell call for their whole duration. Give each call
  the shell tool's `timeout` parameter, set at or above the build's own timeout.
  - If the tool cannot wait that long, run `{build.verify}`'s three parts as separate calls, in the
    order `{build.split}` states — for example `{build.quality-gate}`, `{build.test-compile}` and
    `{build.module-tests}`, each with the same worktree flags.
  - Never omit the test-compile part.
- **Never use the daemon:** never drop `--execution-mode in_process`.
- **Read the result, not the exit code.** The TOON must show `status: success` and an empty
  `errors[]`. Open the `log_file` it names for the test summary.
- **Failures that already fail on the base branch:** environment-dependent tests can fail in a
  project's local module-tests run. They are not yours. Only a failure in a module you touched, or
  one the base branch does not show, is yours.
- **Surface/naming errors** such as "unknown subcommand": suspect a stale executor first and ask the
  operator. Do not change source to silence them.

## 5. Self-review before the PR

Dispatch one sub-agent (the `Task` tool, the general agent) with `persona-code-reviewer` loaded as a
standard. It reports and never edits. Have it apply its adversarial-refute lenses — defect or
preference, surplus or load-bearing, real or false-positive drift, and severity — to every finding
and to the run's own Done-when verdicts. Give it:

- **section 1 of this skill, verbatim, as rules it must keep.** That means no git grep, no shell
  file listing or reading commands, no temp-directory writes or redirects, no inline Python, and no
  workarounds after a guard refusal; use the file tools. Its rule breaks count as yours.
- the spec path;
- `git -C {worktree} diff origin/{base_branch}...HEAD`;
- the instruction to grade **each Done-when as written** as met or not met, with evidence;
- the instruction to report:
  - every pre-existing test assertion the diff removed or relaxed;
  - every doc or comment the change made false;
  - every changed file the spec does not explain.

Fix what it finds, then dispatch it again. Stop when it reports nothing open, or after 3 rounds. At
the round limit, ask the operator whether to continue. Record every finding and its disposition.

## 6. Pull request and reviews

1. **Open the PR.**
   - `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id NO_PLAN`
     returns a path.
   - Write the body there: Summary; Changes, grouped per deliverable; Test evidence, naming the
     failing-then-passing tests. No footer.
   - Then: `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --plan-id NO_PLAN --head {branch} --base {base_branch} --title "{conventional title}"`
2. **Trigger each reviewer** with a PR comment (`ci pr prepare-comment` + `ci pr reply`), posting
   its resolved `trigger_comment`.
3. **Wait for CI:** `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks wait --pr-number {N} --timeout 540`.
4. **Read all three surfaces** after each push — the PR comments (`ci pr comments`), the PR reviews
   (`ci pr reviews`), and the inline threads in the PR comments. Triage every comment with
   `persona-code-reviewer`, applying its adversarial-refute lenses — defect or preference, surplus
   or load-bearing, real or false-positive drift, and severity — before deciding whether it applies.
   Handle every comment:
   - fix it, commit and push; or
   - answer it with `ci pr thread-reply` (the reason it does not apply), then close it with
     `ci pr resolve-thread`.
5. **After every push, re-trigger** a reviewer whose last review predates the head.
6. **Reviewer quota policy** ("review limit reached" or similar), for ANY required reviewer that
   refuses on quota:
   1. Wait 90 minutes. Record the refusal and the next allowed trigger time in the progress file,
      then stop the session or wait for the operator; never `sleep`. Then post that
      reviewer's `trigger_comment` again. Repeat up to 10 times. If no review from that reviewer
      exists at all, post its `escalated_trigger_comment` once.
   2. Still no reaction: close the PR **unmerged**, open a new PR from the same branch, and trigger
      again.
   3. Still nothing: stop and ask the operator. Never merge without the review.
   4. **Do not ask the operator about a quota before steps 1–3 are spent.** An answer that says
      "merge" or "continue" does not shorten the policy.
   5. **Re-trigger no sooner than 90 minutes after the refusal**, even when the reviewer's own notice
      names a shorter wait. Wait with
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments --pr-number {N} --timeout {seconds}`
      (repeat as needed), or stop the session, recording the next trigger time in the progress file.

## 7. Merge gate

Merge only when all of these hold:

- Every required reviewer reviewed the **current head**. **Exception — standing review
  authorization, quota-limited reviewers only.** For a required reviewer that the resolve result
  marks `quota_limited`, "reviewed the current head" may be replaced by ALL of:
  1. **a qualifying review exists** — a formal review by that reviewer on one of this PR's heads,
     listed by `ci pr reviews` with its commit id. Rate-limit notices, summary comments and thread
     replies do not count;
  2. **every finding is handled** — each finding from that review and from any later one is fixed in
     a pushed commit, or answered with a reason, and every one of that reviewer's threads is
     resolved;
  3. **it was re-triggered once after the last push**, and the refusal or silence is recorded;
  4. **every other gate condition holds on the current head** — every reviewer that is not
     quota-limited reviewed it, every comment is handled, the build gate is green, CI is green.
- Every comment is handled.
- `verify` (the full build, step 4) is green on the current head.
- CI is green on the current head.

The reviewer quota policy (step 6) applies only while no qualifying review exists. The standing
authorization never applies to a reviewer that is not quota-limited, and never to a PR without a
qualifying review.

**Any question that bears on the merge** states, per required reviewer, which head it last reviewed,
and whether that is the current head. It states the CI status and the `verify` status only from a
result obtained on that head AFTER the last push; where no such result exists it reports `pending`,
never an older run's answer. Its options never mark a rule-bending choice "Recommended". A false or
incomplete statement in such a question fails the run.

**Immediately before enqueue,** fetch the base branch again. **If it moved:**
`git -C {worktree} fetch origin {base_branch}`, then `git -C {worktree} merge origin/{base_branch}`. Run the build
gate again, push, re-trigger the reviewers, and repeat step 6.

**Before enqueue, re-check the authorization rule:** merge only when every condition above holds, or
when the operator **selected** an option in a question-tool call that names the exact gap (which
reviewer, which head). Free text — "continue with merge", "at least one review is ok", "do merge" —
is never that selection. If you have only free text, ask the question with the tool and wait for the
selection.

**Enqueue and settle:**

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge-queue --pr-number {N}
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-queue-settle --pr-number {N} --timeout 540
```

- Only `settle: merged` with a `merge_commit_sha` is a landing.
- `dequeued`: report it and ask the operator.

**Clean up after the merge**, from the main checkout:

1. Check `git -C {worktree} status --porcelain`. If it shows anything, stop and ask. Then run
   `git worktree remove {worktree}`, never with force. The git-workflow `worktree-remove` verb
   refuses in this lane, so do not use it.
2. `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow prune-local-and-remote-ref --project-dir . --head {branch}`
3. `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow switch-and-pull --project-dir . --base {base_branch}`

Never use `git branch -D`. If a cleanup step refuses, report it and ask. Never move the main
checkout by hand (`git fetch` + `merge`, `pull`, `switch`, `reset`): other sessions may be working
in it, and step 3 is the only sanctioned way to update it.

## 8. Landing message (the last step, after the merge)

Write the payload to `{landing_file}`, then send it:

```bash
{inbox_write_command}
```

The payload is a facts block followed by the report, both taken from the progress file (section 0a).
The facts block is fenced with the `landing-facts` info-string and carries exactly the schema fields
the orchestrator's landing-payload contract defines; its field values follow.

```landing-facts
schema=landing-facts/1
plan_id={sender_id}
epic={slug}
pr=#{N}
merge_state=merged
cleanup_owed=false
deliverables_total={spec deliverable count}
deliverables_done={deliverables whose every Done-when is met}
total_tokens=unknown
harness={harness}
model={every model and variant used, comma-separated, e.g. deepseek-v4.1-flash/max,deepseek-v4.1-flash/high; record each switch in the progress file}
steps=setup:done,implement:done,build-gate:done,self-review:{clear|budget-exhausted},pr:done,reviews:done,merge:done
```

- **Values:** write `unknown` for anything you could not read, never `n/a` and never a guess.
  `deliverables_done` counts only fully met deliverables.
- **Every line inside the facts fence is a `key=value` pair** — no line is dropped by the consumer's
  parser. The guard state travels as a prose note beside the block rather than as a fence line:
  `guard: none on this harness (unenforced)` when the resolve result reported `guard: none`, and
  `guard: present` otherwise.
- **Guard:** where the resolve result reported `guard: none`, the rule-check section of the report
  says `guard: none on this harness (unenforced)`. Never report "all kept" or "no guard-log line"
  for a harness with no guard.
- **The report follows the facts block,** one short section each:
  1. **Deliverables** — per Done-when: met or not met; the test name and its fail-then-pass evidence;
     the commit.
  2. **Personas and skills** — per step, which persona was applied (section 1's table, or the
     deliverable's own `Persona:` line); per deliverable, the domain skills it named — or
     `skills: none named` when the spec declares none — and any skill added for surface drift as
     `skills added: …, reason: …`.
  3. **Hypotheses** — each one confirmed or refuted, with `file:line`.
  4. **Findings** — self-review, CI and every PR comment, each with its disposition.
  5. **Reviewers** — one row per reviewer in `{required_bots}` and `{optional_bots}`: reviewed /
     refused / silent, the head reviewed, and the trigger and wait history. **Standing review
     authorization:** per quota-limited reviewer, the head it reviewed, the current head, and each
     finding with how it was handled.
  6. **Operator questions** — **every** question-tool call in the run, in order: its text, its
     options, and the option selected. List free-text operator messages separately, as free text.
     If no question-tool call was made, write "none asked".
  7. **Rule check** — every section 1 rule that you or a sub-agent did not keep, and every guard
     refusal: read `{guard_log}` (the path `resolve` returns) for this run's sessions and list each
     line. "All kept" is allowed only when that log has no line for the run — and never on a harness
     whose resolve result reported `guard: none`.
  8. **Residue** — anything left open.

Then tell the operator the PR number, the merge commit, and that the landing message was written.

**Never edit a filed inbox message.** To correct it, stage the correction body and run
`python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox amend --slug {slug} --message {name} --payload-file .plan/temp/amend-{plan}.md`
(see its `--help`), which stamps a revision.

**Stopping before the merge** (blocked, or the operator stops the run): write the same message with
`merge_state` set to `open` or `n/a`, and `pr` set to the PR number or `n/a`.
