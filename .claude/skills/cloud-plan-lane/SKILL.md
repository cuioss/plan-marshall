---
name: cloud-plan-lane
description: The complete working contract for a plan under doc/plans/ — the standalone lane that runs OUTSIDE the plan-marshall command lifecycle. Load this first, before any other action, when executing a plan from doc/plans/{epic}/. Covers skill loading, the plan directory lifecycle, the conditional build gate, the pre-PR verification sub-agent, the branch/PR/review-comment cycle, the merge gate, and the persisted run report.
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
| CI operations via `tools-integration-ci:ci` | **Superseded** — use `gh` directly (§ Branch, PR, review cycle) |
| `.plan/` access through `execute-script.py` | **Not applicable** — this lane never touches `.plan/` |
| Structured queries before Glob/Grep | **Not applicable** — `architecture` needs the executor |
| Findings via `manage-findings` + `ext-triage-*` | **Superseded** — findings go in the run report (§ Report) |

Every other rule in `CLAUDE.md` still binds — in particular the branch-prefix table, the
documentation standards, and the one-command-per-Bash-call discipline.

## Step 1 — Load the core skills

Load the work identity, then only the domain skills the plan's surface actually needs. Loading
skills you will not use is pure context cost.

**Always:**

```text
Skill: plan-marshall:persona-implementer
Skill: plan-marshall:ref-code-quality
```

**Conditionally, by what the plan touches:**

| Surface | Load |
|---|---|
| Python production code | `pm-dev-python:python-core` |
| Python tests | `pm-dev-python:pytest-testing` |
| Scripts under `marketplace/bundles/*/skills/*/scripts/` | `pm-plugin-development:plugin-script-architecture` |
| `SKILL.md` / bundle structure | `pm-plugin-development:plugin-architecture` |
| `.adoc` documentation | `pm-documents:ref-asciidoc` |
| Security-relevant change | `plan-marshall:persona-security-expert` |

These are plugin skills. They resolve only when the `plan-marshall` plugin is installed — which the
repository's `.claude/settings.json` declares, so a cloud session installs it at session start. If a
skill fails to resolve, say so in the report rather than proceeding as if it had loaded.

## Step 2 — Establish the plan directory

A plan arrives as a single file, e.g. `doc/plans/truthful-signals/my-plan.md`. Before any other work:

1. Create the plan directory: `doc/plans/{epic}/{plan-name}/`
2. Move the plan into it as `plan.md` (`git mv`, so history follows).

The resulting layout is the plan's whole workspace:

```text
doc/plans/{epic}/{plan-name}/
├── plan.md          # the plan, moved here in this step
└── report-NN.md     # one per run (§ Report)
```

A plan already in this shape is resumed, not re-established — skip to Step 3.

## Step 3 — Create the branch

Branch from up-to-date `main`, using one of the three canonical prefixes from `CLAUDE.md`
(`feature/`, `fix/`, `chore/` — the set is closed; any other prefix gets no CI run and can never
produce the required `verify / conclusion` check):

```bash
git checkout -b feature/{plan-name}
```

## Step 4 — Implement

Work the plan's deliverables in order. Commit in coherent units with conventional-commit subjects.

Every commit message ends with exactly this trailer, and **no** "Generated with Claude Code" footer:

```text
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Step 5 — Build gate (conditional)

**Build only when the branch changes Python.** Determine this from git, never from recollection:

```bash
git diff --name-only origin/main...HEAD -- '*.py'
```

- **Empty output** → no Python changed. Skip the build entirely and record "no Python changes, build
  skipped" in the report. A documentation-only change legitimately skips CI's heavy build too, so
  this matches what the pipeline does.
- **Non-empty** → run the full verification, from the repository root:

  ```bash
  ./pw verify
  ```

  Narrower calls when you need them: `./pw quality-gate` (lint + types), `./pw module-tests` (tests),
  `./pw compile`. Append a bundle name to scope to one module, e.g. `./pw verify plan-marshall`.

  Give every `./pw` call a Bash timeout of at least **600000 ms (10 minutes)**.

  **Read the output, not the exit code.** The build wrapper can exit 0 on failure. Confirm the
  reported `status` and an empty `errors[]` before calling the build green. Fix and re-run until it
  is genuinely clean; a build that is not clean blocks the PR.

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

## Step 7 — Branch, PR, review-comment cycle

Push and open the PR:

```bash
git push -u origin feature/{plan-name}
```

```bash
gh pr create --fill
```

Then work the review cycle until it is genuinely finished:

1. Wait for the automated reviewers and CI to report.
2. Read the actual comment bodies — `gh pr view {N} --comments`. A summary of a review is not the
   review, and a green check is not evidence that a reviewer participated.
3. Handle **every** comment: fix it, or reply on the thread explaining why it is not actionable.
   Push fixes as further commits.
4. Re-check after each push — new comments arrive on new commits.

Record in the report which reviewers commented and how each comment was dispositioned.

> `gh` may not be pre-installed in a cloud environment. If it is missing, add
> `apt update && apt install -y gh` to the cloud environment's setup script; GitHub authentication
> is handled by the session's proxy, so no token configuration is needed.

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
| 2 Plan directory | `doc/plans/{epic}/{plan-name}/plan.md` exists |
| 3 Branch | Branch exists with the correct prefix |
| 4 Implement | Commits carry the trailer; deliverables addressed |
| 5 Build gate | Report states the git-derived Python-change verdict and the build outcome |
| 6 Verification sub-agent | Findings and dispositions in the report |
| 7 PR cycle | PR exists; every comment dispositioned in the report |
| 8 Merge gate | `state: MERGED` confirmed and recorded |
| 9 This check | Its result appended to the report |

Any step that was skipped, or whose artifact is missing, is reported as **not done** — do not
retroactively narrate it as complete. If a step can still be completed, complete it and re-check.

## Report

**Write one report per run**, as the run proceeds — not reconstructed at the end. Persist it at:

```text
doc/plans/{epic}/{plan-name}/report-NN.md
```

`NN` is the next free two-digit ordinal in that directory (`report-01.md`, `report-02.md`, …). A
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
Per-step verdict, and any step reported as not done.

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
