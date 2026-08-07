---
name: cloud-plan-lane
description: The complete working contract for a plan under doc/plans/ — the standalone lane that runs OUTSIDE the plan-marshall command lifecycle. Load this first, before any other action, when executing a plan from doc/plans/{epic}/. Covers skill loading, the plan directory lifecycle, the conditional build gate, the pre-PR verification sub-agent, the branch/PR/review-comment cycle, the merge gate, and the persisted run report.
user-invocable: true
mode: workflow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, Skill, AskUserQuestion
---

# Cloud Plan Lane

The working contract for one plan under `doc/plans/`. It is **self-contained**: it does not use
`/plan-marshall`, `/marshall-orchestrator`, `.plan/execute-script.py`, or any `.plan/` state.

Load this skill as the **first action of every run**, before reading the plan.

## Why this lane exists

`.plan/` is git-ignored, so the plan-marshall lifecycle's state — plan directories, orchestrator
ledgers, findings, locks, and the generated executor — exists only on the machine that created it.
A cloud session clones the repository and gets none of it. This lane keeps everything a plan needs
inside git: the plan, the rules, and the report.

## Scope and precedence

This skill **overrides** the `## Workflow Discipline (Hard Rules)` section of the repository's
`CLAUDE.md` for the duration of a `doc/plans/` run — see `CLAUDE.md` § "Standalone Plan Lane", which
records the carve-out. Specifically, within this lane:

| `CLAUDE.md` hard rule | Status in this lane |
|---|---|
| Build commands resolved via `architecture resolve` | **Superseded** — call `./pw` directly (§ Build gate) |
| CI operations via `tools-integration-ci:ci` | **Superseded** — see § GitHub access |
| GitHub access via `gh`, not MCP | **Superseded** — the GitHub MCP server is the cloud path (§ GitHub access) |
| `.plan/` access through `execute-script.py` | **Not applicable** — this lane never touches `.plan/` |
| Temp files under `.plan/temp/` | **Superseded** — scratch goes in the system temp dir (`$TMPDIR`), never in the repository and never in `.plan/` |
| Structured queries before Glob/Grep | **Not applicable** — `architecture` needs the executor; use Glob/Grep/Read |
| Findings via `manage-findings` + `ext-triage-*` | **Superseded** — findings go in the run report (§ Report) |
| Plugin Cache Sync after editing `marketplace/bundles/` | **Not applicable** — `/sync-plugin-cache` reads the git-ignored `target/` and writes `~/.claude/`, neither of which this lane has or may touch. Record in the report that the plan's bundle edits are unsynced, so whoever picks the work up locally knows a sync is owed |
| No shell file operations | **Binds, with one clarification** — `git mv` and `mkdir -p` are permitted for Step 2's directory work; the rule's target is reading and searching file content, which still goes through Read/Glob/Grep |

Every other rule in `CLAUDE.md` still binds — in particular the documentation standards and the
one-command-per-Bash-call discipline. The closed branch-prefix set binds for branches this run
creates; a cloud session's pre-assigned `claude/*` branch is kept as-is (§ Step 2).

## Step 1 — Load the core skills

Load the work identity, then only the domain skills the plan's surface actually needs. Loading
skills you will not use is pure context cost.

**Read the bundle source by path.** This repository *is* the marketplace, so every skill named below
is a file in the tree — that route works in any session, including a fresh cloud clone. The plugin
notation is an optimization on top of it, not the primary route:

```text
Read: marketplace/bundles/{bundle}/skills/{skill}/SKILL.md
```

The `plan-marshall` plugin is frequently **not** installed in a Claude Code cloud session — this has
been observed, with the plugin cache verified absent — and every `Skill: {notation}` load then fails
with "Unknown skill". So:

1. Optionally try `Skill: {bundle}:{skill}` first; it is cheaper when the plugin happens to be present.
2. On failure — or without trying — `Read` the bundle path. That is the route that always works here.

**Always:**

| Skill | Path |
|---|---|
| `plan-marshall:ref-code-quality` | `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` |
| `pm-plugin-development:plugin-script-architecture` | `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md` |

**Conditionally, by what the plan touches** — each lives at
`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`:

| Surface | Load |
|---|---|
| Workflow docs, dispatch topology, skill composition | `plan-marshall:ref-workflow-architecture` |
| Production code (work identity) | `plan-marshall:persona-implementer` |
| Python production code | `pm-dev-python:python-core` |
| Python tests | `pm-dev-python:pytest-testing` |
| `SKILL.md` / bundle structure | `pm-plugin-development:plugin-architecture` |
| `.adoc` documentation | `pm-documents:ref-asciidoc` |
| Security-relevant change | `plan-marshall:persona-security-expert` |

