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

Change-type determines the outline workflow (how deliverables are discovered and structured). Profile determines task execution (which executor skill runs). A single deliverable with change-type `feature` may produce tasks with profiles `implementation` and `module_testing`. See [task-executors.md](task-executors.md) for profile→executor mapping.

### Skill-Based Handling

Each change type has:
- **Generic sub-skill instructions** in `plan-marshall:phase-3-outline/standards/` (baseline behavior)
- Optional **domain-specific sub-skill instructions** that override generic behavior
- Routing logic in `plan-marshall:phase-3-outline` (Steps 9-10) that resolves the appropriate instructions

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

| Type | Purpose | Key Indicators | Deliverable | Example |
|------|---------|---------------|-------------|---------|
| `analysis` | Investigate, research, understand | analyze, investigate, why, how, find out | Findings report | "Analyze why login is slow" |
| `feature` | New functionality | add, create, new, implement, build | New code | "Add user authentication" |
| `enhancement` | Improve existing | improve, extend, update, optimize | Modified code | "Extend search to support filters" |
| `bug_fix` | Fix defect | fix, repair, correct, bug, broken | Fixed code (minimal) | "Fix the login timeout issue" |
| `tech_debt` | Refactor without behavior change | refactor, clean up, remove, migrate, simplify | Same behavior, better structure | "Refactor the auth module" |
| `verification` | Validate correctness | verify, check, confirm, ensure | Pass/fail report | "Check all endpoints return valid JSON" |

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

### Recipes

Recipes are a **plan source**, not a change-type.

- A recipe provides its own `default_change_type` for deliverables
- Change_type is not detected via LLM — it comes from the recipe definition
- Example: "refactor-to-standards" recipe uses change_type=tech_debt
- Example: "refactor-to-test-standards" recipe uses change_type=tech_debt

See `plan-marshall:extension-api` standards/extension-contract.md#provides_recipes for the recipe contract.

---

## Skill-Based Routing

Change-type routing and domain skill resolution is handled by `plan-marshall:phase-3-outline` (Steps 9-10). See that skill for the full resolution process, marshal.json configuration, and fallback pattern.

**Architecture summary**:

| Component | Purpose |
|-----------|---------|
| `plan-marshall:phase-3-outline` (Steps 9-10) | Change-type routing and domain skill resolution |
| `phase-3-outline/standards/change-{type}.md` | Generic sub-skill instructions per change type |
| `{domain-skill}/standards/change-{type}.md` | Domain-specific sub-skill instructions (override) |

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

- [task-executors.md](task-executors.md) - Profile-based executor routing and shared workflow
- [phases.md](phases.md) - Phase workflow overview
- `plan-marshall:detect-change-type-agent` - Detection agent
