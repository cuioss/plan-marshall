---
name: runbook-lane
description: The runbook lane - implementation contract for ONE staged orchestrator plan spec on a cheap model, without the /plan-marshall lifecycle. Resolves every project-specific value (epic slug, derived names, build commands, reviewers with their trigger comments, commit trailer, inbox command) through the runbook_lane resolve verb, then runs the lane - progress file and resume, hard rules, evidence orders (test-first, mutation-after, none), build gate, self-review rounds, PR and review cycle, merge gate, cleanup, and a landing message to the epic inbox - from any project that has plan-marshall installed
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
with their trigger comments, the commit trailer, the harness and guard state, the build server's
preflight state (`build_server`, plus `build_server_reason` when it is `down`), the Sonar state
(`sonar`, plus `sonar_project_key` when it is `configured`) and the `inbox write`
command. `--project-dir` defaults to the current directory and anchors every project-scoped read.
The spec read is worktree-first: the shared ledger worktree's copy is read when it exists and the
main checkout's is the fallback. The result always carries `spec_source` (`ledger_worktree` |
`main_checkout`), plus `spec_differ: true` when both copies exist and differ.
`--spec-from-ledger` is accepted as a documented no-op: it names the read the default makes, so a
command line that carries it behaves exactly as one that does not.
Fails closed with a specific error code for a spec outside the orchestrator tree, an unreadable
configuration, an unreadable Sonar block (`sonar_config_unreadable`) or a Sonar block with no
project key (`sonar_config_incomplete`), a missing automatic-review
step, an empty required-reviewer list, a project that
resolves no gate build command (naming the gate canonicals it could not resolve), or a bare
skill/persona name in a flat install with no recorded bundle identity
(`flat_skill_identity_missing`).

### executor-skew

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane executor-skew \
  [--executor .plan/execute-script.py] [--lane-dir DIR]
```

Compares the version the executor carries with the version of the lane text it will run, reading the
executor through the shared `plugin_registry` reader rather than parsing it. It answers `match`,
`skew`, `not_applicable` or `could_not_check`, and names both versions; `skew` also carries the
remedy. The lane runs it before `resolve` (section 0), because a stale executor's own `resolve`
cannot perform the check.

Where the lane text's version comes from, once, per layout: a versioned plugin cache supplies it from
the newest eligible `{bundle}/{version}/skills/{skill}` directory; a flat install (OpenCode,
Antigravity) has no version directory, so it supplies the `version` of the install stamp — the
`dist-manifest.json` the sync writes at the deploy root that contains the skill root, where the
target's sync publishes one (without it the comparison stays `could_not_check`). The stamp moves only
on a sync, so an edit made to the installed lane text in place is not part of what the comparison
sees.

A source checkout — a bundle carrying `.claude-plugin/plugin.json` directly, with no version
directory — answers `not_applicable` when the lane text it probed is the text this run executes. It
is not `match`: nothing agreed, because nothing was compared. It is safe because the executor maps
that checkout's own scripts, so the lane text cannot name a verb its mapped script lacks — an unknown
verb fails at once with the surface named. A source checkout probed from another tree (an explicit
`--lane-dir` pointing elsewhere) is not excused: its lane text may name a verb this run's mapped
script lacks, so it stays `could_not_check`. The lane proceeds without asking, and records the
verdict in the landing. What it does not cover is a stale executor TEMPLATE: the executor's own code,
not its mapped scripts, decides how a run is dispatched. Only `bootstrap` compares the embedded
template hash, and it regenerates in place when that is stale, so it is not a read-only witness a
lane may call; `preflight` compares the manifest's version fields, so a template-only change does not
reach it at all.

A `could_not_check` is reported and the operator is asked — never read as "no skew" — and its reason
names the thing it could not read: the executor, the install stamp it probed, or the version-less
bundle directory.

### build-routing

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane build-routing \
  --worktree {worktree}
```

Decides whether the next build may be submitted to the daemon or must run in-process, from whether
the worktree carries a usable `.plan/execute-script.py`. It answers `executor_in_worktree:
present|absent`, then `auto` (submit with no execution flag) or `in_process` with the reason it
names for the degraded case — `executor_absent_from_worktree` for a worktree with no usable slot,
`worktree_not_created` for one that does not exist yet. Section 4 runs it before the first routed
build.

### build-classify

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane build-classify \
  --paths "changed/path/one,changed/path/two" \
  [--project-dir DIR]
```

Classifies changed paths as `docs-only` or `buildable` for the build gate (section 4), reading the
project's own footprint rule. It answers `source: ci-workflow` when the project's CI opts in to the
footprint gate, and `source: architecture` otherwise.

### sonar-gate

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane sonar-gate \
  --state {configured|not_configured} [--count-status {confirmed|undecidable|unconfigured}] \
  [--open-count N] [--open-keys "K1,K2"] [--dismissed-keys "K1,K2"]
```

