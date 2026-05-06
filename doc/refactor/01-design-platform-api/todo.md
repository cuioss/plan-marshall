# 01 — Design Platform API — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested, and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (mandatory for every task in this cluster — every operation has a script surface), **documentation** (whenever public contract changes).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-01-platform-api`
- [ ] Confirm cluster 00 (cleanup / precondition) has been merged to `main` and pulled locally

## Tasks

### 1. Skeleton: `platform-runtime` skill scaffolding
- [ ] Implementation: create `marketplace/bundles/plan-marshall/skills/platform-runtime/{SKILL.md, standards/, scripts/, scripts/__init__.py}`. SKILL.md describes the API contract (intent + invocation + 13 operations). Add the skill to `plan-marshall/.claude-plugin/plugin.json`.
- [ ] Testing: skill loads without error via `Skill: plan-marshall:platform-runtime`; plugin-doctor reports no rule violations
- [ ] Documentation: SKILL.md has all 13 operations enumerated and cross-references `standards/contract.md`

### 2. `runtime_base.py` (abstract base + shared helpers)
- [ ] Implementation: create `scripts/runtime_base.py` with abstract `Runtime` class declaring all 13 operations, plus shared TOON helpers (using `ref-toon-format` parser per cluster compliance section)
- [ ] Testing: unit tests in `test/plan-marshall/test_platform_runtime_base.py` confirm abstract methods are required, TOON helpers round-trip cleanly

### 3. `claude_runtime.py` — all 13 operations on Claude
- [ ] Implementation: implement `project initial-setup`, `session capture`, `permission configure`, `permission analyze`, `permission fix` (all 5 ops), `permission ensure-wildcards`, `permission ensure-steps`, `permission web-analyze`, `permission web-apply`, `session configure-display`, `metrics capture`, `subagent dispatch`, `health-check` for the Claude target
- [ ] Testing: per-operation unit tests covering success, error, and (where applicable) no-op paths; integration test that exercises a fresh-init flow end-to-end
- [ ] Documentation: any operation that diverges from `standards/contract.md` updates the contract

### 4. `opencode_runtime.py` — all 13 operations on OpenCode
- [ ] Implementation: implement the OpenCode side per the per-operation tables in `plan.md`. `session capture` and `metrics capture` return `no-op` per the documented `reason`/`alternative`. `session configure-display` returns `no-op`. All others have real implementations.
- [ ] Testing: per-operation unit tests including the no-op assertions for the three documented no-op operations; integration test exercises a fresh-init OpenCode flow

### 5. `claude_hook.py` — SessionStart hook (Claude only)
- [ ] Implementation: create `scripts/claude_hook.py` that reads `session_id` from stdin JSON and writes it to `$CLAUDE_ENV_FILE` as `$CLAUDE_CODE_SESSION_ID`
- [ ] Testing: unit test feeds a synthetic stdin payload and asserts the env-file contents

### 6. Router `platform_runtime.py`
- [ ] Implementation: create `scripts/platform_runtime.py` reading `runtime.target` from `.plan/marshal.json`, dispatching to `ClaudeRuntime` or `OpenCodeRuntime`, returning TOON. Handle `unknown_target` and `marshal_not_found` errors.
- [ ] Testing: dispatch tests for both targets; error-path tests for missing marshal.json and unknown target

### 7. Bootstrap glob discovery (target-aware)
- [ ] Implementation: implement the bootstrap path-discovery pseudocode in `plan.md` (cluster 01 "Bootstrap Invocation"). Convert the matched location to absolute path before invoking. Fallback to default `target=claude` when no `marshal.json` exists.
- [ ] Testing: unit tests for both target paths, including the OpenCode 7-root walk and the absolute-path conversion

### 8. Target-aware executor resolution
- [ ] Implementation: implement the per-target resolver tables documented in cluster 01 "Executor Resolution Per Target". The `tools-script-executor` generator emits the matching resolver template based on `runtime.target`. (Note: this is shared with cluster 03 work on `tools-script-executor`; coordinate.)
- [ ] Testing: resolver-table unit tests for both targets; integration test with a sample notation `plan-marshall:manage-status:manage_status get` resolving correctly on each target

### 9. `standards/contract.md` (TOON schemas)
- [ ] Implementation: write per-operation TOON schemas for `success`, `error`, and `no-op` paths. Reference `ref-toon-format` parser.
- [ ] Documentation: cross-link from SKILL.md and from `plan.md` once published

### 10. `standards/no-op-policy.md`
- [ ] Implementation: write the no-op policy document (status, reason, alternative format; caller behaviour requirement)
- [ ] Documentation: cross-link from `principles.md` and SKILL.md

## Quality Gate

After every task is done:

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate"` with Bash timeout ≥ 600000 ms. Inspect the result TOON: `status` must be `success`; review `errors[]` for any failures.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "verify"` with Bash timeout ≥ 600000 ms. Same TOON inspection.
- [ ] Both must complete with `status: success` before proceeding to "Ship".

## Ship

- [ ] Commit all changes (conventional commits, one logical change per commit)
- [ ] Push the feature branch to `origin`
- [ ] Create the PR via the CI integration script: `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create ...`
- [ ] **Wait 5 minutes** for review automation
- [ ] Fetch PR review comments. For each comment:
  - Real issue + sensible fix → apply, commit, push.
  - Wrong / out of scope → ask the user before skipping.
- [ ] After review-comment handling, **wait for the user to review** the PR.

## Close

- [ ] User has approved the PR
- [ ] Merge the PR via the CI integration script
- [ ] `git switch main && git pull origin main`
- [ ] Mark this cluster's TODO as **completed** (add `> ✅ Completed: {YYYY-MM-DD}` under the top-level heading)
