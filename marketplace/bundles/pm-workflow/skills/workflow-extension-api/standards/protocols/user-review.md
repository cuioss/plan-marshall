# User Review Protocol

Standard protocol for mandatory user review after solution outline creation.

## Purpose

This protocol defines the **required interaction** between the `/plan-marshall` command and the user after the solution outline agent completes. User review ensures alignment before task creation.

**Rationale**: Solution outlines define deliverables that become tasks. User review ensures alignment before committing to implementation scope.

## Protocol Flow

```
[Solution Outline Agent] → [Command displays outline] → [User Review] → [Task Plan Agent]
                                                              ↓
                                                    [Request changes] → [Re-invoke Solution Outline Agent]
```

## Command Responsibility

After the solution outline agent completes, the `/plan-marshall` command MUST:

### Step 1: Display the Solution Outline

```markdown
## Solution Outline Created

📄 **Review your solution outline**: .plan/plans/{plan_id}/solution_outline.md

Please review the deliverables and architecture before proceeding.
```

### Step 2: Ask User via AskUserQuestion

Present options to the user:

| Option | Description | Next Action |
|--------|-------------|-------------|
| "Proceed to create tasks" | User approves outline | Continue to task plan agent |
| "Request changes" | User wants modifications | Capture feedback, re-invoke solution outline agent |

### Step 3: Loop Until Approval

This halt is **NOT OPTIONAL**. Task creation MUST NOT proceed without user confirmation.

```
while not approved:
    response = AskUserQuestion("Review and approve or request changes")
    if response == "Proceed":
        approved = true
    else:
        write each feedback point as Q-Gate finding (source: user_review)
        re-invoke 3-outline phase (reads findings at Step 1)
        display updated outline
```

## Re-Invocation via Q-Gate Findings

When user requests changes, write each feedback point as a Q-Gate finding and re-invoke the outline phase:

**Write findings**:
```bash
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase 3-outline --source user_review \
  --type triage --title "User: {feedback summary}" \
  --detail "{full feedback text}"
```

**Re-invoke**: The phase-3-outline skill reads unresolved findings at its Step 1 (Check for Unresolved Q-Gate Findings) and addresses them before re-running.

## Example Interaction

```
Command: "Solution outline created with 5 deliverables. Review .plan/plans/auth-feature/solution_outline.md"
User: "Deliverable 3 should use CDI instead of Spring - please update"

Command: Writes Q-Gate finding: "User: Use CDI instead of Spring for Deliverable 3"
Command: Re-invokes phase-3-outline (reads finding at Step 1)
Agent: Updates solution_outline.md, returns {status: success, deliverable_count: 5}

Command: "Solution outline updated. Please review changes."
User: "Looks good, proceed to create tasks"

Command: Invokes task plan agent
```

## Anti-Patterns

| Pattern | Problem |
|---------|---------|
| Auto-proceeding to task creation | User has no chance to review scope |
| Skipping review for "simple" plans | Definition of "simple" is subjective |
| Single-shot feedback | User may need multiple iterations |
| Not displaying outline location | User can't find what to review |

## Integration

**Implements**: Command responsibility in [Solution Outline Agent Contract](solution-outline-agent-contract.md)

**Callers**: `/plan-marshall action=outline` command

**Next Step**: [Task Plan Agent](task-plan-agent-contract.md) invocation after approval