A skill that can be obtained by **neither** route — no plugin, and no file at the bundle path — is
reported in the run report, never silently skipped.

## Step 2 — Resolve and check out the branch

**The branch comes before any change to the plan tree.** Step 3 moves files with `git mv`; done on
whatever the session happens to have checked out, that move lands on the wrong branch and can drag
unrelated working-tree state into the plan's history.

First, refuse to start on a dirty tree — this precondition also underwrites the Step 5 and Step 6
diffs, both of which see only committed work:

```bash
git status --porcelain
```

Non-empty output means stop and report the run **blocked**, naming the dirty paths. Do not stash,
do not commit unrelated changes.

Then resolve **one** branch name and reuse it for the rest of the run — creation, pushes, and PR
alike.

**A cloud session MUST keep its harness-assigned branch.** Claude Code cloud sessions pre-assign a
branch named `claude/{slug}-{hash}` and **bind the session to it**. Renaming it breaks session
resume: a cloud VM is reclaimed on inactivity, its replacement re-clones from the remote, and the
harness then cannot find the renamed branch. That is not hypothetical — it is how one observed run
lost its work entirely, with the branch present on no remote. When the session arrives on such a
branch, **use it as-is**; do not create a prefixed branch, do not rename, and do not ask.

Keeping the assigned name costs nothing, because the closed prefix set does not govern whether the
PR is verified.
`.github/workflows/python-verify.yml` applies its branch filter to the `push:` trigger only; the
`pull_request:` trigger filters on the **base** branch (`main`), so a PR from any head branch runs
verify and produces the required `verify / conclusion` check. A non-prefixed branch loses its
push-triggered build, nothing more. See `CLAUDE.md` § "Branch Naming".

The closed prefix set applies to branches **the run itself creates** — every local run, and a cloud
run where no branch was pre-assigned. There, choose the prefix from what the plan actually does
(`feature/` for a new capability, `fix/` for a bug fix, `chore/` for maintenance, refactoring, or
documentation). Do not default to `feature/`.

Record in the run report which branch form was used — harness-assigned or run-created.

```bash
git fetch origin main
```

A first run creates the branch from freshly-fetched `origin/main`:

```bash
git checkout -b {prefix}/{plan-name} origin/main
```

A **resumed** run checks the existing branch out instead — `checkout -b` fails when the branch
already exists, so branching unconditionally breaks every resume:

```bash
git checkout {prefix}/{plan-name}
```

Determine which case you are in before acting (`git rev-parse --verify --quiet {prefix}/{plan-name}`
succeeds when the branch exists).

### Get the branch onto the remote before any work

**The invariant, independent of how the branch came to be: no work proceeds until the branch exists
on `origin`.** Not one edit, not one commit.

State it that way because the older wording — "push the branch immediately *on creation*" — keyed the
obligation on the run **creating** a branch, and a cloud run never creates one: the paragraphs above
tell it to keep its harness-assigned branch as-is. The instruction then read as inapplicable, and an
observed run made three commits with nothing on the remote at all. A branch you were handed is no
more published than one you cut.

So decide which arrival you are in, and act:

- **You created the branch** (`git checkout -b …` above) — push it immediately, before any edit:

  ```bash
  git push -u origin {branch}
  ```

- **You arrived on a harness-assigned branch** — it exists *locally*; that says nothing about the
  remote. Check, and treat pushing it as your **first action** if it is absent:

  ```bash
  git ls-remote --heads origin {branch}
  ```

  Empty output means the branch is not on the remote. Push it before anything else:

  ```bash
  git push -u origin {branch}
  ```

  Non-empty output means it is already published; carry on, and Step 4's per-commit push keeps it
  current.

### The remote is the only durable storage

A cloud VM is reclaimed on inactivity, and its replacement **re-clones** — the filesystem does not
persist across that boundary. Anything that exists only in the working tree, or only in a local
commit, is gone. The run report is itself committed on the branch, so it is lost along with the work
it describes, leaving no record that the run happened at all.

So the branch is pushed the moment it exists — see the invariant above — and pushed again after every
commit (§ Step 4). Step 7 opens the PR on an already-published branch; it is not the first push.

