---
name: cloud-plan-lane
description: The complete working contract for a plan under doc/plans/ — the standalone lane that runs OUTSIDE the plan-marshall command lifecycle. Load this first, before any other action, when executing a plan from doc/plans/{epic}/. Covers skill loading, the plan directory lifecycle, the conditional build gate, the pre-PR verification sub-agent, the branch/PR/review-comment cycle, the merge gate, and the persisted run report.
user-invocable: true
mode: workflow
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, Skill, AskUserQuestion
---

# Cloud Plan Lane

The working contract for one plan under `doc/plans/`. It is **self-contained**: it does not use
`/plan-marshall`, `/plan-orchestrator`, `.plan/execute-script.py`, or any `.plan/` state.

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
| Plugin Cache Sync after editing `marketplace/bundles/` | **Not applicable — and not owed.** `/sync-plugin-cache` is a machine-local build step: it reads the git-ignored `target/` and writes `~/.claude/`, neither of which this lane has or may touch. A cloud run **neither performs nor owes** a sync — the merged bundle source is authoritative, and refreshing a local cache is a local-developer concern, not a debt this run tracks or records |
| No shell file operations | **Binds, with one clarification** — `git mv` and `mkdir -p` are permitted for Step 2's directory work; the rule's target is reading and searching file content, which still goes through Read/Glob/Grep |
| Bash: one command per call / no shell constructs | **Superseded** — ordinary shell use is fine here, loops, `&&`/`;` and heredocs included. That rule is the documented basis for the PreToolUse hook's **R1** family (`platform-runtime/standards/pretooluse-enforcement.md`), and the hook cannot apply in this lane on two independent grounds: its context gate fires only for an `execution-context` sub-agent or a cwd under `.plan/local/worktrees/`, and it is installed machine-locally into `.claude/settings.local.json`, which a fresh clone does not carry. Prefer one heredoc over ten Bash calls where that is genuinely clearer — this epic is about what enters context, and a rule with no enforcer here is pure tool-call overhead |

Every other rule in `CLAUDE.md` still binds — in particular the documentation standards and **No
shell file operations**, whose remedy (the Read/Glob/Grep tools) is fully available in a cloud session. The closed branch-prefix set binds for branches this run
creates; a cloud session's pre-assigned `claude/*` branch is kept as-is (§ Step 2).

## Cloud session affordances

The cloud session this lane runs in is **not** the local machine the plan-marshall lifecycle assumes:
it clones fresh and reaches GitHub only through the MCP server. These facts are stated **once, here**,
so the steps below rely on them instead of each run re-deriving them.

| Affordance | In a cloud session |
|---|---|
| **GitHub access** | The **GitHub MCP server** only. There is **no `gh` CLI**, and Bash cannot reach `api.github.com` (egress-blocked — direct calls return `403`). Every `gh` spelling in this contract has an MCP equivalent (mapping below). |
| **Self-wake / polling** | `send_later` and `subscribe_pr_activity` may be **approval-gated** ("requires approval") **or absent entirely** — an observed run had both return "No such tool available" because the `claude-code-remote` MCP server was not connected, not merely gated. Either way, and because Bash cannot poll GitHub, a run **cannot** reliably block-until-green and re-check inside the session — Step 8's arm-and-hand-off completion exists for exactly this. The GitHub *read* surface (`pull_request_read`) is **not** gated, though, so a session that stays active may instead drive the cycle by manual read-polling on re-entry (§ Step 8, "Manual read-polling"). |
| **Ruleset-config API** | **Not reachable** — the MCP server exposes no branch-protection / ruleset tool, and direct API access is `403`. Read required-ness from `mergeStateStatus` (GitHub applying the ruleset for you), never from a ruleset-config call — § Step 8 condition 1. |
| **Auto-merge arming** | On this merge-queue repo, arming auto-merge while the required checks are green **queues the PR at once** and locks the branch — § Step 8's one-way-door rule. |
| **Writing the tree** | Normally `git push`. The GitHub MCP server is **also** a write-the-tree surface (`create_or_update_file` / `push_files`), which matters only when push is unavailable — § Step 4, "When `git push` stops working mid-run". |
| **Local build** | The build gate triggers on `*.py` only; the merge queue's `merge_group` run verifies docs-only changes before they land — § Step 5. |
| **Plugin cache** | `/sync-plugin-cache` is a machine-local step a cloud run never performs or owes — § Scope and precedence. |

**`gh` ↔ GitHub MCP mapping.** This contract writes commands in `gh` form for a precise, quotable
spelling; in a cloud session use the MCP equivalent. Match by **function**, not by a transcribed name —
the exact MCP tool names vary by server build, so resolve the current names by listing the server's
pull-request tools and matching what they do:

| `gh` form | GitHub MCP equivalent (observed name — verify against the live tool list) |
|---|---|
| `gh pr create --fill` / `--label L` | `create_pull_request`; apply the label with the issue-label call *after* create |
| `gh pr merge {N} --squash --auto` | `enable_pr_auto_merge` with `mergeMethod: SQUASH` (`disable_pr_auto_merge` disarms but does **not** dequeue — § Step 8) |
| `gh pr checks {N}` | `pull_request_read` with `method: get_status` and `get_check_runs` |
| `gh pr view {N} --json mergeStateStatus,mergeable,state,mergedAt,mergeCommit` | `pull_request_read` with `method: get` — the MCP payload names this field `mergeable_state` (lowercase), **not** `mergeStateStatus`, and omits `auto_merge` (§ Step 8 condition 1) |
| `gh pr view {N} --comments` (issue comments only) | `pull_request_read` with `method: get_comments` — the **issue-comment** surface ONLY. Unlike `gh pr view --comments`, the MCP `get_comments` does NOT fold in review-summary bodies, so it is not sufficient on its own — see the next row |
| `gh pr view {N} --json reviews` | `pull_request_read` with `method: get_reviews` — the **review-summary-body** surface. This is where the principal automated reviewers file their consolidated findings; a run that reads only `get_comments` + `get_review_comments` misses them entirely (observed on an actual run — six bot findings arrived here and nowhere else). MUST be read before the merge gate |
| `gh api repos/{owner}/{repo}/pulls/{N}/comments --paginate` | `pull_request_read` with `method: get_review_comments` — the **inline review-thread** surface (the one the conversation view omits — § Step 7) |

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

### A run resumed in a NEW session, on a DIFFERENT assigned branch

The two arrivals above are "first run" and "resumed run", and the second silently assumes the resumed
run is bound to the **same** branch name. A cloud session halted mid-run and picked up later is not:
the replacement session is pre-assigned its **own** `claude/{slug}-{hash}`, while the work sits on the
previous session's branch. Neither arrival covers that, and the two rules that do apply point in
opposite directions — *keep your assigned branch* (§ "A cloud session MUST keep its harness-assigned
branch") and *the remote is the only durable storage* (so the earlier work must be carried forward,
not abandoned).

**Resolve it in favour of both: carry the work onto the branch this session is bound to.**

⛔ **Establish the precondition BEFORE resetting anything.** `checkout -B` force-moves an existing
local branch, and the assigned branch may already carry commits — its own, or a previous attempt's.
Resetting it discards them silently, which is the exact work-loss failure this contract exists to
prevent, committed by the step written to prevent it. Check first:

```bash
git fetch origin main {previous-branch}
git ls-remote --heads origin {assigned-branch}
git log --oneline origin/main..{assigned-branch}     # empty ⇒ safe to reset
```

Then act on what you found:

- **The assigned branch has no unique commits** (the ordinary case — a fresh session's branch sits at
  `main`): reset it and rebase.
- **It has unique commits**: do **not** reset. They are unpushed or unreviewed work belonging to this
  session; rebase the previous branch's commits **on top of** them, or stop and report the run
  **blocked**, naming both sets. Never choose silently between two lines of real work.
- **It already exists on `origin` with commits**: the push below will be rejected as a non-fast-forward.
  That rejection is information, not an obstacle to force past — resolve it as the case above, and do
  not reach for `--force` to make the symptom go away.

```bash
git checkout -B {assigned-branch} origin/{previous-branch}
git rebase origin/main
git push -u origin {assigned-branch}
```

A plain checkout of the previous branch is not an option — it leaves every later commit somewhere this
session's harness cannot find after a VM reclaim. A fast-forward often is not available either: once
`main` has taken any commit the older branch predates, the two have diverged and `merge --ff-only`
refuses. **Leave the previous branch on `origin` untouched**; it costs nothing and is the only copy of
the pre-rebase history.

⛔ **A rebase changes the SHA of every commit it REPLAYS, and any document quoting one then cites a
commit on no branch under review — a condition-A defect the run manufactured by following this very
step.** Scope that precisely rather than overstating it: the replayed set is what the branch carries
and `main` does not. A SHA already reachable from `origin/main` keeps its object id and stays valid,
so **rewrite only references you have proven stale** — checking each with
`git cat-file -e {sha}` against the current branch, or `git merge-base --is-ancestor {sha} HEAD`.

**Pair old to new by patch content, not by subject.** Subjects repeat, conflict resolution edits them,
and a rebase can drop or squash a commit, so subject-and-order matching is a guess dressed as a method:

```bash
git range-diff origin/main...{previous-branch} origin/main...{assigned-branch}
```

Its output pairs each old commit with its replayed counterpart and marks any that were dropped or
changed — a commit with no counterpart must be reported, never silently remapped to a neighbour.

**Two surfaces hold quoted SHAs and they are not equally fixable.** Run documents (`report-NN.md`,
`actual-state.md`) and the **PR description** are editable — correct them here, and say in the new
run's report that you did. **Commit messages are not**, short of another history rewrite; a stale SHA
in an already-written commit message is therefore accepted and disclosed, not chased. The practical
consequence is forward-looking: **do not quote a same-branch SHA in a commit message** on a branch that
may still be rebased.

Record in the report which arrival this run was.

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

This per-commit push cadence is in direct tension with review integrity: each push to an open PR can
supersede the in-flight `verify` run and change the head mid-review, aborting a bot's in-progress
review and consuming its rate window. The tension is **resolved without weakening durability** — the
reconciling rule is stated at § Step 4 ("Commit and push") and its review-side handling at § Step 7.
Read neither as licence to leave a finished commit unpushed: durability is absolute, and the
resolution lives entirely on the commit side.

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

When a commit touches any `*.py` — the **same** predicate Step 5 uses to decide whether to build —
run the quality gate first:

```bash
python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"
```

A lane run without the generated executor — the ordinary cloud case, since `.plan/` is git-ignored —
runs the same gate directly:

```bash
./pw quality-gate
```

**Read the tool output, not the exit code** — the gate can report a green summary while failing, so
the exit code proves nothing. How you read "clean" depends on which of the two commands above you ran,
because they emit different things:

- **Executor path** (`.plan/execute-script.py … pyproject_build`) emits a TOON result: open the
  `log_file` it names and confirm `total_issues: 0` **and** an empty `errors[]`. `status` with
  `total_issues` alone is one field short of the repository-wide rule, which names `errors[]` too (a
  build can report a green status and zero issues while `errors[]` is non-empty), so all three are
  checked.
- **Direct `./pw quality-gate` path** (the ordinary cloud case) emits **no** such structured log — it
  streams the tools' own output. Confirm each reports clean instead: `ruff … All checks passed!`,
  `mypy … Success: no issues found`, and the `SPDX-header check passed` line.

Commit only when the path you used reports genuinely clean, then push.

Two points in the run need **no** gate, because neither changes source: Step 2's initial push of an
empty branch, and Step 3's plan-directory move (a `git mv`, no content change).

This is the cheap per-commit gate. It does not replace Step 5's `./pw verify` over the whole branch
diff before the PR — that one stays.

### Commit and push

Every commit message ends with exactly this trailer, and **no** "Generated with Claude Code" footer:

```text
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Stage the deliverable paths explicitly — never `git add -A`.** A `./pw` build (§ Step 5) run under a
session interpreter older than the project's floor rewrites `uv.lock` as a side effect; `git add -A`
then sweeps that churn into a deliverable commit. It was observed in two consecutive cloud runs, each
caught only because it looked. So name the paths you actually changed when you stage, and check
`git status` for stray generated-file churn — a lone `uv.lock`, a regenerated lockfile — **before**
committing; back it out rather than shipping it.

**Push after every commit** — not once at Step 7:

```bash
git push
```

An unpushed commit is lost work the moment the VM is reclaimed (§ Step 2, "The remote is the only
durable storage").

### When `git push` stops working mid-run

Every durability instruction above is a `git push`, so a run whose push stops working has no way to
satisfy them as written. That state is real: an observed run pushed sixteen commits, then began failing
every push with `fatal: could not read Username for 'https://github.com'` — inside the sandbox and
outside it — with no credential helper in `.git/config`, no token in the environment, and `add_repo`
`access: push` returning `already_present` for a workspace path that did not exist. Reads kept working
throughout, because the git proxy serves them anonymously, so `git fetch` succeeding proves nothing
about push.

**Diagnose it, and do not let it become a reason to keep working locally.** A local commit is not
storage (§ Step 2). Establish which cause holds — helper absent, token absent, attach record stale —
and record it in the report as a finding.

**The MCP API is the fallback write path, and its cost is asymmetric.** `create_or_update_file` and
`push_files` take the **full content of every file written** as a parameter, so the price of a write
scales with the size of the files touched, not with the size of the diff. A small diff over small files
ships normally; the same diff over large files may not, because every line must pass through the
agent's context twice — once read, once written. When the deliverable does not fit, ship the **diff**:
a patch file committed to the plan directory costs a fraction of the files it reconstructs. Record in
the report that it must be applied and then deleted. **A patch file is a durability workaround, never a
deliverable, and must not reach `main`.**

**Re-test the push before planning around its absence.** The same run recovered credentials later with
no intervention, which retired the workaround entirely — so a run that plans around a dead push without
re-checking may be paying for a constraint that has already lifted.

### The push cadence versus review integrity — resolved on the commit side

The per-commit push above collides with a second rule the run also owes: **do not needlessly
supersede an in-flight review or CI run.** Each push to an open PR (a) supersedes the running `verify`
via GitHub Actions concurrency, emitting a spurious `verify / conclusion` cancellation, and (b)
changes the head mid-review, which aborts a bot's in-progress review *and consumes its rate window*.
Both are real costs — but they are the **lesser** cost. A reclaimed VM loses unpushed work
irrecoverably; an aborted review is re-triggerable. **Durability therefore outranks review
cleanliness, and no finished commit is ever held back to spare a reviewer or a running check.**

Because durability MUST NOT be weakened, the conflict is resolved entirely by *how you commit*, never
by delaying a push:

- **Batch at the commit boundary, not the push boundary.** Commit in coherent units (above), not in a
  flurry of tiny commits. Ten trivial commits mean ten pushes and ten chances to abort a review; the
  same work in one coherent commit means one push — at **zero** durability cost, because nothing is
  left uncommitted. Fewer commits ⇒ fewer pushes ⇒ fewer disruptions. This is the only lever, and it
  never trades work-loss risk for review cleanliness.
- **The one forbidden move:** leaving a *completed* unit uncommitted-and-unpushed to protect a review.
  That re-introduces the exact work-loss failure durability exists to prevent, and this rule does not
  permit it. "Batch the commits" is not "delay the push."

The review-side half of this rule — how to read a superseded CI run, and what to do about a review a
push already aborted — lives at § Step 7, so the run meets it while working the review cycle.

## Step 5 — Build gate (conditional)

Determine what changed from git, never from recollection:

```bash
git diff --name-only origin/main...HEAD
```

**This diff sees committed work only** — staged, unstaged, and untracked files are invisible to it.
An uncommitted new `.py` file would therefore skip the build *and* be invisible to the Step 6
sub-agent, which likewise sees only committed work — its `git diff` read and any beyond-diff bundle
sweep alike read committed HEAD content, never an uncommitted file. So re-assert the clean tree Step 2
required, and treat a dirty result as a defect in the run rather than working around it:

```bash
git status --porcelain
```

Two gates, because the quality gate and the test suite have **different** trigger surfaces:

| Changed | Run |
|---|---|
| Any `*.py` | `./pw verify` (quality gate **and** tests) |
| No `*.py` | Nothing locally — record "no buildable footprint, build skipped" |

> **Why the gate is `*.py`-only.** For this project the local build gate builds on buildable source —
> `*.py` — and nothing else. A docs-, skill-, or bundle-only change is **not** built locally, and not
> because it cannot be linted (plugin-doctor does lint `SKILL.md` frontmatter, workflow docs, and
> relative links) but because **the merge queue is the net.** `.github/workflows/python-verify.yml`
> opts into `skip-on-docs-only`, and its own comment records that *a `merge_group` run … still
> verif[ies]* — so a docs-only change is built by the queue before it lands, and the local gate does
> not duplicate that. Keep the gate keyed on `*.py`; the queue covers the rest.

**This gate is run again at the merge gate when `main` has moved under the branch** — § Step 8
condition 2, which re-runs it on the merged tree. The predicate and the commands are the ones stated
here; what changes is only the tree they are run against.

Both commands run from the repository root:

```bash
./pw verify
```

```bash
./pw quality-gate
```

Narrower calls when you need them: `./pw module-tests` (tests only), `./pw compile`. Append a bundle
name to scope to one module, e.g. `./pw verify plan-marshall`.

**Running one test file to watch it fail first.** None of the `./pw` sub-commands runs a *single*
test file — they are the whole suite or a whole module — and `pytest` is not on the session
interpreter. When a new test warrants the red-before-green check (observe it fail before the fix
exists, so a vacuous test cannot pass silently), run that one file through `uv` with the same
interpreter pin `./pw` uses, from the repository root:

```bash
UV_PYTHON=3.12 UV_HTTP_TIMEOUT=600 uv run pytest {path/to/test_file.py}
```

This runs in seconds against one file instead of the whole `verify` suite, and never substitutes for
the Step 5 gate — the full `./pw verify` still runs over the branch diff before the PR.

**Gate on the full `./pw verify` — the narrower calls do not add up to it.** `./pw verify` is exactly
three sub-steps: **quality-gate** (`ruff`/`mypy` over `*.py` sources, SPDX, plugin-doctor),
**test-compile** (`mypy` over the whole `test/` tree), and **module-tests** (`pytest`). Only
`test-compile` type-checks the tests, and *neither* `quality-gate` *nor* `module-tests` runs it. So do
not substitute `./pw quality-gate` + a scoped `./pw module-tests` for the gate: that pair goes green
while a test-only type error slips straight through to CI, which runs the full `verify`. The classic
shape is a dynamically-loaded class (`load_script_module`) bound to a module-level name and then used
as a type annotation — legal at runtime, but `mypy` rejects a variable used as a type, so it is green
locally under the narrower calls and red on CI's `test-compile`. Run the full `./pw verify` (scope it
to a bundle if you must, but keep all three sub-steps).

**For fast iterative red/green checks on specific test files, `uv run` is far faster than `./pw` — but
it is NOT the gate.** `uv` is on `PATH` in a cloud session and resolves the same pyproject-defined
environment `./pw` uses, so `uv run python -m pytest <path> -o addopts=""` runs a targeted subset in
about a second (after the first dependency fetch) instead of routing every check through
`./pw module-tests` (whole-suite, minutes). Use it to iterate — confirming a test goes red before a fix
and green after, or re-checking one file you just edited — and reserve the full `./pw verify` for the
authoritative gate before the PR (nothing about the gate changes). The `-o addopts=""` clears the repo's
default pytest options (coverage, `--durations`) for a clean single-file run; it alters nothing the gate
checks. An observed run drove the red-first test verification and every incremental test-update check
this way — order-of-seconds each — then ran `./pw verify` once, unchanged, as the gate.

Give every `./pw` call a Bash timeout of at least **600000 ms (10 minutes)**.

Also export **`UV_HTTP_TIMEOUT=600`** (or higher) on every `./pw` call in a cloud session. The wrapper
fetches its Python toolchain and dependencies through the direct PyPI path, and `uv`'s default per-request
HTTP timeout (30 s) is too short for the large wheels here — an observed run's first two build attempts
failed with `uv` HTTP timeouts until the value was raised. This is distinct from the Bash timeout above:
that one bounds the whole call, while `UV_HTTP_TIMEOUT` bounds each individual dependency fetch inside it.
A `uv` HTTP timeout is an environmental fetch failure, not a build failure — do not read it as the gate
failing.

**Read the output, not the exit code.** The build can report a green summary while failing. How you
read "clean" depends on the path: the **executor** path emits a TOON result — confirm the reported
`status` and open the `log_file` it names to confirm `total_issues: 0` **and an empty `errors[]`** (the
repository-wide rule names all three). The **direct `./pw verify`** path emits no such log — it streams
the tools' output, so confirm each is clean instead: the quality-gate lines (`ruff … All checks
passed!`, `mypy … Success: no issues found`, `SPDX-header check passed`) **and** a pytest summary
reporting `0 failed` / `0 errors`. A green summary line is not the same as a clean run; fix and re-run
until it is genuinely clean, since a build that is not clean blocks the PR.

**This build can leave lockfile churn.** Under a session interpreter below the project's floor, `./pw`
rewrites `uv.lock` as a side effect. Do not let it reach a commit: stage the deliverable paths
explicitly and never `git add -A` (§ Step 4, "Commit and push").

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
- when the change alters a value, default, constant, or schema that documentation restates, the
  instruction to sweep **beyond the diff** — across the owning bundle/skill, not only the diff's own
  hunks — for any comment, docstring, or prose statement the change makes false. A stale claim in an
  *untouched* file (a "stays unset", a "defaults to `null`", a "the seeded shape is X") is the same
  misleading-signal defect as one in a touched file, and the diff-scoped collateral check above cannot
  see it — an observed run had to re-dispatch a second time to catch two such statements in bundle
  docs the diff never opened. **Sweep the changed value's consumers by kind, not by a single
  phrasing.** One value is restated in several distinct forms — a prose restatement, a schema field or
  its placeholder, a worked example, a cross-document reference, a test fixture or stub that hardcodes
  the value, a prose-bearing string literal in production code — and a sweep that greps for the way the
  primary claim happens to be phrased finds the
  restatement that reads like it and silently misses the rest. An observed run's single value change (a
  `SKILL.md`-only path widened to a `SKILL.md`-plus-`standards/*.md` set) had three stale consumers of
  three different kinds — an echo-field enumeration, a check description, and a schema placeholder — and
  no single reviewer caught all three: the phrase-oriented sub-agent sweep found the enumeration while
  the automated PR reviewer found the description and the placeholder. A later run surfaced the
  highest-risk kind of all: a **test stub/fixture that hardcodes the retired value and still passes**,
  because it is driven by a synthetic double rather than the real code path (a `_StubAttributor`
  encoding the old `(prefix, module)` claim), so neither the local build gate nor CI ever fails on it —
  it survived two sub-agent sweeps and was caught only by a third that explicitly grepped `*.py`
  fixtures. A further run surfaced the kind that hides in the seam between the two sweeps a run already
  performs: **prose embedded in production code as a string literal** — an argparse
  `help=` / `description=` / `epilog=`, an error-message or log-line template, an operator-facing
  message assembled in code. It reads as documentation and lives as code, so a documentation sweep
  never opens the file and a code sweep never reads the sentence; it is also the surface an **operator**
  reads directly, which makes a stale claim there worse than a stale doc — it misinforms a human
  decision rather than a later author. In that run the missed consumer was a subcommand's argparse
  `description` restating the retired predicate verbatim, and the same literal was **already** stale
  from an earlier change to the same code: two independent changes, one surface, and no gate that could
  see either, because the literal type-checks, lints, and passes every test while stating something
  false. ⛔ Naming the kind is not sufficient on its own — the same run then missed a SECOND instance,
  a module-docstring verb summary, in the very file whose argparse string it had just corrected. So
  re-walk the whole file, not the line the finding named. The sweep covers **test fixtures and stubs
  (`*.py`) AND prose-bearing string literals in production code, not only prose and docs**; name the
  consumer kinds a changed value can take and sweep for each in turn, which surfaces the restatements by
  construction rather than by luck;
- when the change introduces a computed metric — a rate, a share, a total, a duration roll-up — the
  instruction to test it at the boundaries of **its own** precision: one unit below its rounding
  granularity, and the smallest value its producing format can express. **A fixture set that shares the
  implementation's scale cannot see a scale defect.** An observed run's roll-up rounded to deciseconds
  before dividing, so two `0.06 s` inputs each published `0.1 s` and **both reported 100 %**, while a
  lone `0.04 s` call published `0.0 s`. Four verification rounds read that arithmetic — one of them
  brute-forcing 3,970 corpora against a *different* property of the same function — and none used an
  input below the rounding granularity, because every round inherited the whole- and tenth-second
  fixtures of the change under review. The defect was invisible by construction, and it misreported
  precisely the class the instrument existed to surface: a dominant-but-fast script is by definition one
  with many small durations;
- the instruction to report every gap it finds with file and symbol, and to state explicitly when a
  deliverable cannot be verified from the diff alone rather than assuming it passed;
- the instruction that a clean verdict must name what it checked, so an empty finding list is
  distinguishable from a check that examined nothing;
- **the stop question**, asked directly: *does anything you found remain that condition A or B forbids
  leaving open?* — with A and B quoted to it, and every survivor still open from earlier rounds listed
  for re-checking. Its answer is what ends the loop on the verifier exit (§ "When the loop stops"; the
  other exit is a spent budget no operator extended), so it is asked of the verifier here rather than decided by the
  author afterwards.

Then:

- **Findings that are real** → fix them, then re-dispatch. A verification pass that found a defect
  has not finished — unless conditions **A** and **B** permit that finding to be left open, or the
  round budget is spent with no operator extending it, in which case everything **A** forbids is still
  **fixed**, B's survivors are characterised, and the loop ends there (§ "When the loop stops", at the
  end of this step).
- **Findings you reject** → record the finding *and the reason for rejecting it* in the report. A
  dismissed finding is still evidence.
- Every finding — fixed, rejected-with-reason, deferred to a named follow-up, or left open as a
  **survivor** — goes in the run report (§ Report). A *deferred* finding is real and unfixed here;
  a *survivor* is one the run argues needs no fixing at all (§ "When the loop stops"). Neither is
  available to a finding condition **A** governs: a false statement is fixed, not deferred. And
  **B reaches a deferred behavioural finding too** — deferring it is still leaving it open, so it
  carries the same (a) proof or (b) bound a survivor carries, or it is fixed here.

**A fix is a change, so it gets the same beyond-diff sweep the original change got.** The sweep above
is written against the diff under review; by the second round the diff under review is largely the
*previous round's fixes*, and the sweep that matters is over what those fixes made false elsewhere. So
before re-dispatching, list the claims your fix changed — the value, the ordering, the count, the
mechanism it renamed — and sweep each one's restatements the same way: by **consumer kind** (naming
each kind a changed value can take — prose, docs, tests, `*.py` fixtures and stubs, and prose-bearing
string literals in production code — and sweeping for
each in turn, per the sub-agent instruction above), exactly as you did for the original change.

### Sweep-and-count: a claim is corrected at every site or it is not corrected

⛔ **Before recording a finding as fixed, enumerate every site that states the claim, and correct them
in one commit.** Not the site the finding named — *every* site. The enumeration is the work; the edit
is the easy part.

This is not the beyond-diff sweep restated. That one asks *"what did my change make false
elsewhere?"* — it hunts for **collateral**. This one asks *"where else is the thing I just corrected
also asserted?"* — it hunts for **the same claim, unfixed**. A run can perform the first perfectly and
still leave the corrected claim standing in four other places, because those places were never false
in a new way; they were false all along, and only one of them was pointed at.

⭐ **A fix applied at n−1 of n sites is why a corrected claim keeps reappearing round after round.**
One run's verification loop measured it directly:

| Round | Findings | Of which were a prior round's fix applied at too few sites |
|---|---|---|
| 3 | 11 | 5 |
| 4 | 13 | 5 — 1-of-3 surfaces, 2-of-7 statements, 1-of-4 enumerations, 1-of-3 |
| 5 | 6 | 3 |
| 6 | 4 | 1 |

Its round-4 verifier diagnosed the pattern in one line: *"each round's fix was sound where it landed
but applied at fewer sites than the claim it corrected spans."* Two rounds later the same run
corrected a claim **two lines from where the previous round's sweep had stopped**, inside the very
comments that round had edited.

The mechanical form, and it is cheap:

- **Grep for the claim before fixing any instance of it.** Its distinctive phrase, the value it names,
  the symbol it cites — then fix the whole set together.
- **A contract has surfaces, not a site.** When a fix implements a contract another surface already
  implements, enumerate that contract's surfaces and check each. One run's `unmeasured` contract had
  three (withhold the counts, suppress the summary metric, flag the downstream coupling); the fix
  applied one, and a later round found the withheld zero still being persisted and still rendering
  downstream.
- **Prefer naming to counting, and never write a count you have not just re-derived.** "The three
  mechanisms below" stood above four entries at three separate sites in one run — an enumeration that
  run had already fixed once.

**Sweep the previous round's fixes as a first-class surface, not only the original change.** A
"round" here is one iteration of this step's dispatch → fix → re-dispatch loop, within a single run —
not a prior PR and not a previous execution of the plan. By round N the highest-risk text is what
round N−1 *wrote*: a docstring, a table row, or a decision record added to explain a fix, which is
young, unreviewed, and not yet on anyone's list of consumers to grep for. So before re-dispatching:

- List the files the previous round edited, and re-read each against the current design —
  **especially any prose it added**, which no reviewer has yet seen.
- Where the fix amended a shared or governing document, check every sibling surface that cites it. A
  cross-surface record made true for the surface you fixed can be made false for the one you did not.
- List the fields, constants, and return keys the previous round **added**, and confirm each has a test
  that fails if its documented behaviour regresses. An untested addition is the highest-risk item in the
  round's own diff, because nothing but prose describes it — so the next round has only prose to check
  it against, and prose is what goes wrong. An observed run added five fields in one round and gave four
  of them pinning tests; the fifth is precisely the one whose docstring the next round got wrong, and the
  error survived until the round after that. That same round's commit message had already made "with a
  regression test that would have caught it" its stated standard, and then did not apply it to the field
  it was itself adding.

### A guard must not derive its expectation from the code it guards

⛔ **A test written to close a verification finding is itself unverified until it has been shown to
FAIL against the defect it names.** Write it, then break the code the way the finding describes, and
watch it go red. If it stays green, it is not a guard — it is a second copy of the implementation
wearing a test's name, and recording the finding as closed on its strength is a false clean signal.

The failure has a specific and recurring shape: **the guard computes its expectation with the very
function whose blind spot it exists to detect.** Both sides then agree by construction, and the
contradiction is invisible to the assertion. One run wrote a census guard whose expectation came from
the production population-reader; a check publishing its population under a name that reader did not
recognise was judged to have a full population by *both* the code and the test, so the block saying
`0` and the census saying "a non-empty population was examined" never contradicted each other in the
suite. The fix was to share the *key set* with production while reading the block *independently* —
sharing what must not drift, deriving separately what must be checked.

⭐ **Two more shapes from the same run, all three written by a run that had just been told about
vacuous guards, in a plan whose entire subject was detectors that cannot fire:**

| Shape | How it passed anyway |
|---|---|
| The fixture reached the asserted state by a **different route** than the one the test named — a non-shipping plan starved the check via the shipping exclusion, not the axis under test | Mutating the axis under test changed nothing |
| The assertion was **negative-only** (`X not in row`) | A regression to any *third* value also satisfied it |
| The test asserted a **splitter** while its name claimed a **coupling** — it called the parser directly instead of proving any pattern could reach it | Deleting the only pattern that reaches that branch left it green |

So, before recording a finding closed:

- **Mutation-test the new guard against the defect the finding names.** Not against a plausible
  neighbouring defect — that one.
  - ⛔ **Restore the mutated file from a snapshot the harness took itself — NEVER with a git command.**
    `git checkout -- <path>`, `git restore <path>` and `git restore --worktree <path>` all rewrite the
    working tree from the **index**, and `git stash` moves the edit aside; every one of them discards
    the *unstaged* changes in that file, not just the mutation. Mutating a file the run has edited but
    not committed therefore reverts the run's own work, and every red count the sweep then reports is
    measured against reverted code — a clean matrix that means nothing. An observed run lost a whole
    round's fixes this way and caught it only because the next mutation's anchor happened not to match;
    looser anchors would have left it undetected.
    **Order matters: commit everything the sweep must not lose (`git status --porcelain` empty), THEN
    snapshot, THEN mutate.** A commit records only what was staged, so an unstaged remnant is still
    unprotected. The snapshot is the harness's own copy of each file's bytes, written back in a
    `finally` — which covers a normal return and any exception but **not** a killed process, so
    re-check `git status` when the sweep ends and treat a surviving mutation as a failed sweep rather
    than a result.
  - ⛔ **Scratch paths are unique per agent.** Put the snapshot under a path carrying the agent's own
    name or role (`$TMPDIR/{agent}-mutsweep/…`), never a shared generic one. A run's mutation sweeps
    can be in flight concurrently — the author's and a dispatched verifier's — and two agents choosing
    the same filename clobber each other's snapshot, so the `finally` restores the *other* agent's
    bytes. An observed run had exactly this collision between two independent sub-agents.
- **Assert the verdict positively.** `assert x == expected`, never only `assert wrong not in x`.
- **Check the fixture reaches the state by the route the test claims**, and pin that precondition with
  its own assertion where a second route exists.
- **Quantify over the registry, not over a name list.** A guard looping three hard-coded names
  reproduces the n−1-of-n failure above by construction; one looping the live registry covers a
  member added later without anyone remembering.

⛔ **This is not the paragraph above it restated, and reading it as one is how the defect survives.**
That one says *sweep what your fix made false elsewhere in the tree*; this one says *the fix's own new
text is itself a surface, and the next fix will invalidate it.* One run leaked this exact class four
rounds running while obeying the paragraph above:

| Round | What leaked |
|---|---|
| 1→2 | Round 1 wrote a docstring describing the marker it introduced; round 2 replaced the marker without re-reading it, leaving a module's own return contract describing a field that no longer existed. |
| 2→3 | Round 2 rewrote one test's docstring to disclaim an invariant and left the neighbouring assertion **in the same file** encoding it. |
| 3→4 | Round 3 amended a governing ADR and did not check the sibling extension axis citing it, making that record false for a surface the fix never touched. |

Each round swept the surface the *original* change touched and missed the surface the *previous
round's fix* touched.

**A fix that hardens one value is checked against every value that must hold the same property.** Both
sweeps above look *outward* — what did this fix make false elsewhere in the tree. This one looks
*inward*, at the fix's own diff: when a change guards, validates, normalises, or clamps one value, name
the values that must hold that property alongside it and check each. A numerator and its denominator, a
reader and its writer, a getter and its setter, both ends of a range. It is a narrower and far more
mechanical question than the outward sweeps, and it catches what they structurally cannot. An observed
run hardened one side of a rate against `None`, non-integer, and negative input and left the other side
— one line away, part of the same expression — unguarded, so a null numerator raised `TypeError`
instead of being classified as the recording gap the function existed to classify. **Four verification
rounds read that line and none caught it**, because each saw a guard and confirmed that the guard was
correct. The question every round was answering is "is this guard right?"; the question that finds the
defect is "what else needs this guard?"

**A rationale you *wrote* is a claim about code you may not have read.** The sweeps above both ask
what your change made **false** — text that was true once and is not any more. This asks the other
question, about text that was **never** true: of the prose this round *added*, which sentences assert a
**mechanism** rather than restating the assertion beside them? "Rejected by the fail-closed whitelist",
"these two can disagree", "a falsy sentinel would satisfy this comparison" — each names behaviour
somewhere else in the tree. For every such clause, name the file and symbol that makes it true and
confirm it there, or delete the clause and keep the plain restatement.

⛔ **Nothing else in this contract catches an invented rationale, because there is nothing to catch it
against.** A stale claim contradicts the current tree, so a sweep can find it. An invented one
contradicts only reality: the suite is green, the linter is clean, the doctor passes, and the sentence
has no earlier version to diff against. It is introduced most often at exactly the moment least
scrutinised — writing a docstring to *explain a fix a reviewer just asked for*.

An observed run produced all three of the examples above, each in prose written by the round that was
fixing the previous round's finding:

| Written to explain | The claim | What the code said |
|---|---|---|
| a knob-registration table | an unregistered knob "is rejected by the fail-closed provisioning whitelist" on `set` | that whitelist is wired to three unrelated blocks and never to these knobs — and it is `get` that rejects, not `set` |
| the same table's header | the constant and the assembled config "can disagree" | assembly deep-copies the constant wholesale, so for these knobs they cannot |
| an identity assertion | `''` "would satisfy `== None`-style chains" | `'' == None` is `False`; the counterexample does not exist |

The fix in each case was right; only the *reason given for it* was wrong — which is the worst form,
because a docstring that explains **why** is trusted more than one that repeats **what**. That is
exactly why an unverified rationale is worse than none: it is the sentence a later reader believes
instead of checking. Prefer no rationale to an unchecked one.

⭐ **If the clause asserts what a function RETURNS, run the function.** Reading the callee and finding
it compatible is not confirmation — it is the same act that produced the claim, so it agrees with the
claim by construction. A rationale of the form *"X maps to Y"*, *"this shape resolves to Z"*, *"that
predicate covers W"*, *"the producer only ever emits V"* is a prediction about an executable, and the
tree can settle it in one call. Execute it on the **actual** argument the clause is about, not on a
representative one: the two defects this rule comes from were both claims that held for the value
their author had in mind and failed for the value the code actually passes.

⛔ **This is not the paragraph above it restated.** That one asks whether a named site *says*
something compatible; this one asks what the site *does* with your input. One run wrote both of these
and neither sweep caught either:

| Where | The claim | What running it showed |
|---|---|---|
| a run report's findings table | nine test stubs "supply a non-empty path, which the state machine maps to `materialized`" | True of the path; the stubs return a **boolean** as the tuple's first element. `True == 'materialized'` is `False`, so every one of them silently took the fallback branch. The build failed 12 tests |
| a docstring, inside the check written to prevent this exact class | `documentation_only` "is the only bucket checkable without the build extensions" | Calling the aggregator on a config-only write-set returns `documentation_only`. The check was **rejecting three shapes the classifier accepts**, blocking valid outlines |

⛔ **When the clause asserts something ENVIRONMENT-DERIVED, running it once is not enough — run it
against a second shape it will actually meet.** A path's depth below `/`, a hostname, a user, a home
directory, a locale, a CPU count, a temp-dir location: each is a property of the *machine*, not of the
code, so executing the claim where it was written confirms it by construction — the same failure this
rule already names, one level up. The check is to evaluate it against a shape CI will present, not
merely a representative one.

This is the class the local build gate **structurally cannot** catch, which is what makes it worth its
own paragraph. An observed run's test hard-coded `../../../etc` to escape the repository and asserted
the result was `/etc`. That holds only from a checkout three levels below `/`; the authoring machine's
was, a GitHub Actions checkout at `/home/runner/work/{repo}/{repo}` is five. `./pw verify` reported
`SUCCESS` with the whole suite green **on the exact commit CI rejected**, and the test's own docstring
stated the false premise as a fact — *"`PROJECT_ROOT` is three levels below `/`"* — so test and prose
agreed, both derived from the same unexamined assumption. Four verification rounds read the file.

⭐ **And such a fix is verified by DERIVATION, not by re-running**, because the machine that must
confirm it is the one that cannot reproduce the failure. Evaluate the corrected expression against
several shapes — the authoring path, CI's actual path, a degenerate one — and show it holds for each.
A green local re-run proves only that the machine still agrees with itself.

Both were one function call from being falsified, and both were expensive to find: a full build, and
a dispatched sub-agent. The second is the sharper warning — the sentence violating this rule sat
three lines from the sentence stating the rule it violated, in prose written to explain a fix a
reviewer had just asked for.

The obligations below are part of that same per-round sweep, not a separate pass done once at the
end. Each is checked **before every re-dispatch and again before the merge gate**.

**The run report is part of that surface.** A findings table recording a disposition the artifacts
contradict — a row saying "fixed at all four sites" when one still carries the old claim — is the same
defect as a stale doc, and it is the one a re-dispatch is *least* likely to catch, because the
verifier reads the code rather than the record. Re-read your own dispositions against the artifacts
before declaring a round closed.

**So is the PR description — and it is the surface most likely to be missed.** Every sweep you run
treats *the repository* as the thing being checked, and the description lives outside it: written once
at PR-creation time, never re-read, and yet the one restatement most reviewers actually read. Re-read
it against the tree and update stale claims, on the same cadence as the report. One observed
description reached the merge gate carrying four false statements — a control-flow ordering the code
no longer had, two test counts that had moved twice since, and "none rejected" on a PR with two
reasoned rejections — none of which any verification round could have caught, because none of them
reads the description.

**Figures that move between rounds are re-derived at the moment of the claim, never carried forward.**
Test totals, character budgets, population counts: each round's fixes change them, and a number copied
from an earlier round is stale by construction. Re-derive it (collect the tests, measure the string,
re-run the query) every time you state it, and say which unit you are stating — a count of test
*functions* and a count of *collected cases* are different numbers, and a reader who runs the suite
sees only the second.

⛔ **An enumeration lead-in is a figure.** "Two obligations follow", "three consumers", "N of M rounds
ran", a numbered list's introducing count, and an ordinal that names an object described elsewhere
("a **fourth** declaration surface") are all figures that move the moment the run edits the thing they
count — and they do **not read as figures**, which is exactly why they survive a sweep that catches
test totals. Count the items in the file as it now stands, at the moment of the claim. **A correction
to a count is itself a count**: re-count after editing it, because the corrected value is as easily
guessed as the original was.

The failure this closes is mechanical, not careless. One run applied this rule diligently to a
`20298 passed` figure and to a five-number population table — every one of which survived five rounds
of audit intact — while walking twice past a "Two obligations follow" lead-in over a six-item list,
"correcting" it to "Five". Across that run the same shape recurred **nine** times: a one-item list
introduced as "Two further consumers"; "Two independent verification rounds" standing above three
sections; a build-gate count the same commit had just invalidated; one object called "fourth",
"fifth", and "second" in three places. Three consecutive rounds introduced a fresh instance of this
defect *while fixing the previous one*.

Two corollaries follow from that pattern:

- **Prefer naming to counting.** "W3 and W4 are rows that were not actually fixed" cannot go stale;
  "Two rows were not actually fixed" goes stale the moment a third is found. Where a count carries no
  information the names do not, drop it.
- **Do not number an object across category boundaries.** The "fourth/fifth/second" drift above came
  from numbering a *declaration surface* into a sequence of *denominator consumers*. Once an ordinal
  spans two kinds of thing, every later edit to either kind invalidates it somewhere. Describe the
  object; let the reader count if they need to.

The run-report, PR-description, and moving-figure obligations above all exist because runs paid for
them: across one run's four verification rounds, each round's fixes landed at the site the finding
named and not at the sites restating the same claim — twice in the run report's own findings table.
(They are named rather than counted here for the reason the enumeration rule gives: a count in this
position goes stale the moment an obligation is added to the list — as one was, in the very commit
that rewrote this sentence.)

### When the loop stops

"Re-dispatch until a round finds nothing" is not a terminating rule: a round can always probe one
more mutation, one more boundary, one more restatement. The evidence runs both ways. One observed run
reached **twelve** rounds, eleven of which found a defect in the previous round's
fix, and concluded that *"no findings" is not a state this process reaches*. Another went five, and
its rounds 3–5 produced **zero** findings against the code and every finding against the run's own
report — each round's fixes are new unreviewed prose, so the loop keeps finding defects in its own
corrections long after the artefact under review has stopped improving.

**The loop ends in exactly one of two ways**, and the report says which (§ Report):

- **(i) the verifier answers that nothing remains** that A or B forbids leaving open, on the evidence
  required below; or
- **(ii) the round budget is exhausted** and no operator extends it — the hard terminator, because
  (i) is not guaranteed to be reachable. A reachable operator is asked at that boundary and may grant
  another five rounds; the loop ends here only once the answer is "stop", or once there is nobody to
  ask — the budget rule and its headless carve-out are stated later in this section.

Either way, **A and B govern what may be left open**. Call them **A** and **B** (§ Step 8's merge gate
has its own numbered conditions; these are not those).

**A — nothing false is left, ever.** A finding that some STATEMENT is false — a comment, a docstring,
a bundle doc, a test's own description, a report figure, the PR description — is fixed, wherever it
lives and whether or not it executes. This step's beyond-diff sweep and its ⛔ on invented rationales
exist to produce exactly these findings. **A is not subject to the budget below**: running out of
rounds bounds how often you *verify*, never whether you *fix* what verification already found.

**B — every behavioural finding left open is a characterised survivor.** For a finding about
behaviour under some input — a mutant, an edge case, a shape no test covers — the loop may leave it
open only when the run can state either

> **(a)** a proof that it cannot change what the deliverable does, or
> **(b)** the bound on what it *can* reach, and the promise it stays outside of — that promise named
> in the plan's own terms.

**(a) and (b) reach only a finding about behaviour under some input.** Both are stated about what the
*deliverable* does, so neither is available to a finding that changes **a test's meaning or a
deliverable's verdict**: those reset the loop always. That scoping is load-bearing, not pedantry — a
vacuous test satisfies (a) trivially, since it cannot change what the code does at runtime, and a
vacuous test is precisely the defect that hides a real one. **A finding that changes code behaviour
resets the loop too, absent (a) or (b)** — fix it and re-dispatch. Characterisation is the only thing
that lets one stay open, and being small is not characterisation. Survivors are listed individually;
a bulk mention is not a disclosure. **A finding that is both a false statement and a behavioural
defect is governed by A** — it is fixed, not characterised.

**Exit (i) requires evidence stronger than another read.** A verifier's "nothing remains" rests on
something that could have come back different: a differential run against the merge base, a fuzz
sweep, a mutation test that proves a new guard non-vacuous, an exhaustive enumeration of a function's
return branches — or, where the deliverable is prose, opening every cross-reference onto the section
it names and re-deriving every figure from its source, each of which returns a verdict rather than an
impression. A skill is behavioural prose reviewed as code (§ Step 7), so exit (i) is reachable for a
prose deliverable; what it is not reachable by is another read.
*"Three agents read it and found nothing"* is not that. Where the late rounds'
findings are not merely fewer but **narrower** — about the run's own report and plan documents rather
than the shipped change — say so, as the observation it is.

⛔ **Whether A and B are met is the VERIFIER's call, not the author's.** The dispatch checklist above
puts the question to the round, over its own findings *and* every survivor still open from earlier
rounds. Honour the answer.
The author is the party motivated to stop, and in the twelve-round run **three** of the tests written
to close previously-found gaps were themselves vacuous — they passed against the fixed code *and*
against the defect they named. An author polling their own work for permission to stop will get it.

⛔ **Stopping is a decision the run discloses, never a state it reports.** The verifier supplies the
answer; the run still owns the act of stopping on it, and must not launder the one into the other.
"Verification converged" and "I stopped at round 6, on the verifier's answer, with these survivors
open" are different claims. Writing the first is the same unmeasurable-rendered-as-measured defect
this lane exists to catch, applied to the lane's own process.

**The round budget is FIVE, unless the plan sets another.** It is not the run's to choose. The earlier
rule — declare your own, up front — still handed the number to the party motivated to stop, and "up
front" only stops a run picking the number at the moment it wants to quit; it does nothing about a run
that picks two. Five is the default because it is where the one run that was correctly assessed as
finished landed: its rounds 3–5 found nothing against the code and everything against its own report,
which is the signal that the artefact has stopped improving. The twelve-round run is the reason the
number alone is not enough — it kept finding real defects in its own fixes, so a fixed ceiling with no
way to extend it would have stopped that run mid-repair. Hence a default plus a checkpoint, rather
than either alone.

Exhausting the budget is a **STOP CONDITION**. What happens next depends on whether anyone can be
asked.

**With a reachable operator, ask at the boundary — do not stop, and do not continue, silently.**
Report where the loop stands and put the choice to the operator via `AskUserQuestion`:

- how many rounds have run, and what the last one found;
- whether the findings are getting **narrower** (about the run's own report and plan documents) or are
  merely fewer — the distinction that says whether more rounds would buy anything;
- every survivor still open, with its (a) proof or (b) bound;
- the question itself: **another five rounds, or stop here?**

A granted extension is another five on identical terms — the same boundary question again when it
runs out, the same fallback if the operator has since become unreachable. Record the question, the
answer, and every extension in the report: a conversation event is not a committed artifact, so the
report is its only durable trace.

⛔ **A headless run does NOT ask, and MUST NOT block waiting for an answer.** A cron-fired run, or a
dispatched leaf with no operator to reach, takes the autonomous fallback below the moment the budget
is spent.

This carve-out is what makes the budget safe to enforce at all, and it must not be "simplified" away
by a later editor who reads the ask as unconditional. An unconditional ask turns every unattended run
into one that stalls forever at round five — strictly worse than stopping with survivors disclosed,
because a stalled run delivers nothing and discloses nothing. Escalation is the reachable case's
**obligation** and the headless case's **impossibility**; the headless path always remains a complete,
unblocked outcome.

**The autonomous fallback** — taken when the budget is spent and no operator extends it, whether
because none is reachable or because the operator said stop. The run still **fixes everything A
forbids**, then stops with B's survivors characterised and disclosed per instance. Nothing false ships
because the rounds ran out. `Outcome` keeps its ordinary meaning — a verdict on the **deliverables**
(§ Report), not on the loop — so a run whose deliverables are complete records `completed` and
discloses its survivors, exactly as one that exited on a verifier's "nothing left" would.

The budget, every extension and who granted it, the round that ended the loop, the verifier's last
answer, and every survivor go in the report either way.

⭐ **A stopped loop is not defect-free code, and the report must not blur them.** In the five-round run
above the loop was correctly assessed as finished — and an external reviewer then found **two real
code defects** in the same diff, one of them a `Path.cwd()` fallback the run had seen and consciously
left. What either exit licenses is stopping *this loop*; it licenses no claim about the code's
correctness. Where a reviewer is still owed a look (§ Step 7), give it to them: this loop is not a
substitute for review coverage, and a rate-limited reviewer whose window reopens is worth
another attempt precisely because its method differs from the loop that just ended — by whichever
route that reviewer honours (§ Step 7), which for an auto-review reviewer is a push and not a comment.

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
on MCP, use the equivalent call — the `gh`↔MCP mapping is in § Cloud session affordances. Never assume
a tool is present — check, and if neither path is available, stop at Step 7 and report the run
**blocked**. Do not attempt to install tooling into the session, and do not treat an unreachable
review surface as an empty one.

## Step 7 — Branch, PR, review-comment cycle

The branch was published at Step 2 and kept current by Step 4's per-commit pushes, so this step
opens the PR on an already-pushed branch. Flush anything still unpushed first, then create it:

```bash
git push
```

```bash
gh pr create --fill
```

**Suppress bot review where the budget buys least.** Bot-review capacity is contended across this
repository and is regularly exhausted; every PR that draws a review spends budget another PR needs.
Two kinds of diff therefore carry `skip-bot-review` **by default**:

- **A diff with no reviewable footprint** — nothing a reviewer can act on.
- **A change to this repository's own project-level skills** (`.claude/skills/**`). These are the
  operating instructions the meta-project runs itself by, not the product it ships. A reviewer
  *could* act on them, so this is a deliberate spend decision and not a claim that they are
  unreviewable: the scarce budget goes to the shipped bundles and to code. **The operator can
  reverse it per PR** — asked for a bot review on a project-level skill change, create the PR
  without the label.

**A bundle skill is the product, and is reviewed as code.** Any change under `marketplace/bundles/**`
— a `SKILL.md`, a workflow doc, a script — keeps its review exactly as a `*.py` change does. It is
prose, but it is *behavioural* prose that governs how every consumer project's runs act, which is
precisely what a reviewer should see; do **not** treat it as documentation.

**A plan is behavioural prose too, and is reviewed the same way.** A diff that adds or edits a
`plan.md` — or a not-yet-moved `{NNN}-{slug}.md` — under `doc/plans/` keeps its review, for the
identical reason a bundle skill does: a plan is executed by a later run that has no operator to ask, so a
wrong path, an unobservable *done when*, a contradiction between deliverables, or an invented
rationale is a defect that run will act on. Only the *records* under `doc/plans/` are unreviewable in
this sense — a `report-NN.md`, a `verification.md`, a `gaps.md`, an epic `README.md`.

So `skip-bot-review` applies to **two** cases: a change under `.claude/skills/**` that the operator
has not asked to have reviewed, and a diff with **no `*.py`, no `marketplace/bundles/**`, and no plan
file under `doc/plans/`** — genuinely nothing but `doc/**` prose, run reports, or ledger bookkeeping.
The label is all-or-nothing, so a PR that mixes a project-level skill change with any reviewable
class **keeps its review**: the reviewable part decides. Note this is a different question from Step
5's build skip: a bundle- or plan-only change **skips the local build** (the gate is `*.py`-only) yet
**still gets reviewed**. Determine it from the same git evidence Step 5 uses, and apply the label
**at creation** — applying it afterwards is too late, because the bots are
triggered by the PR opening:

```bash
gh pr create --label skip-bot-review --fill
```

The rule in one line: **a project-level skill change gets `skip-bot-review` unless the operator asks
otherwise; every other PR gets it only when it has no `*.py`, no bundle change and no plan.** A
bundle change is code, and so is a plan. This suppresses waste, never scrutiny — a project-level
skill change is one the operator approved before it was written (§ closing self-check), which is the
scrutiny that matters most for text that governs future runs.

⛔ **The label is a one-way, creation-time decision, so it is disclosed before it is applied.** It
cannot be added later and removing it afterwards does not summon the reviewers that were never
triggered. Where an operator is reachable, say which way the rule comes out and why *before* creating
the PR; a run that applies it silently has made a scrutiny decision on the operator's behalf that the
operator cannot reverse.

Then work the review cycle until it is genuinely finished:

1. Wait for the automated reviewers and CI to report.
2. Read the actual comment bodies, from **all three** surfaces (see § GitHub access, and the table
   below). A summary of a review is not the review, and a green check is not evidence that a
   reviewer participated.
3. Handle **every** comment: fix it, or reply on the thread explaining why it is not actionable.
   Push fixes as further commits.
4. Re-check after each push — new comments arrive on new commits.

Record in the report which reviewers commented and how each comment was dispositioned.

**PR comments live on three surfaces, and the conversation view is only one of them.** Reviewers file
findings as inline review-thread comments and as review-summary bodies, neither of which the
conversation view contains. Reading only the conversation view and then asserting "all comments
handled" is a false clean signal — the exact failure this lane is built to avoid.

| Surface | Holds | `gh` | GitHub MCP `pull_request_read` method |
|---|---|---|---|
| Issue comments | Free-form conversation comments | `gh pr view {N} --comments` | `get_comments` |
| Review summary bodies | The review bots' **consolidated** findings (often the bulk of them) | `gh pr view {N} --json reviews` | `get_reviews` |
| Inline review threads | Per-file findings anchored to lines | `gh api repos/{owner}/{repo}/pulls/{N}/comments --paginate` | `get_review_comments` |

All THREE surfaces MUST be read before the merge gate — they are three **different** MCP calls, and no
one of them subsumes the others. The trap is specific to the MCP path: `gh pr view {N} --comments`
folds review-summary bodies into its output, but the MCP `get_comments` does **not** — review summaries
live only under `get_reviews`. A run that reads `get_comments` (issue comments) and `get_review_comments`
(inline threads) but skips `get_reviews` will assert "all comments handled" while never having seen the
review bots' main findings — the exact false-clean signal this lane exists to prevent, and one observed
in practice (six bot findings that arrived only in the review summary body).

### Record per-reviewer participation, from the bodies

Reading the comments answers whether each comment was *handled*. It does not answer whether each
expected reviewer *participated* — and those are different questions. A PR that received no review at
all trivially satisfies "every comment handled" against an empty comment set, so the merge gate can
read green on a diff no reviewer looked at. Closing that gap starts here: **establish the expected
reviewer population, then record a verdict per reviewer, from the bodies.**

**The population is derived from configuration, never hand-maintained here.** This repository registers
its automated reviewers in a machine-readable registry — one data block per reviewer at
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`, each declaring an
`author_login` (parsed generically by that skill's `scripts/bot_registry.py`; the same set is named in
prose by `.github/workflows/pr-agent.yml`). Read the `author_login` of every such registry doc — that
set **is** the expected reviewer population for this PR. Do **not** transcribe a reviewer list into
this contract or into the report: a hand-maintained list is the defect this step exists to prevent,
and it goes stale the instant a reviewer is added to or removed from the registry.

**Record a verdict per reviewer, derived from the stored comment bodies** — never from a check state,
a review summary, an absence of complaint, or this contract's prose. For each `author_login` in the
population, read that author's actual comment/review bodies on the PR (all three surfaces above) and
assign exactly one verdict:

| Verdict | Body evidence |
|---|---|
| `reviewed` | The author published a review artifact **against the diff** — an inline thread comment, or a review/issue-comment body carrying findings (or an explicit "nothing to report" over the diff). |
| `rate-limited` | The author published **only a refusal/quota notice** in place of a review (e.g. "Review limit reached", "reached your weekly rate limit of … diff characters"). It engaged but did not review this diff. |
| `silent` | The author published **nothing at all** — no review, no notice. Before recording it, run the recovery check below; an unexplained silence is recorded as such only once that check has been made. |
| `unreadable` | The surface that would carry this author's body **errored**. Not a statement about the author at all — a statement about the run's access. |

⛔ **An unreadable surface is not an empty one, and `silent` MUST NOT be used for it.** `silent` claims
a reviewer published nothing; a run whose read failed cannot make that claim, and recording it as
`silent` manufactures a clean signal out of a tool failure — which is the precise defect this lane
exists to prevent, committed at its own merge gate.

This is not hypothetical. One run found `pull_request_read` `get_comments` and `get_reviews` returning
**HTTP 404 on every attempt for hours**, while `get_review_comments` on the same PR read cleanly and
returned a genuine empty set — so the failure was per-surface, not an outage, and the clean inline read
was trustworthy where the other two were not.

**Take a positive control before believing any absence.** In that run the PR payload's own
`comments: 2` (from `pull_request_read` `method: get`) proved bodies existed that the run had never
read. A count from a surface you *can* read is the cheapest control available; take it, and record what
it says.

⭐ **`unreadable` blocks merge-gate condition 3, where `rate-limited` and `silent` do not** — a statement about condition 3 alone, since condition 6 separately gates CodeRabbit, so a `rate-limited` or `silent` CodeRabbit can hold the merge under *that* condition while leaving condition 3 satisfied. The
shortfall verdicts say a reviewer did not review — condition 3 is about whether every *comment* was
handled, and a reviewer who filed none leaves nothing to handle. An unreadable surface is different in
kind: comments may exist and be unhandled, and the run cannot show otherwise. So condition 3 is **not
established**, and a run that merges anyway is proceeding on an operator's instruction, not on a
satisfied gate. Report it that way — "overridden", never "met".

A check-run state is never a verdict: a green check can conclude having published nothing, and a
reviewer that posts no check at all would read as absent on every run. The verdict comes from the
bodies or it is not evidence.

#### Every non-`reviewed` verdict also records whether it reopens

The verdict says a reviewer did not review. It does not say whether that is temporary — and the two
cases call for opposite handling, so the record carries both. Alongside each non-`reviewed` verdict,
state **`Reopens? yes / no / unknown`**:

| Reopens? | Meaning | Example |
|---|---|---|
| `yes` | The limit clears on its own, and the notice usually says when. Re-requesting later is productive. | "Review limit reached … next review available in 27 minutes" |
| `no` | A property of *this diff*, not of the clock. The same request never succeeds at this size, so waiting is futile. | "your pull request is larger than the review limit of 150000 diff characters" |
| `unknown` | The notice states a refusal without a clearing condition, or the reason for silence could not be established. | An unexplained silence; a bare "cannot review this PR" |

⛔ **`rate-limited` alone cannot carry this**, and that is the whole reason for the column: two
reviewers were observed refusing one PR **at the same moment**, one on a countdown that cleared and
one on a size ceiling that never would, and the participation table rendered them identically. A
reader of the table could not tell which — if either — was worth re-requesting.

Take the value from the **notice body**, the same source as the verdict; do not infer it from the
reviewer's identity, since one reviewer can refuse under both kinds.

Record the population, each reviewer's verdict, its `Reopens?` value, and the body evidence for it in
the report's **Reviewer participation** table (§ Report), and state the coverage as N-of-M. A reviewer
that never spoke is then *visibly* `silent` in the record, not merely unmentioned.

#### A `Reopens? yes` refusal is RETRIED, not recorded

A `Reopens? no` refusal is a fact about this diff: waiting cannot change it, so it goes straight into
the record. A **`Reopens? yes`** refusal is not a fact about anything — it is a clock. Recording it as
a shortfall the moment it appears converts a delay into a permanent gap, and the run then discloses a
missing review it never actually tried to get.

**So a `Reopens? yes` verdict is provisional.** It becomes a shortfall only once the retry schedule
below is exhausted; until then the run owes another attempt.

- **Wait the window the notice states, then add jitter** — a random 5–20 minutes on top. ⛔ **The
  jitter is not politeness, it is correctness.** Several plans run in parallel against **one
  per-developer allowance**, and every one of them reads the same "available in N minutes" from its
  own notice. Without jitter they all wake at the same instant and contend for a single slot: at most
  one is served, the rest are refused and re-synchronise on the *next* slot, and the convoy never
  breaks up. Jitter is what decorrelates them.
- **Know what an "attempt" IS before making one — it differs per reviewer.** For a reviewer that
  runs automatically (CodeRabbit here) an attempt is a **push**; its trigger comment is inapplicable
  and achieves nothing (§ "Obtaining a CodeRabbit review"). For a reviewer triggered by a comment, an
  attempt is that comment. Read the route before spending a wake on the wrong one.
- **One attempt per wake. Never two.** A second attempt in the same turn cannot succeed where the
  first failed — the window has not moved — so it buys nothing and obscures the record.
- **Never poll in Bash, and never `sleep` on a reviewer.** Arm a timer (§ Cloud session affordances)
  and let the wake do it. Where no timer is available, § Step 8 condition 6's cannot-re-enter arm
  applies — do not wait without one.
- **A finished commit is never held back to time an attempt.** § Step 4's push cadence outranks this
  schedule: push it when it is ready, and treat the review the push triggers as that wake's attempt.
  Waiting out a window with completed work uncommitted is the failure durability exists to prevent.
- **Budget: six attempts.** Six covers roughly a working day of hourly windows. When it is spent,
  stop attempting, record `rate-limited` with its `Reopens?` value and the attempt count, and treat
  it as a shortfall from that point on. Count every attempt the run makes, whatever it returned —
  the budget bounds the run's *effort*, not the provider's accounting, which the run cannot observe.

Record every attempt — its time and the notice it drew — in the report. An attempt that was made and
refused is different evidence from one that was never made, and only the record distinguishes them.

#### Obtaining a CodeRabbit review — the strategy that actually works

Written out because three separate mechanisms interact here, and a run that knows only one of them
draws the wrong conclusion from a refusal.

**1. The trigger depends on whether AUTOMATIC review is enabled — and usually it is, which makes the
comment a no-op.** Read the governing `.coderabbit.yaml` (a repository-level file, else the
organization's central one) at `reviews.auto_review`. Where auto-review is on — this organization
enables it for every PR not carrying `skip-bot-review` — CodeRabbit reviews on the PR-open and on
each **push**, and its own reply to a manual request says the command *"is applicable only when
automatic reviews are paused"*. ⛔ **So on an auto-review repository, posting `@coderabbitai review`
does nothing**, however many times a run posts it, and however open the allowance is. **The lever
that works is a push**, which is what the refusal notice itself offers alongside the comment ("or
push new commits to the PR"). Post the comment only where auto-review is genuinely paused.

**2. The allowance is per DEVELOPER, and it is set by HISTORY, not by this PR.** CodeRabbit's notice
states it: the hourly allowance is derived from "a developer's included PR review attempts over the
past 7 days", and "higher sustained activity can lower the allowance until earlier attempts leave the
7-day window". Two consequences a run must not get wrong:

- **A refusal consumes nothing.** The notice says "we couldn't start this review" — nothing ran. Do
  not model refusals as spending a budget; the countdown is the allowance returning, not a balance
  the run drew down.
- **A refusal is often not about this PR at all.** Sibling plans, and this project's own sustained
  volume over the preceding week, set the allowance. ⛔ **So a run that keeps waiting may be waiting
  on something no amount of waiting fixes.** Establish that concretely rather than by feel: after
  **three** of the run's own windows have passed with no review, read `get_reviews` on the two or
  three most recently updated pull requests in the repository (`list_pull_requests`, sorted by
  update). **No CodeRabbit review body on any of them** means the limit is exhausted at the account
  level, not on this PR. Say so to the operator rather than spending the rest of the budget on it;
  the remedy is theirs — an admin raising the limit in Billing, or less concurrent review volume.

**3. The incremental-review property.** CodeRabbit "does not re-review already reviewed commits", so
a request against a head it has already processed yields **nothing**: no review body, no inline
threads, no status change. Combined with (1), this is why a run can post request after request and
observe no review at all — an inapplicable command against an unchanged head cannot produce one.

⛔ **Do not read *"Reviews are available now"* as a review.** It reports the allowance, not the
outcome. Confirm the review from the surfaces (§ Step 7), never from that reply.

**Both problems have the same remedy: a NEW HEAD SHA.** A push re-triggers the automatic review *and*
offers material the reviewer has not seen. Merge `origin/main` in — usually owed anyway under § Step 8
condition 2 — or land the next real commit. **A new PR is not a remedy**: it neither changes the head
nor resets a per-developer allowance.

**When no new head is available** — the base has not moved and the plan has no further commit to make
— there is nothing left that could produce a review. Record it as **unobtainable** — condition 6's
own word for this state, not "budget spent", which means something else — and proceed under § Step 8
condition 5. ⛔ **Never manufacture a head** with an empty or
cosmetic commit to summon a reviewer: § Step 7 forbids that for CI, and the reason is the same here.

**4. Verify by the bodies.** A review has happened when `get_reviews` carries a summary body from
`coderabbitai`, or `get_review_comments` carries its inline threads. A green check, an absence of
complaint, and the acceptance reply are none of them evidence.

#### A `silent` verdict is not terminal until the recovery check says so

Silence has several causes that look identical from the comment surfaces — the bodies are empty, which
is what `silent` means — and **one of them is recoverable**. So `silent` is a provisional verdict:
before disclosing it, establish *why*, and act on the answer.

Check whether the reviewer's workflow ran at all, and split on it:

- **No run at all** → the reviewer never got the event. It is not rate-limited; it was not invited.
  Invite it by whichever route that reviewer actually honours: post the registry's declared
  `trigger_comment` (`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`)
  as a PR comment where a comment is what triggers it, and **a push where the reviewer runs
  automatically** — for CodeRabbit on an auto-review repository the comment is inapplicable and only a
  push works (§ "Obtaining a CodeRabbit review"). Then re-read the surfaces and record the *result* —
  a review that arrives this way is `reviewed` like any other. Where neither route is available (no
  new head to push, comment inapplicable), the check is discharged by establishing that.
- **A run that concluded `skipped`, or failed** → a guard or a failure suppressed it, and no comment
  will change that. Record the run's conclusion as the reason and disclose.

This adds a cheap recovery attempt before the disclosure. It is **not** a gate *of its own*: if the
trigger produces nothing, disclose the shortfall and carry on as § Step 8 condition 5 says — with one
exception it does not override. **For CodeRabbit on a PR carrying no `skip-bot-review` label,
condition 6 still applies**, and this recovery attempt is what satisfies it in the `silent` and
`Reopens? unknown` cases. Carrying on is licensed by having made the attempt, not by skipping it.

⛔ **Do not run this recovery on a `skip-bot-review` PR.** The label means the bot was deliberately
not invited, so inviting it — by comment or by push — summons the reviewer the label exists to
suppress. There
the `silent` verdict is expected, is recorded as such, and needs no recovery.

⛔ **Query by `event`, never by head branch.** A **command**-triggered run (`issue_comment`) is
attributed to the repository's **default** branch, because `issue_comment` is not a pull-request
event. A head-branch-filtered query therefore returns `total_count: 0` *whether or not the run
exists*. One run believed that false negative twice — once recording "no workflow run" while a run
existed, and again eleven minutes after the recovery run had already succeeded, nearly reporting the
recovery as failed. Written loosely as "check the Actions API", this rule reproduces the defect it
fixes, because the obvious query is the wrong one.

⭐ **And treat any negative as unverified until a positive control returns.** Before believing a
`total_count: 0`, re-run the same query against something known present — another PR's branch, a
broader filter — and confirm it returns a row. A filtered query that can only ever return zero is
indistinguishable from a true absence, and this generalizes well past this one check: every false
"nothing there" in the run above came from a filtered query believed without a control.

### A push during the review cycle: superseded runs and aborted reviews

Pushing fixes as further commits (above) is mandatory — durability outranks review cleanliness, and
the push-cadence rule at § Step 4 forbids holding a finished commit back. But a mid-cycle push has two
review-side effects, and each has a defined handling so neither is misread:

- **A superseded CI run is not a failure.** A push that lands while `verify` is running cancels the
  in-flight run via Actions concurrency, surfacing a `verify / conclusion` *cancellation*. That is a
  superseded run, not a real failure — do not treat it as a red gate. Step 8 reads the *actual* check
  state of the latest run; wait for the re-triggered run to conclude and judge that one.
- **A push that aborted a review consumed that reviewer's window — re-trigger it, never bank the
  abort.** If a push changed the head while a bot was mid-review, that bot did **not** review the new
  head, and its rate window may now be spent. Record its verdict as `rate-limited` or `silent` per the
  bodies (above), disclose the shortfall (§ Step 8), and — when its window permits — re-request its
  review rather than reading the aborted attempt as coverage. An aborted review is never counted as
  `reviewed`.

## Step 8 — Merge gate

**The merge is gated on conditions 1–4 and 6 below. Condition 5 is a disclosure the run performs
before arming auto-merge — it is not a gate on the merge. Merge only when conditions 1–4 and 6
hold:**

1. **Every required context is present on the exact head SHA and concluded successfully** — not
   merely "all checks green." A repository's check set mixes two kinds of context: those the branch
   **ruleset requires** before a merge, and those that merely report — advisory bots, informational
   statuses, third-party badges. **Required-ness is the ruleset's to define, never this document's**:
   read it from GitHub's own computation over the ruleset (`mergeStateStatus`, below), never from the
   shape of whatever check set came back, and **name no individual check here** — a check named
   ignorable in this contract would be wrong the moment the ruleset changed. **The ruleset-config API
   itself is not reachable on the cloud MCP path** (§ Cloud session affordances), so "read it from the
   ruleset" means read `mergeStateStatus` — never a ruleset-config API call, which returns `403` here.

   Read required-ness from GitHub's own computation over the ruleset — the actual state now, not an
   assumption that time has passed — through whichever surface this run's GitHub access path exposes:

   ```bash
   gh pr checks {N}                              # per-context state on the head
   gh pr view {N} --json mergeStateStatus,mergeable
   ```

   > **On the MCP path this field is `mergeable_state`, not `mergeStateStatus`.** `pull_request_read`
   > with `method: get` returns GitHub's REST payload, whose merge-state field is **`mergeable_state`**
   > with **lowercase** values (`clean` / `unstable` / `blocked`, plus `behind` / `dirty` / `unknown`) —
   > there is no `mergeStateStatus` key and no uppercase form in the response. Read `mergeable_state` and
   > map it case-insensitively onto the states named below (`clean` → clean, `unstable` → `UNSTABLE`,
   > `blocked` → `BLOCKED`); the semantics are identical. The MCP `get` payload also omits the
   > `auto_merge` field, so arm-state cannot be read from it — see "Confirm the merge actually happened".

   `mergeStateStatus` is GitHub applying the ruleset for you: **`BLOCKED`** means a **required**
   context is unsatisfied — failing, pending, **or absent** — so the merge must wait; **`UNSTABLE`**
   means every required context has passed and only **non-required** contexts are still pending or
   failed; **`clean`** means every required context has passed and nothing non-required is pending or
   failing either — the PR is fully mergeable. **`UNSTABLE` and `clean` both report the required
   contexts satisfied**, so both are states in which the PR may be armed; the difference is only
   whether a non-required context is still outstanding. On this merge-queue repository the queue is
   the final enforcer — it admits a PR only when the ruleset's required contexts pass — so arming
   auto-merge (below) defers required-ness to the queue rather than to a greenness check performed
   here.

   - A **required** context that is failing, pending, or **absent from the head** is **not** satisfied:
     this condition is not met. Absence never reads as success — a required context that has not
     reported is treated as unmet, never waved through, because a required context missing from the
     head is exactly the failure mode that nearly cost a merge.
   - A **non-required** context that is pending, failed, or absent **does not block** the merge but
     **is disclosed** to the operator — the same disclose-not-block treatment condition 5 gives a
     review-coverage shortfall. State it in words before arming auto-merge; never hold the merge for it.

   When `mergeStateStatus` is `BLOCKED`, derive **which** context blocks from (required contexts ∩
   non-green contexts) — never from whichever pending status is loudest. A visible, non-required
   pending status (a prominent bot comment, an informational badge) is not the blocker just because it
   is salient; the blocker is the unsatisfied **required** context, which may be quietly `in_progress`
   or absent from the head. A run once disclosed a non-required pending check as "the blocker" while
   the actually-required check was still running — the operator disclosure named the wrong cause.
   Derive the blocker from the intersection, and never promote a non-required pending status to "the
   blocker" in an operator disclosure.

2. **A stale base is re-verified before arming.** When `origin/main` has advanced past the PR's merge
   base, merge it into the branch and re-run § Step 5's gate on the **merged** tree.

   `mergeable_state: clean` reports the absence of a **textual** conflict and says nothing about a
   **semantic** one — a renamed fixture, a moved constant, a widened rule, a guard that names a file
   another slice owns. The PR's own CI cannot see it either: it verifies the base the branch was cut
   from, so a green `verify / conclusion` on the head is a statement about a tree that no longer
   exists. A run that arms on a stale base hands the merge queue a build nobody has run.

   This is systematic for this lane rather than incidental. A cloud session can end at any point, and
   the interval between "PR opened" and "PR armed" is exactly where `main` moves. An observed PR sat
   `clean` with every check green while a sibling slice's rename had already reddened one of its
   guards against merged `main`; the queue would have rejected it, and nothing in conditions 1, 3, 4, 5
   or 6 could have caught it.

   Read the gap from git, never from recollection or from `mergeable_state`:

   ```bash
   git fetch origin main
   git rev-list --count HEAD..origin/main
   ```

   A non-zero count means the base has moved and this condition applies. **Re-run § Step 5's gate on
   the merged tree** — the full one, by the same `*.py` predicate Step 5 uses, so a docs-only advance
   costs nothing.

   **Where the merge is performed decides what the report must say, so choose before you merge —
   the two shapes are not interchangeable:**

   - **On the branch (the default).** `git merge origin/main`, gate, push. The Step 9 report commit
     (condition 4) then lands *on top of* the merge, so pushing the report pushes the merge with it —
     there is no third option where the branch carries the report but not the merge. The PR's own CI
     therefore verifies what actually lands, at the cost of one more CI cycle and a base that may move
     again before it finishes.
   - **On a throwaway branch, leaving the PR head untouched.** Cut one from the PR head, merge
     `origin/main` there, gate there, then return to the PR head and delete it. Use this when the
     merge must stay out of the PR's history. The tested tree is then **not** the PR head, and the
     report says so, naming the merge commit that was tested — otherwise the record claims a
     verification of a tree the PR does not contain.

   The condition is met by having **run** the gate on a merged tree either way. The report records
   which shape was used, the tested merge commit, and the gate's result (§ Report → Build gate).

   ⛔ **Fail closed.** Every command this condition runs is load-bearing, and a failure of any of them
   leaves the check unperformed rather than passed: a failed `git fetch` leaves `origin/main` stale
   and the count meaningless; a conflicting merge leaves no merged tree to gate; a red gate on the
   merged tree is the defect this condition exists to surface. In each case **condition 2 is NOT
   established, auto-merge is NOT armed**, and the report records the command that failed and why. A
   conflicted merge is resolved (or the merge aborted and the conflict reported as a blocker) before
   the condition can be met — never left half-applied in the working tree, which would make every
   later check read against a tree that is neither the PR head nor the merged one.

   ⛔ **Re-running the gate is not optional when the count is non-zero, and "the queue re-verifies" is
   not a substitute.** It does — on `merge_group`, after arming — and by then the branch is locked and
   a rejection costs a bounced PR that nobody is watching, in a lane whose sessions do not survive to
   watch it. The queue is the enforcer of last resort, not the first place a break should surface.

3. **Every PR comment is handled** — fixed or answered on the thread. No open, unaddressed comment.

4. **The report is finalized and pushed** — run Step 9 now and commit its report artifacts (the
   contract-check table and the "what have we learned" section) as the **last pre-merge commit**,
   *before* you arm auto-merge. This ordering is load-bearing, not cosmetic: the report lands *in
   this PR*, and the instant the branch enters the merge queue a protected-branch hook rejects every
   further push to it ("Branches that are queued for merging cannot be updated" — observed). A report
   finalized after arming can never reach this PR, forcing a second follow-up PR just to complete the
   record. So Step 9's report sections are written here; only the post-merge landing confirmation
   (below) happens after.

   **A retry cycle under condition 6 may add commits after this one, and that is fine.** The branch
   locks at *arming*, not at the report commit, so a run waiting on § Step 7's schedule re-commits
   the report — retry log included — each time it wakes. What condition 4 requires is that the report
   is complete and pushed **immediately before arming**, whichever commit that turns out to be.

5. **A review-coverage shortfall is disclosed to the operator.** From the per-reviewer participation
   record (§ Step 7), read the verdict of every expected reviewer. When **any** expected reviewer's
   verdict is not `reviewed`, state the shortfall and its reason to the operator, explicitly and in
   words, *before* arming auto-merge — carrying each reviewer's `Reopens?` value (§ Step 7), since
   that is what tells the operator whether the gap was ever closable. For example: "Review coverage:
   1 of 3 — `cuioss-review-bot` reviewed; `coderabbitai` rate-limited on a countdown, six attempts
   spent without obtaining it; `sourcery-ai` rate-limited on a size ceiling, does not reopen."
   **A run that merges on 1-of-3 must _say_ 1-of-3.**

   ⛔ **The example says "six attempts spent" for a reason.** A CodeRabbit line here reports a state
   in which condition 6 is *satisfied* — never a bare countdown the run could still act on. Those
   states are the ones condition 6 names, and the disclosure borrows its word for each: **obtained**,
   **budget spent**, **unobtainable**, a run that **could not re-enter** to spend the budget, or a
   `skip-bot-review` PR. Read condition 6 for the list rather than counting it here.

   What is forbidden is narrower than "a live countdown": it is disclosing a countdown the run could
   still have acted on and did not. A countdown may well still be ticking when the run arms —
   `unobtainable` and `could not re-enter` both look like that from outside — and each says *why*
   acting further was impossible. For example: "`coderabbitai` rate-limited on a countdown, three
   attempts made, no review on any recent PR in the repository — the limit is exhausted at the
   account level, not on this PR"; or "`coderabbitai` rate-limited on a countdown, one attempt made;
   no self-wake available in this session, so the budget could not be spent." 

   A `silent` verdict reaches this disclosure only after its recovery check (§ Step 7) — so what is
   disclosed here is a shortfall that survived an attempt to fix it, not merely one that was noticed.

   ⛔ **Disclosing a shortfall and being free to proceed past it are different acts.** The run
   **always** says what coverage it got. Whether it may then proceed depends on which of three rules
   the shortfall falls under:

   - **A clearing rate limit (`Reopens? yes`) is not a shortfall yet.** § Step 7 retries it on a
     jittered schedule; it reaches this disclosure once that budget is spent — or, for a run that
     cannot re-enter to spend it, once that inability is established and named (condition 6).
     Recording it here on first sight discloses a gap the run never tried to close.
   - **CodeRabbit, on a PR carrying no `skip-bot-review` label, is gated by condition 6.** Disclosure
     does not discharge that condition; obtaining the review, or exhausting its budget, does.
   - **Every other shortfall proceeds on disclosure** — a ceiling that cannot reopen, a silence that
     survived its recovery check, any other reviewer's absence. For these the shortfall changes what
     the run **says**, never whether it **merges**.

   **The defect this closes is the _silence_, not the shortfall:** a run that proceeds on partial
   coverage, having satisfied whichever rule above applies, is fine; a run that proceeds *without
   saying so* is the failure. A quota outside our control must not strand a finished landing
   indefinitely, which is why condition 6 is bounded by a budget rather than left open-ended. Once
   the applicable rule is satisfied and the shortfall stated, arm auto-merge — conditions 1–4 and 6
   are the gates on the merge itself.

6. **CodeRabbit has reviewed, or the run has established it cannot — on a PR with no
   `skip-bot-review` label.** A plan and a bundle change are behavioural prose a later run executes with no
   operator (§ Step 7), and CodeRabbit is the reviewer that reads them as such. So on any PR the
   label rule leaves reviewable, **do not arm auto-merge on a first CodeRabbit refusal.** A
   project-level skill change is normally *not* such a PR — it carries the label by default — so this
   condition reaches it only when the operator asked for the review.

   Satisfy it one of three ways, and say which:

   - **Obtained** — `get_reviews` carries a `coderabbitai` summary body, or `get_review_comments`
     carries its inline threads, and every finding in them is handled per § Step 7. This is the
     intended outcome.
   - **Budget spent** — § Step 7's budget of six attempts is exhausted, counting every attempt the
     run made whatever it returned, and each retry made after its stated window plus jitter. Record
     every attempt with its time and notice, then proceed under condition 5's disclosure.
   - **Unobtainable** — the run established that no attempt can succeed: auto-review is enabled so the
     trigger comment is inapplicable and no new head is available, or several windows passed with no
     review anywhere in the repository. Record which, and proceed. Waiting out a budget against a
     mechanism that cannot deliver is the non-option this contract exists to eliminate.

   ⛔ **A `Reopens? yes` refusal does NOT satisfy this condition** — it is the state the retry
   schedule exists to work through. ⛔ **Nor does an accepted attempt that produced no review**: read
   § Step 7's incremental-review trap, get a new head SHA, and spend the next attempt on material the
   reviewer has not seen.

   **A `Reopens? no` refusal satisfies it immediately**, because waiting cannot change a property of
   this diff. Record it and proceed — retrying a size ceiling is the non-option this contract's own
   epic exists to eliminate.

   **A `skip-bot-review` PR is out of scope for this condition entirely** — the label means no bot was
   invited, so there is nothing to wait for. § Step 7 governs when that label may be applied; a
   project-level skill change carries it by default, everything else only on an empty reviewable
   footprint.

   **A `silent` or `Reopens? unknown` CodeRabbit satisfies it once the § Step 7 recovery check has
   been RUN.** Neither posts a countdown, so § Step 7's retry schedule — which waits "the window the
   notice states" — has nothing to key on and does not apply. Run that check **as it is written,
   including its split** — and including its route rule: the check invites a reviewer only by the
   route that reviewer honours, which for CodeRabbit on an auto-review repository is a push and never
   the trigger comment. Where a run concluded `skipped` or failed, where the reviewer posted a bare
   refusal naming no clearing condition, or where the reviewer is a hosted app with no workflow run to
   query at all, the check is discharged by *establishing that*, with nothing posted. Either way the
   condition is satisfied once the check has been run and yielded no review, and the run proceeds
   under condition 5. Do not invent a wait for a clock that was never stated.

   ⛔ **This condition delays; it must never deadlock — and the run that cannot wait is the case to
   get right.** § Step 7's retry schedule needs a timer, and § Cloud session affordances records that
   the self-wake tools may be approval-gated or absent entirely. **A run that cannot re-enter cannot
   spend the budget, and must not treat that as a reason to hold the PR.** So:

   - **A run that can re-enter** (a live session, a working timer, an operator who will resume it)
     spends the budget as written.
   - **A run that cannot re-enter** satisfies this condition with the attempts it was able to make —
     one, if that is all it had — and records **why** the budget was not spent, naming the missing
     affordance. That is a complete outcome, not a partial one: it is the same arm-and-hand-off
     completion § Step 8 already defines for the landing, applied to review coverage.

   Either way the condition is bounded — by the budget, by the recovery attempt, or by the run's
   inability to wait — and never by another team's quota consumption. A finished, green PR is never
   held open indefinitely.

Then merge (the repository uses a merge queue, so enable auto-merge and let the queue land it):

```bash
gh pr merge {N} --squash --auto
```

**Arming auto-merge is a one-way door — the branch locks the instant you arm.** On this merge-queue
repository, the moment the required contexts are green, arming adds the PR to the merge queue and a
protected-branch hook then rejects every further push ("Branches that are queued for merging cannot be
updated"). **Disabling auto-merge does not release the lock, and converting the PR to draft does not
release it** — both were tried on one run, both left the branch queued. Two rules follow:

- **Push everything that must land in this PR _before_ you arm** — the report above all (condition 4).
  After arming, nothing more can reach the PR.
- **Invoking the auto-merge command _is_ arming — there is no dry run.** Do not run it to probe a merge
  flag or "see what happens": against a PR whose required checks are already green, it queues that PR
  for real, and you cannot take it back except by the recovery below.

**If you are already queue-locked with an unpushed commit** — a finished report that will not push —
the only reachable dequeue is to **close the PR**. Close it → push to the now-unqueued branch → reopen
→ mark it ready → re-arm as the gate's final step (above). Closing is the dequeue; disabling
auto-merge and drafting are not. This costs a second CI pass, but it lands the report *in this PR*
rather than stranding it in a follow-up.

**Confirm the merge actually happened.** A merge command reporting success is a claim, not the
outcome — this repository has seen a merge call report success, delete the branch, and not merge:

```bash
gh pr view {N} --json state,mergedAt,mergeCommit
```

Only `state: MERGED` with a real `mergedAt` is a landing.

**On the MCP path, arm-state is not readable and a queued clean PR looks un-armed.** Observed:
`enable_pr_auto_merge` returns a canned "Auto-merge enabled …" with an **empty `method`** field
(identical on repeat calls), the PR's `updated_at` does **not** bump on enqueue, and
`pull_request_read method: get` omits the `auto_merge` field. So after arming a clean, already-green
PR, none of these tells you whether the arm took — and the PR can sit `open`/`clean` for many minutes
while it is in fact queued. Do not read that silence as a failed arm. The two reliable enqueue/landing
signals are a later `state: MERGED` read, or a `405 "Pull Request is in the merge queue"` returned by a
`merge_pull_request` attempt — which is harmless here, because the queue **refuses** the direct merge
rather than performing it, and does not dequeue. Absent either signal, treat the PR as
armed-and-delegated (below), not failed.

**When the session cannot self-confirm the landing, arm-and-hand-off is a completed run — not a partial
one.** Confirming `state: MERGED` assumes the run can wait for the queue to land the PR and re-check. A
cloud session often cannot: the self-wake tools (`send_later`, `subscribe_pr_activity`) may be
approval-gated **or absent entirely**, and Bash cannot poll GitHub (§ Cloud session affordances), so
there is no way to block-until-landed inside the session. When that is the case, the run has finished once it has (a) met
conditions 1–4 and 6, (b) armed auto-merge, and (c) handed the `MERGED` confirmation to the orchestrator's
collect step, which reads it from the PR merge event. Record the outcome as **completed with the
landing delegated** — not `partial`, and not a failure. A run that armed a green PR into the queue and
merely could not self-wake to watch it has done everything the lane asks; reading its own inability to
watch the queue as a failed run is the mistake this paragraph prevents. (A run that *can* self-confirm
still does — this is not licence to assert a merge that was never read back.)

**When there is no self-wake AND a required check is still `in_progress` at the gate, arm anyway — the
merge queue is the enforcer, not this session.** (Condition 6 is unaffected by this carve-out: the
queue enforces the ruleset's checks, not review coverage, so a CodeRabbit review that has been neither
obtained nor budget-exhausted is still outstanding when the required build is merely in progress.) Condition 1's "BLOCKED → wait" assumes the run can
wait for the required check to conclude; a run with no self-wake cannot, and holding the arm until green
would strand a fully-ready PR indefinitely with no one to land it. On this merge-queue repo the queue
admits a PR only when the ruleset's required contexts pass and re-verifies on `merge_group`, so arming
auto-merge while the required build is still running does **not** merge a red PR — it defers the
required-green gate to the queue, exactly as arming does when the PR is already green (§ Cloud session
affordances, "Auto-merge arming"). The one ordering that stays non-negotiable: conditions 2–4 must be
met and the report committed as the last pre-merge commit **before** arming (§ Step 8 condition 4),
because arming locks the branch the instant the checks go green. Record it as arm-and-hand-off, noting
the required check's in-progress state at arm time; an observed run armed with `verify` still running,
and the queue landed the PR cleanly once `verify / conclusion` went green.

**Manual read-polling is the in-session alternative to arm-and-hand-off while the session stays
active.** "No way to block-until-landed" forbids a *blocking wait* — never `sleep` on GitHub in Bash
(§ Cloud session affordances) — not an on-demand *read*. The GitHub read surface (`pull_request_read`:
check-runs, `mergeStateStatus`, and ALL THREE comment surfaces) is **not** approval-gated even where
`send_later` / `subscribe_pr_activity` are, so a session that is still active — an interactive run with a
reachable operator, or one re-entered by any means — MAY drive the whole review cycle and merge gate by
polling that read surface on each re-entry: read the checks and comments, handle every comment, finalize
the report, arm auto-merge, and (since the same read reports `state: MERGED`) self-confirm the landing
when the queue lands it. Arm-and-hand-off stays the completion for a run that cannot re-enter at all;
this paragraph only records that a still-live session need not hand off blind, which is how an observed
run drove a PR to a confirmed merge after both self-wake tools returned "requires approval".

**Record the merge commit outside the in-PR report.** The squash merge SHA does not exist until the
merge completes, so it cannot appear in a report that was committed before the merge (condition 4
above). Read it from the PR merge event (`state,mergedAt,mergeCommit`) and report it to the operator;
the orchestrator collects the landing from the PR itself, not from a SHA embedded in the report body.

**Record nothing outside your own plan directory.** There is no status file, no ledger, no shared
table — the tree itself is the state, and the orchestrator records the landing at collect by reading
your report. Write your status and records to `doc/plans/{epic}/{plan-name}/` and nowhere else under
`doc/plans/`; a **declared-deliverable** edit to a shared lane doc is permitted — that is a
deliverable, not a record (§ Step 9 Bridge row).

**Your report is the channel back.** It must state the PR number and the outcome per deliverable —
including a run that ended **blocked or partial**, and why. (The merge commit is read from the PR
merge event and reported to the operator, not embedded here — see the merge-commit note above.) An
overstated outcome gets collected as done; an understated one gets picked up again.

The full rule, including how a row is created and later collected, is
[`doc/plans/cloud-bridge.md`](../../../doc/plans/cloud-bridge.md).

## Step 9 — Final step: verify this contract was followed

**The last committed action of every run.** Its report sections (this contract-check and the "what
have we learned" below) are written and pushed at Step 8 condition 4, as the final pre-merge commit,
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
| 4 Per-commit gate | Every commit touching `*.py` was preceded by a clean quality gate — a `total_issues: 0` / empty `errors[]` executor log, or the direct `./pw` tools each reporting clean (`ruff`/`mypy`/SPDX passed) |
| 4 Pushed | No unpushed commit remains (`git status -sb` reports no `ahead`) |
| 5 Build gate | Report states the git-derived Python-change verdict and the build outcome |
| 6 Verification sub-agent | Findings and dispositions in the report; **which of the two exits ended the loop** — named with the same `verifier-clear` / `budget-exhausted` token the report header carries, plus the `non-converging` qualifier where it applies (§ Report) — the **budget that applied** (five, or the plan's) with **every extension and who granted it**, and the round that stopped it. Where the budget ran out with an operator reachable, that the boundary question was **put to them** and what they answered; where it ran out headless, that fact and the fallback taken. On the verifier exit: **the verifier's own last answer** — never the author's verdict — and the **evidence stronger than a read** it rests on, named. On the budget exit: that fact, with everything A forbids **fixed** regardless and what closing each remaining B survivor would take. Either way: each survivor — and each behavioural finding left `deferred` — listed individually with its (a) proof or (b) bound and confirmation it was **re-put to the verifier** in the stopping round; whether the late rounds' findings were **narrower and not merely fewer**; the **residue to assume remains**; and `Outcome` still reporting the deliverables, not the loop (§ Step 6, "When the loop stops") |
| 7 PR cycle | PR exists; every comment dispositioned in the report; the participation table carries a verdict **and** a `Reopens?` value per reviewer, and every `silent` verdict records what its recovery check found. An `unreadable` verdict means condition 3 is NOT established — the row is reported as **not done**, whatever the merge outcome |
| 8 Merge gate | Conditions 1–4 and 6 met and auto-merge armed; where the base had advanced, the report names the shape used, the merge commit tested, and the gate's result on it (condition 2) — and a condition 2 that failed closed is reported as **not established**, with nothing armed. Either `state: MERGED` was confirmed after arming, **or** the session could not self-wake to watch the queue (§ Cloud session affordances) and delegated the landing to the orchestrator's collect — both are completed, neither is partial (§ Step 8). The merge commit is recorded to the operator, not in the pre-merge report |
| 8 Bridge | No **status or bookkeeping** write landed under `doc/plans/` outside this plan's own directory — no ledger, no status file, no other plan's directory was touched; a **declared-deliverable** edit to a shared lane doc (e.g. `cloud-bridge.md`, `README.md`, the plan template) is permitted — and the report carries the PR number and per-deliverable outcome the orchestrator will collect from |
| 9 This check | Its result appended to the report |
| 9 What have we learned | A contract-change proposal presented to the operator, or a recorded "none, because …" |

Any step that was skipped, or whose artifact is missing, is reported as **not done** — do not
retroactively narrate it as complete. If a step can still be completed, complete it and re-check.

**Re-verify every report claim about the working tree.** Claims about the *diff* are re-derived by the
sweeps in § Step 6; claims about the *filesystem* are not — and the run's own build gate mutates the
very tree the report describes. No gate can catch this, because the claim is about the filesystem
rather than the code: the suite stays green while the sentence goes false. An observed report stated
that `.plan/` carried only `marshal.json` and `project-architecture`, with no `logs/` and no `local/`.
That was true when written; by the time the build gate had run, the same tree held
`.plan/execute-script.py`, `.plan/temp/`, and a file under `.plan/local/logs/`.

**Re-verify every HISTORY claim too, whenever this run rebased.** A commit SHA quoted anywhere — a
prior `report-NN.md`, this run's own report, a commit message, the PR description — is a claim about
the branch under review, and a rebase makes every one of them false at once (§ Step 2, "A run resumed
in a NEW session"). It is the same shape as the tree claim above and equally invisible: the suite
stays green, the diff is unchanged, and only the citations rot. An observed run rebased nine commits
and left two documents naming SHAs that existed on no branch under review. Re-derive each against the
current branch at the moment of the claim.

So three claim classes, and only one is covered for free: **diff** claims are re-derived by the § Step
6 sweeps; **tree** and **history** claims are not, and are re-checked here.

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
   gh pr create --title "chore(cloud-plan-lane): {what changed}" --body-file {file}
   ```

   **Apply `skip-bot-review`.** A project-level skill change carries the label by default (§ Step 7):
   the scarce bot-review budget goes to the shipped bundles and to code. Its scrutiny is step 1 above
   — the operator approved this change before it was written. If the operator asks for a bot review
   on it instead, create the PR without the label and condition 6 applies as usual.

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

> **Verification loop exit:** `{exit}` [`, non-converging`]

**The schema is a primary exit plus an optional qualifier — not a three-value enum.** `{exit}` is
exactly one of **`verifier-clear`** or **`budget-exhausted`**, because § Step 6 defines exactly two
ways the loop ends. **`non-converging`** is a *qualifier* appended to either, and it is appended
whenever the late rounds' findings were not narrower — which § Step 6 already requires the stop record
to state. It is a qualifier rather than a third exit because it answers a different question: the exit
says *what stopped the loop*, the qualifier says *whether the loop was still finding things when it
stopped*. Both combinations are real — a budget can run out on a converging loop, and a verifier can
answer "nothing remains" on a loop whose previous round was still finding defects.

Write it exactly as `**Verification loop exit:** budget-exhausted, non-converging` or
`**Verification loop exit:** verifier-clear`. Use these same two tokens and this same qualifier in the
§ Step 6 stop record and the § Step 9 contract-check row; do not paraphrase them into other wording.

## Skills loaded
…

## Deliverables
Per deliverable: what was done, in which commit, and its verification state.

## Build gate
The `git diff --name-only origin/main...HEAD -- '*.py'` verdict, and the build result — or
"no Python changes, build skipped".

Then the stale-base re-verification (§ Step 8 condition 2): the `git rev-list --count HEAD..origin/main`
figure at the gate, and — when it was non-zero — which shape was used (merged on the branch and pushed,
or gated on a throwaway branch with the PR head left untouched), **the merge commit that was tested**,
and the gate's result on that merged tree. A zero count is recorded as the measurement it is ("base
current at the gate"), not left unstated: an absent line is indistinguishable from a check that was
never run. Where the condition failed closed — a failed fetch, a conflicting merge, a red merged-tree
gate — the report names the command that failed and states that condition 2 was **not established**.

## Findings
Every finding from the verification sub-agent, from CI, and from PR review — each with source,
description, and disposition (fixed / rejected-with-reason / deferred / **survivor**). An empty
section states what was checked to reach it.

Then the stop record (§ Step 6, "When the loop stops"):

- **which of the two exits ended the loop**, named with the header's own token (`verifier-clear` or
  `budget-exhausted`, plus `non-converging` where it applies) — the verifier's answer, or a spent budget no operator
  extended — the budget that applied (five, or the plan's), every extension granted and by whom, and
  which round stopped it. A budget exhausted with a reachable operator records the boundary question
  and its answer; one exhausted headless records that there was nobody to ask;
- on the **verifier exit**: **the verifier's own last answer**, since the run does not assert the stop
  on its own authority, and **the evidence stronger than a read** that answer rests on — the
  differential run, fuzz sweep, mutation campaign or branch enumeration, named;
- whether the late rounds' findings were **narrower and not merely fewer** — about the run's own
  report and plan documents rather than the shipped change — or were not: stated as the observation
  it is, never as a licence to stop;
- one row per **survivor, and per behavioural finding left `deferred`**, each either (a) proved
  equivalent, with the proof, or (b) bounded, with the bound and the promise it stays outside of, and
  each confirmed **re-put to the verifier** in the stopping round rather than carried forward unread;
- **what residue to assume remains** — the deliverables should be read as still carrying defects of
  the kind the last round found, and the report says so rather than implying the last round exhausted
  them;
- on the **budget exit**: that the rounds ran out and were not extended — naming which case it was,
  an operator who answered "stop" or no operator to ask — with everything A forbids fixed regardless,
  and what closing each remaining B survivor would take. `Outcome` is unaffected either way: it
  reports the deliverables, not the loop.

A run that fixed everything says so, and has no survivor rows.

⭐ **The exit belongs in the report HEADER, not only in this stop record.** `Outcome` reports the
deliverables and says nothing about the loop, so a run that stopped because it ran out of rounds
carries the same `Outcome: completed` as one that stopped on a verifier's all-clear — and `Outcome` is
what a collector reads. Naming the exit in the header (above) costs one line and makes the difference
visible without hunting for this section. **A `non-converging` loop is the case that most needs
saying**: the useful signal is not "verification finished" but *"each round is still finding defects at
the same rate, and the rate is not decaying."* An observed run reached its fourth round finding **more**
shipped-surface defects than its third, and a fifth party — an automated reviewer — then found a
fail-open none of the four had caught.

## Reviewer participation
The expected reviewer population **derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc,
cross-named by `.github/workflows/pr-agent.yml` — never a list transcribed here. One row per
reviewer, each verdict derived from the stored comment bodies (§ Step 7), never from a check state or
a summary:

| Reviewer (`author_login`) | Verdict (`reviewed` / `rate-limited` / `silent` / `unreadable`) | Reopens? (`yes` / `no` / `unknown`, blank when `reviewed`) | Body evidence / reason — for `unreadable`, the surface and the error, plus whatever positive control was taken |
|---|---|---|---|
| … | … | … | … |

State the coverage as N-of-M, and whether the § Step 8 shortfall disclosure fired and what it said.

Where a reviewer was `rate-limited` with `Reopens? yes`, add its **retry log** — one row per attempt,
each carrying the time, the notice the attempt drew, and the wait-plus-jitter that preceded it:

| # | Waited before it | Attempt time | Notice returned |
|---|---|---|---|
| … | window + jitter | … | … |

An attempt that was made and refused is different evidence from one that was never made, and only
this log distinguishes them. State the budget that applied (six, per § Step 7), how many attempts
were spent, and — for CodeRabbit on a PR without `skip-bot-review` — **which arm of § Step 8
condition 6 satisfied it**, in that condition's own words: `obtained`, `budget spent`, `unobtainable`,
`could not re-enter`, or `skip-bot-review` (out of scope). A record that cannot name the arm cannot be
checked against the gate.
Where a `silent` verdict triggered the recovery check (§ Step 7), record what the check found and
whether the reviewer was recovered. Where a verdict is `unreadable`, state plainly that merge-gate
condition 3 was **not established** and say whether the merge proceeded anyway on an operator
instruction — an overridden gate is reported as overridden, never as met.

## Cost
What the run cost, each figure carrying its **population** — a bare number that merely looks
comparable is worse than none:

- **Tokens:** … (source named) — or "not available to the agent in this session", stated plainly.
- **Wall-clock:** … (source named — e.g. run start/end timestamps).
- **Population:** what these figures count (e.g. "this single Claude Code cloud session's usage as the
  harness counts it"). ⛔ This is **NOT comparable** to a plan-marshall `metrics.toon` total: a
  `metrics.toon` total counts the orchestrator-plus-agent dispatch tree under plan-marshall's own
  per-task billing boundary, which a single interactive cloud session does not share. If the figures
  cannot be made comparable, **say so here** rather than presenting a number that implies parity.

## Contract check (Step 9)
Per-step verdict, and any step reported as not done. Which GitHub access path was used, and which
branch form was used (harness-assigned or run-created). A cloud run **never owes** a
`/sync-plugin-cache` — it is a machine-local build step, not a debt a cloud run records (§ Scope and
precedence).

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
- **A reachable operator may be asked; a headless run may not wait for one.** This lane is written for
  autonomous execution, but a run sometimes executes in an interactive main session with the operator
  reachable. When that is so, the run **MAY** escalate a decision via `AskUserQuestion`, recording both
  the question and its answer in the report — a conversation event is not a committed artifact, so the
  report is its only durable trace. Escalation is a permitted option in the reachable case, with the
  **one exception** below. A **headless** run, or a **dispatched leaf** that cannot reach the operator
  at all, never waits: it takes the plan's stated autonomous fallback where the plan states one, and
  this skill's own stated fallback otherwise — so the headless path always remains a complete,
  unblocked outcome.

  **The exception: the verification loop's round budget, where the ask is an obligation rather than an
  option** (§ Step 6, "When the loop stops"). A reachable operator IS asked when the budget runs out,
  because the alternative is a run silently deciding for itself how much verification is enough. This
  obligation does **not** depend on a plan offering a re-scope or naming a STOP CONDITION: the budget
  defaults to five whether or not a plan sets one, so the default case has no plan-stated fallback to
  key on. The headless half is unchanged and non-negotiable — no operator to reach means the fallback,
  never a wait.

  **Reachability is decided by whether `AskUserQuestion` can actually be issued and answered, not by
  how the run was launched.** A run that cannot issue it is headless. A run that can issue it but is
  unattended — nobody is watching the session — is reachable by the letter and useless by the fact, so
  the obligation carries a bound: **ask, and if no answer has arrived by the time the run would
  otherwise idle, take the fallback and record in the report both that the ask was issued and that it
  went unanswered.** An ask that blocks forever is strictly worse than stopping with survivors
  disclosed, which is the same reasoning the headless carve-out rests on.
- **Never write outside the repository** — this lane has no business in `.plan/` or `~/.claude/`.