`--count-status`, `--open-count`, `--open-keys` and `--dismissed-keys` belong to a `configured`
state: supplying any of them beside `--state not_configured` is refused as `state_contradicts_read`,
because a project with no Sonar has no read to report.

Decides the merge gate's Sonar condition (section 7) from the read taken on the head:
`merge_allowed: true` for `not_configured`, for a confirmed `0`, and for a confirmed count whose
every enumerated key carries a recorded dismissal. `undecidable` and `unconfigured` reads, an
undismissed key and a count with no enumerated keys all answer `merge_allowed: false` with their
`reason`.

### sonar-facts

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane sonar-facts \
  --state {configured|not_configured} [--count-status {confirmed|undecidable|unconfigured}] \
  [--open-count N] [--rules "R1,R2"]
```

Renders the landing's optional Sonar facts (section 8) from the read taken at the merge head:
`step.sonar-roundtrip.open_issue_count` and `step.sonar-roundtrip.open_issue_rules` in `fact_lines`.
A confirmed count carries the measured figure and the rules it left open (`--rules` is required
above zero, and `none` at a measured `0`); `undecidable` and `unconfigured` both carry `unknown`, and
a project without Sonar carries `n/a` at both.

## 0. Input

The invocation names a spec:

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/{slug}/plans/PLAN-NN-{slug}.md
```

