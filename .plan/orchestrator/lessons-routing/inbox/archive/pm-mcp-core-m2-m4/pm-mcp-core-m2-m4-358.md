envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:49Z

# Candidate lesson: sibling-repository paths written relative to the main checkout do not resolve from the plan worktree

- Source: Q-Gate finding 3501b4 (phase 3-outline, severity warning, resolution taken_into_account)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Candidate component: plan-marshall:phase-3-outline

## Observation

The plan ran with use_worktree=true, so phase 5 executes in `.plan/local/worktrees/{plan_id}/` of pm-mcp-core. The first outline addressed the sibling repositories (plan-marshall, plan-marshall-documentation) by paths relative to the main checkout: `git -C ../plan-marshall log -1`, `../plan-marshall-documentation/doc/roadmap/migration-inventory.csv`, and the link check `../plan-marshall-documentation/.claude/skills/doc-review/scripts/trace.py ../plan-marshall-documentation/doc .`. From the worktree root, `..` is `.plan/local/worktrees/`, so every one of these paths misses the sibling checkout. trace.py's relative links from `.` into the documentation would also be checked against the wrong tree, or skipped without any error.

## Resolution in this run

The outline added a "Sibling Checkouts" section. MAIN_ROOT, PM_REPO, DOC_REPO and WORKTREE_ABS are named relative to the main checkout root, resolved once at D1 and recorded with the pin in one decision-log entry. Every later command uses the recorded absolute paths. D1 creates a documentation link beside the worktree so relative links into the documentation are really checked, and D6 removes it.

## Possible rule (for orchestrator judgement)

In a multi-repository project where the sibling checkouts sit beside each other (CLAUDE.md "Links here are relative, also into the documentation (sibling paths)"), an outline for a use_worktree=true plan should never use `../{sibling}` paths in commands or verification steps. Resolve the sibling roots once, relative to the main checkout, and record them. An outline Q-Gate check could flag `../` paths in deliverables of worktree plans.
