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

Every other rule in `CLAUDE.md` still binds — in particular the documentation standards and the
one-command-per-Bash-call discipline. The closed branch-prefix set binds for branches this run
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
  the value — and a sweep that greps for the way the primary claim happens to be phrased finds the
  restatement that reads like it and silently misses the rest. An observed run's single value change (a
  `SKILL.md`-only path widened to a `SKILL.md`-plus-`standards/*.md` set) had three stale consumers of
  three different kinds — an echo-field enumeration, a check description, and a schema placeholder — and
  no single reviewer caught all three: the phrase-oriented sub-agent sweep found the enumeration while
  the automated PR reviewer found the description and the placeholder. A later run surfaced the
  highest-risk kind of all: a **test stub/fixture that hardcodes the retired value and still passes**,
  because it is driven by a synthetic double rather than the real code path (a `_StubAttributor`
  encoding the old `(prefix, module)` claim), so neither the local build gate nor CI ever fails on it —
  it survived two sub-agent sweeps and was caught only by a third that explicitly grepped `*.py`
  fixtures. So the sweep covers **test fixtures and stubs (`*.py`), not only prose and docs**; name the
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
  for re-checking. Its answer is what ends the loop (§ "When the loop stops"), so it is asked of the
  verifier here rather than decided by the author afterwards.

Then:

- **Findings that are real** → fix them, then re-dispatch. A verification pass that found a defect
  has not finished — unless conditions **A** and **B** permit that finding to be left open, which is
  narrow and separately justified (§ "When the loop stops", at the end of this step).
- **Findings you reject** → record the finding *and the reason for rejecting it* in the report. A
  dismissed finding is still evidence.
- Every finding — fixed, rejected-with-reason, deferred to a named follow-up, or left open as a
  **survivor** — goes in the run report (§ Report). A *deferred* finding is real and unfixed here;
  a *survivor* is one the run argues needs no fixing at all (§ "When the loop stops").

**A fix is a change, so it gets the same beyond-diff sweep the original change got.** The sweep above
is written against the diff under review; by the second round the diff under review is largely the
*previous round's fixes*, and the sweep that matters is over what those fixes made false elsewhere. So
before re-dispatching, list the claims your fix changed — the value, the ordering, the count, the
mechanism it renamed — and sweep each one's restatements the same way: by **consumer kind** (naming
each kind a changed value can take — prose, docs, tests, `*.py` fixtures and stubs — and sweeping for
each in turn, per the sub-agent instruction above), exactly as you did for the original change.

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

The two obligations below are part of that same per-round sweep, not a separate pass done once at
the end. Both are checked **before every re-dispatch and again before the merge gate**.

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

These three exist because one run paid for them: across four verification rounds, each round's fixes
landed at the site the finding named and not at the sites restating the same claim — twice in the run
report's own findings table.

### When the loop stops

"Re-dispatch until a round finds nothing" is not a terminating rule: a round can always probe one
more mutation, one more boundary, one more restatement. An observed run reached **twelve** rounds,
eleven of which found a defect in the previous round's fix, and concluded that *"no findings" is not
a state this process reaches*.

Two conditions govern what a round may leave open. Call them **A** and **B** (§ Step 8's merge gate
has its own numbered conditions; these are not those).

**A — nothing false is left.** A finding that some STATEMENT is false — a comment, a docstring, a
bundle doc, a test's own description, a report figure, the PR description — is **never** left open,
wherever it lives and whether or not it executes. Those are fixed. This step's beyond-diff sweep and
its ⛔ on invented rationales exist to produce exactly these findings, and a rule that let them ship
would cancel both.

**B — every behavioural finding left open is a characterised survivor.** For a finding about
behaviour under some input — a mutant, an edge case, a shape no test covers — the loop may leave it
open only when the run can state either

> **(a)** a proof that it cannot change what the deliverable does, or
> **(b)** the bound on what it *can* reach, and the promise it stays outside of — that promise named
> in the plan's own terms.

Survivors are listed individually; a bulk mention is not a disclosure. **A finding that is both — a
false statement AND a behavioural defect, which the commonest ones are — is governed by A.**

