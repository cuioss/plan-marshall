# Tools Integration CI API Contract

Shared TOON output formats and API specifications for all CI operations.

---

## Output Format: TOON

All scripts output TOON format for consistency and easy parsing.

**Structure**:
```toon
status: success|error
operation: <operation_name>
{operation_specific_fields}

{optional_tables}
```

---

## Health Operations (ci_health.py)

### detect

Detect CI provider from git remote.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health detect
```

**Success Output**:
```toon
status: success
provider: github|gitlab|unknown
repo_url: https://github.com/org/repo
confidence: high|medium|none
```

**Error Output**:
```toon
status: error
error: Failed to detect provider
context: git remote get-url origin failed
```

---

### verify

Verify CLI tools are installed and authenticated.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health verify [--tool TOOL]
```

**Success Output** (all tools):
```toon
status: success
all_required_available: true

tools[3]{name,installed,authenticated,version}:
git	true	true	2.43.0
gh	true	true	2.45.0
glab	false	false	-
```

**Success Output** (specific tool):
```toon
status: success
tool: gh
installed: true
authenticated: true
version: 2.45.0
```

---

### status

Full health check combining detect and verify.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health status
```

**Success Output**:
```toon
status: success
provider: github
repo_url: https://github.com/org/repo
confidence: high
required_tool: gh
required_tool_ready: true
overall: healthy|degraded|unknown

tools[2]{name,installed,authenticated}:
git	true	true
gh	true	true
```

---

### verify-all

Live verification of CI provider and tools. Returns the current authenticated tools, git presence, provider, and repo URL. Nothing is persisted — tool/auth status is cheap to verify on demand and varies per machine. Provider identity and repo URL are read from `providers[]` in marshal.json.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health verify-all
```

**Success Output**:
```toon
status: success
provider: github
repo_url: https://github.com/org/repo
authenticated_tools[2]:
  - git
  - gh
git_present: true
```

---

## PR Operations (github_ops.py / gitlab_ops.py)

Every PR subcommand returns the standard envelope: success shape (`status: success`, `operation: {op}`, plus the identifiers listed in the "Response fields" column) and error shape (`status: error`, `operation: {op}`, `error: ...`, `context: {cli exit reason}`).

**Bodies are never passed as arguments.** Every body-bearing verb takes `--plan-id` (plus an optional `--slot`) and reads the body from the scratch file its paired `prepare-body` / `prepare-comment` call allocated. There is no `--body` and no `--body-file` argument on this surface; a plan-less caller passes `--plan-id NO_PLAN`. See [`../SKILL.md`](../SKILL.md) § "The `NO_PLAN` sentinel — one plan-less convention for every `--plan-id` verb".

| Subcommand | Required args | Optional flags | Response fields |
|------------|---------------|----------------|-----------------|
| `pr prepare-body` | `--plan-id` | `--for create\|edit`, `--slot` | `path` |
| `pr prepare-comment` | `--plan-id` | `--for reply\|thread-reply`, `--slot` | `path` |
| `pr create` | `--title`, `--plan-id` | `--slot`, `--base` (default: repo default), `--head`, `--draft`, `--label` (repeatable) | `pr_number`, `pr_url` |
| `pr view` | — (uses current branch) | _at most one of_ `--pr-number` _or_ `--head` | `pr_number`, `pr_url`, `state`, `title`, `head_branch`, `base_branch`, `is_draft`, `mergeable`, `merge_state`, `review_decision` |
| `pr list` | — | `--head {branch}`, `--state open\|closed\|all` (default `open`) | `total`, `state_filter`, `head_filter`, `prs[N]{number,url,title,state,head_branch,base_branch}` |
| `pr reply` | `--pr-number`, `--plan-id` | `--slot` | `pr_number` |
| `pr resolve-thread` | `--thread-id` (GitLab also requires `--pr-number`) | — | `thread_id` |
| `pr thread-reply` | `--pr-number`, `--thread-id`, `--plan-id` | `--slot` | `pr_number`, `thread_id` |
| `pr reviews` | `--pr-number` | — | `pr_number`, `review_count`, `reviews[N]{user,state,submitted_at}` |
| `pr comments` | `--pr-number` | `--unresolved-only` | `provider`, `pr_number`, `total`, `unresolved`, `comments[N]{id,author,body,path,line,resolved,created_at}` |
| `pr wait-for-comments` | `--pr-number` | `--timeout` (default 300), `--interval` (default 30) | `pr_number`, `timed_out`, `duration_sec`, `polls`, `baseline_count`, `final_count`, `new_count`, `rate_limited_bots[N]{bot_kind,rate_limit_class,eta}`, `movement_matched_bots[N]{bot_kind}`, `detector_answerable`, `unanswerable_reason` |
| `pr update-branch` | _exactly one of_ `--pr-number` _or_ `--head` | — | `pr_number` |