**A path outside the git working tree is not storage.** The scratchpad directory, `$TMPDIR`, `/tmp`,
the home directory: every one of them is on the same reclaimed filesystem as the working tree, and
none of them is any more durable than an uncommitted file. Writing something aside preserves nothing.
An observed run captured expensive test fixtures into a scratchpad directory and described them as
persisted "durably" — they were one reclaim from gone.

The consequence is sharper than it looks: content that never enters the working tree is **invisible
to "commit and push"**. No amount of pushing saves it, because there is nothing to push. So an
artifact worth keeping is written **into the repository**, committed, and pushed — and if it is not
worth committing, it is not worth treating as kept. That is not a licence to commit scratch: the
`CLAUDE.md` rule keeping temp files out of the repository still binds, and the choice a run faces is
between committing an artifact deliberately and accepting that it is disposable. What it may not do
is call a scratch path durable.

## Step 3 — Establish the plan directory

A plan arrives as a single file, e.g. `doc/plans/truthful-signals/010-my-plan.md`, authored from the
template at [`doc/plans/_template/plan.md`](../../../doc/plans/_template/plan.md). If the plan you
were handed is not in that shape, do not silently proceed on a thinner brief — say so in the report,
and flag any missing section that changes what you would build (deliverables, out-of-scope,
claim labels).

**Enforce the first-instruction block.** Every plan opens with the blockquote that loads this skill.
Check that the plan you were handed carries it, before moving the file:

- **Present** — nothing to do.
- **Absent** — restore it from the template verbatim as part of this step, and record the repair in
  the report. A plan without it is one careless hand-off away from being executed by a session that
  never loads this contract, which is the single failure that silently disables every gate below.

The block is load-bearing rather than decorative, so it is checked, not assumed — and the same check
is repeated at Step 9 against the moved file.

On the branch from Step 2:

1. Create the plan directory: `doc/plans/{epic}/{plan-name}/`
2. Move the plan into it as `plan.md` (`git mv`, so history follows).

**The plan file's numeric priority prefix is preserved by the move.** Cloud plans are named
`{NNN}-{slug}.md`, where `{NNN}` orders the epic's queue for hand-over; the directory takes the whole
name, so `{NNN}-{slug}.md` becomes `{NNN}-{slug}/plan.md`. Do not strip the prefix, and do not
renumber — a plan handed to a session is bound to its path, and both this run and the orchestrator's
collect step address it by that name. A plan authored before the scheme has no prefix; move it under
the name it has.

The resulting layout is the plan's whole workspace:

```text
doc/plans/{epic}/{NNN}-{plan-name}/
├── plan.md          # the plan, moved here in this step
└── report-NN.md     # one per run (§ Report)
```

A plan already in this shape is resumed, not re-established — skip to Step 4.

## Step 4 — Implement

Work the plan's deliverables in order. Commit in coherent units with conventional-commit subjects.

**The rule for every commit: gate, then commit, then push.** Eager pushing must never carry
unverified work to the remote.

### Gate before committing

When a commit touches any `*.py`, `.claude/skills/**`, or `marketplace/bundles/**` — the **same**
predicate Step 5 uses to decide whether to build — run the quality gate first:

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"
```

A lane run without the generated executor — the ordinary cloud case, since `.plan/` is git-ignored —
runs the same gate directly:

```bash
./pw quality-gate
```

**Open the `log_file` it names and confirm `total_issues: 0`.** The wrapper exits 0 on failure, so
the exit code proves nothing; only the log does. Commit when the log is clean, then push.

Two points in the run need **no** gate, because neither changes source: Step 2's initial push of an
empty branch, and Step 3's plan-directory move (a `git mv`, no content change).

This is the cheap per-commit gate. It does not replace Step 5's `./pw verify` over the whole branch
diff before the PR — that one stays.

### Commit and push

Every commit message ends with exactly this trailer, and **no** "Generated with Claude Code" footer:

```text
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Push after every commit** — not once at Step 7:

```bash
git push
```