⛔ **Whether A and B are met is the VERIFIER's call, not the author's.** The dispatch checklist above
puts it to the round directly: *does anything you found remain that A or B forbids leaving open?* A
**no** is what permits the stop; a **yes** earns another round. Honour the answer either way. The
author is the party motivated to stop, and in the run above **three** of the tests written to close
previously-found gaps were themselves vacuous — they passed against the fixed code *and* against the
defect they named. An author polling their own work for permission to stop will get it.

**A round budget, declared before the first dispatch.** A and B can go unmet round after round; on
the run above they still were at round twelve, and its own conclusion was that continuing would find
more. So the run states its maximum number of rounds **up front**, before it knows what the rounds
will say — a budget chosen at the moment of wanting to stop is not a budget.

Exhausting it with the verifier still answering **yes** is a **STOP CONDITION**, and this is its
stated autonomous fallback: **end the loop, record `Outcome: partial`, and disclose per instance every
finding A or B forbids, each with what closing it would take.** A run whose operator is reachable MAY
instead escalate the choice (§ "Rules that outrank convenience" — permitted there, never required).
Either way the round budget, the verifier's last answer, and every still-open finding are on the
record.

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

**Suppress bot review only when the PR has no reviewable footprint.** Bot-review capacity is contended
across this repository and is regularly exhausted; a diff with nothing a reviewer can act on spends
budget another PR needs. But **a skill is code, and is reviewed as code**: any change under
`.claude/skills/**` or `marketplace/bundles/**` — a `SKILL.md`, a workflow doc, a script — keeps its
review exactly as a `*.py` change does. It is prose, but it is *behavioural* prose that governs how
every future run acts, which is precisely what a reviewer should see; do **not** treat it as
documentation.

So `skip-bot-review` applies to **one** case only: a diff with **no `*.py`, no `.claude/skills/**`,
and no `marketplace/bundles/**`** — genuinely nothing but `doc/**` prose, run reports, or ledger
bookkeeping. This is narrower than Step 5's build skip: a skill- or bundle-only change **skips the
local build** (the gate is `*.py`-only) yet **still gets reviewed** — build and review are different
questions. Determine it from the same git evidence Step 5 uses, and apply the label **at creation** —
applying it afterwards is too late, because the bots are triggered by the PR opening:

```bash
gh pr create --label skip-bot-review --fill
```

The rule in one line: **only a PR with no `*.py`, no skill, and no bundle change gets
`skip-bot-review`.** Anything that touches code keeps its review — and a skill is code. This
suppresses waste, never scrutiny.

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

#### A `silent` verdict is not terminal until the recovery check says so

Silence has several causes that look identical from the comment surfaces — the bodies are empty, which
is what `silent` means — and **one of them is recoverable in a single comment**. So `silent` is a
provisional verdict: before disclosing it, establish *why*, and act on the answer.

Check whether the reviewer's workflow ran at all, and split on it:

- **No run at all** → the reviewer never got the event. It is not rate-limited; it was not invited.
  Post the registry's declared `trigger_comment` (`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`)
  as a PR comment, re-read the surfaces, and record the *result* — a review that arrives this way is
  `reviewed` like any other.
- **A run that concluded `skipped`, or failed** → a guard or a failure suppressed it, and no comment
  will change that. Record the run's conclusion as the reason and disclose.

This adds a cheap recovery attempt before the disclosure. It is **not** a gate: if the trigger
produces nothing, disclose the shortfall and carry on exactly as § Step 8 condition 4 says.

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

**The merge is gated on conditions 1–3 below. Condition 4 is a disclosure the run performs before
arming auto-merge — it is not a gate on the merge. Merge only when conditions 1–3 hold:**

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
     **is disclosed** to the operator — the same disclose-not-block treatment condition 4 gives a
     review-coverage shortfall. State it in words before arming auto-merge; never hold the merge for it.

   When `mergeStateStatus` is `BLOCKED`, derive **which** context blocks from (required contexts ∩
   non-green contexts) — never from whichever pending status is loudest. A visible, non-required
   pending status (a prominent bot comment, an informational badge) is not the blocker just because it
   is salient; the blocker is the unsatisfied **required** context, which may be quietly `in_progress`
   or absent from the head. A run once disclosed a non-required pending check as "the blocker" while
   the actually-required check was still running — the operator disclosure named the wrong cause.
   Derive the blocker from the intersection, and never promote a non-required pending status to "the
   blocker" in an operator disclosure.