**Before `resolve`, check that the executor is not older than this text.** Compare the version the
executor carries with the version of the lane text this run read:

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane executor-skew
```

It answers `match`, `skew`, `not_applicable` or `could_not_check`, naming both versions. A `skew` —
or an `unknown_verb`/argparse rejection that shows the executor predates this text — stops the run as
**blocked**, naming both versions and the remedy: regenerate the executor (`/marshall-steward`, or
the project's equivalent generate step). A `could_not_check` (the executor is unreadable, its
version is absent, or the lane text's own version cannot be derived) is reported as **could not
check** and the operator is asked; it is never read as no skew. A `not_applicable` (a source
checkout; § executor-skew says why it is safe, and what it leaves uncovered) proceeds without asking
and is recorded in the landing. The check cannot live inside
`resolve`: a stale executor runs the stale `resolve`, which is exactly the code that lacks it, while
this text is loaded from the installed plugin and is current when the executor is not.

**A target difference is not a regeneration trigger.** One executor serves every harness: the
generated file does not depend on which harness generated it, and a call from any harness resolves
and dispatches. Only a changed script set or a stale version justifies a regeneration — never the
fact that another harness last wrote the file.

The spec is read from the **shared ledger worktree** first —
`{epic_dir}/plans/{spec name}`, where `epic_dir` follows the same store seam
`orchestrator resolve-path --slug {slug}` publishes — and the main checkout's copy only when the
worktree holds none. That worktree-first order is the default, so an emitted command needs no flag
and no ledger land between a spec edit and the emit; with `orchestrator.use_worktree` off there is
no second copy and the one copy is read without error. `--spec-from-ledger` is accepted as a
documented no-op: it names the read the default makes, so a command line that carries it behaves
exactly as one that does not.
`resolve` reports which copy it read (`spec_source`) and, when both copies exist and differ, the
`spec_differ` marker — "the copy NOT read says something else", which is now the main checkout's
copy — so a read of the older copy is never silent. The worktree copy is READ ONLY either way. Then
**resolve** every value the run uses, and read the result before doing anything else:

```bash
python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane resolve --spec {spec}
```

The result supplies, and nothing below is spelled from anywhere else:

| Name | Field of the resolve result |
|------|-----------------------------|
| spec copy read, and whether the other copy differs | `spec_source` (`ledger_worktree` \| `main_checkout`), plus `spec_differ: true` when both copies exist and differ |
| epic slug | `slug` |
| `{plan}` | `plan` |
| worktree | `worktree` |
| branch | `{branch} = {prefix}{plan}`; one closed set supplies the prefix — the canonical `feature/` (a new capability), `fix/` (a bug fix) and `chore/` (docs or maintenance), plus a prefix the project's configured `working_prefixes` declares. The two sources are one set with no precedence between them |
| base branch | `base_branch` (the project's own base branch, never a spelling of it) |
| inbox sender id | `sender_id` |
| progress file | `progress_file` |
| landing file | `landing_file` |
| build commands | `build` |
| gate canonicals the project does not publish | `build_missing_canonicals`, present only when one is missing |
| build timeout (seconds) | `build_timeout_seconds` |
| runtime stamp reason | `runtime_stamp_reason`, present when a stamp fact could not be measured |
| required and optional reviewers, with their trigger comments | `required_bots`, `optional_bots` |
| commit trailer | `commit_trailer` |
| `inbox write` command | `inbox_write_command` |
| harness, guard and the landing's runtime stamp | `harness`, `guard`, `model`, `effort`, `plugin_version`, and `executor_version` when it was read |
| guard-log path | `guard_log` |
| build server state | `build_server`, plus `build_server_reason` when the state is `down` |
| Sonar state, and the project key when configured | `sonar` (`configured` \| `not_configured`), plus `sonar_project_key` when it is `configured` |
| Sonar CE-readiness wait budget (seconds) | `sonar_ce_wait_timeout_seconds`, present only when `sonar` is `configured`: the harness's Bash ceiling less a teardown margin (the provider's own 600s default when the target imposes no ceiling). An unreadable ceiling is `sonar_ce_ceiling_unreadable`, never a 600s fallback that a lower ceiling would kill |
| worktree executor state | `executor_in_worktree` (`present` \| `absent`), plus `executor_reason` when `absent`: `worktree_not_created` for a resolve taken before setup, `executor_absent_from_worktree` for a worktree whose slot was never filled |

The branch row is derived from the project's configuration rather than returned by `resolve`; every
other row names a field of the resolve result.

The verb **fails closed**: a spec outside `.plan/orchestrator/{slug}/plans/`, an unreadable
configuration, a missing or unreadable project architecture (`architecture_unavailable`), an
unreadable Sonar block (`sonar_config_unreadable`) or a Sonar block with no project
key (`sonar_config_incomplete`), a missing automatic-review
step, an empty required-reviewer list, no gate build
command (`quality-gate` or `verify`) the project's architecture can resolve, or a bare
`Skills:`/`Persona:` name in a flat install whose `SKILL.md` records no bundle identity
(`flat_skill_identity_missing`) is an error carrying a specific code. There is never a fall-back to
a default reviewer list or a default build. Stop and report a resolve error; do not substitute a
value.

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

**Re-read this skill in full** at every session start, after every server restart, after every
context compaction and after any idle gap. It can change during a run; the current version binds.
Record the re-read in the progress file with its timestamp and what triggered it.

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
build-server: {ready|disabled|down}{ (reason)}; builds: {mechanism: count, …}; fallback: {none|in_process|degraded}, {reason or none}
re-read: lane text loaded at {timestamp} ({session start|compaction|restart|idle gap})
D{n} hypothesis: {claim} — confirmed|refuted, {file:line}
D{n} test: {test name} — order {test-first|mutation-after|none}; failing run {commit} {output identifier}; passed at {sha}
D{n} done: commit {sha}
sonar: {configured (project key)}|{not_configured}; read at {sha}: {count} confirmed|{undecidable, retried}|{not_configured}; dismissals: {issue-key: reason, … or none}
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
- **Evidence.** Every Done-when's evidence carries an `order` — exactly one of `test-first`,
  `mutation-after` or `none` — and this rule is the ONE place a Done-when is graded by it:
  - `test-first` is met: the test was written and seen failing against the unfixed code, and the
    failing output is recorded.
  - `mutation-after` is met with the order stated: the failing output came from mutating or
    reverting the committed fix, and the test, commit and output identifier are reported.
  - `none` on a Done-when whose clause says "fails at `{sha}`" is reported **not met as written**,
    with the reason, so its deliverable is **not** fully met — and `deliverables_done` counts only
    fully met deliverables.
  - A green run at HEAD is never evidence that a test fails without the fix. The words "fail-first"
    and "observed failing before the fix" are reserved for `test-first`; a `mutation-after` or
    `none` order says so instead.
  - The failing run is reported by its commit and output identifier wherever the order is not
    `none`.
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
  - a required reviewer cannot be obtained (§ 6 step 7).

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
  pre-tool-use hooks at all). Where nothing was enforced, the landing message says so: the guard
  state travels as prose beside the fence, never as a facts-fence line, and the rule-check section
  reports `guard: none on this harness (unenforced)`. The lane never reports "all kept" or "no
  guard-log line" when nothing was enforced. The guard's audit log is `{guard_log}` (the path
  `resolve` returns); step 8 reads it there for this run's sessions.

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
   - It PRODUCES the worktree's own `.plan/execute-script.py` and reports `executor_in_worktree:
     present`, or `absent` with the reason. Record the verdict; an `absent` slot is a degradation the
     build gate has to route around (section 4), never a reason to fail the creation.
4. `git -C {worktree} push -u origin {branch}`. Make no edit before this push.
5. **Check every named skill and persona exists.** The resolve result carries one row per spec
   deliverable with its `Skills:` and `Persona:` declarations. A `Skills:` entry is a
   `bundle:skill` notation (comma-separated for several); a `Persona:` entry is the persona kind
   (`implementer`) or its full skill name. Every named skill and persona must
   exist in the installed bundles; `resolve` reports a name that does not as a
   `named_skill_not_found` error, and the run then **stops and asks the operator**. A bare name in a
   flat install whose `SKILL.md` records no bundle identity is the
   `flat_skill_identity_missing` error for the same reason. A missing skill
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
executor path. One exception is a verb the plan's own branch introduces: only the WORKTREE's
executor knows that surface, so that call runs with the shell in the worktree, in the same relative
form — section 3 step 5 refreshes that executor first. Builds run against the worktree with the
resolved `build` commands (section 4) and the default routing (`auto`): the project's build wrapper
decides whether the job runs in-process or is submitted to the build daemon.

6. **Build-server preflight — once, here.**
   `python3 .plan/execute-script.py plan-marshall:build-server-client:build_server preflight --project-path {worktree}`
   answers `ready`, `disabled` or `down`. Record it in the progress file and the landing message as
   `build_server: ready|disabled|down`, with `reason` when the state is `down`. The resolve result
   carries the same field for the project root; this setup call is the one that describes the
   worktree.
   - `disabled` — the project is not enrolled at setup. That is not an error: enrolment is an
     operator action in `manage-build-server`, and the default routing's own preflight answers
     `disabled` for an unenrolled project, so the builds run in-process.
   - `down` — the daemon was unreachable at setup. Record the reason. The builds still run with the
     default routing, which preflights again per build, so the `mechanism` a build result reports is
     the authority for how THAT build ran. The `build-routing` check (section 4) decides whether a
     build may be routed at all.
   - `ready` — routing is available. A routed job re-runs the worktree's own `.plan/execute-script.py`,
     never the main checkout's. Worktree creation PRODUCES that executor through the same seam the
     phase-5 move-in uses, and its payload reports `executor_in_worktree: present`, or `absent` with
     the reason. Read that verdict and record it; a `present` slot is what lets a routed build submit.
     Section 4 still runs the `build-routing` check before the first routed build, and only an
     `absent` slot degrades it to `in_process` with the `executor_absent_from_worktree` reason.

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
2. Write the Done-when tests and capture their evidence under the `order` §1 defines.
3. Implement. Run the tests; record them passing.
4. If any `*.py` changed, run the quality gate (step 4) until clean.
5. **Refresh the worktree executor after adding, removing or renaming a script verb**, before running
   the new verb:
   `python3 .plan/execute-script.py plan-marshall:workflow-integration-git:git-workflow worktree-executor-refresh --plan-id {plan}`.
   The executor embeds the script map and argparse surface it derived when the worktree was created,
   so a verb the branch adds is not in that record — the executor may refuse the call as
   `unknown_verb`, and cannot describe the verb's flags — until the surface is rebuilt. The rebuild
   goes through this verb, never through a direct interpreter call to the generator by path.
   Record `executor_regenerated` and its detail; a `false` is a blocker, not a warning.
   Then run the new verb **through the worktree's executor**, with the shell in the worktree and the
   same relative form (`python3 .plan/execute-script.py …`): that executor is the only one whose
   surface the refresh rebuilt, and it is the same one a routed build re-runs.
   - **The plan that introduces this refresh verb itself** cannot call it: no executor's surface
     carries it yet. Bootstrap that one case through the registered generator notation, from the
     worktree: `python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate --marketplace-root .`
     with the shell in the worktree. It is a notation like any other, never the generator's path, and
     every plan landing after this one finds the verb already in its own executor.
   - A worktree reporting `executor_in_worktree: absent` has no executor to bootstrap through. That is
     a **blocker**: record it, and have the operator regenerate the checkout's executor with the
     project's own steward step. The lane never spells the generator's path to get around it.
6. Commit with the deliverable paths staged by name, then push. Record `D{n} done` in the progress
   file.

## 4. Build gate

Every build runs from the main checkout against the worktree, using the commands the resolve result
supplies and the default routing. Each line below applies only where the resolve result supplies
that canonical — a project with a single gate canonical supplies no `{build.verify}`, and one that
publishes no test part supplies no `{build.module-tests}`:

```bash
{build.quality-gate} --project-dir {worktree}
{build.module-tests} --project-dir {worktree}
{build.verify} --project-dir {worktree} --timeout {build_timeout_seconds}
```

- **Routing.** The DEFAULT routing — no `--execution-mode` flag — is used for EVERY build. Under it
  `auto` submits the job to the build daemon when the setup preflight found it `ready`, and runs
  in-process otherwise. Before the first routed build, run
  `python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane build-routing --worktree {worktree}`:
  `auto` means the worktree carries its own executor and the build submits with no execution flag, so
  the daemon re-runs that executor; `in_process` is the DEGRADED answer for an `absent` slot, where
  the run passes `--execution-mode in_process` for that build and records the
  `executor_absent_from_worktree` reason, so the gate still runs instead of ending terminal on an
  executor the worktree does not carry. The daemon applies its OWN supervisory bound, which
  `--timeout` can only raise; a bound expiry comes back as `timeout` naming `timeout_used_seconds`
  and `timeout_source`, and the client's rules for it are cited, not restated. Record a bound
  expiry and continue with the split form below rather than re-submitting the same bound.
- **A launch fault costs ONE retry, not the server.** A routed build whose result is a launch fault
  (`error: execution_failed` or `log_file_failed`) never started, so it is NOT a red build: re-run
  that build ONCE with `--execution-mode in_process`, record the retry with its `reason` in the
  progress file and the landing message, and submit the NEXT build with the default routing again.
  `--execution-mode in_process` as a STANDING setting for the rest of the run is allowed only where
  `build-routing` answered `in_process`; never let one routed failure turn the server off for the
  run.
- **Read the routing outcome** from the build result's own fields (`requested`, `resolved`, `reason`,
  `mechanism`). A `degraded` result has already fallen back in-process: record the degradation and
  its `reason` in the progress file and the landing message.
- **A `killed` job is never blind-retried.** Read its status and record it; whether to run it again
  is the operator's decision, asked with the question tool.
- **One daemon-routed build at a time per worktree**, sub-agents included. The build-server client's
  prohibitions — a routed build is never backgrounded, and a `running` result is re-attached with a
  bounded wait — are stated in `build-server-client/SKILL.md` and bind here as written, not
  restated. A second concurrent submission is the case that client cannot see: two routed builds
  from one worktree can interleave, and a result can carry its sibling job's counts.
- **Shell timeout:** an in-process build holds the shell call for its whole duration, and a routed
  build also holds the call — its wait is bounded and re-polled inside the same call, never
  backgrounded. Give each call the shell tool's `timeout` parameter, set at or above the build's own
  timeout; on a harness whose default shell timeout is shorter than the build, raise that parameter
  or run the split form below. The routing choice does not shorten the call.
  - If the tool cannot wait that long, run the gate's parts as separate calls, in the order
    `{build.split}` states, running each canonical the resolve result supplies — for example
    `{build.quality-gate}`, `{build.test-compile}` and `{build.module-tests}` where the project
    publishes all three, each with the same worktree flags.
  - Run exactly the canonicals `split` names. `module-tests` and `test-compile` are test-conditional
    in the architecture's contract, so an absent one means the project publishes no such part — not
    that a part was skipped. `quality-gate` and `verify` are the gate, and each build system
    publishes them conditionally, so the resolve result carries at least one; a project that
    resolves neither has already failed `resolve`. Where `split` names nothing, run the gate
    canonical the resolve result supplies — `{build.quality-gate}` where supplied, otherwise
    `{build.verify}` — because the project publishes no separable part. Where the only candidate
    parts are gate canonicals, the split cannot be shorter than `verify` (Maven's `quality-gate` IS
    `verify -Ppre-commit`), so `resolve` answers an empty `split` and the lane runs the gate
    canonical itself.
  - A daemon-routed build is waited on in the same call, never moved to the background.
- **Read the result, not the exit code.** The TOON must show `status: success` and an empty
  `errors[]`. Open the `log_file` it names for the test summary.
- **Docs-only change.** Before running the full build, classify the worktree diff against the base:
  get the changed paths with `git -C {worktree} diff --name-only origin/{base_branch}...HEAD`, then
  pass them to the `build-classify` verb. When it answers `kind: docs-only`, run **no** full
  `verify`: check the changed docs instead (format, internal links and references, and a
  `git status` showing only doc files) and record `build-gate: docs-only` in the progress file and
  the landing message. A docs-only head runs no `module-tests` and no `test-compile`: the build was
  skipped, so there is no test part to run, and CI's required checks still gate the head.
  `kind: buildable` runs the gate below as usual. The classifier applies the
  PROJECT's own footprint rule rather than assuming a `.py` file is the only thing that builds. Its
  non-building class is the project's CI rule where the checkout HOLDS it: a `paths-ignore` block in
  the workflow that carries the `skip-on-docs-only` opt-in. Where it does not — the rule lives in a
  reusable workflow the checkout does not hold — the narrow fallback is the architecture's
  documentation module prefix AND that module's own `doc` extensions, matched case-sensitively.
  `extra-buildable` globs force a build ahead of either. A path the classifier cannot place, and any
  rule it could not read (reported as `reason`), builds — the fail-closed direction, so a wrong
  answer costs a local build and never skips one the CI would run. Pass the same `--project-dir`
  the build gate uses. Required CI checks still have to be green, so the merge gate is unchanged.
- **When to run what:** run the gate canonical the project publishes (`{build.quality-gate}` where
  the resolve result supplies it, otherwise `{build.verify}`) before each commit that touches
  `*.py`, and the same gate canonical once before the PR. Scope the tests to one module while
  iterating.
- **Every pushed head:** a test run at every head pushed to a PR — not once for the run. Run
  `{build.module-tests}` where the resolve result supplies it, plus `{build.test-compile}` where the
  project publishes one; a project that supplies neither is gated by the gate canonical it
  publishes. Record the sha of each run; a head that was not tested is not a green head.
- **A single gate canonical is a complete gate.** The merge gate's `verify` condition (section 7)
  names what replaces it when the project publishes no `verify` or the routed run hit the daemon's
  bound.
- **Failures that already fail on the base branch:** environment-dependent tests can fail in a
  project's local module-tests run. They are not yours. Only a failure in a module you touched, or
  one the base branch does not show, is yours.
- **Surface/naming errors** such as "unknown subcommand": suspect a stale executor first and ask the
  operator with the question tool — do not change source to silence them. The landing records that
  the question was asked and the answer it got, or, where the harness offered no question tool, says
  `no question tool was available`.

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

Fix what it finds, then dispatch it again. Stop when a round reports nothing open, or after 3 rounds.
At the round limit the still-open items are reported AS open, and `self-review: clear` is never
permitted while any finding is open — that state is reported as `budget-exhausted`. Ask the operator
whether to continue at the limit. Record every finding and its disposition.

## 6. Pull request and reviews

1. **Open the PR.**
   - `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id NO_PLAN`
     returns a path.
   - Write the body there: Summary; Changes, grouped per deliverable; Test evidence. The evidence
     carries, per Done-when, the `order` and verdict §1 defines, the test name, and the failing
     run's commit and output identifier only where the order is not `none`. No footer.
   - Then: `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --plan-id NO_PLAN --head {branch} --base {base_branch} --title "{conventional title}"`
2. **Trigger each reviewer** with a PR comment (`ci pr prepare-comment` + `ci pr reply`), posting
   its resolved `trigger_comment`.
3. **Wait for CI:** `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks wait --pr-number {N} --timeout 540`.
4. **Read the pull request's open Sonar issues** — after CI is green on the head and before the
   pull request is reported ready. Skip nothing when `sonar` is `configured`:
   - `resolve` reported `not_configured`: there is nothing to read. Record `sonar: not_configured`
     in the progress file and the landing, and go on.
   - `configured`: read the head's open new-code issues with the provider's plan-less read, which
     needs no plan directory —
     `python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar read_open_issues --project {sonar_project_key} --pr {N} --ce-wait-timeout {sonar_ce_wait_timeout_seconds}`.
     Pass the resolved budget: it sits below this harness's Bash ceiling, so a read that does not
     settle returns its own `undecidable` instead of being killed with no state at all.
     Fix each issue in a pushed commit, or dismiss it with a stated reason (see the dismissal rule
     below). Re-read after every push until the count is `0` confirmed, or every remaining issue
     carries a recorded dismissal. Then decide the gate:
     `python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane sonar-gate --state configured --count-status {confirmed|undecidable|unconfigured} --open-count {n} --open-keys {k1,k2} --dismissed-keys {k1,k2}`.
   - **A dismissal** is recorded in the progress file as `{issue-key}: {reason}` and transmitted with
     the provider's raw REST transition, which is the one dismissal surface that takes a bare issue
     key and needs no plan —
     `python3 .plan/execute-script.py plan-marshall:workflow-integration-sonar:sonar_rest transition --issue-key {key} --transition {falsepositive|wontfix}`.
     A dismissal the lane cannot transmit is a **blocker**, never a silent pass: record the failure
     and stop.
   - An `undecidable` read (the analysis did not settle, the analysis is of another commit —
     `stale_analysis` — no revision was reported for it, its head could not be resolved, or the
     REST/auth call failed) is a **blocker**, never a `0`: retry the read, and if it stays
     undecidable do not merge. An
     `unconfigured` read — the typed status the provider answers when the credential resolve said
     existed could not authenticate — is a blocker too; pass it to the gate and to `sonar-facts` as
     `--count-status unconfigured`.
5. **Read all three surfaces** after each push — the PR comments (`ci pr comments`), the PR reviews
   (`ci pr reviews`), and the inline threads in the PR comments. Triage every comment with
   `persona-code-reviewer`, applying its adversarial-refute lenses — defect or preference, surplus
   or load-bearing, real or false-positive drift, and severity — before deciding whether it applies.
   Handle every comment:
   - fix it, commit and push; or
   - answer it with `ci pr thread-reply` (the reason it does not apply), then close it with
     `ci pr resolve-thread`.
6. **After every push, re-trigger** a reviewer whose last review predates the head. Re-read the open
   Sonar issues after every push too, on the same condition as step 4.
7. **Reviewer quota policy** ("review limit reached" or similar), for ANY required reviewer that
   refuses on quota **while no qualifying review exists** (see section 7):
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
     listed by `ci pr reviews` with its commit id, or, where the reviewer publishes a clean review
     only as a summary comment, the marker-bearing summary comment whose `sourceCommitId` /
     `coveredCommitId` name one of this PR's heads and whose `kind=reviewed` (the
     `final_review_risk_coverage` marker the reviewer's summary comment carries; read it from the
     comment itself, because the marker names the head the review covered).
     Rate-limit notices, marker-less walkthroughs and thread replies do not count;
  2. **every finding is handled** — each finding from that review and from any later one is fixed in
     a pushed commit, or answered with a reason, and every one of that reviewer's threads is
     resolved;
  3. **it was re-triggered once after the last push**, and the refusal or silence is recorded;
  4. **every other gate condition holds on the current head** — every reviewer that is not
     quota-limited reviewed it, every comment is handled, the build gate is green, CI is green.
- Every comment is handled.
- `verify` (the full build, step 4) is green on the current head. Where the project publishes no
  `verify`, the gate canonical it does publish is green instead — a single gate canonical is a
  complete gate (section 4). Where the routed `verify` hit the daemon's supervisory bound, the split
  form's parts are the run that must be green.
- CI is green on the current head.
- The Sonar state of the current head admits the merge: `sonar-gate` reports `merge_allowed: true`
  on a read taken after the last push — its open new-code issue count is `0` confirmed, or every
  remaining issue carries a recorded dismissal with its reason, or `resolve` reported
  `not_configured`. An `undecidable` read is a blocker and is retried, and an `unconfigured` read is
  a blocker too; the lane never treats either as `0`.

The reviewer quota policy (§ 6 step 7) applies only while no qualifying review exists. The standing
authorization never applies to a reviewer that is not quota-limited, and never to a PR without a
qualifying review.

**An unresolved review thread or an unhandled outside-diff finding on the merge head blocks the
standing authorization.** A reviewer's thread that is still open, or an outside-diff finding the run
neither fixed nor answered, means a finding is not handled, so the second condition fails however
strong the review credit is.

**Any question that bears on the merge** first re-reads the review surfaces — `ci pr comments`,
`ci pr reviews`, and the reviewer's summary comment — in the same step as the question, and again
immediately before the enqueue, and states only facts read in that step: per required reviewer,
which head it last reviewed, and whether that is the current head; the CI status, the `verify`
status and the Sonar state only from a result obtained on that head AFTER the last push, reporting
`pending` where no such result exists, with the Sonar state as the gate's verdict for that head
alone. Its options never mark a rule-bending choice "Recommended". A review of the current head that
arrived after the question was asked invalidates the answer: ask the question again. A false or
incomplete statement in such a question fails the run.

**Immediately before enqueue,** fetch the base branch again. **If it moved:**
`git -C {worktree} fetch origin {base_branch}`, then
`git -C {worktree} merge origin/{base_branch} -m "merge: origin/{base_branch} into {branch}" -m "{commit_trailer}"`,
so the merge commit it creates ends with the resolved `{commit_trailer}` line the Commit trailer rule
requires. Run the build gate again, push, re-trigger the reviewers, re-read the Sonar issues, and
repeat the reviewer quota policy (§ 6 step 7).

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
effort={the effort level measured with the model}
plugin_version={the plan-marshall bundle version}
executor_version={the executor version when resolve returned one; drop this line when it did not (optional)}
steps=setup:done,implement:done,build-gate:done,self-review:{clear|budget-exhausted},pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count={measured count|unknown|n/a}
step.sonar-roundtrip.open_issue_rules={rules left open|none|unknown|n/a}
```