An unpushed commit is lost work the moment the VM is reclaimed (§ Step 2, "The remote is the only
durable storage").

## Step 5 — Build gate (conditional)

Determine what changed from git, never from recollection:

```bash
git diff --name-only origin/main...HEAD
```

**This diff sees committed work only** — staged, unstaged, and untracked files are invisible to it.
An uncommitted new `.py` file would therefore skip the build *and* be invisible to the Step 6
sub-agent, which reads the same range. So re-assert the clean tree Step 2 required, and treat a
dirty result as a defect in the run rather than working around it:

```bash
git status --porcelain
```

Two gates, because the quality gate and the test suite have **different** trigger surfaces:

| Changed | Run |
|---|---|
| Any `*.py` | `./pw verify` (quality gate **and** tests) |
| No `*.py`, but any `.claude/skills/**` or `marketplace/bundles/**` | `./pw quality-gate` |
| Neither | Nothing — record "no buildable footprint, build skipped" |

> **Why the second row exists.** `quality-gate` runs plugin-doctor across the whole tree, and
> plugin-doctor lints **markdown** — `SKILL.md` frontmatter, workflow docs, relative links — under
> both `marketplace/bundles/*/skills/` and `.claude/skills/`. A markdown-only change therefore can
> and does fail the build. A gate keyed on `*.py` alone would skip the build and open a red PR. This
> is not hypothetical: it is how this contract's own first PR went red, on a missing `mode:` field
> in this very file.

Both commands run from the repository root:

```bash
./pw verify
```

```bash
./pw quality-gate
```

Narrower calls when you need them: `./pw module-tests` (tests only), `./pw compile`. Append a bundle
name to scope to one module, e.g. `./pw verify plan-marshall`.

Give every `./pw` call a Bash timeout of at least **600000 ms (10 minutes)**.

**Read the output, not the exit code.** The build wrapper can exit 0 on failure. Confirm the reported
`status`, and open the `log_file` it names to confirm `total_issues: 0` — a green summary line is not
the same as a clean log. Fix and re-run until it is genuinely clean; a build that is not clean blocks
the PR.

## Step 6 — Pre-PR verification sub-agent

**Before creating the PR**, dispatch an independent sub-agent to verify the work against the plan.
This is the lane's self-review gate, and its independence is the point: the agent that wrote the
code is the worst judge of whether it satisfies the requirement.

Dispatch it with the Task tool (`general-purpose`), read-only in effect: **the sub-agent reports, it
never fixes.**

Give it, at minimum:

- the path to `plan.md` and the instruction to verify against **its** requirements, not against the
  diff's apparent intent;
- the diff under review (`git diff origin/main...HEAD`);
- the instruction to check each deliverable for: implemented at all, implemented as specified,
  covered by a test where a test is warranted, and no undeclared collateral change;
- the instruction to report every gap it finds with file and symbol, and to state explicitly when a
  deliverable cannot be verified from the diff alone rather than assuming it passed;
- the instruction that a clean verdict must name what it checked, so an empty finding list is
  distinguishable from a check that examined nothing.

Then:

- **Findings that are real** → fix them, then re-dispatch. A verification pass that found a defect
  has not finished.
- **Findings you reject** → record the finding *and the reason for rejecting it* in the report. A
  dismissed finding is still evidence.
- Every finding, accepted or rejected, goes in the run report (§ Report).

## GitHub access

Use whichever of these two paths is actually available in the running session, and say in the report
which one was used:

- **GitHub MCP server** — available in Claude web / cloud sessions. Its traffic routes through
  Anthropic's servers rather than the session's network, so it needs no domain allowlisting and no
  package install. This is the expected path for a cloud run.
- **`gh` CLI** — the expected path locally.

`CLAUDE.md`'s "GitHub access — use `gh`, not MCP" rule is superseded **inside this lane only**, for
this reason: the lane's whole purpose is to run in an environment where the plan-marshall CI
abstraction that rule protects does not exist. Everywhere else in the repository the rule stands.

Commands below are written in `gh` form because it is the precise, quotable spelling; when running
on MCP, use the equivalent call. Never assume a tool is present — check, and if neither path is
available, stop at Step 7 and report the run **blocked**. Do not attempt to install tooling into the
session, and do not treat an unreachable review surface as an empty one.

## Step 7 — Branch, PR, review-comment cycle

The branch was published at Step 2 and kept current by Step 4's per-commit pushes, so this step
opens the PR on an already-pushed branch. Flush anything still unpushed first, then create it:

```bash
git push
```

```bash
gh pr create --fill
```

**Suppress bot review when the PR changes no source.** Bot-review capacity is contended across this
repository and is regularly exhausted; a diff that touches only documentation, reports, or ledger
bookkeeping has nothing to offer a reviewer and spends budget another PR needs. Determine it from the
same git evidence Step 5 uses, and apply the label **at creation** — applying it afterwards is too
late, because the bots are triggered by the PR opening:

```bash
gh pr create --label skip-bot-review --fill
```

The rule in one line: **a PR that changes no source gets no bot review.** A PR that does change
source keeps its review — this suppresses waste, never scrutiny.

Then work the review cycle until it is genuinely finished:

1. Wait for the automated reviewers and CI to report.
2. Read the actual comment bodies, from **both** surfaces (see § GitHub access). A summary of a
   review is not the review, and a green check is not evidence that a reviewer participated.
3. Handle **every** comment: fix it, or reply on the thread explaining why it is not actionable.
   Push fixes as further commits.
4. Re-check after each push — new comments arrive on new commits.

Record in the report which reviewers commented and how each comment was dispositioned.

**PR comments live on two surfaces, and one of them is the one that matters here.** The repository's
principal automated reviewers file their findings as *inline review-thread* comments, which the
conversation view does not contain. Reading only the conversation view and then asserting "all
comments handled" is a false clean signal — the exact failure this lane is built to avoid.

| Surface | Holds | `gh` |
|---|---|---|
| Conversation | Issue comments, review summary bodies | `gh pr view {N} --comments` |
| Inline review threads | Per-file findings from the review bots | `gh api repos/{owner}/{repo}/pulls/{N}/comments --paginate` |

Both surfaces MUST be read before the merge gate. With the GitHub MCP server, use its equivalent
pull-request review-comment call for the second surface — not only the conversation listing.

## Step 8 — Merge gate

**Merge only when both conditions hold:**

1. **All checks are green** — verify against actual check state, not against an assumption that time
   has passed:

   ```bash
   gh pr checks {N}
   ```

2. **Every PR comment is handled** — fixed or answered on the thread. No open, unaddressed comment.

3. **The report is finalized and pushed** — run Step 9 now and commit its report artifacts (the
   contract-check table and the "what have we learned" section) as the **last pre-merge commit**,
   *before* you arm auto-merge. This ordering is load-bearing, not cosmetic: the report lands *in
   this PR*, and the instant the branch enters the merge queue a protected-branch hook rejects every
   further push to it ("Branches that are queued for merging cannot be updated" — observed). A report
   finalized after arming can never reach this PR, forcing a second follow-up PR just to complete the
   record. So Step 9's report sections are written here; only the post-merge landing confirmation
   (below) happens after.

Then merge (the repository uses a merge queue, so enable auto-merge and let the queue land it):

```bash
gh pr merge {N} --squash --auto
```

**Confirm the merge actually happened.** A merge command reporting success is a claim, not the
outcome — this repository has seen a merge call report success, delete the branch, and not merge:

```bash
gh pr view {N} --json state,mergedAt,mergeCommit
```

Only `state: MERGED` with a real `mergedAt` is a landing.

**Record the merge commit outside the in-PR report.** The squash merge SHA does not exist until the
merge completes, so it cannot appear in a report that was committed before the merge (condition 3
above). Read it from the PR merge event (`state,mergedAt,mergeCommit`) and report it to the operator;
the orchestrator collects the landing from the PR itself, not from a SHA embedded in the report body.

**Record nothing outside your own plan directory.** There is no status file, no ledger, no shared
table — the tree itself is the state, and the orchestrator records the landing at collect by reading
your report. Write to `doc/plans/{epic}/{plan-name}/` and nowhere else under `doc/plans/`.

**Your report is the channel back.** It must state the PR number and the outcome per deliverable —
including a run that ended **blocked or partial**, and why. (The merge commit is read from the PR
merge event and reported to the operator, not embedded here — see the merge-commit note above.) An
overstated outcome gets collected as done; an understated one gets picked up again.

The full rule, including how a row is created and later collected, is
[`doc/plans/cloud-bridge.md`](../../../doc/plans/cloud-bridge.md).

## Step 9 — Final step: verify this contract was followed

**The last committed action of every run.** Its report sections (this contract-check and the "what
have we learned" below) are written and pushed at Step 8 condition 3, as the final pre-merge commit,
because they must land in the PR — a queued branch can no longer be pushed to. Only the merge-landing
confirmation happens after, recorded to the operator rather than into the report. Re-read this skill
and check each step against what actually happened, confirming both that the step was performed and
that its artifact exists on disk:

| Step | Artifact that proves it |
|---|---|
| 1 Skills loaded | Named in the report |
| 2 Branch | Branch exists **on `origin`** — the harness-assigned `claude/*` branch, or one this run cut from `origin/main` with a prefix from the closed set; the report names which |
| 3 Plan directory | `doc/plans/{epic}/{plan-name}/plan.md` exists, and opens with the first-instruction block |
| 4 Implement | Commits carry the trailer; deliverables addressed |
| 4 Per-commit gate | Every commit touching `*.py`, `.claude/skills/**`, or `marketplace/bundles/**` was preceded by a `total_issues: 0` quality-gate log |
| 4 Pushed | No unpushed commit remains (`git status -sb` reports no `ahead`) |
| 5 Build gate | Report states the git-derived Python-change verdict and the build outcome |
| 6 Verification sub-agent | Findings and dispositions in the report |
| 7 PR cycle | PR exists; every comment dispositioned in the report |
| 8 Merge gate | `state: MERGED` confirmed after arming; the merge commit recorded to the operator, not in the pre-merge report (§ Step 8) |
| 8 Bridge | Nothing under `doc/plans/` outside this plan's own directory was changed, and the report carries the PR number and per-deliverable outcome the orchestrator will collect from |
| 9 This check | Its result appended to the report |
| 9 What have we learned | A contract-change proposal presented to the operator, or a recorded "none, because …" |

Any step that was skipped, or whose artifact is missing, is reported as **not done** — do not
retroactively narrate it as complete. If a step can still be completed, complete it and re-check.

### What have we learned

Then ask the second question: **should this contract itself change?** The run just exercised it end
to end, which is the only moment its gaps are visible.

Propose a change only where **this run produced the evidence** — a step that was ambiguous in
practice, a step whose artifact could not be produced as written, a command that did not work in the
actual environment, a failure mode the contract does not catch, or a step that turned out to be
unnecessary. Speculative improvements are not proposals; a proposal names what happened.

If there is something worth changing:

1. **Present it to the operator** with the evidence from this run and the concrete proposed edit.
   Never self-approve a change to the contract that governs you.
2. On approval, ship it as a **separate PR** — its own `chore/` branch, touching only the skill (and
   `CLAUDE.md` or `doc/plans/README.md` if the change reaches them):

   ```bash
   gh pr create --label skip-bot-review --title "chore(cloud-plan-lane): {what changed}" --body-file {file}
   ```

   The `skip-bot-review` label suppresses the automated bot review, which has nothing useful to say
   about a prose contract.

Keep it out of the plan's own PR. Two changes with different review audiences in one diff means
neither gets read properly, and it couples a contract amendment to whether the plan lands.

Record the outcome in the report either way — including "no contract change proposed", with the
reason. A run that examined the contract and found nothing is a different fact from a run that never
looked.

## Report

**Write one report per run**, as the run proceeds — not reconstructed at the end. Persist it at:

```text
doc/plans/{epic}/{plan-name}/report-NN.md
```

`NN` is the next free two-digit ordinal in that directory (`report-01.md`, `report-02.md`, …).
Selecting "next free" and then writing is not atomic — two concurrent runs can pick the same ordinal
and one silently overwrites the other's findings. **Create the file exclusively** (fail if it
exists, then retry the next ordinal) rather than checking-then-writing. A
resumed or re-entered run gets its **own** report; never overwrite an earlier one.

The report is committed on the plan's branch, so it lands with the PR.

Required content:

```markdown
# Run report — {plan-name} (run NN)

**Date (UTC):** …    **Branch:** …    **PR:** …    **Outcome:** completed | partial | blocked

## Skills loaded
…

## Deliverables
Per deliverable: what was done, in which commit, and its verification state.

## Build gate
The `git diff --name-only origin/main...HEAD -- '*.py'` verdict, and the build result — or
"no Python changes, build skipped".

## Findings
Every finding from the verification sub-agent, from CI, and from PR review — each with source,
description, and disposition (fixed / rejected-with-reason / deferred). An empty section states
what was checked to reach it.

## Contract check (Step 9)
Per-step verdict, and any step reported as not done. Which GitHub access path was used, and which
branch form was used (harness-assigned or run-created).
Whether the plan edited `marketplace/bundles/` and therefore owes a local `/sync-plugin-cache`.

## What have we learned (Step 9)
The proposed contract change and its evidence from this run, and whether the operator accepted it —
or "none proposed", with the reason.

## Residue
Anything left open, and where it should go next.
```

A finding is recorded **per instance**, not bundled: three occurrences of one defect are three rows.

## Rules that outrank convenience

- **A claim is not an outcome.** Merge state, check state, and review participation are read back
  from the actual source, never inferred from the command that was supposed to produce them.
- **A count derived by looking is a sample.** State how it was derived, and re-derive it at the
  moment of the claim.
- **A skipped step is reported as skipped.** Silent omission is the failure mode this lane exists to
  prevent.
- **Never write outside the repository** — this lane has no business in `.plan/` or `~/.claude/`.
