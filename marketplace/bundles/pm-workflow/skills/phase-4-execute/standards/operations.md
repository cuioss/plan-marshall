# Delegation Operations

Reference for executing common checklist items. The executor uses these patterns when encountering specific checklist items.

## Build Operations

### Maven Build
**Trigger**: "Run build", "maven", "mvn verify"

```
Task:
  subagent_type: pm-dev-builder:maven-builder
  prompt: Execute mvn clean verify, report results and coverage
```

### npm Build
**Trigger**: "npm build", "npm test"

```
Task:
  subagent_type: pm-dev-builder:npm-builder
  prompt: Execute npm build and test, report results and coverage
```

## Quality Operations

### Java Quality
**Trigger**: "quality check", "static analysis" (Java context)

```
Task:
  subagent_type: pm-dev-java:java-quality-agent
  prompt: Analyze code quality (checkstyle, PMD, SpotBugs)
```

### JavaScript Lint
**Trigger**: "lint", "eslint" (JavaScript context)

```bash
npm run lint
```

### Sonar Check
**Trigger**: "sonar", "quality gate"

```
mcp__sonarqube__search_sonar_issues_in_projects
```

## Implementation Operations

### Java Implementation
**Trigger**: "implement" (Java context)

```
Task:
  subagent_type: pm-dev-java:java-implement-agent
  prompt: Execute Task {N}: {name}, Goal: {goal}, Criteria: {list}
```

### JavaScript Implementation
**Trigger**: "implement" (JavaScript context)

```
Task:
  subagent_type: pm-dev-builder:npm-builder
  prompt: Execute Task {N}: {name}, Goal: {goal}, Criteria: {list}
```

## Git Operations

### Commit
**Trigger**: "commit", "create commit"

```
Skill: pm-workflow:workflow-integration-git
operation: commit
message: {from task title}
push: true
```

### Create PR
**Trigger**: "create PR", "pull request"

```bash
gh pr create --title "{task-title}" --body "$(cat <<'EOF'
## Summary
{description}

**Related Issue**: {issue-link}

## Changes
{key changes}

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## Plugin Operations

### Plugin Doctor
**Trigger**: "/plugin-doctor", "verify component"

```
SlashCommand: /plugin-doctor {type}={name}
```

## Documentation Operations

### JavaDoc Check
**Trigger**: "javadoc", "documentation check" (Java)

```
Task:
  subagent_type: pm-dev-java:java-fix-javadoc-agent
  prompt: Check JavaDoc coverage (report only)
```

### JSDoc Check
**Trigger**: "jsdoc", "documentation check" (JavaScript)

```bash
npm run docs:check
```

## Logging Operations

### Work Log Entry
**Trigger**: "**Log**:", "Record completion"

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
  work {plan_id} INFO "{what was done}: {outcome}"
```

### Lesson Learned
**Trigger**: "**Learn**:", "Capture lesson"

Only execute if unexpected behavior occurred. Follow `plan-marshall:script-runner` Error Handling workflow.
