# 00 — Cleanup / Precondition — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested (if applicable), and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (only when the change touches a script or executable surface), **documentation** (only when user- or developer-facing docs change).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Briefing

Read these documents in full **before touching anything**. Do not start the tasks below until you have done so.

- [ ] Read [`plan.md`](plan.md) — this cluster's design, scope, audit checklist, concrete cleanup tasks, and verification criteria
- [ ] Read [`../principles.md`](../principles.md) — cross-cutting rules that bind every cluster
- [ ] Read [`../README.md`](../README.md) — refactor overview, terminology, dependency graph
- [ ] Confirm to yourself you have understood the cluster's objective, the audit checklist, what is and is not in scope, and how this cluster relates to others
- [ ] If **any** part is unclear or contradictory, **stop and ask the user** before continuing — do not guess

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-00-cleanup`
- [ ] Confirm `.plan/marshal.json` exists. If not, run the wizard from a Claude Code session: type `/marshall-steward` (or invoke the skill: `Skill: plan-marshall:marshall-steward`) and walk through Step 1 (Init).

## Tasks

### 1. Move "Terminal Title Integration" out of `plan-marshall/SKILL.md`
- [ ] Implementation: cut the "Terminal Title Integration" section (~25 lines) from `marketplace/bundles/plan-marshall/skills/plan-marshall/SKILL.md` into `marketplace/bundles/plan-marshall/skills/plan-marshall/references/terminal-title.md`; leave a one-line pointer in the SKILL body
- [ ] Documentation: confirm the new reference file renders correctly and links resolve

### 2. Move "Session ID Resolver" out of `plan-marshall/SKILL.md`
- [ ] Implementation: cut the "Session ID Resolver" section (~15 lines) into `marketplace/bundles/plan-marshall/skills/plan-marshall/references/session-id-resolver.md`; leave a one-line pointer in the SKILL body
- [ ] Documentation: confirm the new reference file renders correctly

### 3. Rephrase tool-name rules in `plan-marshall/SKILL.md`
- [ ] Implementation: replace the three Claude-tool-name rules ("Never use `EnterPlanMode`/`ExitPlanMode`", "All user interactions use `AskUserQuestion`", "Never spawn `Agent(subagent_type=…)`") with platform-agnostic phrasings per the audit checklist in `plan.md`

### 4. Sweep remaining `plan-marshall` skills
- [ ] Implementation: grep every `marketplace/bundles/plan-marshall/skills/*/SKILL.md` for the audit-checklist patterns (Claude tool names in rules, hook descriptions, cache/session-resolver descriptions, `.claude/` prose outside platform-runtime call sites). Apply the same fixes per the audit checklist.

### 5. Sweep `pm-plugin-development`
- [ ] Implementation: grep skills for the audit patterns; apply fixes; pay extra attention to plugin-path references in `plugin-doctor`, `plugin-create`, `plugin-maintain`

### 6. Sweep remaining bundles
- [ ] Implementation: grep `pm-dev-java`, `pm-dev-java-cui`, `pm-dev-frontend`, `pm-dev-frontend-cui`, `pm-dev-oci`, `pm-dev-python`, `pm-documents`, `pm-requirements` skills for audit patterns; apply fixes

### 7. Final grep verification
- [ ] Implementation: run a final pass — `grep -rE '(EnterPlanMode|ExitPlanMode|AskUserQuestion|Agent\(subagent_type)' marketplace/bundles/*/skills/*/SKILL.md` and equivalent greps for hook event names (`SessionStart|UserPromptSubmit|PostToolUse|Notification|Stop|statusLine`), `~/.cache/plan-marshall/sessions`, and `.claude/` prose. Confirm no hits remain — or each remaining hit is explicitly classified out-of-scope (e.g. inside fenced code blocks demonstrating a pattern).
- [ ] Testing: run plugin-doctor's quality gate against the modified skills: `python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:doctor-marketplace quality-gate` (Bash timeout ≥ 600000 ms); inspect the result TOON for any new findings.

## Quality Gate

Run **once**, after every task above is complete. Do not run between tasks — the gate is a single pre-ship checkpoint, not a per-task check.

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate"` with Bash timeout ≥ 600000 ms. Inspect the result TOON: `status` must be `success`; review `errors[]` for any failures.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "verify"` with Bash timeout ≥ 600000 ms. Same TOON inspection.
- [ ] Both must complete with `status: success` before proceeding to "Ship".

## Ship

Use `PLAN_ID=refactor-00-cleanup` in the commands below as the body-tracking handle for the `tools-integration-ci` script.

- [ ] Commit all changes (conventional commits, one logical change per commit)
- [ ] Push the feature branch:
      ```
      git push -u origin feature/refactor-00-cleanup
      ```
- [ ] Allocate a body file for the PR description (returns a path under `.plan/temp/`):
      ```
      python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id refactor-00-cleanup
      ```
      Write the PR body (summary + test plan) to the returned path with the `Write` tool.
- [ ] Create the PR (CLAUDE.md hard rule: never use `gh pr create` directly):
      ```
      python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --title "refactor(cleanup): strip Claude-only plumbing prose from skill bodies" --plan-id refactor-00-cleanup --base main
      ```
      Capture the returned PR number into `PR=<n>` for subsequent calls.
- [ ] Wait 5 minutes for review automation (Gemini and other bots) — use the script (replaces blocking shell sleep):
      ```
      python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments --pr-number $PR --timeout 300
      ```
- [ ] Fetch unresolved comments and reviews:
      ```
      python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments --pr-number $PR --unresolved-only
      python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews  --pr-number $PR
      ```
- [ ] For each comment:
      - **Real issue + sensible fix** → apply it, commit, push, and reply to the thread:
        ```
        python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id refactor-00-cleanup --for edit --slot reply-<n>
        ```
        (write reply text to the returned path), then
        ```
        python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reply --pr-number $PR --plan-id refactor-00-cleanup --slot reply-<n>
        ```
      - **Wrong / out of scope** → do **not** silently skip. Ask the user first ("Skip comment X because Y?"); only skip after explicit approval.
- [ ] After all comment handling, **wait for the user to review** the PR. Do not merge unilaterally.

## Close

- [ ] User has approved the PR
- [ ] Merge with **squash** strategy and delete the branch:
      ```
      python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge --pr-number $PR --strategy squash --delete-branch
      ```
- [ ] Switch to `main` locally: `git switch main`
- [ ] Pull latest: `git pull origin main`
- [ ] Mark this cluster's TODO as **completed** (add `> ✅ Completed: {YYYY-MM-DD}` immediately under the top-level heading)
