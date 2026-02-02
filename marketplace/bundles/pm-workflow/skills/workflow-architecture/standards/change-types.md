# Change-Type Vocabulary

Defines the fixed vocabulary of change types used for solution outline routing. Change types describe the **intent** of a request and determine which agent handles the outline workflow.

---

## Core Principles

### Single Change-Type Per Request

Each request is assigned exactly **one** change type. The change type determines which agent handles the solution outline workflow.

### Orthogonality

Change types are orthogonal to other dimensions:

| Dimension | Purpose | Example |
|-----------|---------|---------|
| **Domain** | WHAT technology stack | Java, JavaScript, plugin-dev |
| **Profile** | WHAT aspect of work | implementation, module_testing, quality |
| **Change-type** | WHY you're doing it | analysis, feature, bug_fix |

### Agent-Based Handling

Each change type has:
- A **generic agent** in pm-workflow (baseline behavior for all domains)
- Optional **domain-specific agents** that override generic behavior

---

## Change-Type Definitions

| Key | Priority | Description | Expected Deliverable |
|-----|----------|-------------|---------------------|
| `analysis` | 1 | Investigate, research, understand | Findings report |
| `feature` | 2 | New functionality or component | New code |
| `enhancement` | 3 | Improve existing functionality | Modified code |
| `bug_fix` | 4 | Fix a defect or issue | Fixed code |
| `tech_debt` | 5 | Refactoring, cleanup, removal | Improved code |
| `verification` | 6 | Validate, check, confirm | Pass/fail report |

---

## Priority Ordering Rationale

```
analysis (1)     →  Understand first before acting
feature (2)      →  Build new things after understanding
enhancement (3)  →  Improve existing after building
bug_fix (4)      →  Fix defects in existing
tech_debt (5)    →  Clean up after functional changes
verification (6) →  Validate at end
```

---

## Detailed Definitions

### analysis (Priority 1)

**Purpose**: Investigate, research, or understand something before taking action.

**Indicators**:
- "analyze", "investigate", "understand", "research", "explore"
- "why is X happening", "how does X work"
- "find out", "determine", "assess"

**Deliverable**: Findings report with conclusions and recommendations.

**Example Requests**:
- "Analyze why login is slow"
- "Investigate the memory leak"
- "Understand how the plugin system works"

### feature (Priority 2)

**Purpose**: Create new functionality that doesn't currently exist.

**Indicators**:
- "add", "create", "new", "implement", "build"
- "introduce", "establish"
- Request describes functionality that doesn't exist

**Deliverable**: New code (files, classes, functions).

**Example Requests**:
- "Add user authentication"
- "Create a new API endpoint"
- "Implement dark mode"

### enhancement (Priority 3)

**Purpose**: Improve or extend existing functionality.

**Indicators**:
- "improve", "enhance", "extend", "update", "upgrade"
- "add to existing", "expand", "optimize"
- Request describes changes to something that exists

**Deliverable**: Modified code with improved functionality.

**Example Requests**:
- "Improve error messages in the login flow"
- "Add validation to the existing form"
- "Extend the search to support filters"

### bug_fix (Priority 4)

**Purpose**: Fix a defect, error, or incorrect behavior.

**Indicators**:
- "fix", "repair", "correct", "resolve"
- "bug", "error", "issue", "broken", "wrong"
- Describes something that should work but doesn't

**Deliverable**: Fixed code with minimal changes.

**Example Requests**:
- "Fix the login timeout issue"
- "Resolve the null pointer exception"
- "Correct the date formatting bug"

### tech_debt (Priority 5)

**Purpose**: Refactor, clean up, or improve code quality without changing behavior.

**Indicators**:
- "refactor", "restructure", "reorganize", "clean up"
- "remove", "delete", "deprecate", "migrate"
- "simplify", "consolidate"

**Deliverable**: Improved code structure, same behavior.

**Example Requests**:
- "Refactor the authentication module"
- "Remove deprecated API endpoints"
- "Migrate from callbacks to async/await"

### verification (Priority 6)

**Purpose**: Validate, verify, or confirm something is correct.

**Indicators**:
- "verify", "validate", "check", "confirm"
- "ensure", "test that", "make sure"
- Asks to confirm a state rather than change it

**Deliverable**: Pass/fail report with evidence.

**Example Requests**:
- "Verify the migration completed successfully"
- "Check that all endpoints return valid JSON"
- "Confirm the refactoring didn't break tests"

---

## What's NOT a Change-Type

### Testing

Testing is a **profile**, not a change-type.

- Request: "Add tests for the login module"
- Change-type: `feature` (creating new test files)
- Profile: `module_testing`

### Documentation

Documentation is a **domain** (pm-documents), not a change-type.

- Request: "Write documentation for the API"
- Domain: `pm-documents`
- Change-type: `feature` (creating new documentation)

### Quality

Quality (linting, formatting, JavaDoc) is a **profile**, not a change-type.

- Request: "Fix all JavaDoc warnings"
- Change-type: `tech_debt` (cleanup task)
- Profile: `quality`

---

## Agent Resolution

### Resolution Process

1. **Detect change_type** via LLM analysis (detect-change-type-agent)
2. **Check domain configuration** for override agent
3. **Fall back to generic** if no override configured

### Configuration in marshal.json

```json
"skill_domains": {
  "plan-marshall-plugin-dev": {
    "change_type_agents": {
      "feature": "pm-plugin-development:change-feature-outline-agent",
      "enhancement": "pm-plugin-development:change-enhancement-outline-agent"
    }
  }
}
```

### Fallback Pattern

If no domain-specific agent is configured:
- Use generic agent: `pm-workflow:change-{change_type}-agent`
- Example: `pm-workflow:change-feature-agent`

---

## Agent Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Generic | `pm-workflow:change-{change_type}-agent` | `pm-workflow:change-feature-agent` |
| Domain-specific | `{bundle}:change-{change_type}-outline-agent` | `pm-plugin-development:change-feature-outline-agent` |

---

## Detection Contract

The `detect-change-type-agent` returns:

```toon
status: success
plan_id: {plan_id}
change_type: enhancement
confidence: 90
reasoning: "Request describes improving existing plugin functionality"
```

### Confidence Thresholds

| Confidence | Meaning |
|------------|---------|
| 90-100 | High confidence, proceed |
| 70-89 | Medium confidence, proceed with note |
| < 70 | Low confidence, may need clarification |

---

## Related

- [task-executor-routing.md](task-executor-routing.md) - Profile-based executor routing
- [phases.md](phases.md) - Phase workflow overview
- `pm-workflow:detect-change-type-agent` - Detection agent