### Provider Field Mapping

The PR operations normalize responses from `gh` (JSON) and `glab` (JSON) into the same shape. Mappings:

- **Top-level identifiers**: `pr_number` ← `.number` (GitHub) / `.iid` (GitLab); `pr_url` ← `.url` / `.web_url`; `state` lower-cased ("opened" → "open"); `title`, `head_branch` ← `.headRefName` / `.source_branch`; `base_branch` ← `.baseRefName` / `.target_branch`; `is_draft` ← `.isDraft` / `.draft`; `mergeable` ← `.mergeable` / `.merge_status`; `merge_state` ← `.mergeStateStatus` (GitHub only); `review_decision` ← `.reviewDecision` / `.approved_by` (mapped).
- **`pr list` CLI differences**: GitHub `gh pr list --head {branch} --state open|closed|all --json number,url,...`; GitLab `glab mr list --source-branch {branch} --state opened|closed|all --output json`.
- **`pr resolve-thread`**: GitHub uses the GraphQL `resolveReviewThread` mutation with a self-contained thread node id (e.g. `PRRT_kwDO...`), so `--pr-number` is ignored; GitLab uses REST `PUT discussions/:id` and requires both `--pr-number` and the discussion id.
- **`pr thread-reply`**: GitHub uses GraphQL `addPullRequestReviewComment` with `inReplyTo` set to the comment node id (the PR node id is fetched internally); GitLab uses REST `POST discussions/:id/notes` and does not require a PR node id.
- **`pr comments` field mapping**: `id` ← `comments.nodes[].id` / `notes[].id`; `author` ← `author.login` / `author.username`; `body` ← `body`; `path` ← `reviewThreads.nodes[].path` / `position.new_path`; `line` ← `reviewThreads.nodes[].line` / `position.new_line`; `resolved` ← `isResolved` / `resolved`.
- **`pr wait-for-comments` field mapping**: the poll counters (`baseline_count` / `final_count` / `new_count`) are provider-agnostic — derived from the `pr comments --unresolved-only` unresolved count. The completion predicate is TWO-ARMED: the count-growth arm above fires for a bot that appends a new comment per review (`participation_requires_update: false`), while a movement arm fires for a bot that re-reviews by EDITING one persistent comment in place (`participation_requires_update: true`), keying on the LATER of that comment's `updated_at` / `created_at` moving strictly past the wait-start. `movement_matched_bots[]` names one `{bot_kind}` record per bot the movement arm matched (empty when none), so a caller can tell WHICH bot's edit ended the wait rather than inferring it — and a `timed_out: false` return with `new_count == 0` is the normal shape for an in-place re-review, not an anomaly. `detector_answerable` / `unanswerable_reason` report whether the await COULD have succeeded at all: `false` means the observable could never move (the bot registry declares no bot kinds, or every registered bot declares an empty `participation_evidence`), which is a structurally different operator signal from a genuine timeout where answerable bots simply stayed silent. The signal is derived from the REGISTRY alone and never from the observed comment set, so a wait that merely starts with no comments on the PR reports `detector_answerable: true`. `rate_limited_bots[]` is additive and bot-agnostic: it carries one `{bot_kind, rate_limit_class, eta}` record per REGISTERED reviewer bot whose newest comment on the PR is a rate-limit / service notice posted in place of a review, and is empty (the default) when no registered bot is rate-limited. No bot is named in the detection path — the bot set and each bot's author login are derived from the per-bot registry docs under `automatic-review/standards/{bot_kind}.md`, and the notice itself is recognised by a structural two-part recogniser (a limit-exceeded statement AND a notice shape) paired with that bot's registry `ignore_patterns`.

  The per-field table below scopes to `rate_limited_bots[]` ONLY — it does not describe `movement_matched_bots[]`, whose own single `bot_kind` field names a bot that PARTICIPATED (its comment moved), the opposite of a refusal:

  | `rate_limited_bots[]` field | Meaning |
  |-------|---------|
  | `bot_kind` | Registry key of the refusing bot. |
  | `rate_limit_class` | That bot's registry `rate_limit_class`: `awaitable_window` (a rolling window that reopens on its own — awaiting the reset is productive), `hard_quota` (a budget that does not reopen on a useful timescale — awaiting only burns budget), or `unknown` (no refusal observed for this bot). `unknown` is the FAIL-CLOSED default: a caller MUST NOT await a bot whose refusal shape has never been observed. |
  | `eta` | The reset time the notice itself stated, extracted via that bot's registry `rate_limit_eta_patterns`, or `""` when the notice stated none. An empty `eta` means *unknown*, never *reopens now*. |

  The list is per-bot and class-bearing by design: a single boolean can say neither WHICH bot refused nor whether waiting for it is worth anything, and those answers differ per bot. Detection is best-effort and never alters poll behaviour — a failed post-poll comment fetch leaves the list empty. On GitLab no registered-bot detection runs, so the list is always empty there.

