# User Review Protocol

Standard protocol for mandatory user review after solution outline creation.

## Purpose

This protocol defines the **required interaction** between the `/plan-manage` command and the user after the solution outline agent completes. User review ensures alignment before task creation.

**Rationale**: Solution outlines define deliverables that become tasks. User review ensures alignment before committing to implementation scope.

## Protocol Flow

```
[Solution Outline Agent] → [Command displays outline] → [User Review] → [Task Plan Agent]
                                                              ↓
                                                    [Request changes] → [Re-invoke Solution Outline Agent]
```

## Command Responsibility

After the solution outline agent completes, the `/plan-manage` command MUST:

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
    feedback = AskUserQuestion("Review and approve or request changes")
    if feedback == "Proceed":
        approved = true
    else:
        invoke 2-outline phase agent with feedback parameter
        display updated outline
```

## Re-Invocation with Feedback

When user requests changes, re-invoke the solution outline agent with the `feedback` parameter:

**Input to Solution Outline Agent**:

| Parameter | Value |
|-----------|-------|
| `plan_id` | Same plan identifier |
| `feedback` | User's change request (captured from AskUserQuestion) |

The agent incorporates feedback into the existing solution_outline.md and re-validates.

## Example Interaction

```
Command: "Solution outline created with 5 deliverables. Review .plan/plans/auth-feature/solution_outline.md"
User: "Deliverable 3 should use CDI instead of Spring - please update"

Command: Re-invokes solution outline agent with feedback="Deliverable 3 should use CDI instead of Spring"
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

**Callers**: `/plan-manage action=outline` command

**Next Step**: [Task Plan Agent](task-plan-agent-contract.md) invocation after approval
