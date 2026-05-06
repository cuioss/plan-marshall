# 00 — Cleanup / Precondition — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested (if applicable), and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (only when the change touches a script or executable surface), **documentation** (only when user- or developer-facing docs change).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-00-cleanup`
- [ ] Confirm `.plan/marshal.json` exists (run `marshall-steward` once if not)

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
- [ ] Implementation: run a final pass — `grep -rE '(EnterPlanMode|ExitPlanMode|AskUserQuestion|Agent\(subagent_type)' marketplace/bundles/*/skills/*/SKILL.md` and equivalent greps for hook event names, `~/.cache/plan-marshall/sessions`, and `.claude/` prose; confirm no hits remain (or each remaining hit is explicitly classified out-of-scope, e.g. inside fenced code blocks demonstrating a pattern)

## Quality Gate

Run **once**, after every task above is complete. Do not run between tasks — the gate is a single pre-ship checkpoint, not a per-task check.

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate"` with Bash timeout ≥ 600000 ms. Inspect the result TOON: `status` must be `success`; review `errors[]` for any failures.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "verify"` with Bash timeout ≥ 600000 ms. Same TOON inspection.
- [ ] Both must complete with `status: success` before proceeding to "Ship".

## Ship

- [ ] Commit all changes (conventional commits, one logical change per commit)
- [ ] Push the feature branch to `origin`
- [ ] Create the PR via the CI integration script: `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create ...` (do **not** use `gh pr create` directly — CLAUDE.md hard rule)
- [ ] **Wait 5 minutes** to give review automation (Gemini and any other review bots) time to post comments
- [ ] Fetch PR review comments via the CI integration script. For each comment:
  - If the comment identifies a real issue and the fix is sensible: apply the fix, commit, push.
  - If the comment is wrong or out of scope: do **not** silently skip. Ask the user first ("Skip review comment X because Y?"); only skip after the user approves.
- [ ] After review-comment handling, **wait for the user to review** the PR. Do not merge unilaterally.

## Close

- [ ] User has approved the PR
- [ ] Merge the PR via the CI integration script
- [ ] Switch to `main` locally: `git switch main`
- [ ] Pull latest: `git pull origin main`
- [ ] Mark this cluster's TODO as **completed** (add `> ✅ Completed: {YYYY-MM-DD}` immediately under the top-level heading)
