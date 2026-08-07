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

Every other rule in `CLAUDE.md` still binds — in particular the closed branch-prefix set, the
documentation standards, and the one-command-per-Bash-call discipline.

## Step 1 — Load the core skills

Load the work identity, then only the domain skills the plan's surface actually needs. Loading
skills you will not use is pure context cost.

**Always:**

```text
Skill: plan-marshall:ref-code-quality
Skill: pm-plugin-development:plugin-script-architecture
```

**Conditionally, by what the plan touches:**

| Surface | Load |
|---|---|
| Workflow docs, dispatch topology, skill composition | `plan-marshall:ref-workflow-architecture` |
| Production code (work identity) | `plan-marshall:persona-implementer` |
| Python production code | `pm-dev-python:python-core` |
| Python tests | `pm-dev-python:pytest-testing` |
| `SKILL.md` / bundle structure | `pm-plugin-development:plugin-architecture` |
| `.adoc` documentation | `pm-documents:ref-asciidoc` |
| Security-relevant change | `plan-marshall:persona-security-expert` |

These are plugin skills. They resolve only when the `plan-marshall` plugin is installed — which the
repository's `.claude/settings.json` declares, so a cloud session installs it at session start. If a
skill fails to resolve, say so in the report rather than proceeding as if it had loaded.

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
alike. Choose the prefix from what the plan actually does; the set is closed (`feature/` for a new
capability, `fix/` for a bug fix, `chore/` for maintenance, refactoring, or documentation), because
any other prefix gets no CI run and can therefore never produce the required `verify / conclusion`
check. Do not default to `feature/`.

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

## Step 3 — Establish the plan directory

A plan arrives as a single file, e.g. `doc/plans/truthful-signals/my-plan.md`, authored from the
template at [`doc/plans/_template/plan.md`](../../../doc/plans/_template/plan.md). If the plan you
were handed is not in that shape, do not silently proceed on a thinner brief — say so in the report,
and flag any missing section that changes what you would build (deliverables, out-of-scope,
claim labels).

On the branch from Step 2:

1. Create the plan directory: `doc/plans/{epic}/{plan-name}/`
2. Move the plan into it as `plan.md` (`git mv`, so history follows).

The resulting layout is the plan's whole workspace:

```text
doc/plans/{epic}/{plan-name}/
├── plan.md          # the plan, moved here in this step
└── report-NN.md     # one per run (§ Report)
```

A plan already in this shape is resumed, not re-established — skip to Step 4.

## Step 4 — Implement

Work the plan's deliverables in order. Commit in coherent units with conventional-commit subjects.

Every commit message ends with exactly this trailer, and **no** "Generated with Claude Code" footer:

```text
Co-Authored-By: Claude <noreply@anthropic.com>
```

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

Push and open the PR:

```bash
git push -u origin {prefix}/{plan-name}
```

```bash
gh pr create --fill
```

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

Then merge (the repository uses a merge queue, so enable auto-merge and let the queue land it):

```bash
gh pr merge {N} --squash --auto
```

**Confirm the merge actually happened.** A merge command reporting success is a claim, not the
outcome — this repository has seen a merge call report success, delete the branch, and not merge:

```bash
gh pr view {N} --json state,mergedAt,mergeCommit
```

Only `state: MERGED` with a real `mergedAt` is a landing. Record the merge commit in the report.

## Step 9 — Final step: verify this contract was followed

**The last action of every run.** Re-read this skill and check each step against what actually
happened, confirming both that the step was performed and that its artifact exists on disk:

| Step | Artifact that proves it |
|---|---|
| 1 Skills loaded | Named in the report |
| 2 Branch | Branch exists with a prefix from the closed set, cut from `origin/main` |
| 3 Plan directory | `doc/plans/{epic}/{plan-name}/plan.md` exists |
| 4 Implement | Commits carry the trailer; deliverables addressed |
| 5 Build gate | Report states the git-derived Python-change verdict and the build outcome |
| 6 Verification sub-agent | Findings and dispositions in the report |
| 7 PR cycle | PR exists; every comment dispositioned in the report |
| 8 Merge gate | `state: MERGED` confirmed and recorded |
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
Per-step verdict, and any step reported as not done. Which GitHub access path was used.
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