2. **Every PR comment is handled** — fixed or answered on the thread. No open, unaddressed comment.

3. **The report is finalized and pushed** — run Step 9 now and commit its report artifacts (the
   contract-check table and the "what have we learned" section) as the **last pre-merge commit**,
   *before* you arm auto-merge. This ordering is load-bearing, not cosmetic: the report lands *in
   this PR*, and the instant the branch enters the merge queue a protected-branch hook rejects every
   further push to it ("Branches that are queued for merging cannot be updated" — observed). A report
   finalized after arming can never reach this PR, forcing a second follow-up PR just to complete the
   record. So Step 9's report sections are written here; only the post-merge landing confirmation
   (below) happens after.

4. **A review-coverage shortfall is disclosed to the operator — this is a disclosure step, not a
   merge condition.** From the per-reviewer participation record (§ Step 7), read the verdict of every
   expected reviewer. When **any** expected reviewer's verdict is not `reviewed`, state the shortfall
   and its reason to the operator, explicitly and in words, *before* arming auto-merge — carrying each
   reviewer's `Reopens?` value (§ Step 7), since that is what tells the operator whether the gap was
   ever closable. For example: "Review coverage: 1 of 3 — `cuioss-review-bot` reviewed; `coderabbitai`
   rate-limited, reopens in 27 minutes; `sourcery-ai` rate-limited on a size ceiling, does not reopen."
   **A run that merges on 1-of-3 must _say_ 1-of-3.**

   A `silent` verdict reaches this disclosure only after its recovery check (§ Step 7) — so what is
   disclosed here is a shortfall that survived an attempt to fix it, not merely one that was noticed.

   ⛔ **This is a disclosure requirement, and it is NOT a block — the two must never be collapsed.**
   The gate does **not** hold the merge open, does **not** wait for the shortfall to clear, and does
   **not** fail because a reviewer was rate-limited or silent. Rate limits and quotas are routine,
   outside our control, and blocking on them would strand every landing behind a bot's quota — which
   is explicitly the wrong direction. **The defect this closes is the _silence_, not the shortfall:** a
   run that proceeds on partial coverage is fine; a run that proceeds on partial coverage *without
   saying so* is the failure. The shortfall therefore changes only what the run **says**, never
   whether it **merges**. Once the shortfall is stated, arm auto-merge exactly as full coverage would
   — conditions 1–3 are the only gates on the merge itself.

Then merge (the repository uses a merge queue, so enable auto-merge and let the queue land it):

```bash
gh pr merge {N} --squash --auto
```