- **Values:** for a required key, write `unknown` for anything you could not read, never `n/a` and
  never a guess. `deliverables_done` counts only fully met deliverables. The optional per-step facts
  below carry their own two sentinels, where `n/a` is a legal answered absence.
- **Sonar (optional):** when `sonar` is `configured`, render the two facts with
  `python3 .plan/execute-script.py plan-marshall:runbook-lane:runbook_lane sonar-facts --state configured --count-status {confirmed|undecidable|unconfigured} [--open-count {n}] [--rules "{r1,r2}"]`
  and write its `fact_lines` verbatim. When it is `not_configured`, render them with
  `--state not_configured` and write `n/a` at both. They are the lane's own measurement of the
  merge head — the open new-code issue count and the rules of the issues left open there — and they
  are **optional**: the required key set above is unchanged, so their absence never makes a landing
  incomplete. A confirmed count writes the measured figure, with the rules it left open (`none`
  when that count is `0`). An `undecidable` or `unconfigured` read writes `unknown` at both: both
  are failed reads, never `0`, and never a claim the run did not earn.
- **Runtime stamp:** `harness`, `model`, `effort`, `plugin_version` and the optional `executor_version` are
  the resolve result's fields of those names, resolved from the platform-runtime `runtime-info` seam.
  Read the stamp from a `resolve` **re-run at landing time**, not from the setup-time result, so a model
  or effort switch during the run is stamped; record every switch in the progress file. `model` keeps
  its `{model}/{variant}` list form — one element per model and variant used.