---

## CI Operations (github_ops.py / gitlab_ops.py)

### checks status

Check CI status for a pull request.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks status \
    --pr-number 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |

**Success Output**:
```toon
status: success
operation: ci_status
pr_number: 123
overall_status: pending|success|failure
check_count: 3
elapsed_sec: 45

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	in_progress	-	45	https://github.com/org/repo/actions/runs/112	CI
lint	completed	failure	30	https://github.com/org/repo/actions/runs/113	Lint
```

**Overall Status Logic**:
- `success`: All checks completed with success
- `failure`: Any check completed with failure
- `pending`: Any check still in progress

---

### checks wait

Wait for CI checks to complete.

**Command**:
```bash
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks wait \
    --pr-number 123 \
    [--timeout 300] \
    [--interval 30]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |
| `--timeout` | No | Max wait time in seconds (default: 300) |
| `--interval` | No | Poll interval in seconds (default: 30) |

**Success Output**:
```toon
status: success
operation: ci_wait
pr_number: 123
final_status: success|failure
duration_sec: 95
polls: 4
elapsed_sec: 95

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	completed	success	90	https://github.com/org/repo/actions/runs/112	CI
lint	completed	success	30	https://github.com/org/repo/actions/runs/113	Lint
```

**Timeout Output**:
```toon
status: error
operation: ci_wait
error: Timeout waiting for CI
pr_number: 123
duration_sec: 300
last_status: pending

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	in_progress	-	300	https://github.com/org/repo/actions/runs/112	CI
lint	completed	success	30	https://github.com/org/repo/actions/runs/113	Lint
```

---

### checks pull-request-runs

Report whether ANY `pull_request`-event workflow run exists for the PR's head branch — the PR-wide
observable behind the `not_triggered` review-participation state. Pure read: it files nothing, waits
for nothing, and mutates nothing.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks pull-request-runs \
    --pr-number 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--pr-number` | Yes | PR number |

**Provider API shape** — backed by the Actions **runs** collection, not by the checks/statuses surface
the sibling `checks status` / `checks wait` verbs read:

| Aspect | GitHub | GitLab |
|--------|--------|--------|
| PR read | `pr view` (to resolve the head branch) | — |
| Runs read | `gh api --paginate --slurp repos/{owner}/{repo}/actions/runs?branch={head_branch}&per_page=100` | — |
| Predicate | a run whose `event` is `pull_request` exists in the collection | — |
| Availability | supported | **unsupported — explicit refusal** |

