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

## PR Operations (github.py / gitlab.py)

Every PR subcommand returns the standard envelope: success shape (`status: success`, `operation: {op}`, plus the identifiers listed in the "Response fields" column) and error shape (`status: error`, `operation: {op}`, `error: ...`, `context: {cli exit reason}`).

| Subcommand | Required args | Optional flags | Response fields |
|------------|---------------|----------------|-----------------|
| `pr create` | `--title`, `--body` | `--base` (default `main`), `--draft` | `pr_number`, `pr_url` |
| `pr view` | — (uses current branch) | — | `pr_number`, `pr_url`, `state`, `title`, `head_branch`, `base_branch`, `is_draft`, `mergeable`, `merge_state`, `review_decision` |
| `pr list` | — | `--head {branch}`, `--state open\|closed\|all` (default `open`) | `total`, `state_filter`, `head_filter`, `prs[N]{number,url,title,state,head_branch,base_branch}` |
| `pr reply` | `--pr-number`, `--body` | — | `pr_number` |
| `pr resolve-thread` | `--thread-id` (GitLab also requires `--pr-number`) | — | `thread_id` |
| `pr thread-reply` | `--pr-number`, `--thread-id`, `--body` | — | `pr_number`, `thread_id` |
| `pr reviews` | `--pr-number` | — | `pr_number`, `review_count`, `reviews[N]{user,state,submitted_at}` |
| `pr comments` | `--pr-number` | `--unresolved-only` | `provider`, `pr_number`, `total`, `unresolved`, `comments[N]{id,author,body,path,line,resolved,created_at}` |
| `pr update-branch` | `--pr-number` | — | `pr_number` |

### Provider Field Mapping

The PR operations normalize responses from `gh` (JSON) and `glab` (JSON) into the same shape. Mappings:

- **Top-level identifiers**: `pr_number` ← `.number` (GitHub) / `.iid` (GitLab); `pr_url` ← `.url` / `.web_url`; `state` lower-cased ("opened" → "open"); `title`, `head_branch` ← `.headRefName` / `.source_branch`; `base_branch` ← `.baseRefName` / `.target_branch`; `is_draft` ← `.isDraft` / `.draft`; `mergeable` ← `.mergeable` / `.merge_status`; `merge_state` ← `.mergeStateStatus` (GitHub only); `review_decision` ← `.reviewDecision` / `.approved_by` (mapped).
- **`pr list` CLI differences**: GitHub `gh pr list --head {branch} --state open|closed|all --json number,url,...`; GitLab `glab mr list --source-branch {branch} --state opened|closed|all --output json`.
- **`pr resolve-thread`**: GitHub uses the GraphQL `resolveReviewThread` mutation with a self-contained thread node id (e.g. `PRRT_kwDO...`), so `--pr-number` is ignored; GitLab uses REST `PUT discussions/:id` and requires both `--pr-number` and the discussion id.
- **`pr thread-reply`**: GitHub uses GraphQL `addPullRequestReviewComment` with `inReplyTo` set to the comment node id (the PR node id is fetched internally); GitLab uses REST `POST discussions/:id/notes` and does not require a PR node id.
- **`pr comments` field mapping**: `id` ← `comments.nodes[].id` / `notes[].id`; `author` ← `author.login` / `author.username`; `body` ← `body`; `path` ← `reviewThreads.nodes[].path` / `position.new_path`; `line` ← `reviewThreads.nodes[].line` / `position.new_line`; `resolved` ← `isResolved` / `resolved`.

---

## CI Operations (github.py / gitlab.py)

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

```
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

## Issue Operations (github.py / gitlab.py)

### issue create

Create an issue.

**Command**:
```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci issue create \
    --title "Bug: feature X not working" \
    --body "Description of the issue" \
    [--labels "bug,priority:high"]
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `--title` | Yes | Issue title |
| `--body` | Yes | Issue description |
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

| Subcommand | Required args | Optional flags | Notes |
|------------|---------------|----------------|-------|
| `pr merge --pr-number N` | `--pr-number` | `--strategy merge\|squash\|rebase` (default `merge`), `--delete-branch` | Success adds `strategy`. |
| `pr auto-merge --pr-number N` | `--pr-number` | `--strategy` | Enables auto-merge when all checks pass; success adds `enabled: true`. |
| `pr update-branch --pr-number N` | `--pr-number` | — | Updates PR branch with base branch (GitHub REST API). |
| `pr close --pr-number N` | `--pr-number` | — | Closes without merging. |
| `pr ready --pr-number N` | `--pr-number` | — | Marks a draft as ready for review. |
| `pr edit --pr-number N` | `--pr-number` | `--title`, `--body` | Edits title and/or body. |
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

---

## Provider Storage

CI provider identity and repo URL are stored in `marshal.json` under the `providers[]` array (see manage-config data-model). Tool authentication status is not persisted — use `ci_health verify-all` for a live check.
