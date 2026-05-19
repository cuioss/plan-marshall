# 06 — Developer Workflow — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested, and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (whenever a script or workflow is added), **documentation** (whenever the developer-facing inner-loop docs change).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Briefing

Read these documents in full **before touching anything**. Do not start the tasks below until you have done so.

- [ ] Read [`plan.md`](plan.md) — this cluster's inner-loop options (Option A deploy-to-global, Option B `OPENCODE_CONFIG_DIR` with plural staging, Option C `opencode-marketplace install`), the `sync-opencode` script design, and the comparison table
- [ ] Read [`../02-build-system/plan.md`](../02-build-system/plan.md) — the developer workflow consumes the generator's output (singular layout); you must know what is produced and how
- [ ] Read [`../principles.md`](../principles.md) — cross-cutting rules
- [ ] Read [`../README.md`](../README.md) — refactor overview, terminology, dependency graph
- [ ] Confirm to yourself you have understood the singular → plural rename requirement, the `OPENCODE_CONFIG_DIR` precedence caveat (project `.opencode/` shadows it), and which option is recommended for which use case
- [ ] If **any** part is unclear or contradictory, **stop and ask the user** before continuing — do not guess

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-06-developer-workflow`
- [ ] Confirm cluster 02 (build system) has been merged to `main` and pulled locally — the OpenCode workflow depends on the generator producing `target/opencode/`

## Tasks

### 1. `sync-opencode` skill skeleton
- [ ] Implementation: create `marketplace/bundles/plan-marshall/skills/sync-opencode/{SKILL.md, scripts/sync_opencode.py}`. Register in `plan-marshall/.claude-plugin/plugin.json`.
- [ ] Documentation: SKILL.md describes source/destination, namespacing, singular → plural rename, `--source` / `--target` / `--bundles` / `--dry-run` flags

### 2. `sync_opencode.py` implementation
- [ ] Implementation: implement the deploy script per cluster 06 "Deployment Script Design" — rsync `target/opencode/skill/` → `{target}/skills/`, `target/opencode/agent/` → `{target}/agents/`, `target/opencode/command/` → `{target}/commands/` with `--delete`. Default `--target` = `~/.config/opencode/`. Honor `--dry-run` and `--bundles`.
- [ ] Testing: unit tests for path-rename mapping, --dry-run mode, --bundles subset; integration test against a fixture `target/opencode/` directory

### 3. Document Claude Code workflow
- [ ] Documentation: confirm `doc/developer-workflow.md` (produced by cluster 04 porting) accurately documents the existing Claude Code inner loop — `vim` source → `sync-plugin-cache` → test. No code changes here unless the existing workflow is broken.

### 4. Document Option A — Deploy to global user directory
- [ ] Documentation: in `doc/developer-workflow.md`, document the `sync-opencode` deploy path: generate, then run the script via the canonical executor notation `python3 .plan/execute-script.py plan-marshall:sync-opencode:sync_opencode --source target/opencode/ --target ~/.config/opencode/`
- [ ] Testing: smoke-run the documented commands end-to-end on a developer machine

### 5. Document Option B — `OPENCODE_CONFIG_DIR` with plural staging
- [ ] Documentation: document the singular → plural staging copy and `OPENCODE_CONFIG_DIR=...stage opencode` invocation. Spell out the precedence caveat (project-local `.opencode/` overrides the env-var directory).
- [ ] Testing: smoke-run the staged workflow end-to-end

### 6. Document Option C — `opencode-marketplace install` from a local file URL
- [ ] Documentation: document `opencode-marketplace install /path/to/target/opencode/ --scope user` as a way to validate the end-user install path during development
- [ ] Testing: smoke-run against a fresh test machine or container

### 7. Comparison table + recommendations
- [ ] Documentation: include the comparison table from cluster 06 (Edit source / Build step / Deploy step / Reload / Iteration time / Isolation / Namespacing / Best for) in `doc/developer-workflow.md`. Recommend Option A or B for daily; C for distribution validation.

### 8. Repo-root README updates
- [ ] Documentation: update repo-root `README.md` "Working in This Repository" / "Multi-Assistant Support" sections so contributors find the developer workflow doc on first read

## Quality Gate

Run **once**, after every task above is complete. Do not run between tasks — the gate is a single pre-ship checkpoint, not a per-task check.

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "quality-gate"` (Bash timeout ≥ 600000 ms). Inspect TOON.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run --command-args "verify"` (Bash timeout ≥ 600000 ms).
- [ ] Both `status: success` before "Ship".

## Ship

Use `PLAN_ID=refactor-06-developer-workflow` in the commands below. Capture the PR number into `PR=<n>` after `ci pr create`.

- [ ] Commit all changes (conventional commits)
- [ ] Push the feature branch:
      `git push -u origin feature/refactor-06-developer-workflow`
- [ ] Allocate a body file:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id refactor-06-developer-workflow`
      (write PR body to the returned path)
- [ ] Create the PR:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --title "feat(dev-workflow): sync-opencode skill and three OpenCode inner-loop options" --plan-id refactor-06-developer-workflow --base main`
- [ ] Wait 5 minutes for review automation:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments --pr-number $PR --timeout 300`
- [ ] Fetch unresolved comments and reviews:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments --pr-number $PR --unresolved-only`
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews  --pr-number $PR`
- [ ] For each unresolved comment (use `thread_id` from `ci pr comments` output):
      - **Real issue + sensible fix** → apply, commit, push; reply to the inline thread:
        `... pr prepare-comment --plan-id refactor-06-developer-workflow --for thread-reply --slot reply-<n>` (write text), then
        `... pr thread-reply --pr-number $PR --thread-id <THREAD_ID> --plan-id refactor-06-developer-workflow --slot reply-<n>`,
        then `... pr resolve-thread --thread-id <THREAD_ID>` once the fix has landed.
        For PR-level (non-inline) comments use `pr prepare-comment --for reply` + `pr reply --pr-number $PR ...` instead.
      - **Wrong / out of scope** → ask the user before skipping.
- [ ] After comment handling, **wait for the user to review** the PR.

## Close

- [ ] User has approved the PR
- [ ] Merge with squash + delete branch:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge --pr-number $PR --strategy squash --delete-branch`
- [ ] `git switch main && git pull origin main`
- [ ] Mark this TODO as **completed**