`--paginate --slurp` is load-bearing rather than incidental. Without `--slurp`, `gh api --paginate`
emits one JSON document **per page** concatenated into a single stream, which is not valid JSON as a
whole: a parse either raises or — worse — silently decodes only the first document. A PR whose runs
spilled onto page two would then read as zero runs and be misreported as `not_triggered` precisely on
the busy PRs where a review matters most. `--slurp` wraps the pages into one array whose elements each
carry their own `workflow_runs` list, and the handler concatenates them.

**Success Output**:
```toon
status: success
operation: pull_request_runs
provider: github
pr_number: 123
head_branch: feature/example
run_count: 14
pull_request_run_count: 6
has_pull_request_run: true
not_triggered: false
```

| Field | Meaning |
|-------|---------|
| `head_branch` | The PR's head branch, resolved from the PR read; the branch the runs collection is keyed on. |
| `run_count` | Every workflow run recorded for that branch, whatever triggered it. |
| `pull_request_run_count` | The subset whose `event` is `pull_request`. |
| `has_pull_request_run` | The predicate: at least one `pull_request`-event run exists. |
| `not_triggered` | The exact complement of `has_pull_request_run`. Both are carried because callers read the question in both polarities and the participation state's own name is worth stating positively. |

**The predicate is existence only.** No `conclusion` is consulted, so a `pull_request` run that exists
and concluded `skipped` yields `not_triggered: false` — the workflow *was* triggered and declined to do
work, which is a different fact from nothing having run at all. No timestamp is consulted either.
And `mergeable_state` is never read, returned, or branched on: GitHub computes mergeability
asynchronously and reports `UNKNOWN` while it is still computing, so a participation state keyed on it
would depend on *when* the question happened to be asked rather than on what happened.

**Two failure modes fail loud, never into `not_triggered: true`:**

```toon
status: unconfigured
operation: pull_request_runs
provider: github
detail: <gh auth failure reason>
```

An unauthenticated `gh` returns the typed `unconfigured` status — collapsing it into
`not_triggered: true` would report every PR as never having triggered a review. A failed runs fetch
likewise returns the standard error envelope (`operation: pull_request_runs`): "the run list was never
read" and "the run list is empty" are distinct facts, and conflating them would claim the review bots
were never triggered on evidence nobody gathered.

**GitLab returns an explicit refusal**, not silence and not a guessed equivalent:

```toon
status: error
operation: pull_request_runs
error: "unsupported on GitLab: the pull_request-event run observable is GitHub-specific ..."
context: pr_number=123
```

The verb's parser lives in the shared `ci_base.build_parser`, so the token resolves on both providers;
GitLab registers a handler that names the provider-capability gap rather than letting the token surface
as an unrecognised subcommand, which would misattribute the gap as a parser defect. The gap is genuine:
GitLab distinguishes a merge-request pipeline by its `source` (`merge_request_event`) on a different
endpoint, and the detached-vs-branch pipeline distinction does not map one-to-one onto "a
`pull_request`-event run exists". Inferring an equivalent would yield a `not_triggered` verdict from a
signal that does not mean what the caller thinks it means, so `not_triggered` is derivable on GitHub
only until the mapping is deliberately designed.

Both entry points — this abstraction verb and `github_pr pull_request_runs` — call ONE shared handler
(`github_ops.pull_request_runs_result`), so they cannot drift into different answers to the same
question. The consumer-side use is documented in
[`pr-review-operations.md`](pr-review-operations.md) § "The widened participation taxonomy".

---

## CI Failure Log Download & Filtering

When one or more CI checks complete with `result: failure`, the `checks status` and `checks wait` operations augment each failing entry with the on-disk paths of its downloaded raw log and its filtered error-extraction variant. The raw download and the parse/filter pass are two distinct provider operations; both persist under the plan-scoped artifact tree so retrospectives and triage can read the logs offline.

### Download operation

Downloads the raw failing-job log for a single workflow run, keyed by `run_id`.

