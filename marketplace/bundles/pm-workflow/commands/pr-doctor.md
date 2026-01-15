---
name: pr-doctor
description: Diagnose and fix PR issues (build, reviews, Sonar)
allowed-tools: Skill, Read, Edit, Glob, Grep, Bash, Task, SlashCommand
---

# PR Doctor Command

Diagnose and fix pull request issues with parameterized checks.

## CONTINUOUS IMPROVEMENT RULE

Record improvements: `Skill: plan-marshall:manage-lessons` with component `{type: "command", name: "pr-doctor", bundle: "pm-workflow"}`

## PARAMETERS

- **pr** (optional): Pull request number/URL (auto-detects current if not provided)
- **checks** (optional): build|reviews|sonar|all (default: all)
- **auto-fix** (optional): Auto-apply fixes without prompting (default: false)
- **wait** (optional): Wait for CI/Sonar to complete (default: true)
- **handoff** (optional): Handoff structure from previous phase (JSON)

## PREREQUISITES

Load required skills:
```
Skill: pm-workflow:workflow-integration-ci
Skill: pm-workflow:workflow-integration-sonar
Skill: pm-workflow:workflow-patterns
Skill: git-workflow
```

## WORKFLOW

### Step 0: Process Handoff Input

If `handoff` parameter provided: Parse JSON, extract artifacts/decisions/constraints.

### Step 1: Get PR Information

Auto-detect if not provided:
```bash
gh pr view --json number,title,state
```

Validate: PR must be numeric or valid GitHub URL.

### Step 2: Wait for Checks (If Requested)

If wait=true:
```bash
gh pr checks {pr} --json name,status,conclusion
```

Poll every 30 seconds. Timeout after 30 minutes with prompt: "[C]ontinue / [S]kip / [A]bort"

### Step 3: Diagnose Issues

Based on `checks` parameter:

**Build**: `gh pr checks` → BUILD_FAILURE if failed

**Reviews**: pr-workflow (Fetch Comments) → REVIEW_COMMENTS ({count})

**Sonar**: sonar-workflow (Fetch Issues) → SONAR_QUALITY ({count}/{severity})

### Step 4: Generate Diagnostic Report

```
═══════════════════════════════════════════════
PR Diagnostic Report: #{pr}
═══════════════════════════════════════════════

Build Status: {PASS|FAIL}
Review Comments: {count} unresolved
Sonar Issues: {count} ({severity breakdown})

Issues Found:
{per-category breakdown}

Recommended Actions:
{action list}
```

### Step 5: Fix Issues

Based on checks parameter:

**BUILD_FAILURE**: Run `SlashCommand(/maven-build-and-fix push)`

**REVIEW_COMMENTS**: Use pr-workflow (Handle Review). For each: triage → fix/explain/acknowledge.

**SONAR_QUALITY**: Use sonar-workflow (Fix Issues). For each: triage → fix/suppress (with approval if not auto-fix).

### Step 6: Verify and Commit

After fixes: Verify via /maven-build-and-fix, commit via git-workflow, push to PR branch.

### Step 7: Generate Handoff and Display Summary

Return structured result with handoff using `workflow-patterns/templates/handoff-standard.json` format.

Display: `✓ {fixed} fixed, ⚠ {remaining} remaining, → {next_action}`

## USAGE EXAMPLES

**Fix all PR issues:**
```
/pr-doctor pr=123
```

**Fix only Sonar issues:**
```
/pr-doctor pr=456 checks=sonar
```

**Auto-fix without prompts:**
```
/pr-doctor checks=all auto-fix
```

**Skip CI wait, fix current PR:**
```
/pr-doctor wait=false
```

## ARCHITECTURE

Delegates to skills:
```
/pr-doctor (orchestrator)
  ├─> pr-workflow skill (Fetch Comments, Handle Review)
  ├─> sonar-workflow skill (Fetch Issues, Fix Issues)
  ├─> git-workflow skill (Commit workflow)
  └─> SlashCommand(/maven-build-and-fix) [verification]
```

## RELATED

- **pr-workflow** skill - PR review comment handling
- **sonar-workflow** skill - Sonar quality issue handling
- **workflow-patterns** skill - Handoff protocols
- `/task-implement` command - Implement tasks before PR