**Arming auto-merge is a one-way door — the branch locks the instant you arm.** On this merge-queue
repository, the moment the required contexts are green, arming adds the PR to the merge queue and a
protected-branch hook then rejects every further push ("Branches that are queued for merging cannot be
updated"). **Disabling auto-merge does not release the lock, and converting the PR to draft does not
release it** — both were tried on one run, both left the branch queued. Two rules follow:

- **Push everything that must land in this PR _before_ you arm** — the report above all (condition 3).
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
conditions 1–3, (b) armed auto-merge, and (c) handed the `MERGED` confirmation to the orchestrator's
collect step, which reads it from the PR merge event. Record the outcome as **completed with the
landing delegated** — not `partial`, and not a failure. A run that armed a green PR into the queue and
merely could not self-wake to watch it has done everything the lane asks; reading its own inability to
watch the queue as a failed run is the mistake this paragraph prevents. (A run that *can* self-confirm
still does — this is not licence to assert a merge that was never read back.)

**When there is no self-wake AND a required check is still `in_progress` at the gate, arm anyway — the
merge queue is the enforcer, not this session.** Condition 1's "BLOCKED → wait" assumes the run can
wait for the required check to conclude; a run with no self-wake cannot, and holding the arm until green
would strand a fully-ready PR indefinitely with no one to land it. On this merge-queue repo the queue
admits a PR only when the ruleset's required contexts pass and re-verifies on `merge_group`, so arming
auto-merge while the required build is still running does **not** merge a red PR — it defers the
required-green gate to the queue, exactly as arming does when the PR is already green (§ Cloud session
affordances, "Auto-merge arming"). The one ordering that stays non-negotiable: conditions 2–3 must be
met and the report committed as the last pre-merge commit **before** arming (§ Step 8 condition 3),
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
merge completes, so it cannot appear in a report that was committed before the merge (condition 3
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
| 4 Per-commit gate | Every commit touching `*.py` was preceded by a clean quality gate — a `total_issues: 0` / empty `errors[]` executor log, or the direct `./pw` tools each reporting clean (`ruff`/`mypy`/SPDX passed) |
| 4 Pushed | No unpushed commit remains (`git status -sb` reports no `ahead`) |
| 5 Build gate | Report states the git-derived Python-change verdict and the build outcome |
| 6 Verification sub-agent | Findings and dispositions in the report; the **round budget declared up front**, the round that stopped the loop, and **the verifier's own last answer** — never the author's verdict; each survivor listed individually with its (a) proof or (b) bound, and confirmation that every still-open survivor was **re-put to the verifier** in that round; a loop that ended on the exhausted budget recorded as `Outcome: partial` with every forbidden finding disclosed (§ Step 6, "When the loop stops") |
| 7 PR cycle | PR exists; every comment dispositioned in the report; the participation table carries a verdict **and** a `Reopens?` value per reviewer, and every `silent` verdict records what its recovery check found |
| 8 Merge gate | Conditions 1–3 met and auto-merge armed. Either `state: MERGED` was confirmed after arming, **or** the session could not self-wake to watch the queue (§ Cloud session affordances) and delegated the landing to the orchestrator's collect — both are completed, neither is partial (§ Step 8). The merge commit is recorded to the operator, not in the pre-merge report |
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
`.plan/execute-script.py`, `.plan/temp/`, and a file under `.plan/local/logs/`. Only tree claims need
this re-check — diff claims are already covered.

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

   **Do not apply `skip-bot-review`.** This PR changes a skill, and a skill is code that gets reviewed
   (§ Step 7). The change is behavioural — it governs how future runs act — so the automated reviewers
   see it like any other code change.

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
description, and disposition (fixed / rejected-with-reason / deferred / **survivor**). An empty
section states what was checked to reach it.

Then the stop record (§ Step 6, "When the loop stops"):

- the round budget declared before the first dispatch, which round stopped the loop, and **the
  verifier's own last answer** — the run does not assert the stop on its own authority;
- one row per **survivor**, each either (a) proved equivalent, with the proof, or (b) bounded, with
  the bound and the promise it stays outside of, and each confirmed **re-put to the verifier** in the
  stopping round rather than carried forward unread;
- when the loop ended on the exhausted budget instead, that fact, and what closing each still-open
  finding would take. That run's `Outcome` is `partial`.

A run that fixed everything says so, and has no survivor rows.

## Reviewer participation
The expected reviewer population **derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc,
cross-named by `.github/workflows/pr-agent.yml` — never a list transcribed here. One row per
reviewer, each verdict derived from the stored comment bodies (§ Step 7), never from a check state or
a summary:

| Reviewer (`author_login`) | Verdict (`reviewed` / `rate-limited` / `silent`) | Reopens? (`yes` / `no` / `unknown`, blank when `reviewed`) | Body evidence / reason |
|---|---|---|---|
| … | … | … | … |

State the coverage as N-of-M, and whether the § Step 8 shortfall disclosure fired and what it said.
Where a `silent` verdict triggered the recovery check (§ Step 7), record what the check found and
whether the reviewer was recovered.

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
  reachable. When that is so **and** a plan offers a re-scope, or names a STOP CONDITION with an
  autonomous fallback, the run **MAY** escalate the decision via `AskUserQuestion`, recording both the
  question and its answer in the report — a conversation event is not a committed artifact, so the report
  is its only durable trace. A **headless** run, or a **dispatched leaf** that cannot reach the operator
  at all, takes the plan's stated autonomous fallback. Escalation is a permitted option for the reachable case, **never** a requirement — so the
  headless path always remains a complete, unblocked outcome.
- **Never write outside the repository** — this lane has no business in `.plan/` or `~/.claude/`.