- **Every line inside the facts fence is a `key=value` pair** — no line is dropped by the consumer's
  parser. The guard state travels as prose beside the fence rather than as a fence line:
  `guard: none on this harness (unenforced)` when the resolve result reported `guard: none`, and
  `guard: present` otherwise.
- **Guard:** where the resolve result reported `guard: none`, the rule-check section of the report
  says `guard: none on this harness (unenforced)`. Never report "all kept" or "no guard-log line"
  for a harness with no guard.
- **The report follows the facts block,** one short section each:
  1. **Deliverables** — per Done-when: met, or not met / **not met as written** (a Done-when whose
     "fails at `{sha}`" clause was not seen failing); the test name; an `order` field with exactly
     one of `test-first`, `mutation-after` or `none`; the failing run's commit and output identifier
     that the order names; and the commit. The words "fail-first" and "observed failing before the
     fix" are reserved for `test-first` — `mutation-after` means the failing output came from
     mutating or reverting the committed fix, and `none` means no failing output was captured. A
     `not met as written` Done-when leaves its deliverable not fully met. Also report the sha of
     every per-head test run (`module-tests`, and `test-compile` where the project publishes one)
     against a pushed head.
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
     options, and the option selected. List free-text operator messages separately, as free text. A
     surface/naming error that prompted a question is recorded here with the answer it got; when the
     harness offered no question tool at all, this section says `no question tool was available`. If
     no question was needed and none was asked, write "none asked".
  7. **Rule check** — every section 1 rule that you or a sub-agent did not keep, and every guard
     refusal. The check counts the run's OWN actions, not only what the guard recorded: every shell
     file operation the run issued — the read-class ones included — every routed build including a
     failed one, and every operator message including a model switch. Read `{guard_log}` (the path
     `resolve` returns) for this run's sessions; a count taken from the guard log alone is labelled
     as such. Attribute a refusal by the run's own session tree, never by a time window, and list
     every restart, every killed sub-agent and every re-dispatch with what it re-ran. "All kept" is
     allowed only when the log has no line for the run — and never on a harness whose resolve
     result reported `guard: none`. Record the spec read's own two facts here as well — which copy
     `resolve` read (`spec_source`) and, when it carried one, the `spec_differ` marker — because a
     silent read of the older copy is the failure the worktree-first default and this record exist to
     remove.
     Record the `executor-skew` verdict this run read here too: a `not_applicable` from a source
     checkout is answered, recorded and never asked about.
  8. **Build server** — the setup preflight's state (`ready`, `disabled` or `down`, with its reason),
     the per-`mechanism` build count (`daemon_longpoll` versus `in_process_fallback`, so a run that
     did not use the server is visible here and not only in the daemon journal), the fallback each
     build used and why (`degraded` with its `reason`, or `executor_absent_from_worktree`), and any
     `killed` job with its disposition. Add any
     `runtime_stamp_reason` the resolve result carried: it names a runtime-info seam that failed, or
     a fact nothing could measure, and marks the stamp as `unknown` rather than silently absent.
  9. **Residue** — anything left open.

Then tell the operator the PR number, the merge commit, and that the landing message was written.

**Never edit a filed inbox message.** To correct it, stage the correction body and run
`python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox amend --slug {slug} --message {name} --payload-file .plan/temp/amend-{plan}.md`
(see its `--help`), which stamps a revision.

**Stopping before the merge** (blocked, or the operator stops the run): write the same message with
`merge_state` set to `open` or `n/a`, and `pr` set to the PR number or `n/a`.