| Aspect | GitHub | GitLab |
|--------|--------|--------|
| CLI invocation | `gh run view {run_id} --log-failed` | `glab ci trace {run_id}` |
| Source | Failed-job log lines for the run | Job trace for the run |

The downloaded raw log is written to `artifacts/ci-runs/{run_id}/{slug}.log`, where `{slug}` is the failing check's name slugified (lowercased, non-alphanumeric runs collapsed to `-`, e.g. check `verify / verify` → slug `verify-verify`). The absolute (plan-relative) path is surfaced as the per-entry `log_file` field.

### Parse/filter operation

Reads the raw `{slug}.log` and produces a filtered error-extraction variant containing only the error-relevant lines plus surrounding context. The output is written to `artifacts/ci-runs/{run_id}/{slug}.filtered.log` and surfaced as the per-entry `filtered_log_file` field.

The line-selection strategy is governed by the `--error-style` selector:

| `--error-style` | Selection heuristic |
|-----------------|---------------------|
| `maven` | Lines matching Maven failure markers (`[ERROR]`, `BUILD FAILURE`, `Tests run:` with `Failures`/`Errors` > 0, `<<< FAILURE!`, `<<< ERROR!`) plus N context lines. |
| `gradle` | Lines matching Gradle failure markers (`FAILED`, `> Task ... FAILED`, `BUILD FAILED`, `What went wrong:`, stacktrace `Caused by:`) plus N context lines. |
| `npm` | Lines matching npm/node failure markers (`npm ERR!`, `FAIL `, `✕`, `AssertionError`, `Error:`) plus N context lines. |
| `generic` | **Default.** Lines matching the generic heuristic regex `ERROR|FAIL|Exception|Traceback` (case-insensitive) plus N context lines. Used when no style is given or the failing job's build system is unknown. |

`N` is the symmetric before/after context-line count (implementation default applies when unspecified). When the heuristic matches no lines, the filtered file contains the raw log's trailing N lines as a fallback so triage always has content to read.

### Transport shape: per-entry, NOT scalar top-level

`log_file` and `filtered_log_file` are fields of each individual `failing_checks[]` entry — they are **never** scalar top-level keys. A single run can fail multiple checks, each with its own distinctly-slugged raw and filtered file. The failing-checks table is emitted in addition to (not instead of) the existing `checks[]` table; `failing_checks[]` is the subset of `checks[]` whose `result` is `failure`, enriched with the two file paths.

Naming scheme, per failing check, under the run's artifact directory:

```text
artifacts/ci-runs/{run_id}/{slug}.log           # raw downloaded log         → log_file
artifacts/ci-runs/{run_id}/{slug}.filtered.log  # filtered error extraction  → filtered_log_file
```

### Worked example: `checks status` with two failing checks

```toon
status: success
operation: ci_status
pr_number: 123
overall_status: failure
check_count: 3
elapsed_sec: 210

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
verify / verify	completed	failure	180	https://github.com/org/repo/actions/runs/112	CI
lint	completed	failure	40	https://github.com/org/repo/actions/runs/113	Lint

failing_checks[2]{name,run_id,error_style,log_file,filtered_log_file}:
verify / verify	112	generic	artifacts/ci-runs/112/verify-verify.log	artifacts/ci-runs/112/verify-verify.filtered.log
lint	113	generic	artifacts/ci-runs/113/lint.log	artifacts/ci-runs/113/lint.filtered.log
```

### Worked example: `checks wait` with two failing checks

```toon
status: success
operation: ci_wait
pr_number: 123
final_status: failure
duration_sec: 210
polls: 7
elapsed_sec: 210

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
verify / verify	completed	failure	180	https://github.com/org/repo/actions/runs/112	CI
lint	completed	failure	40	https://github.com/org/repo/actions/runs/113	Lint

failing_checks[2]{name,run_id,error_style,log_file,filtered_log_file}:
verify / verify	112	generic	artifacts/ci-runs/112/verify-verify.log	artifacts/ci-runs/112/verify-verify.filtered.log
lint	113	generic	artifacts/ci-runs/113/lint.log	artifacts/ci-runs/113/lint.filtered.log
```

