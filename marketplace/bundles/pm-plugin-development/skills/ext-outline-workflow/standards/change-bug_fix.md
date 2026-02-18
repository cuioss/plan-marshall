# Change Bug Fix — Plugin Development Outline Instructions

Domain-specific instructions for `bug_fix` change type in the plugin development domain. Handles defect location and minimal fix with regression test.

## Additional Skills Required

The parent skill (outline-change-type) loads `pm-plugin-development:ext-outline-workflow`. Additionally load:

```
Skill: pm-plugin-development:plugin-architecture
```

## Step 1: Identify Bug Location

Analyze request to identify:

1. **Affected component** — which skill/agent/command has the bug
2. **Bug symptoms** — incorrect behavior
3. **Expected behavior** — what should happen

If request provides stack trace or error message, extract file paths and error location.

## Step 2: Targeted Search (No Full Inventory)

Use targeted Glob search to find the specific component:

```bash
Glob pattern: marketplace/bundles/**/{component_name}*
```

Read the affected component file directly.

## Step 3: Root Cause Analysis

Analyze the component:

1. **What's wrong** — the actual defect
2. **Why it happens** — triggering conditions
3. **Minimal fix** — smallest change to fix it

## Step 4: Build Deliverables

Always exactly 2 deliverables:

**Deliverable 1: Fix** — include extra section:

```markdown
**Root Cause:**
{Brief description of what's causing the bug}
```

**Deliverable 2: Regression Test** — test that would have caught this bug.

Validate all deliverables (ext-outline-workflow **Deliverable Validation**). Use verification commands from ext-outline-workflow **Verification Commands**.

## Constraints

### MUST NOT
- Use full inventory (targeted search only)
- Make unnecessary changes (minimal fix principle)
- Skip regression test deliverable

### MUST DO
- Document root cause
- Keep fix minimal and focused
- Always produce exactly 2 deliverables (fix + regression test)
- Use ext-outline-workflow shared constraints