In both examples the two failing checks (`verify / verify` and `lint`) carry distinctly-slugged raw and filtered files under their respective `{run_id}` directories, demonstrating the multi-failure transport: one `failing_checks[]` row per failure, each with its own `log_file` and `filtered_log_file`.

---

## Issue Operations (github_ops.py / gitlab_ops.py)

### issue create

Create an issue. The body is supplied via the prepared-body / slot mechanism:
`issue prepare-body` allocates a script-owned scratch path, the caller writes the
markdown body to it with the native Write tool, then `issue create` consumes the
prepared file. No multi-line markdown crosses the shell boundary.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue prepare-body \
    --plan-id PLAN_ID --slot SLOT
# Write the issue body markdown to the returned path, then:
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create \
    --title "Bug: feature X not working" \
    --plan-id PLAN_ID \
    --slot SLOT \
    [--labels "bug,priority:high"]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--title` | Yes | Issue title |
| `--plan-id` | Yes | Plan identifier; binds the prepared-body scratch path. `NO_PLAN` routes a genuinely plan-less caller through the shared plan-less body store |
| `--slot` | No | Prepared-body slot selector (must match the `prepare-body` call) |
| `--labels` | No | Comma-separated labels |

**Success Output**:
```toon
status: success
operation: issue_create
issue_number: 789
issue_url: https://github.com/org/repo/issues/789
```

---

### issue view

View issue details.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue view \
    --issue 123
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--issue` | Yes | Issue number or URL |

**Success Output**:
```toon
status: success
operation: issue_view
issue_number: 123
issue_url: https://github.com/org/repo/issues/123
title: Bug in authentication flow
body: When users try to login...
author: username
state: open
created_at: 2025-01-15T10:30:00Z
updated_at: 2025-01-18T14:20:00Z

labels[2]:
- bug
- priority:high

assignees[1]:
- alice
```

**Field Mapping (GitHub vs GitLab)**:
| Field | GitHub | GitLab |
|-------|--------|--------|
| `issue_number` | `.number` | `.iid` |
| `issue_url` | `.url` | `.web_url` |
| `body` | `.body` | `.description` |
| `author` | `.author.login` | `.author.username` |
| `state` | `.state` (lowercase) | `.state` ("opened"→"open") |
| `labels[]` | `.labels[].name` | `.labels[]` (direct strings) |
| `assignees[]` | `.assignees[].login` | `.assignees[].username` |
| `milestone` | `.milestone.title` | `.milestone.title` |

---

### State-Transition Operations (summary)

The following subcommands all return the standard success shape (`status: success`, `operation: {op}`, plus a key identifier such as `pr_number`, `issue_number`, or `run_id`) and the standard error shape (`status: error`, `operation: {op}`, `error: ...`, `context: {underlying-cli-exit-reason}`). They accept only the listed required arguments and the optional flags noted inline.

**Merge-shaped rows are corroborated.** `pr merge`, `pr auto-merge`, `pr safe-merge`, and `pr merge-queue` never derive their success claim (`merged` / `disposition` / `enqueued`) from the CLI exit code — each establishes it from a re-read of provider state, and each fails closed. The normative statement lives once in [`pr-operations.md`](pr-operations.md) § "The corroborate-not-report contract"; the rows below record only the resulting fields.

| Subcommand | Required args | Optional flags | Notes |
|------------|---------------|----------------|-------|
| `pr merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy merge\|squash\|rebase` (default `merge`), `--delete-branch` | Success adds `strategy`, `merged: true`, `merge_corroboration`. Refuses (`status: error`) when the platform requires the queue/train. |
| `pr auto-merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy` | Schedules the merge without waiting; success adds `disposition` (`enabled`\|`enqueued`) and `disposition_detail`, plus `base_branch` on GitHub. There is no `enabled` key: which of the two dispositions the platform performed is not derivable from the exit code, so the verb reports the probed disposition instead. |
| `pr safe-merge` | _exactly one of_ `--pr-number` _or_ `--head` | `--strategy merge\|squash\|rebase` (default `merge`), `--delete-branch`, `--admin-merge-on-stuck-state` (GitHub-only), `--poll-timeout`, `--poll-interval` | Polls readiness then merges. Success adds `strategy`, `merge_path` (`polled_clean`\|`admin_fallback`), `polls`, `duration_sec`, `merged: true`, `merge_corroboration`. Refuses like `pr merge` when the platform requires the queue/train. The `--admin` stuck-state fallback is GitHub-only, gated by `--admin-merge-on-stuck-state` + provably-met ruleset; ignored on GitLab. |
| `pr update-branch` | _exactly one of_ `--pr-number` _or_ `--head` | — | Updates PR branch with base branch (GitHub REST API). |
| `pr close --pr-number N` | `--pr-number` | — | Closes without merging. |
| `pr ready --pr-number N` | `--pr-number` | — | Marks a draft as ready for review. |
| `pr edit --pr-number N` | `--pr-number`, `--plan-id` | `--title`, `--slot` | Edits title and/or body; the body comes from the `pr prepare-body --for edit` scratch file. At least one of `--title` or a prepared body must be supplied. |
| `pr merge-queue` | _exactly one of_ `--pr-number` _or_ `--head` | — | Enqueues into the platform merge queue / merge train; success adds a **corroborated** `enqueued: true`. The corroboration field is provider-scoped: GitHub adds `base_branch` and `enqueue_corroboration` (its pre-enqueue base-branch probe verdict); GitLab adds `merge_train_car_id` (the created train car, empty when the response carries no id) and **no** `enqueue_corroboration`. A target with no configured queue/train returns `status: error` on **both** providers rather than enqueuing. `enqueued: true` means the PR reached the queue — it is not a merge. Takes no `--strategy` / `--delete-branch`. |
| `checks rerun --run-id ID` | `--run-id` | — | Re-runs a failed workflow. |
| `checks logs --run-id ID` | `--run-id` | — | Success adds `log_lines` and `content` with the log output. |
| `issue close --issue N` | `--issue` | — | Closes the issue. |

---

## Exit Codes

| Code | Meaning | Output Stream |
|------|---------|---------------|
| 0 | Success | stdout |
| 1 | Error | stderr |

---

## Error Format

All errors follow the same TOON structure:

```toon
status: error
operation: <operation_name>
error: <error_message>
context: <additional_context>
```

**Common Error Types**:

| Error | Context |
|-------|---------|
| Authentication failed | CLI auth status returned non-zero |
| Tool not installed | which <tool> returned non-zero |
| Network error | Connection timed out |
| Invalid PR number | PR 999 not found |
| Permission denied | No write access to repository |
| `plan_not_found` | The `--plan-id` on a body-store verb does not resolve to an initialized plan. Carries `hint` + `hint_caveat` — see below |

### `plan_not_found` and the sentinel hint

A body-store verb whose `--plan-id` does not resolve returns the `plan_not_found`
envelope. It is the only error on this surface that carries advice, and it carries
the advice in **two** fields that must be read together:

```toon
status: error
error: plan_not_found
message: "plan 'typoed-id' not found: no status.json (expected at ...)"
plan_id: typoed-id
plan_dir: <resolved path>
hint: "Genuinely plan-less callers pass --plan-id NO_PLAN to route through the shared plan-less sentinel."
hint_caveat: "NO_PLAN is correct ONLY for callers that have no plan at all. If this id was meant to name a real plan, correct the id — do NOT substitute the sentinel."
```

The `hint` is correct **only** for a genuinely plan-less caller; `hint_caveat` states
the condition. Acting on the hint without checking the caveat turns every mistyped
plan id into a silent write against the shared sentinel directory, which is why the
two fields ship together and why a consumer must never surface one without the other.

---

## Provider Storage

CI provider identity and repo URL are stored in `marshal.json` under the `providers[]` array (see manage-config data-model). Tool authentication status is not persisted — use `ci_health verify-all` for a live check.
